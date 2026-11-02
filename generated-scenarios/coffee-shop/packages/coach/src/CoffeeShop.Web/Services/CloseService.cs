using System.Security.Claims;
using System.Text.Json;
using CoffeeShop.Web.Models;

namespace CoffeeShop.Web.Services;

public interface IAgentGateway
{
    Task<AgentReceipt> InvokeAsync(string agent, string evidence, CancellationToken ct);
}

public sealed class CloseService(StoreAccess access, IRepository repository, IAgentGateway agents,
    ILogger<CloseService> logger)
{
    private readonly SemaphoreSlim slots = new(2, 2);

    public async Task<CloseResult> RunAsync(ClaimsPrincipal user, CloseRequest request, CancellationToken ct)
    {
        if (request.StoreIds is not { Length: > 0 and <= 5 } || string.IsNullOrWhiteSpace(request.Question)
            || request.Question.Length > 1500) throw new ArgumentException("Request budget.");
        foreach (var store in request.StoreIds) access.Demand(user, store);
        if (!await slots.WaitAsync(0, ct)) throw new InvalidOperationException("Busy; retry later.");
        try
        {
            using var budget = CancellationTokenSource.CreateLinkedTokenSource(ct);
            budget.CancelAfter(TimeSpan.FromSeconds(90));
            var snapshots = await Task.WhenAll(request.StoreIds.Distinct()
                .Select(store => repository.ReadAsync(store, budget.Token)));
            if (snapshots.Any(snapshot => !snapshot.Ledger.Complete))
                throw new InvalidOperationException("Missing ledger evidence.");
            if (snapshots.Select(snapshot => snapshot.Ledger.Date).Distinct().Count() != 1)
                throw new InvalidOperationException("Cannot aggregate different business dates.");
            var correlation = Guid.NewGuid().ToString("N");
            var inventory = JsonSerializer.Serialize(new
            {
                CorrelationId = correlation, UntrustedQuestion = request.Question,
                Sources = snapshots.Select(s => new { s.Store.StoreId, s.Version, s.Stock })
            });
            var financial = JsonSerializer.Serialize(new
            {
                CorrelationId = correlation, UntrustedQuestion = request.Question,
                Sources = snapshots.Select(s => new { s.Store.StoreId, s.Version, s.Ledger })
            });
            var branches = await Task.WhenAll(
                agents.InvokeAsync("stock", inventory, budget.Token),
                agents.InvokeAsync("margin", financial, budget.Token));
            var synthesis = await agents.InvokeAsync("close", JsonSerializer.Serialize(new
            {
                CorrelationId = correlation, Branches = branches,
                AuthoritativeNetSales = snapshots.Sum(s => s.Ledger.NetSales),
                AuthoritativeProfit = snapshots.Sum(s => s.Ledger.Profit)
            }), budget.Token);
            logger.LogInformation("Close {Correlation} completed for {StoreCount} stores; responses {ResponseIds}",
                correlation, snapshots.Length, string.Join(",", branches.Append(synthesis).Select(a => a.ResponseId)));
            return new(correlation, "Completed", snapshots, snapshots.Sum(s => s.Ledger.NetSales),
                snapshots.Sum(s => s.Ledger.Profit), [.. branches, synthesis]);
        }
        finally { slots.Release(); }
    }
}
