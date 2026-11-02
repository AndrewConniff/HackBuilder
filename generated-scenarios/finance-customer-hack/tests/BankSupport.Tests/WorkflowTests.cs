using System.Text.Json;
using BankSupport.Web.Models;
using BankSupport.Web.Services;
using Microsoft.Extensions.Logging.Abstractions;

namespace BankSupport.Tests;

/// <summary>Local coordination tests use explicit injected doubles, never claim live Foundry execution.</summary>
public sealed class WorkflowTests
{
    private readonly MemoryStore store = new();
    private readonly FakeFoundry foundry = new();
    private BankingWorkflow Workflow => new(store, foundry, NullLogger<BankingWorkflow>.Instance);

    private async Task<string> StartAsync()
    {
        await store.AddAsync("config", "agents", new AgentConfiguration("7", "9", "test"));
        await store.AddAsync("policies", "policy-hours-v1",
            new Policy("policy-hours-v1", "Hours", "09:00 to 17:00 UTC"));
        await store.AddAsync("bank-customer-1", "1",
            new BankRecord(1, "customer-1", "Balance", 245075, "Snapshot", "2026-10-28"));
        await store.AddAsync("bank-customer-2", "2",
            new BankRecord(2, "customer-2", "Balance", 98120, "Snapshot", "2026-10-28"));
        return await Workflow.StartAsync("customer-1", default);
    }

    /// <summary>Both distinct installed agents run and record real-shaped response receipts in this local double.</summary>
    [Fact]
    public async Task AutomatedTurnUsesTwoVersionedAgents()
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, "Opening hours?", false, default);
        var item = (await Workflow.OwnAsync(id, "customer-1", default)).Value;
        Assert.Equal("Automated", item.Status);
        Assert.Equal(2, item.Receipts.Length);
        Assert.Equal(["bank-triage", "bank-knowledge"], foundry.Calls.Select(c => c.Name));
        Assert.Equal(["7", "9"], foundry.Calls.Select(c => c.Version));
        Assert.Equal(2, item.Messages.Length);
    }

    /// <summary>Other customers cannot read a conversation, including its existence.</summary>
    [Fact]
    public async Task OtherCustomerCannotReadOrSend()
    {
        var id = await StartAsync();
        var read = await Assert.ThrowsAsync<BusinessException>(() => Workflow.OwnAsync(id, "customer-2", default));
        var send = await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-2", 0, "Balance?", false, default));
        Assert.Equal(404, read.StatusCode);
        Assert.Equal(404, send.StatusCode);
    }

    /// <summary>Only the server-selected customer's records reach the account specialist.</summary>
    [Fact]
    public async Task AccountRouteWithholdsOtherCustomers()
    {
        var id = await StartAsync();
        foundry.Route = "account";
        await Workflow.SendAsync(id, "customer-1", 0, "My balance?", false, default);
        var evidence = foundry.Calls.Last().Input;
        Assert.Contains("245075", evidence);
        Assert.DoesNotContain("98120", evidence);
        Assert.DoesNotContain("customer-2", evidence);
        Assert.DoesNotContain("245075", foundry.Calls.First().Input);
    }

    /// <summary>Explicit human requests bypass inference and persist before acknowledgement.</summary>
    [Fact]
    public async Task HumanOwnershipPausesAllInference()
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, "Speak to a person", true, default);
        await Workflow.ClaimAsync(id, "representative-1", 1, default);
        await Workflow.SendAsync(id, "customer-1", 2, "More details", false, default);
        await Workflow.ReplyAsync(id, "representative-1", 3, "I will investigate.", false, default);
        var item = (await Workflow.OwnAsync(id, "customer-1", default)).Value;
        Assert.Equal("HumanOwned", item.Status);
        Assert.Empty(foundry.Calls);
        Assert.Equal("Representative", item.Messages.Last().Role);
    }

    /// <summary>Competing claims and wrong-owner reads/writes cannot steal a case.</summary>
    [Fact]
    public async Task ClaimAndReplyRequireCurrentVersionAndOwner()
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, "Human please", true, default);
        await Workflow.ClaimAsync(id, "representative-1", 1, default);
        Assert.Equal(409, (await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.ClaimAsync(id, "coach-1", 1, default))).StatusCode);
        Assert.Equal(403, (await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.AssignedAsync(id, "coach-1", default))).StatusCode);
        Assert.Equal(403, (await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.ReplyAsync(id, "coach-1", 2, "Unauthorized", false, default))).StatusCode);
        Assert.All(await Workflow.QueueAsync(default), c => Assert.Empty(c.Messages));
    }

    /// <summary>Unknown evidence cannot be presented as a grounded answer.</summary>
    [Theory]
    [InlineData("unknown-policy")]
    [InlineData("record-2")]
    public async Task UnknownOrOtherCustomerSourceEscalates(string source)
    {
        var id = await StartAsync();
        foundry.Sources = [source];
        await Workflow.SendAsync(id, "customer-1", 0, "Question", false, default);
        var item = (await Workflow.OwnAsync(id, "customer-1", default)).Value;
        Assert.Equal("AwaitingHuman", item.Status);
        Assert.Single(item.Messages);
    }

    /// <summary>Unsupported model routes fail explicitly rather than selecting a default route.</summary>
    [Fact]
    public async Task InvalidRouteIsPersistedAsFailure()
    {
        var id = await StartAsync();
        foundry.Route = "transfer-money";
        Assert.Equal(502, (await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 0, "Question", false, default))).StatusCode);
        var item = (await Workflow.OwnAsync(id, "customer-1", default)).Value;
        Assert.Equal("Failed", item.Status);
        Assert.NotEmpty(item.Error);
        Assert.Single(item.Messages);
    }

    /// <summary>A service failure saves the request and surfaces a non-success result.</summary>
    [Fact]
    public async Task AgentFailureNeverProducesFakeSuccess()
    {
        var id = await StartAsync();
        foundry.Failure = new HttpRequestException("Simulated offline service");
        await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 0, "Question", false, default));
        Assert.Equal("Failed", (await Workflow.OwnAsync(id, "customer-1", default)).Value.Status);
    }

    /// <summary>A failed specialist preserves the completed triage receipt without inventing a specialist result.</summary>
    [Fact]
    public async Task PartialFailureRetainsCompletedAgentReceipt()
    {
        var id = await StartAsync();
        foundry.Failure = new HttpRequestException("Simulated specialist outage");
        foundry.FailureOnName = "bank-knowledge";
        await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 0, "Opening hours?", false, default));
        var item = (await Workflow.OwnAsync(id, "customer-1", default)).Value;
        Assert.Equal("Failed", item.Status);
        Assert.Equal("bank-triage", Assert.Single(item.Receipts).Name);
        Assert.Single(item.Messages);
    }

    /// <summary>Duplicate turns cannot consume inference twice.</summary>
    [Fact]
    public async Task StaleTurnFailsBeforeInference()
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, "Hours?", false, default);
        await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 0, "Duplicate", false, default));
        Assert.Equal(2, foundry.Calls.Count);
    }

    /// <summary>Closed cases cannot resume automated replies.</summary>
    [Fact]
    public async Task ClosedCaseCannotReopenImplicitly()
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, "Human", true, default);
        await Workflow.ClaimAsync(id, "representative-1", 1, default);
        await Workflow.ReplyAsync(id, "representative-1", 2, "Resolved", true, default);
        await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 3, "Reopen", false, default));
    }

    /// <summary>Blank and oversized input is rejected before a state transition.</summary>
    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    public async Task BlankInputFails(string input)
    {
        var id = await StartAsync();
        Assert.Equal(400, (await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 0, input, false, default))).StatusCode);
        await Assert.ThrowsAsync<BusinessException>(() =>
            Workflow.SendAsync(id, "customer-1", 0, new string('a', 1001), false, default));
        Assert.Empty(foundry.Calls);
    }

    /// <summary>High-risk English escalation signals override a misclassified routine route.</summary>
    [Theory]
    [InlineData("I suspect fraud")]
    [InlineData("My card was stolen")]
    [InlineData("I dispute this charge")]
    [InlineData("Speak to a representative")]
    public async Task RiskSignalCannotBeDowngradedByTriage(string text)
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, text, false, default);
        Assert.Equal("AwaitingHuman", (await Workflow.OwnAsync(id, "customer-1", default)).Value.Status);
        Assert.Single(foundry.Calls);
    }

    /// <summary>Only abandoned reservations can be recovered, and recovery cannot race normal turns.</summary>
    [Fact]
    public async Task InterruptedReservationRecoversOnlyAfterTimeout()
    {
        var id = await StartAsync();
        var saved = (await Workflow.OwnAsync(id, "customer-1", default));
        await store.ReplaceAsync("cases", id, saved.Value with
        { Status = "Processing", UpdatedAt = DateTimeOffset.UtcNow }, saved.ETag);
        await Assert.ThrowsAsync<BusinessException>(() => Workflow.RecoverAsync(id, "customer-1", 0, default));
        var recent = await Workflow.OwnAsync(id, "customer-1", default);
        await store.ReplaceAsync("cases", id, recent.Value with
        { UpdatedAt = DateTimeOffset.UtcNow.AddMinutes(-3) }, recent.ETag);
        await Workflow.RecoverAsync(id, "customer-1", 0, default);
        Assert.Equal("AwaitingHuman", (await Workflow.OwnAsync(id, "customer-1", default)).Value.Status);
        Assert.Empty(foundry.Calls);
    }

    /// <summary>Optimistic concurrency allows only one claimant for the same reviewed queue version.</summary>
    [Fact]
    public async Task CompetingClaimsHaveExactlyOneWinner()
    {
        var id = await StartAsync();
        await Workflow.SendAsync(id, "customer-1", 0, "Investigate", true, default);
        async Task<bool> Claim(string actor)
        {
            try { await Workflow.ClaimAsync(id, actor, 1, default); return true; }
            catch (BusinessException ex) when (ex.StatusCode == 409) { return false; }
        }
        var results = await Task.WhenAll(Task.Run(() => Claim("representative-1")), Task.Run(() => Claim("coach-1")));
        Assert.Single(results, r => r);
    }
}

internal sealed class FakeFoundry : IFoundryGateway
{
    internal string Route { get; set; } = "faq";
    internal string[] Sources { get; set; } = ["policy-hours-v1"];
    internal Exception? Failure { get; set; }
    internal string? FailureOnName { get; set; }
    internal List<(string Name, string Version, string Input)> Calls { get; } = [];

    public Task<(T Value, string ResponseId)> InvokeAsync<T>(string name, string version, object input, CancellationToken ct)
    {
        if (Failure is not null && (FailureOnName is null || FailureOnName == name)) throw Failure;
        Calls.Add((name, version, JsonSerializer.Serialize(input)));
        object result = name == "bank-triage"
            ? new RouteDecision(Route) : new KnowledgeAnswer("Open 09:00 to 17:00 UTC.", Sources, false);
        return Task.FromResult(((T)result, "local-test-response-" + Calls.Count));
    }
}

internal sealed class MemoryStore : IDocumentStore
{
    private readonly Dictionary<(string Partition, string Id), (string Json, int Version)> data = [];
    private readonly object gate = new();
    public Task<Stored<T>?> GetAsync<T>(string partition, string id, CancellationToken ct = default)
    {
        lock (gate)
            return Task.FromResult(data.TryGetValue((partition, id), out var row)
                ? new Stored<T>(JsonSerializer.Deserialize<T>(row.Json)!, row.Version.ToString()) : null);
    }
    public Task<IReadOnlyList<T>> ListAsync<T>(string partition, CancellationToken ct = default)
    {
        lock (gate)
            return Task.FromResult<IReadOnlyList<T>>(data.Where(p => p.Key.Partition == partition)
                .Select(p => JsonSerializer.Deserialize<T>(p.Value.Json)!).ToArray());
    }
    public Task AddAsync<T>(string partition, string id, T value, CancellationToken ct = default)
    {
        lock (gate)
        {
            if (!data.TryAdd((partition, id), (JsonSerializer.Serialize(value), 0)))
                throw new BusinessException(409, "Exists");
        }
        return Task.CompletedTask;
    }
    public Task ReplaceAsync<T>(string partition, string id, T value, string etag, CancellationToken ct = default)
    {
        lock (gate)
        {
            if (!data.TryGetValue((partition, id), out var row) || row.Version.ToString() != etag)
                throw new BusinessException(409, "Stale ETag");
            data[(partition, id)] = (JsonSerializer.Serialize(value), row.Version + 1);
        }
        return Task.CompletedTask;
    }
}
