using System.Text.Json;
using Azure;
using Azure.Data.Tables;
using Woodgrove.Web.Models;

namespace Woodgrove.Web.Services;

/// <summary>Durable single-warehouse transactions and exact-request idempotency receipts.</summary>
public sealed class TableStorageDataService(TableServiceClient client)
{
    private const string Partition = "store-001";
    private readonly TableClient table = client.GetTableClient("Commerce");

    /// <summary>Reads the current catalog from the Azure backend.</summary>
    public async Task<Product[]> ProductsAsync(CancellationToken cancellation = default)
    {
        var products = new List<Product>();
        await foreach (var entity in table.QueryAsync<TableEntity>(
            "PartitionKey eq 'store-001' and RowKey ge 'product-' and RowKey lt 'product.'",
            cancellationToken: cancellation))
            products.Add(Read<Product>(entity));
        if (products.Count == 0)
            throw new PolicyException("The catalog has not been installed.");
        return products.ToArray();
    }

    /// <summary>Reads one order; callers must enforce ownership before returning it.</summary>
    public async Task<GroceryOrder> OrderAsync(string id, CancellationToken cancellation = default) =>
        Read<GroceryOrder>((await table.GetEntityAsync<TableEntity>(
            Partition, Key(id), cancellationToken: cancellation)).Value);

    /// <summary>Lists only the owning customer's orders, or all orders for the trusted worker.</summary>
    public async Task<GroceryOrder[]> OrdersAsync(string? customerId, CancellationToken cancellation = default)
    {
        var result = new List<GroceryOrder>();
        var filter = "PartitionKey eq 'store-001' and RowKey ge 'order-' and RowKey lt 'order.'";
        if (customerId is not null)
            filter += " and " + TableClient.CreateQueryFilter($"CustomerId eq {customerId}");
        await foreach (var entity in table.QueryAsync<TableEntity>(filter, cancellationToken: cancellation))
            result.Add(Read<GroceryOrder>(entity));
        return result.OrderByDescending(x => x.CreatedAt).ToArray();
    }

    /// <summary>Creates a draft, deduplicating the request and atomically enforcing the daily order limit.</summary>
    public async Task<GroceryOrder> CreateAsync(
        string customerId, CartLine[] lines, string slot, string[] exclusions, string requestId,
        CancellationToken cancellation = default)
    {
        CommercePolicy.ValidSlot(slot);
        var products = await ProductsAsync(cancellation);
        var total = CommercePolicy.Price(lines, products);
        var id = CommercePolicy.Hash(customerId + ":" + requestId)[..24];
        var row = "order-" + id;
        var existing = await table.GetEntityIfExistsAsync<TableEntity>(Partition, row, cancellationToken: cancellation);
        if (existing.HasValue && existing.Value is { } existingOrder)
        {
            var previous = Read<GroceryOrder>(existingOrder);
            CommercePolicy.Owns(previous, customerId);
            if (!previous.Lines.SequenceEqual(lines) || previous.Slot != slot ||
                !previous.ExcludedAllergens.SequenceEqual(exclusions))
                throw new PolicyException("The create request ID was already used with different content.");
            return previous;
        }
        var now = DateTimeOffset.UtcNow;
        var dayKey = "count-" + now.ToString("yyyyMMdd");
        var counter = await table.GetEntityIfExistsAsync<TableEntity>(Partition, dayKey, cancellationToken: cancellation);
        var counterEntity = counter.HasValue ? counter.Value : null;
        var count = counterEntity is not null ? counterEntity.GetInt32("Count")!.Value : 0;
        if (count >= 50)
            throw new PolicyException("The synthetic daily order limit has been reached.");
        var order = new GroceryOrder(
            id, customerId, lines, slot, total, exclusions, "Draft", 0, 0, null,
            [new(now, "Draft", "Synthetic grocery cart created.")], now);
        var countEntity = new TableEntity(Partition, dayKey) { ["Count"] = count + 1 };
        var operations = new List<TableTransactionAction>
        {
            new(TableTransactionActionType.Add, Entity(row, order, customerId)),
            counterEntity is not null
                ? new(TableTransactionActionType.UpdateReplace, countEntity, counterEntity.ETag)
                : new(TableTransactionActionType.Add, countEntity)
        };
        try { await table.SubmitTransactionAsync(operations, cancellation); }
        catch (RequestFailedException ex) when (ex.Status is 409 or 412)
        {
            throw new PolicyException("A concurrent create changed the order counter. Refresh before retrying.");
        }
        return order;
    }

    /// <summary>Atomically changes an order, optional stock rows and its payload-bound action receipt.</summary>
    public async Task<GroceryOrder> ChangeAsync(
        string id, string? customerId, string actionKey, string payload,
        Func<GroceryOrder, Product[], (GroceryOrder Order, Product[] Stock)> change,
        CancellationToken cancellation = default)
    {
        var entity = (await table.GetEntityAsync<TableEntity>(Partition, Key(id), cancellationToken: cancellation)).Value;
        var order = Read<GroceryOrder>(entity);
        if (customerId is not null)
            CommercePolicy.Owns(order, customerId);
        var receiptKey = "receipt-" + CommercePolicy.Hash(id + ":" + actionKey);
        var payloadHash = CommercePolicy.Hash(payload);
        var receipt = await table.GetEntityIfExistsAsync<TableEntity>(Partition, receiptKey, cancellationToken: cancellation);
        if (receipt.HasValue && receipt.Value is { } savedReceipt)
        {
            if (savedReceipt.GetString("PayloadHash") != payloadHash)
                throw new PolicyException("An action key was reused with different content.");
            return order;
        }
        var stockEntities = new List<TableEntity>();
        await foreach (var product in table.QueryAsync<TableEntity>(
            "PartitionKey eq 'store-001' and RowKey ge 'product-' and RowKey lt 'product.'",
            cancellationToken: cancellation))
            stockEntities.Add(product);
        var (updated, stocks) = change(order, stockEntities.Select(Read<Product>).ToArray());
        if (updated.Id != order.Id || updated.CustomerId != order.CustomerId || updated.Version != order.Version + 1)
            throw new InvalidOperationException("The mutation violated immutable identity or order versioning.");
        if (updated.Timeline.Length > 160)
            throw new PolicyException("The bounded timeline is full; operator review is required.");
        var actions = new List<TableTransactionAction>
        {
            new(TableTransactionActionType.UpdateReplace, Entity(Key(id), updated, updated.CustomerId), entity.ETag),
            new(TableTransactionActionType.Add, new TableEntity(Partition, receiptKey)
            {
                ["PayloadHash"] = payloadHash, ["OrderId"] = id, ["At"] = DateTimeOffset.UtcNow
            })
        };
        foreach (var stock in stocks)
        {
            var original = stockEntities.Single(x => x.RowKey == "product-" + stock.Id.ToString("D3"));
            if (stock.Stock < 0)
                throw new PolicyException("A reservation cannot make stock negative.");
            actions.Add(new(TableTransactionActionType.UpdateReplace, Entity(original.RowKey, stock), original.ETag));
        }
        try { await table.SubmitTransactionAsync(actions, cancellation); }
        catch (RequestFailedException ex) when (ex.Status is 409 or 412)
        {
            var committed = await table.GetEntityIfExistsAsync<TableEntity>(
                Partition, receiptKey, cancellationToken: cancellation);
            if (!committed.HasValue || committed.Value is not { } committedReceipt ||
                committedReceipt.GetString("PayloadHash") != payloadHash)
                throw new PolicyException("Concurrent state changed. No unverified action was replayed.");
            return await OrderAsync(id, cancellation);
        }
        return updated;
    }

    /// <summary>Acquires or renews a 30-second per-order worker lease using an exact ETag.</summary>
    public async Task<bool> LeaseAsync(string id, string owner, CancellationToken cancellation)
    {
        var key = "lease-" + Key(id);
        var current = await table.GetEntityIfExistsAsync<TableEntity>(Partition, key, cancellationToken: cancellation);
        var currentEntity = current.HasValue ? current.Value : null;
        if (currentEntity is not null && currentEntity.GetDateTimeOffset("Until") > DateTimeOffset.UtcNow &&
            currentEntity.GetString("Owner") != owner)
            return false;
        var entity = new TableEntity(Partition, key)
        {
            ["Owner"] = owner, ["Until"] = DateTimeOffset.UtcNow.AddSeconds(30)
        };
        try
        {
            if (currentEntity is not null)
                await table.UpdateEntityAsync(entity, currentEntity.ETag, TableUpdateMode.Replace, cancellation);
            else
                await table.AddEntityAsync(entity, cancellation);
            return true;
        }
        catch (RequestFailedException ex) when (ex.Status is 409 or 412) { return false; }
    }

    internal static TableEntity Entity<T>(string key, T value, string? customer = null)
    {
        var json = JsonSerializer.Serialize(value);
        if (System.Text.Encoding.Unicode.GetByteCount(json) > 60_000)
            throw new PolicyException("The bounded business record is too large.");
        var entity = new TableEntity(Partition, key) { ["Json"] = json };
        if (customer is not null) entity["CustomerId"] = customer;
        return entity;
    }

    internal static T Read<T>(TableEntity entity) =>
        JsonSerializer.Deserialize<T>(entity.GetString("Json")!)
        ?? throw new InvalidOperationException("A stored business record is invalid.");

    private static string Key(string id) =>
        id.Length == 24 && id.All(char.IsAsciiHexDigit) ? "order-" + id
        : throw new PolicyException("Invalid order identifier.");
}
