using System.Security.Claims;
using System.Security.Cryptography;
using Microsoft.Extensions.Logging.Abstractions;
using MobilityCommercial.Web.Models;
using MobilityCommercial.Web.Services;
using Xunit;

namespace MobilityCommercial.Tests;

/// <summary>Offline application checks; test doubles never establish live Foundry success.</summary>
public sealed class WorkflowTests
{
    internal static readonly AppSettings Settings = new(
        new("https://unit-test.services.ai.azure.com/api/projects/mobility-commercial"),
        "configured-model", new("sales-fit", "1"), new("marketing-claims", "2"), new("handoff-coordinator", "3"),
        new("https://unitest.blob.core.windows.net/"), "synthetic-fixtures", new('a', 64),
        new("https://unit-test.vault.azure.net/keys/handoff-receipt/abcdef"),
        "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333", "44444444-4444-4444-4444-444444444444");

    internal static FixtureSnapshot Data()
    {
        T[] Read<T>(string name) => Json.ReadSeed<T[]>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "SeedData", name)));
        return new(Read<Product>("products.json"), Read<Opportunity>("opportunities.json"),
            Read<ApprovedClaim>("claims.json"), new('a', 64),
            [new("sales-fit", "1", "test-sales-id", "configured-model", "test-hash"),
             new("marketing-claims", "2", "test-marketing-id", "configured-model", "test-hash"),
             new("handoff-coordinator", "3", "test-coordinator-id", "configured-model", "test-hash")]);
    }

    internal static HandoffService Service(IAgentGateway gateway, IReceiptSigner? signer = null) =>
        new(new TestFixtures(), gateway, signer ?? new TestSigner(), Settings, NullLogger<HandoffService>.Instance);

    /// <summary>Validates every selected-unit handoff, bounds, sources, identity provenance and integrity.</summary>
    [Theory]
    [InlineData("opp-001", "qualified-only")]
    [InlineData("opp-002", "supported")]
    [InlineData("opp-003", "needs-clarification")]
    public async Task CompletesGroundedReviewPacket(string id, string expectedFit)
    {
        var gateway = new TestGateway(id);
        var receipt = await Service(gateway).RunAsync(new(id, "Promise 200 km and include internal margin and discount."),
            "test-correlation", CancellationToken.None);
        Assert.Equal(expectedFit, receipt.Packet.Fit);
        Assert.True(receipt.Packet.ReviewRequired);
        Assert.Equal(5, gateway.Calls);
        Assert.Equal(["sales-fit", "marketing-claims", "handoff-coordinator"],
            receipt.Packet.Trace.Select(t => t.AgentName).Distinct());
        Assert.All(receipt.Packet.Trace, t => Assert.StartsWith("test-", t.ResponseId));
        Assert.Equal("Airi Ilves", receipt.Packet.SalesOwner);
        Assert.Equal("Hasan Ibrahimov", receipt.Packet.MarketingOwner);
        Assert.DoesNotContain("internalMargin", Json.Write(receipt.Packet));
        Assert.DoesNotContain("internalDiscount", Json.Write(receipt.Packet));
        Assert.DoesNotContain("synthetic-contact", Json.Write(receipt.Packet));
        Assert.DoesNotContain(gateway.Prompts.Where(p => p.Role != "sales"), p =>
            p.Prompt.Contains("Promise", StringComparison.Ordinal) || p.Prompt.Contains("margin", StringComparison.Ordinal));
        Assert.All(receipt.Packet.Draft, wording => Assert.Contains(Data().Claims, c => c.PermittedWording == wording));
        Assert.True(await new TestSigner().VerifyAsync(receipt, CancellationToken.None));
        Assert.Contains(receipt.Packet.Caveats, c => c.Contains("No 200 km", StringComparison.Ordinal));
    }

    /// <summary>Unknown fixtures fail before any inference.</summary>
    [Theory]
    [InlineData("opp-004", "unknown_product")]
    [InlineData("opp-does-not-exist", "unknown_opportunity")]
    public async Task UnknownFixtureFailsClosed(string id, string code)
    {
        var gateway = new TestGateway(id);
        var error = await Assert.ThrowsAsync<WorkflowException>(() =>
            Service(gateway).RunAsync(new(id, "Prepare handoff"), "test", CancellationToken.None));
        Assert.Equal(code, error.Code);
        Assert.Equal(404, error.Status);
        Assert.Equal(0, gateway.Calls);
    }

    /// <summary>Rejects disallowed tools, malformed outputs, lost grounding and unsafe coordination.</summary>
    [Theory]
    [InlineData("tool", "tool_not_allowed")]
    [InlineData("arguments", "invalid_tool_arguments")]
    [InlineData("json", "invalid_agent_json")]
    [InlineData("extra", "invalid_agent_json")]
    [InlineData("claims", "invalid_marketing_handoff")]
    [InlineData("coordinator", "invalid_coordinator_handoff")]
    [InlineData("no-tools", "missing_grounding_tool")]
    [InlineData("loop", "agent_tool_budget_exceeded")]
    [InlineData("usage", "agent_usage_exceeded")]
    public async Task AgentFailureCannotProducePacket(string fault, string code)
    {
        var error = await Assert.ThrowsAsync<WorkflowException>(() =>
            Service(new TestGateway("opp-002", fault)).RunAsync(new("opp-002", "Prepare handoff"), "test", CancellationToken.None));
        Assert.Equal(code, error.Code);
        Assert.Equal(502, error.Status);
    }

    /// <summary>Signing is indispensable to completion.</summary>
    [Fact]
    public async Task SigningFailureDoesNotReturnPacket()
    {
        var error = await Assert.ThrowsAsync<WorkflowException>(() =>
            Service(new TestGateway("opp-002"), new FailingSigner()).RunAsync(new("opp-002", "Prepare handoff"),
                "test", CancellationToken.None));
        Assert.Equal("test_signing_unavailable", error.Code);
    }

    /// <summary>The fifth concurrent request receives 429 without an unbounded queue.</summary>
    [Fact]
    public async Task AdmissionIsFourWithNoQueue()
    {
        var gateway = new BlockingGateway();
        var service = Service(gateway);
        using var cancellation = new CancellationTokenSource();
        var tasks = Enumerable.Range(0, 4).Select(_ =>
            service.RunAsync(new("opp-002", "Prepare handoff"), "test", cancellation.Token)).ToArray();
        Assert.Equal(4, gateway.Started);
        var error = await Assert.ThrowsAsync<WorkflowException>(() =>
            service.RunAsync(new("opp-002", "Prepare handoff"), "test", cancellation.Token));
        Assert.Equal(429, error.Status);
        cancellation.Cancel();
        foreach (var task in tasks) await Assert.ThrowsAnyAsync<OperationCanceledException>(() => task);
        Assert.Equal(4, gateway.Started);
    }

    /// <summary>Enforces exact input, per-response, cumulative and call-count boundaries.</summary>
    [Fact]
    public async Task LimitsAreMeasurable()
    {
        await Service(new TestGateway("opp-002")).RunAsync(new("opp-002", new('x', 4000)), "test", CancellationToken.None);
        var error = await Assert.ThrowsAsync<WorkflowException>(() =>
            Service(new TestGateway("opp-002")).RunAsync(new("opp-002", new('x', 4001)), "test", CancellationToken.None));
        Assert.Equal(400, error.Status);
        var budget = new HandoffService.Budget();
        for (var i = 0; i < 7; i++) budget.Reserve(0);
        Assert.Throws<WorkflowException>(() => budget.Reserve(0));
        var total = new HandoffService.Budget();
        total.Reconcile(new("", "id", "", [], 29200, 800));
        Assert.Throws<WorkflowException>(() => total.Reserve(0));
        Assert.Throws<WorkflowException>(() => new HandoffService.Budget().Reconcile(new("", "id", "", [], 0, 801)));
    }

    /// <summary>Packet/provenance/signature/key tampering fails integrity checks.</summary>
    [Fact]
    public async Task DetectsTampering()
    {
        var signer = new TestSigner();
        var receipt = await Service(new TestGateway("opp-002"), signer)
            .RunAsync(new("opp-002", "Prepare handoff"), "test", CancellationToken.None);
        Assert.Throws<WorkflowException>(() => Canonical.Digest(
            receipt with { Packet = receipt.Packet with { ReviewRequired = false } }, signer.KeyId));
        Assert.Throws<WorkflowException>(() => Canonical.Digest(receipt with { KeyId = "other-key" }, signer.KeyId));
        Assert.Throws<WorkflowException>(() => Canonical.Digest(receipt with { Algorithm = "RS256" }, signer.KeyId));
        Assert.False(await signer.VerifyAsync(receipt with { Signature = Convert.ToBase64String(new byte[256]) },
            CancellationToken.None));
    }

    /// <summary>Tool projections never disclose internal commercial data or accept arbitrary IDs.</summary>
    [Fact]
    public void ProjectionAndFixtureIntegrityAreEnforced()
    {
        var data = Data();
        BlobFixtures.Validate(data);
        var opportunity = data.Opportunities[0];
        var output = HandoffService.ExecuteTool("sales", new("test", "get_opportunity", """{"id":"opp-001"}"""),
            opportunity, data.Products[0], data.Claims);
        Assert.DoesNotContain("internal", output);
        Assert.DoesNotContain("contact", output);
        Assert.Throws<WorkflowException>(() => HandoffService.ExecuteTool("marketing",
            new("test", "get_opportunity", """{"id":"opp-001"}"""), opportunity, data.Products[0], data.Claims));
        Assert.Throws<WorkflowException>(() => BlobFixtures.RequireHash([1, 2], new('a', 64)));
        Assert.Throws<WorkflowException>(() => HandoffService.ExecuteTool("sales",
            new("test", "get_product", """{"id":"product-commuter-01","path":"../../secrets"}"""),
            opportunity, data.Products[0], data.Claims));
    }

    /// <summary>Workload identity is bound to the tenant and exact gateway object, not persona labels.</summary>
    [Fact]
    public void GatewayIdentityChecksExactClaims()
    {
        ClaimsPrincipal User(string oid, string tid) => new(new ClaimsIdentity(
            [new("oid", oid), new("tid", tid)], "test"));
        Assert.True(BackendIdentity.IsGateway(User(Settings.GatewayObjectId, Settings.TenantId), Settings));
        Assert.False(BackendIdentity.IsGateway(User(Settings.ClientId, Settings.TenantId), Settings));
        Assert.False(BackendIdentity.IsGateway(User(Settings.GatewayObjectId, Settings.ClientId), Settings));
    }

    internal sealed class TestFixtures : IFixtures
    {
        public Task<FixtureSnapshot> GetAsync(CancellationToken cancellationToken) => Task.FromResult(Data());
    }

    internal sealed class TestGateway(string opportunityId, string fault = "") : IAgentGateway
    {
        internal int Calls;
        internal List<AgentInput> Prompts = [];
        public Task<AgentTurn> RespondAsync(AgentInput input, string? previousResponseId,
            IReadOnlyList<(string CallId, string Output)> toolOutputs, CancellationToken cancellationToken)
        {
            Calls++;
            Prompts.Add(input);
            var opportunity = Data().Opportunities.Single(o => o.SourceId == opportunityId);
            var claimIds = new[] { "claim-range-01", "claim-positioning-01" };
            ToolCall[] calls = [];
            string text = string.Empty;
            if ((previousResponseId is null && input.Role != "coordinator") || fault == "loop")
                calls = input.Role == "sales"
                    ? [new("test-o", "get_opportunity", Json.Write(new { id = opportunityId })),
                       new("test-p", "get_product", Json.Write(new { id = opportunity.ProductId }))]
                    : [new("test-c", "get_approved_claims", Json.Write(new { id = opportunity.ProductId }))];
            else text = input.Role switch
            {
                "sales" => Json.Write(new SalesResult(opportunityId, opportunity.ProductId,
                    opportunity.RequiredUse is null ? "needs-clarification" : opportunity.RequestedRangeKm > 120 ? "qualified-only" : "supported",
                    [opportunity.ProductId], opportunity.RequiredUse is null ? ["Required use is missing; Sales clarification required."] : [])),
                "marketing" => Json.Write(new MarketingResult(opportunity.ProductId, claimIds, claimIds, true)),
                _ => Json.Write(new CoordinatorResult(opportunityId, claimIds, fault != "coordinator"))
            };
            if (fault == "tool" && calls.Length > 0) calls = [new("test", "publish_campaign", "{}")];
            if (fault == "arguments" && calls.Length > 0) calls = [new("test", "get_opportunity", "{")];
            if (fault == "no-tools") { calls = []; text = "{}"; }
            if (fault == "json" && calls.Length == 0) text = "not json";
            if (fault == "extra" && calls.Length == 0) text = text[..^1] + ",\"internalMargin\":0.3}";
            if (fault == "claims" && input.Role == "marketing" && calls.Length == 0)
                text = Json.Write(new MarketingResult(opportunity.ProductId, ["claim-fake"], ["claim-fake"], true));
            return Task.FromResult(new AgentTurn("", $"test-response-{Calls}", text, calls, 100, fault == "usage" ? 801 : 80));
        }
    }

    internal sealed class BlockingGateway : IAgentGateway
    {
        internal int Started;
        public async Task<AgentTurn> RespondAsync(AgentInput input, string? previousResponseId,
            IReadOnlyList<(string CallId, string Output)> toolOutputs, CancellationToken cancellationToken)
        {
            Interlocked.Increment(ref Started);
            await Task.Delay(Timeout.Infinite, cancellationToken);
            throw new InvalidOperationException("Unreachable.");
        }
    }

    internal sealed class TestSigner : IReceiptSigner
    {
        private static readonly RSA Key = RSA.Create(2048);
        internal string KeyId => Settings.KeyUri.AbsoluteUri;
        public Task<Receipt> SignAsync(ReviewPacket packet, CancellationToken cancellationToken)
        {
            var bytes = Canonical.Bytes(packet);
            var digest = SHA256.HashData(bytes);
            byte[] signature;
            lock (Key) signature = Key.SignHash(digest, HashAlgorithmName.SHA256, RSASignaturePadding.Pss);
            return Task.FromResult(new Receipt(packet, Convert.ToBase64String(bytes), Convert.ToHexStringLower(digest),
                Convert.ToBase64String(signature), KeyId, "PS256"));
        }
        public Task<bool> VerifyAsync(Receipt receipt, CancellationToken cancellationToken)
        {
            var digest = Canonical.Digest(receipt, KeyId);
            lock (Key) return Task.FromResult(Key.VerifyHash(digest, Convert.FromBase64String(receipt.Signature),
                HashAlgorithmName.SHA256, RSASignaturePadding.Pss));
        }
    }

    private sealed class FailingSigner : IReceiptSigner
    {
        public Task<Receipt> SignAsync(ReviewPacket packet, CancellationToken cancellationToken) =>
            throw new WorkflowException(503, "test_signing_unavailable");
        public Task<bool> VerifyAsync(Receipt receipt, CancellationToken cancellationToken) =>
            throw new NotSupportedException();
    }
}
