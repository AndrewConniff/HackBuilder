using System.Text.Json;
using Azure;
using FeedbackCampaign.Web;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace FeedbackCampaign.Tests;

public sealed class WorkflowTests
{
    private static Post Packet(string id = "launch-1") => new(id, "Airi Ilves", "subscriber1@example.test",
        "Streaming launch", "Campaign feedback", "I like the company but dislike the player.");
    private static Analysis Result(double positive, double negative, double productNegative = .5) =>
        new(new(positive, negative, 1 - positive - negative), new(.5, .5, 0), new(1 - productNegative, productNegative, 0),
            "Company and product disagree; these are estimates.", "Check player telemetry with consent.",
            "Propose product-aspect routing for human evaluation.", "Thank you; we will investigate.", "campaign-policy-v1");

    [Theory]
    [InlineData(.8, .1, "Auto")]
    [InlineData(.799, .1, "ConflictResolutionSpecialist")]
    [InlineData(.1, .89, "ProductManager")]
    [InlineData(.1, .889, "ConflictResolutionSpecialist")]
    [InlineData(.5, .5, "ConflictResolutionSpecialist")]
    [InlineData(.1, .8, "ConflictResolutionSpecialist")]
    public void OriginalBoundaryRules(double p, double n, string expected) =>
        Assert.Equal(expected, Control.Route(Result(p, n), Rules.Initial));

    [Fact]
    public void ProposedAspectRuleIsDisabledUntilPromotion()
    {
        var result = Result(.5, .5, .9);
        Assert.Equal("ConflictResolutionSpecialist", Control.Route(result, Rules.Initial));
        Assert.Equal("ProductManager", Control.Route(result, Rules.Initial with { ProductRouting = true }));
    }

    [Theory]
    [InlineData(double.NaN)]
    [InlineData(double.PositiveInfinity)]
    [InlineData(-.1)]
    [InlineData(1.1)]
    public void InvalidScoresCannotTriggerActions(double value) =>
        Assert.Throws<ArgumentException>(() => Control.Route(Result(value, 0), Rules.Initial));

    [Fact]
    public async Task HumanGateSurvivesReconstructedWorkflowAndRejectsDuplicateSend()
    {
        var store = await Ready();
        var flow = new CampaignWorkflow(store, new(store), new Agent(Result(.1, .89)));
        var submitted = await flow.Submit(Packet(), "operator");
        await flow.Process(submitted, default);
        // Reconstruct service against the same durable-store contract: not a live Azure restart test.
        var resumed = new CampaignWorkflow(store, new(store), new Agent(Result(.1, .89)));
        var pending = (await store.Get<Case>("cases", submitted.Value.Id))!;
        Assert.Equal("AwaitingHuman", pending.Value.Status);
        await Assert.ThrowsAsync<UnauthorizedAccessException>(() => resumed.Review(pending.Value.Id, pending.ETag, "reply", "sales", ["ConflictResolutionSpecialist"]));
        await resumed.Review(pending.Value.Id, pending.ETag, "Edited reply", "pm", ["ProductManager"]);
        Assert.Equal("PendingSend", (await store.Get<Case>("cases", pending.Value.Id))!.Value.Status);
        await Assert.ThrowsAsync<InvalidOperationException>(() => resumed.Review(pending.Value.Id, pending.ETag, "repeat", "pm", ["ProductManager"]));
    }

    [Fact]
    public async Task StaleReviewCannotOverwriteAndEmptyReplyCannotSend()
    {
        var store = await Ready(); var flow = new CampaignWorkflow(store, new(store), new Agent(Result(.5, .5)));
        var row = await flow.Submit(Packet(), "operator"); await flow.Process(row, default);
        var pending = (await store.Get<Case>("cases", row.Value.Id))!;
        await Assert.ThrowsAsync<ArgumentException>(() => flow.Review(row.Value.Id, pending.ETag, " ", "sales", ["ConflictResolutionSpecialist"]));
        await Assert.ThrowsAsync<RequestFailedException>(() => flow.Review(row.Value.Id, row.ETag, "reply", "sales", ["ConflictResolutionSpecialist"]));
    }

    [Fact]
    public async Task FailedAgentPersistsFailureWithoutReplyAndSupportsExplicitRetry()
    {
        var store = await Ready(); var flow = new CampaignWorkflow(store, new(store), new Agent(null));
        var row = await flow.Submit(Packet(), "operator"); await flow.Process(row, default);
        var failed = (await store.Get<Case>("cases", row.Value.Id))!;
        Assert.Equal("Failed", failed.Value.Status); Assert.Null(failed.Value.Reply);
        Assert.Null(failed.Value.AgentResponseId);
        await flow.Retry(row.Value.Id, failed.ETag, "operator");
        Assert.Equal("Received", (await store.Get<Case>("cases", row.Value.Id))!.Value.Status);
    }

    [Fact]
    public async Task DeduplicateSourceAndRejectChangedPayload()
    {
        var store = await Ready(); var flow = new CampaignWorkflow(store, new(store), new Agent(Result(.9, .1)));
        var first = await flow.Submit(Packet(), "operator");
        var second = await flow.Submit(Packet(), "operator");
        Assert.Equal(first.Value.Id, second.Value.Id);
        Assert.Single(await store.List<Case>("cases"));
        await Assert.ThrowsAsync<InvalidOperationException>(() => flow.Submit(Packet() with { Body = "Changed" }, "operator"));
    }

    [Fact]
    public async Task ImmutableVersionsAndOptimisticHumanPromotion()
    {
        var store = await Ready(); var service = new RuleService(store);
        var before = (await store.Get<ActiveRules>("config", "active"))!;
        await service.Save(Rules.Initial with { Version = "v2", ProductRouting = true, Author = "admin", Reason = "Reviewed test" });
        Assert.Equal("v1", (await service.Current()).Version);
        await Assert.ThrowsAsync<InvalidOperationException>(() => service.Save(Rules.Initial));
        await service.Promote("v2", "admin", "Reviewed aspect routing", before.ETag);
        Assert.Equal("v2", (await service.Current()).Version);
        await Assert.ThrowsAsync<RequestFailedException>(() => service.Promote("v1", "admin", "Stale attempt", before.ETag));
    }

    [Fact]
    public async Task ExistingCaseKeepsOldRulesAfterPromotion()
    {
        var store = await Ready(); var rules = new RuleService(store);
        var flow = new CampaignWorkflow(store, rules, new Agent(Result(.5, .5, .95)));
        var old = await flow.Submit(Packet(), "operator");
        await rules.Save(Rules.Initial with { Version = "v2", ProductRouting = true });
        var active = (await store.Get<ActiveRules>("config", "active"))!;
        await rules.Promote("v2", "admin", "Reviewed", active.ETag);
        await flow.Process(old, default);
        var saved = (await store.Get<Case>("cases", old.Value.Id))!;
        Assert.Equal("v1", saved.Value.Rules.Version);
        Assert.Equal("ConflictResolutionSpecialist", saved.Value.Owner);
    }

    [Fact]
    public void MissingContactAndOversizedInputAreRejected()
    {
        Assert.Throws<ArgumentException>(() => (Packet() with { Contact = "" }).Validate());
        Assert.Throws<ArgumentException>(() => (Packet() with { Body = new string('x', 6001) }).Validate());
        Assert.Throws<ArgumentException>(() => (Rules.Initial with { Version = "../rules" }).Validate());
    }

    [Fact]
    public async Task LocalHttpRejectsAnonymousAndSpoofedPrincipal()
    {
        await using var app = new WebApplicationFactory<Program>();
        var client = app.CreateClient();
        Assert.Equal(System.Net.HttpStatusCode.OK, (await client.GetAsync("/")).StatusCode);
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, (await client.GetAsync("/api/cases")).StatusCode);
        client.DefaultRequestHeaders.Add("X-MS-CLIENT-PRINCIPAL", Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(
            """{"claims":[{"typ":"roles","val":"ControlAdmin"}]}""")));
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, (await client.GetAsync("/api/rules")).StatusCode);
    }

    private static async Task<MemoryStore> Ready()
    {
        var store = new MemoryStore();
        await store.Add("rules", "v1", Rules.Initial);
        await store.Add("config", "active", new ActiveRules("v1", "installation", "Original rules"));
        return store;
    }
    private sealed class Agent(Analysis? analysis) : IFoundryAgent
    {
        public Task<(Analysis Analysis, string ResponseId)> Analyze(Post post, Rules rules, CancellationToken cancellation) =>
            analysis is null ? throw new HttpRequestException("Test-only provider failure")
                : Task.FromResult((analysis, "test-double-not-live-evidence"));
        public Task<(string Text, string ResponseId)> Chat(string prompt, CancellationToken cancellation) => throw new NotSupportedException();
    }
    // Contract test double, never registered by production application.
    internal sealed class MemoryStore : IStateStore
    {
        private readonly Dictionary<string, (string Json, int Revision)> rows = [];
        public Task<bool> Add<T>(string p, string k, T value) =>
            Task.FromResult(rows.TryAdd($"{p}/{k}", (JsonSerializer.Serialize(value, TableStateStore.Json), 1)));
        public Task<Versioned<T>?> Get<T>(string p, string k) => Task.FromResult(rows.TryGetValue($"{p}/{k}", out var r)
            ? new Versioned<T>(JsonSerializer.Deserialize<T>(r.Json, TableStateStore.Json)!, r.Revision.ToString()) : null);
        public Task Replace<T>(string p, string k, T value, string etag)
        {
            if (!rows.TryGetValue($"{p}/{k}", out var r) || r.Revision.ToString() != etag)
                throw new RequestFailedException(412, "Test stale ETag");
            rows[$"{p}/{k}"] = (JsonSerializer.Serialize(value, TableStateStore.Json), r.Revision + 1);
            return Task.CompletedTask;
        }
        public async Task<IReadOnlyList<Versioned<T>>> List<T>(string p)
        {
            var results = new List<Versioned<T>>();
            foreach (var key in rows.Keys.Where(k => k.StartsWith($"{p}/")))
                results.Add((await Get<T>(p, key[(p.Length + 1)..]))!);
            return results;
        }
    }
}
