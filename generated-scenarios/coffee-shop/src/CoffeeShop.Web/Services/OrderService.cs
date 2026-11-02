using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using CoffeeShop.Web.Models;

namespace CoffeeShop.Web.Services;

public sealed class OrderService(StoreAccess access, IRepository repository)
{
    public async Task<Order> DraftAsync(ClaimsPrincipal user, string storeId, CancellationToken ct)
    {
        access.Demand(user, storeId);
        var snapshot = await repository.ReadAsync(storeId, ct);
        var lines = snapshot.Stock.Where(stock => stock.Target > stock.OnHand)
            .Select(stock => new OrderLine(stock.Sku, stock.Unit, stock.Target - stock.OnHand, stock.UnitCost)).ToArray();
        if (lines.Length == 0) throw new InvalidOperationException("No shortfall.");
        var oid = user.FindFirstValue("oid")!;
        var key = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(
            $"{storeId}|{snapshot.Version}")))[..24].ToLowerInvariant();
        var existing = await repository.GetOrderAsync(storeId, key, ct);
        if (existing is not null)
        {
            if (existing.Value.Status == "Approved" || existing.Value.ExpiresAt >= DateTimeOffset.UtcNow)
                return existing.Value;
            var renewed = existing.Value with { ExpiresAt = DateTimeOffset.UtcNow.AddMinutes(15), CreatedBy = oid };
            if (!await repository.ReplaceOrderAsync(new(renewed, existing.ETag), ct))
                throw new InvalidOperationException("Concurrent draft renewal.");
            return renewed;
        }
        return (await repository.AddOrderAsync(new Order(1, key, storeId, snapshot.Version, oid,
            DateTimeOffset.UtcNow.AddMinutes(15), lines, "Draft"), ct)).Value;
    }

    public async Task<Order> ApproveAsync(ClaimsPrincipal user, string storeId, string draftId, CancellationToken ct)
    {
        access.Demand(user, storeId);
        if (!System.Text.RegularExpressions.Regex.IsMatch(draftId, "^[a-f0-9]{24}$"))
            throw new ArgumentException("Invalid draft ID.");
        var existing = await repository.GetOrderAsync(storeId, draftId, ct) ?? throw new KeyNotFoundException();
        if (existing.Value.Status == "Approved") return existing.Value;
        if (existing.Value.ExpiresAt < DateTimeOffset.UtcNow) throw new InvalidOperationException("Expired draft.");
        var snapshot = await repository.ReadAsync(storeId, ct);
        if (snapshot.Version != existing.Value.SnapshotVersion) throw new InvalidOperationException("Stale draft.");
        var approved = existing.Value with
        {
            Status = "Approved", ApprovedBy = user.FindFirstValue("oid"), ApprovedAt = DateTimeOffset.UtcNow
        };
        if (!await repository.ReplaceOrderAsync(new(approved, existing.ETag), ct))
        {
            var current = await repository.GetOrderAsync(storeId, draftId, ct);
            if (current?.Value.Status == "Approved") return current.Value;
            throw new InvalidOperationException("Concurrent approval.");
        }
        return approved;
    }
}
