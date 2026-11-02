using System.Text.Json;
using BankSupport.Web.Models;

namespace BankSupport.Web.Services;

/// <summary>Deterministic authorization, bounded two-agent routing and durable human ownership.</summary>
public sealed class BankingWorkflow(
    IDocumentStore store, IFoundryGateway foundry, ILogger<BankingWorkflow> logger)
{
    /// <summary>Creates a customer-owned conversation with no inferred or client-assigned privileged owner.</summary>
    public async Task<string> StartAsync(string customer, CancellationToken ct)
    {
        var id = Guid.NewGuid().ToString("N");
        await store.AddAsync("cases", id,
            new ServiceCase(id, customer, "Automated", string.Empty, 0, DateTimeOffset.UtcNow, [], []), ct);
        return id;
    }

    /// <summary>Reads only the current customer's case, hiding other customers' existence.</summary>
    public async Task<Stored<ServiceCase>> OwnAsync(string id, string customer, CancellationToken ct)
    {
        var item = await store.GetAsync<ServiceCase>("cases", id, ct);
        if (item is null || item.Value.CustomerId != customer)
            throw new BusinessException(404, "Conversation not found.");
        return item;
    }

    /// <summary>Returns only authorized customer records; caller identity is never supplied by a model.</summary>
    public Task<IReadOnlyList<BankRecord>> RecordsAsync(string customer, CancellationToken ct) =>
        store.ListAsync<BankRecord>("bank-" + customer, ct);

    /// <summary>Runs a turn after reserving its version, or appends to an already human-owned case.</summary>
    public async Task SendAsync(string id, string customer, int version, string text, bool human, CancellationToken ct)
    {
        ValidateText(text);
        var saved = await OwnAsync(id, customer, ct);
        var item = saved.Value;
        MatchVersion(item, version);
        if (item.Status is "Closed" or "Processing")
            throw new BusinessException(409, "Conversation is closed or already processing.");
        if (item.Messages.Length >= 18)
            throw new BusinessException(400, "Conversation limit reached. Start a new conversation.");
        var next = item with
        {
            Messages = [.. item.Messages, new Message("Customer", text.Trim(), DateTimeOffset.UtcNow)],
            Version = item.Version + 1, UpdatedAt = DateTimeOffset.UtcNow, Error = string.Empty
        };
        if (human || item.Status is "AwaitingHuman" or "HumanOwned" or "Failed")
        {
            await store.ReplaceAsync("cases", id, next with
            {
                Status = item.Status == "HumanOwned" ? "HumanOwned" : "AwaitingHuman"
            }, saved.ETag, ct);
            return;
        }
        await store.ReplaceAsync("cases", id, next with { Status = "Processing" }, saved.ETag, ct);
        var reserved = await OwnAsync(id, customer, ct);
        using var budget = CancellationTokenSource.CreateLinkedTokenSource(ct);
        budget.CancelAfter(TimeSpan.FromSeconds(90));
        var receipts = new List<AgentReceipt>();
        try
        {
            var agents = (await store.GetAsync<AgentConfiguration>("config", "agents", budget.Token))?.Value
                ?? throw new InvalidDataException("Agent installation is missing.");
            var route = await foundry.InvokeAsync<RouteDecision>(
                "bank-triage", agents.TriageVersion, new { Message = text }, budget.Token);
            if (route.Value.Route is not ("faq" or "account" or "human"))
                throw new InvalidDataException("Triage returned an unsupported route.");
            if (System.Text.RegularExpressions.Regex.IsMatch(text,
                @"\b(fraud|disput\w*|stolen|human|representative)\b",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase
                    | System.Text.RegularExpressions.RegexOptions.CultureInvariant))
                route = (new RouteDecision("human"), route.ResponseId);
            receipts.Add(new("bank-triage", agents.TriageVersion, route.ResponseId, route.Value.Route, []));
            if (route.Value.Route == "human")
            {
                await CompleteAsync(reserved, "AwaitingHuman", null, receipts, budget.Token);
                return;
            }
            var policies = await store.ListAsync<Policy>("policies", budget.Token);
            var records = route.Value.Route == "account"
                ? await RecordsAsync(customer, budget.Token) : [];
            var sources = policies.Select(p => p.Id).Concat(records.Select(r => $"record-{r.Id}")).ToHashSet();
            var answer = await foundry.InvokeAsync<KnowledgeAnswer>("bank-knowledge", agents.KnowledgeVersion,
                new { Message = text, Policies = policies, Records = records }, budget.Token);
            if (answer.Value.Sources is null || answer.Value.Answer is null || answer.Value.Answer.Length > 3000)
                throw new InvalidDataException("Specialist returned invalid answer fields.");
            var escalate = answer.Value.Escalate || string.IsNullOrWhiteSpace(answer.Value.Answer)
                || answer.Value.Sources.Length == 0 || answer.Value.Sources.Any(s => !sources.Contains(s));
            receipts.Add(new("bank-knowledge", agents.KnowledgeVersion, answer.ResponseId,
                route.Value.Route, answer.Value.Sources));
            await CompleteAsync(reserved, escalate ? "AwaitingHuman" : "Automated",
                escalate ? null : answer.Value.Answer, receipts, budget.Token);
        }
        catch (Exception ex) when (ex is HttpRequestException or JsonException or InvalidDataException
            or KeyNotFoundException or OperationCanceledException or Azure.RequestFailedException
            or Azure.Identity.AuthenticationFailedException)
        {
            logger.LogError(ex, "Agent turn failed for case {CaseId}", id);
            using var recovery = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            await store.ReplaceAsync("cases", id, reserved.Value with
            {
                Status = "Failed", Version = reserved.Value.Version + 1, UpdatedAt = DateTimeOffset.UtcNow,
                Error = "Agent service failed. Request human service or start a new conversation.",
                Receipts = [.. reserved.Value.Receipts.TakeLast(6), .. receipts]
            }, reserved.ETag, recovery.Token);
            throw new BusinessException(502, "Agent service failed. Your message is saved; request human service.");
        }
    }

    /// <summary>Returns a minimal queue without exposing other customers' transcripts.</summary>
    public async Task<IReadOnlyList<ServiceCase>> QueueAsync(CancellationToken ct) =>
        (await store.ListAsync<ServiceCase>("cases", ct))
        .Where(c => c.Status is "AwaitingHuman" or "HumanOwned").Select(c => c with
        { Messages = [], Receipts = [] }).OrderBy(c => c.UpdatedAt).Take(100).ToArray();

    /// <summary>Reads case details only for the representative who owns the case.</summary>
    public async Task<Stored<ServiceCase>> AssignedAsync(string id, string representative, CancellationToken ct)
    {
        var saved = await store.GetAsync<ServiceCase>("cases", id, ct);
        if (saved is null || saved.Value.Owner != representative)
            throw new BusinessException(403, "Claim this case before reading its conversation.");
        return saved;
    }

    /// <summary>Claims a waiting case; competing requests cannot overwrite ownership.</summary>
    public async Task ClaimAsync(string id, string representative, int version, CancellationToken ct)
    {
        var saved = await store.GetAsync<ServiceCase>("cases", id, ct)
            ?? throw new BusinessException(404, "Case not found.");
        MatchVersion(saved.Value, version);
        if (saved.Value.Status != "AwaitingHuman" || saved.Value.Owner.Length != 0)
            throw new BusinessException(409, "Case is no longer available.");
        await store.ReplaceAsync("cases", id, saved.Value with
        {
            Status = "HumanOwned", Owner = representative, Version = version + 1, UpdatedAt = DateTimeOffset.UtcNow
        }, saved.ETag, ct);
    }

    /// <summary>Replies or closes only an owned case at the reviewed version.</summary>
    public async Task ReplyAsync(string id, string representative, int version, string text, bool close, CancellationToken ct)
    {
        ValidateText(text);
        var saved = await AssignedAsync(id, representative, ct);
        MatchVersion(saved.Value, version);
        if (saved.Value.Status != "HumanOwned" || saved.Value.Messages.Length >= 20)
            throw new BusinessException(409, "Case is closed or its message limit was reached.");
        await store.ReplaceAsync("cases", id, saved.Value with
        {
            Status = close ? "Closed" : "HumanOwned", Version = version + 1, UpdatedAt = DateTimeOffset.UtcNow,
            Messages = [.. saved.Value.Messages, new Message("Representative", text.Trim(), DateTimeOffset.UtcNow)]
        }, saved.ETag, ct);
    }

    /// <summary>Recovers an abandoned inference reservation to a human queue after the configured timeout.</summary>
    public async Task RecoverAsync(string id, string customer, int version, CancellationToken ct)
    {
        var saved = await OwnAsync(id, customer, ct);
        MatchVersion(saved.Value, version);
        if (saved.Value.Status != "Processing" || saved.Value.UpdatedAt > DateTimeOffset.UtcNow.AddMinutes(-2))
            throw new BusinessException(409, "Only processing turns older than two minutes can be recovered.");
        await store.ReplaceAsync("cases", id, saved.Value with
        {
            Status = "AwaitingHuman", Version = version + 1, UpdatedAt = DateTimeOffset.UtcNow,
            Error = "Interrupted turn recovered to human service."
        }, saved.ETag, ct);
    }

    private Task CompleteAsync(Stored<ServiceCase> saved, string status, string? answer,
        List<AgentReceipt> receipts, CancellationToken ct) =>
        store.ReplaceAsync("cases", saved.Value.Id, saved.Value with
        {
            Status = status, Version = saved.Value.Version + 1, UpdatedAt = DateTimeOffset.UtcNow,
            Messages = answer is null ? saved.Value.Messages
                : [.. saved.Value.Messages, new Message("Assistant", answer, DateTimeOffset.UtcNow)],
            Receipts = [.. saved.Value.Receipts.TakeLast(6), .. receipts]
        }, saved.ETag, ct);

    private static void MatchVersion(ServiceCase item, int version)
    {
        if (item.Version != version)
            throw new BusinessException(409, "The conversation changed. Refresh before continuing.");
    }

    private static void ValidateText(string text)
    {
        if (string.IsNullOrWhiteSpace(text) || text.Length > 1000)
            throw new BusinessException(400, "Enter between 1 and 1,000 characters.");
    }
}
