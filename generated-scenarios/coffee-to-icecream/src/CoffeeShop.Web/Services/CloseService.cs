using System.Security.Claims;
using System.Text.Json;
using CoffeeShop.Web.Models;

namespace CoffeeShop.Web.Services;

/// <summary>Invokes a real scoped Foundry agent; tests may explicitly substitute a test-only implementation.</summary>
public interface IAgentGateway
{
    /// <summary>Returns a completed invocation receipt or throws; never supplies mock-success fallback.</summary>
    Task<AgentReceipt> InvokeAsync(string agent, string evidence, CancellationToken ct);
}

/// <summary>Partitions authorized store evidence into bounded workers, reconciles results and persists review state.</summary>
public sealed class CloseService(StoreAccess access, IRepository repository, IAgentGateway agents,
    ILogger<CloseService> logger)
{
    private readonly SemaphoreSlim slots = new(10, 10);

    /// <summary>Generates an advisory report; it is not finalized until a human reviews the exact evidence.</summary>
    public async Task<CloseResult> RunAsync(ClaimsPrincipal user, CloseRequest request, CancellationToken ct)
    {
        if (request.StoreIds is not { Length: > 0 and <= 10 } || string.IsNullOrWhiteSpace(request.Question)
            || request.Question.Length > 1500
            || request.StoreIds.Distinct().Count() != request.StoreIds.Length)
            throw new ArgumentException("Invalid request or duplicate store assignments.");
        foreach (var store in request.StoreIds) access.Demand(user, store);
        if (!await slots.WaitAsync(0, ct)) throw new InvalidOperationException("Close capacity exhausted; retry later.");
        try
        {
            using var budget = CancellationTokenSource.CreateLinkedTokenSource(ct);
            budget.CancelAfter(TimeSpan.FromSeconds(55));
            var snapshots = await Task.WhenAll(request.StoreIds
                .Select(store => repository.ReadAsync(store, budget.Token)));
            if (snapshots.Any(snapshot => !snapshot.Ledger.Complete || snapshot.Input is null))
                throw new InvalidOperationException("Missing daily recipe or ledger evidence.");
            if (snapshots.Select(snapshot => snapshot.Ledger.Date).Distinct().Count() != 1)
                throw new InvalidOperationException("Cannot aggregate different business dates.");
            var correlation = Guid.NewGuid().ToString("N");
            using var workers = new SemaphoreSlim(4, 4);
            var assignments = snapshots.SelectMany(snapshot => new[] { "stock", "margin" }
                .Select(domain => (Snapshot: snapshot, Domain: domain))).ToArray();
            var receipts = await Task.WhenAll(assignments.Select(async assignment =>
            {
                await workers.WaitAsync(budget.Token);
                try
                {
                    var snapshot = assignment.Snapshot;
                    var id = $"{snapshot.Store.StoreId}-{assignment.Domain}";
                    object source = assignment.Domain == "stock"
                        ? new { snapshot.Stock, snapshot.Input!.Recipes, snapshot.Input.Sales, snapshot.Input.Spoilage }
                        : new { snapshot.Ledger };
                    var evidence = JsonSerializer.Serialize(new
                    {
                        CorrelationId = correlation, AssignmentId = id,
                        StoreId = snapshot.Store.StoreId, SnapshotVersion = snapshot.Version,
                        UntrustedQuestion = request.Question, Source = source
                    });
                    var receipt = await agents.InvokeAsync(assignment.Domain, evidence, budget.Token);
                    return new WorkReceipt(id, snapshot.Store.StoreId, assignment.Domain, snapshot.Version, receipt);
                }
                finally { workers.Release(); }
            }));
            if (receipts.Length != assignments.Length
                || receipts.Select(receipt => receipt.AssignmentId).Distinct().Count() != assignments.Length
                || receipts.Select(receipt => receipt.Agent.ResponseId).Distinct().Count() != assignments.Length
                || receipts.Any(receipt => string.IsNullOrWhiteSpace(receipt.Agent.ResponseId)))
                throw new InvalidOperationException("Missing or duplicate worker result.");
            var synthesis = await agents.InvokeAsync("close", JsonSerializer.Serialize(new
            {
                CorrelationId = correlation, Assignments = receipts,
                AuthoritativeSnapshots = snapshots.Select(snapshot => new
                {
                    snapshot.Store.StoreId, snapshot.Version, snapshot.Ledger, snapshot.Stock
                }),
                AuthoritativeNetSales = snapshots.Sum(s => s.Ledger.NetSales),
                AuthoritativeProfit = snapshots.Sum(s => s.Ledger.Profit)
            }), budget.Token);
            if (string.IsNullOrWhiteSpace(synthesis.ResponseId))
                throw new InvalidOperationException("Missing synthesis receipt.");
            // Raw import packets remain in store snapshots; the durable review binds to their versions.
            var evidenceSnapshots = snapshots.Select(snapshot => snapshot with { Input = null }).ToArray();
            var result = new CloseResult(correlation, "AwaitingReview", evidenceSnapshots,
                snapshots.Sum(s => s.Ledger.NetSales), snapshots.Sum(s => s.Ledger.Profit),
                [synthesis], receipts, DateTimeOffset.UtcNow);
            await repository.SaveCloseAsync(result, budget.Token);
            logger.LogInformation("Close {Correlation} awaiting review; {Assignments} assignments for {Stores} stores.",
                correlation, assignments.Length, snapshots.Length);
            return result;
        }
        finally { slots.Release(); }
    }

    /// <summary>Loads a report only when the caller can access every store in it.</summary>
    public async Task<StoredClose> ReadAsync(ClaimsPrincipal user, string id, CancellationToken ct)
    {
        if (!System.Text.RegularExpressions.Regex.IsMatch(id, "^[a-f0-9]{32}$"))
            throw new ArgumentException("Invalid close ID.");
        var report = await repository.GetCloseAsync(id, ct);
        foreach (var snapshot in report.Value.Evidence) access.Demand(user, snapshot.Store.StoreId);
        return report;
    }

    /// <summary>Finalizes the persisted proposal once, rejecting expired reports or changed evidence.</summary>
    public async Task<CloseResult> ReviewAsync(ClaimsPrincipal user, string id, bool confirm, CancellationToken ct)
    {
        if (!confirm) throw new ArgumentException("Explicit human confirmation is required.");
        var stored = await ReadAsync(user, id, ct);
        var report = stored.Value;
        if (report.Status == "Reviewed") return report;
        if (report.Status != "AwaitingReview" || DateTimeOffset.UtcNow - report.CreatedAt > TimeSpan.FromMinutes(15))
            throw new InvalidOperationException("Report expired; generate a new report.");
        foreach (var snapshot in report.Evidence)
        {
            var current = await repository.ReadAsync(snapshot.Store.StoreId, ct);
            if (current.Version != snapshot.Version) throw new InvalidOperationException("Close evidence changed.");
        }
        var reviewed = report with
        {
            Status = "Reviewed", ReviewedBy = user.FindFirstValue("oid"), ReviewedAt = DateTimeOffset.UtcNow
        };
        await repository.ReviewCloseAsync(new(reviewed, stored.ETag), ct);
        logger.LogInformation("Close {Correlation} reviewed by {Reviewer}.", id, reviewed.ReviewedBy);
        return reviewed;
    }
}
