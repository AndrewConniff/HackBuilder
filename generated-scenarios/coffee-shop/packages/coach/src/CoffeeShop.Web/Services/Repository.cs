using System.Text.Json;
using Azure;
using Azure.Core;
using Azure.Data.Tables;
using CoffeeShop.Web.Models;

namespace CoffeeShop.Web.Services;

public interface IRepository
{
    Task<StoreSnapshot> ReadAsync(string storeId, CancellationToken ct);
    Task<StoredOrder?> GetOrderAsync(string storeId, string draftId, CancellationToken ct);
    Task<StoredOrder> AddOrderAsync(Order order, CancellationToken ct);
    Task<bool> ReplaceOrderAsync(StoredOrder order, CancellationToken ct);
}

public sealed class TableRepository(IConfiguration configuration, TokenCredential credential) : IRepository
{
    private TableClient Client => new(new Uri(configuration["Storage:Endpoint"]
        ?? throw new InvalidOperationException("Storage endpoint not installed.")), "CoffeeBackOffice", credential);

    public async Task<StoreSnapshot> ReadAsync(string storeId, CancellationToken ct)
    {
        var entity = await Client.GetEntityIfExistsAsync<TableEntity>(storeId, "snapshot", cancellationToken: ct);
        if (!entity.HasValue) throw new KeyNotFoundException();
        return JsonSerializer.Deserialize<StoreSnapshot>(entity.Value!.GetString("Payload"))!;
    }

    public async Task<StoredOrder?> GetOrderAsync(string storeId, string draftId, CancellationToken ct)
    {
        var entity = await Client.GetEntityIfExistsAsync<TableEntity>(storeId, $"order-{draftId}", cancellationToken: ct);
        return entity.HasValue ? new(JsonSerializer.Deserialize<Order>(entity.Value!.GetString("Payload"))!,
            entity.Value.ETag.ToString()) : null;
    }

    public async Task<StoredOrder> AddOrderAsync(Order order, CancellationToken ct)
    {
        try
        {
            await Client.AddEntityAsync(Entity(order), ct);
        }
        catch (RequestFailedException error) when (error.Status == 409) { /* Idempotent draft replay. */ }
        return await GetOrderAsync(order.StoreId, order.DraftId, ct) ?? throw new InvalidOperationException();
    }

    public async Task<bool> ReplaceOrderAsync(StoredOrder order, CancellationToken ct)
    {
        try
        {
            await Client.UpdateEntityAsync(Entity(order.Value), new ETag(order.ETag), TableUpdateMode.Replace, ct);
            return true;
        }
        catch (RequestFailedException error) when (error.Status == 412) { return false; }
    }

    private static TableEntity Entity(Order order) => new(order.StoreId, $"order-{order.DraftId}")
    {
        ["Payload"] = JsonSerializer.Serialize(order)
    };
}
