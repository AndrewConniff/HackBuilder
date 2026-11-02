using System.Diagnostics;
using System.Text;
using System.Text.Json;
using MobilityCommercial.Web.Models;

namespace MobilityCommercial.Web.Services;

internal sealed class HandoffService(IFixtures fixtures, IAgentGateway agents, IReceiptSigner signer,
    AppSettings settings, ILogger<HandoffService> logger)
{
    private readonly SemaphoreSlim admission = new(4, 4);

    internal async Task<Receipt> RunAsync(HandoffRequest request, string correlationId, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.OpportunityId) || string.IsNullOrWhiteSpace(request.Request)
            || request.Request.Length > 4000)
            throw new WorkflowException(400, "invalid_handoff_request");
        if (!await admission.WaitAsync(0, cancellationToken)) throw new WorkflowException(429, "handoff_overloaded");
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(90));
        try
        {
            var data = await fixtures.GetAsync(deadline.Token);
            var opportunity = data.Opportunities.SingleOrDefault(o => o.SourceId == request.OpportunityId)
                ?? throw new WorkflowException(404, "unknown_opportunity");
            var product = data.Products.SingleOrDefault(p => p.SourceId == opportunity.ProductId)
                ?? throw new WorkflowException(404, "unknown_product");
            var projection = Project(opportunity);
            var approved = data.Claims.Where(c => c.ProductId == product.SourceId).ToArray();
            if (approved.Length == 0) throw new WorkflowException(502, "no_approved_claims");
            var trace = new List<AgentTrace>();
            var budget = new Budget();
            var salesText = await RunAgent("sales", settings.Sales,
                Json.Write(new { opportunity = projection, userRequest = request.Request }), 3);
            var sales = Parse<SalesResult>(salesText);
            var unknowns = opportunity.RequiredUse is null ? new[] { "Required use is missing; Sales clarification required." } : [];
            var expectedFit = unknowns.Length > 0 ? "needs-clarification"
                : opportunity.RequestedRangeKm > 120 ? "qualified-only" : "supported";
            if (sales.OpportunityId != opportunity.SourceId || sales.ProductId != product.SourceId
                || sales.Fit != expectedFit || sales.SourceIds is null || sales.Unknowns is null
                || !sales.SourceIds.SequenceEqual([product.SourceId])
                || !sales.Unknowns.SequenceEqual(unknowns))
                throw new WorkflowException(502, "invalid_sales_handoff");
            var marketingText = await RunAgent("marketing", settings.Marketing,
                Json.Write(new { opportunity = projection, sales }), 3);
            var marketing = Parse<MarketingResult>(marketingText);
            if (marketing.ProductId != product.SourceId || !marketing.ReviewRequired
                || marketing.ClaimIds is null || marketing.SourceIds is null
                || marketing.ClaimIds.Length == 0
                || marketing.ClaimIds.Distinct().Count() != marketing.ClaimIds.Length
                || marketing.ClaimIds.Any(id => !approved.Any(c => c.SourceId == id))
                || !marketing.SourceIds.Order().SequenceEqual(marketing.ClaimIds.Order()))
                throw new WorkflowException(502, "invalid_marketing_handoff");
            var coordinatorText = await RunAgent("coordinator", settings.Coordinator,
                Json.Write(new { opportunity = projection, sales, marketing }), 1);
            var coordinator = Parse<CoordinatorResult>(coordinatorText);
            if (coordinator.OpportunityId != opportunity.SourceId || !coordinator.ReviewRequired
                || coordinator.ClaimIds is null || !coordinator.ClaimIds.SequenceEqual(marketing.ClaimIds))
                throw new WorkflowException(502, "invalid_coordinator_handoff");
            var claims = marketing.ClaimIds.Select(id => approved.Single(c => c.SourceId == id)).ToArray();
            var packet = new ReviewPacket("Adventure Works Cycles", correlationId, opportunity.SourceId,
                product.SourceId, opportunity.Audience, expectedFit, unknowns,
                claims.Select(c => c.PermittedWording).ToArray(),
                claims.Select(c => c.Caveat).Append("No 200 km or all-condition range guarantee. Human review required.")
                    .Distinct().ToArray(),
                new[] { new SourceReference(product.SourceId, product.Version) }
                    .Concat(claims.Select(c => new SourceReference(c.SourceId, c.Version))).ToArray(),
                opportunity.SalesOwner, opportunity.MarketingOwner, true, data.ManifestSha256, trace.ToArray());
            return await signer.SignAsync(packet, deadline.Token);

            async Task<string> RunAgent(string role, AgentPin pin, string prompt, int maxTurns)
            {
                var installation = data.Agents.SingleOrDefault(a => a.Name == pin.Name && a.Version == pin.Version);
                if (installation is null || string.IsNullOrWhiteSpace(installation.Id) || installation.Model != settings.Model)
                    throw new WorkflowException(503, "agent_installation_mismatch");
                var clock = Stopwatch.StartNew();
                var seenTools = new HashSet<string>(StringComparer.Ordinal);
                string? previous = null;
                List<(string CallId, string Output)> outputs = [];
                for (var attempt = 0; attempt < maxTurns; attempt++)
                {
                    var inputBytes = Encoding.UTF8.GetByteCount(prompt) + outputs.Sum(o => Encoding.UTF8.GetByteCount(o.Output));
                    budget.Reserve(inputBytes);
                    var turn = await agents.RespondAsync(new(role, pin, prompt), previous, outputs, deadline.Token);
                    budget.Reconcile(turn);
                    logger.LogInformation("Agent stage {Stage} response {ResponseId} correlation {CorrelationId} tokens {Tokens}",
                        role, turn.ResponseId, correlationId, turn.InputTokens + turn.OutputTokens);
                    if (string.IsNullOrWhiteSpace(turn.ResponseId) || turn.Calls.Length > 4)
                        throw new WorkflowException(502, "invalid_agent_response");
                    var toolNames = turn.Calls.Select(c => c.Name).ToArray();
                    trace.Add(new(pin.Name, pin.Version, installation.Id, turn.ResponseId,
                        turn.InputTokens, turn.OutputTokens, toolNames, clock.ElapsedMilliseconds));
                    if (turn.Calls.Length == 0)
                    {
                        var required = role switch
                        {
                            "sales" => new[] { "get_opportunity", "get_product" },
                            "marketing" => new[] { "get_approved_claims" },
                            _ => []
                        };
                        if (!required.All(seenTools.Contains))
                            throw new WorkflowException(502, "missing_grounding_tool");
                        return turn.Text;
                    }
                    if (role == "coordinator" || attempt == maxTurns - 1
                        || turn.Calls.Select(c => c.CallId).Distinct().Count() != turn.Calls.Length)
                        throw new WorkflowException(502, "agent_tool_budget_exceeded");
                    outputs = [];
                    foreach (var call in turn.Calls)
                    {
                        string output;
                        try { output = ExecuteTool(role, call, opportunity, product, approved); }
                        catch (JsonException) { throw new WorkflowException(502, "invalid_tool_arguments"); }
                        seenTools.Add(call.Name);
                        outputs.Add((call.CallId, output));
                    }
                    previous = turn.ResponseId;
                }
                throw new WorkflowException(502, "agent_turn_limit");
            }
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new WorkflowException(504, "handoff_deadline_exceeded");
        }
        finally { admission.Release(); }
    }

    internal static SalesProjection Project(Opportunity opportunity) => new(opportunity.SourceId,
        opportunity.ProductId, opportunity.Audience, opportunity.RequiredUse, opportunity.RequestedRangeKm);

    internal static string ExecuteTool(string role, ToolCall call, Opportunity opportunity,
        Product product, ApprovedClaim[] claims)
    {
        if ((role, call.Name) is not (("sales", "get_opportunity") or ("sales", "get_product")
            or ("marketing", "get_approved_claims")))
            throw new WorkflowException(502, "tool_not_allowed");
        using var arguments = JsonDocument.Parse(call.Arguments);
        var root = arguments.RootElement;
        if (root.ValueKind != JsonValueKind.Object || root.EnumerateObject().Count() != 1
            || !root.TryGetProperty("id", out var id) || id.ValueKind != JsonValueKind.String)
            throw new WorkflowException(502, "invalid_tool_arguments");
        return (role, call.Name, id.GetString()) switch
        {
            ("sales", "get_opportunity", var value) when value == opportunity.SourceId => Json.Write(Project(opportunity)),
            ("sales", "get_product", var value) when value == product.SourceId => Json.Write(product),
            ("marketing", "get_approved_claims", var value) when value == product.SourceId => Json.Write(claims),
            _ => throw new WorkflowException(502, "tool_not_allowed")
        };
    }

    private static T Parse<T>(string text)
    {
        try { return Json.Read<T>(text); }
        catch (JsonException) { throw new WorkflowException(502, "invalid_agent_json"); }
    }

    internal sealed class Budget
    {
        internal int Calls { get; private set; }
        internal int Tokens { get; private set; }
        private int previousInputBound;

        internal void Reserve(int inputBytes)
        {
            // One token per UTF-8 byte is a conservative bound; reserve history and installed instructions/tools too.
            previousInputBound += inputBytes + 2000;
            if (Calls >= 7 || Tokens + previousInputBound + 800 > 30000)
                throw new WorkflowException(502, "agent_budget_exceeded");
            Calls++;
        }

        internal void Reconcile(AgentTurn turn)
        {
            if (turn.InputTokens < 0 || turn.OutputTokens < 0 || turn.OutputTokens > 800
                || (long)Tokens + turn.InputTokens + turn.OutputTokens > 30000)
                throw new WorkflowException(502, "agent_usage_exceeded");
            Tokens += turn.InputTokens + turn.OutputTokens;
        }
    }
}
