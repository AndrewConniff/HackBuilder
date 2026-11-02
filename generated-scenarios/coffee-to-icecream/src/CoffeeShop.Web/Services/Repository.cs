using System.Text.Json;
using Azure;
using Azure.Core;
using Azure.Data.Tables;
using CoffeeShop.Web.Models;

namespace CoffeeShop.Web.Services;

/// <summary>Persists isolated snapshots, immutable import receipts, orders and reviewable closes.</summary>
public interface IRepository
{
    /// <summary>Reads one store's current evidence.</summary>
    Task<StoreSnapshot> ReadAsync(string storeId, CancellationToken ct);
    /// <summary>Reads one internal order.</summary>
    Task<StoredOrder?> GetOrderAsync(string storeId, string draftId, CancellationToken ct);
    /// <summary>Creates a draft once, including replay handling.</summary>
    Task<StoredOrder> AddOrderAsync(Order order, CancellationToken ct);
    /// <summary>Updates only the order version read by the caller.</summary>
    Task<bool> ReplaceOrderAsync(StoredOrder order, CancellationToken ct);
    /// <summary>Commits snapshot and import receipt in a single store-partition transaction.</summary>
    Task<StoreSnapshot> ImportAsync(StoreSnapshot snapshot, string expectedVersion, string importId, CancellationToken ct);
    /// <summary>Persists a generated report awaiting human review.</summary>
    Task SaveCloseAsync(CloseResult result, CancellationToken ct);
    /// <summary>Reads a persisted report with its concurrency token.</summary>
    Task<StoredClose> GetCloseAsync(string id, CancellationToken ct);
    /// <summary>Finalizes only the report version read by the reviewer.</summary>
    Task ReviewCloseAsync(StoredClose report, CancellationToken ct);
}

/// <summary>Uses managed identity for all business storage and ETags for optimistic concurrency.</summary>
public sealed class TableRepository(IConfiguration configuration, TokenCredential credential) : IRepository
{
    private readonly TableClient client = new(new Uri(configuration["Storage:Endpoint"]
        ?? throw new InvalidOperationException("Storage endpoint not installed.")), "IceCreamBackOffice", credential);

    /// <inheritdoc />
    public async Task<StoreSnapshot> ReadAsync(string storeId, CancellationToken ct)
    {
        var entity = await client.GetEntityIfExistsAsync<TableEntity>(storeId, "snapshot", cancellationToken: ct);
        if (!entity.HasValue) throw new KeyNotFoundException();
        return JsonSerializer.Deserialize<StoreSnapshot>(entity.Value!.GetString("Payload"))!;
    }

    /// <inheritdoc />
    public async Task<StoredOrder?> GetOrderAsync(string storeId, string draftId, CancellationToken ct)
    {
        var entity = await client.GetEntityIfExistsAsync<TableEntity>(storeId, $"order-{draftId}", cancellationToken: ct);
        return entity.HasValue ? new(JsonSerializer.Deserialize<Order>(entity.Value!.GetString("Payload"))!,
            entity.Value.ETag.ToString()) : null;
    }

    /// <inheritdoc />
    public async Task<StoredOrder> AddOrderAsync(Order order, CancellationToken ct)
    {
        try
        {
            await client.AddEntityAsync(Entity(order), ct);
        }
        catch (RequestFailedException error) when (error.Status == 409) { /* Idempotent draft replay. */ }
        return await GetOrderAsync(order.StoreId, order.DraftId, ct) ?? throw new InvalidOperationException();
    }

    /// <inheritdoc />
    public async Task<bool> ReplaceOrderAsync(StoredOrder order, CancellationToken ct)
    {
        try
        {
            await client.UpdateEntityAsync(Entity(order.Value), new ETag(order.ETag), TableUpdateMode.Replace, ct);
            return true;
        }
        catch (RequestFailedException error) when (error.Status == 412) { return false; }
    }

    /// <inheritdoc />
    public async Task<StoreSnapshot> ImportAsync(StoreSnapshot snapshot, string expectedVersion, string importId,
        CancellationToken ct)
    {
        var storeId = snapshot.Store.StoreId;
        var prior = await client.GetEntityIfExistsAsync<TableEntity>(storeId, $"import-{importId}",
            cancellationToken: ct);
        if (prior.HasValue) throw new InvalidOperationException("Import already committed; refresh current evidence.");
        var current = (await client.GetEntityAsync<TableEntity>(storeId, "snapshot", cancellationToken: ct)).Value;
        var old = JsonSerializer.Deserialize<StoreSnapshot>(current.GetString("Payload"))
            ?? throw new InvalidOperationException("Invalid persisted snapshot.");
        if (old.Version != expectedVersion) throw new InvalidOperationException("Stale import version.");
        var replacement = new TableEntity(storeId, "snapshot") { ["Payload"] = JsonSerializer.Serialize(snapshot) };
        await client.SubmitTransactionAsync([
            new(TableTransactionActionType.UpdateReplace, replacement, current.ETag),
            new(TableTransactionActionType.Add, new TableEntity(storeId, $"import-{importId}")
            {
                ["BusinessDate"] = snapshot.Ledger.Date.ToString("yyyy-MM-dd")
            })
        ], ct);
        return snapshot;
    }

    /// <inheritdoc />
    public async Task SaveCloseAsync(CloseResult result, CancellationToken ct)
    {
        var payload = JsonSerializer.Serialize(result);
        if (System.Text.Encoding.Unicode.GetByteCount(payload) > 60000)
            throw new InvalidOperationException("Report exceeds durable record budget.");
        await client.AddEntityAsync(new TableEntity("closes", result.CorrelationId) { ["Payload"] = payload }, ct);
    }

    /// <inheritdoc />
    public async Task<StoredClose> GetCloseAsync(string id, CancellationToken ct)
    {
        var entity = (await client.GetEntityAsync<TableEntity>("closes", id, cancellationToken: ct)).Value;
        return new(JsonSerializer.Deserialize<CloseResult>(entity.GetString("Payload"))
            ?? throw new InvalidOperationException("Invalid persisted close."), entity.ETag.ToString());
    }

    /// <inheritdoc />
    public async Task ReviewCloseAsync(StoredClose report, CancellationToken ct) =>
        await client.UpdateEntityAsync(new TableEntity("closes", report.Value.CorrelationId)
        {
            ["Payload"] = JsonSerializer.Serialize(report.Value)
        }, new ETag(report.ETag), TableUpdateMode.Replace, ct);

    private static TableEntity Entity(Order order) => new(order.StoreId, $"order-{order.DraftId}")
    {
        ["Payload"] = JsonSerializer.Serialize(order)
    };
}
