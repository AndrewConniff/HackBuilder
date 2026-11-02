using System.Text.Json;
using Microsoft.Azure.Cosmos;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>An explicitly authorized dead-letter replay request with its own stable transport idempotency key.</summary>
public sealed record ReplayRequest(string id, string aggregateKey, string Type, string Subject,
    string MessageId, string SessionId, string Status, string? Failure, DateTimeOffset CreatedAt,
    DateTimeOffset? LeaseUntil = null);

/// <summary>Manager-only reconciliation and audited replay requests; the web identity has no broker access.</summary>
public sealed class OperationsService(CosmosStore store, TimeProvider clock)
{
    /// <summary>Returns synthetic settlement totals and bounded recovery evidence.</summary>
    public async Task<object> View(Caller caller, CancellationToken token)
    {
        DemandManager(caller);
        var visits = await store.Query<Visit>(store.Transactions,
            new("SELECT TOP 1250 * FROM c WHERE c.Type = 'visit'"), 1250, token);
        var deadLetters = await CosmosStore.Read<JsonElement>(store.Reporting, "deadletters", "operations", token);
        var pending = await store.Query<Outbox>(store.Transactions,
            new("SELECT TOP 250 * FROM c WHERE c.Type = 'outbox' AND c.Status = 'pending'"), 250, token);
        var replays = await store.Query<ReplayRequest>(store.Reporting,
            new("SELECT TOP 50 * FROM c WHERE c.Type = 'replay-request'"), 50, token);
        return new
        {
            PaymentNotice = "Synthetic settlement - no money charged", Currency = "USD",
            SettledVisits = visits.Count(v => v.Settled),
            SettledTotalMinor = visits.Where(v => v.Settled).Sum(v => (long)v.TotalMinor),
            VisitsReturned = visits.Length, VisitLimit = 1250, PendingOutboxReturned = pending.Length, PendingLimit = 250,
            OldestPendingAt = pending.Select(item => (DateTimeOffset?)item.CreatedAt).Min(),
            DeadLetters = deadLetters?.Item, ReplayRequests = replays,
            Notice = "Bounded operational view, not an unbounded accounting export. Missing DLQ observation is not zero DLQ."
        };
    }

    /// <summary>Records an auditable manager request, not a claim that the broker has already replayed it.</summary>
    public async Task<ReplayRequest> RequestReplay(string messageId, string sessionId, Caller caller, CancellationToken token)
    {
        DemandManager(caller);
        if (string.IsNullOrWhiteSpace(messageId) || messageId.Length > 128
            || string.IsNullOrWhiteSpace(sessionId) || sessionId.Length > 128)
            throw new DomainException(400, "A bounded message ID and session ID are required.");
        var request = new ReplayRequest(Guid.NewGuid().ToString("N"), "operations", "replay-request",
            caller.Subject, messageId, sessionId, "pending", null, clock.GetUtcNow());
        await store.Reporting.CreateItemAsync(request, new("operations"), cancellationToken: token);
        return request;
    }

    private static void DemandManager(Caller caller)
    {
        if (caller.Role != "Manager") throw new DomainException(403, "Manager role required for reconciliation and recovery.");
    }
}
