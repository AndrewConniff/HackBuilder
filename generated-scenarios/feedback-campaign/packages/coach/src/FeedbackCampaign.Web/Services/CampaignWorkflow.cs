namespace FeedbackCampaign.Web;

public sealed class CampaignWorkflow(IStateStore store, RuleService rules, IFoundryAgent agent)
{
    public async Task<Versioned<Case>> Submit(Post post, string actor)
    {
        post.Validate();
        var item = new Case(post.CaseId, post, await rules.Current(), "Received", "CampaignListener",
            null, null, null, null, [new(DateTimeOffset.UtcNow, actor, "Received")]);
        await store.Add("cases", item.Id, item);
        var existing = (await store.Get<Case>("cases", item.Id))!;
        if (existing.Value.Post != post) throw new InvalidOperationException("Source ID is already bound to a different post.");
        return existing;
    }

    public async Task Process(Versioned<Case> stored, CancellationToken cancellation)
    {
        var item = stored.Value;
        if (item.Status != "Received") return;
        try
        {
            var result = await agent.Analyze(item.Post, item.Rules, cancellation);
            var owner = Control.Route(result.Analysis, item.Rules);
            var next = item with { Analysis = result.Analysis, AgentResponseId = result.ResponseId, Owner = owner,
                Status = owner == "Auto" ? "PendingSend" : "AwaitingHuman",
                Reply = owner == "Auto" ? result.Analysis.Draft : null,
                Audit = [.. item.Audit, new(DateTimeOffset.UtcNow, "CampaignListener", $"Routed:{owner}:{item.Rules.Version}")] };
            await store.Replace("cases", item.Id, next, stored.ETag);
        }
        catch (Azure.RequestFailedException ex) when (ex.Status == 412) { throw; }
        catch (Exception ex) when (ex is not OperationCanceledException || !cancellation.IsCancellationRequested)
        {
            // No raw prompt, post or provider response goes into errors/telemetry.
            await store.Replace("cases", item.Id, item with { Status = "Failed", Error = ex.GetType().Name,
                Audit = [.. item.Audit, new(DateTimeOffset.UtcNow, "CampaignListener", "AnalysisFailed")] }, stored.ETag);
        }
    }

    public async Task Review(string id, string etag, string reply, string actor, string[] roles)
    {
        var stored = await store.Get<Case>("cases", id) ?? throw new ArgumentException("Unknown case.");
        Control.RequireReviewer(stored.Value, roles);
        if (string.IsNullOrWhiteSpace(reply) || reply.Length > 4000) throw new ArgumentException("Reply must contain 1-4000 characters.");
        var next = stored.Value with { Reply = reply, Status = "PendingSend",
            Audit = [.. stored.Value.Audit, new(DateTimeOffset.UtcNow, actor, "HumanApprovedAndQueued")] };
        await store.Replace("cases", id, next, etag);
    }

    public async Task Retry(string id, string etag, string actor)
    {
        var stored = await store.Get<Case>("cases", id) ?? throw new ArgumentException("Unknown case.");
        if (stored.Value.Status != "Failed") throw new InvalidOperationException("Only Failed cases can be retried.");
        await store.Replace("cases", id, stored.Value with { Status = "Received", Error = null,
            Audit = [.. stored.Value.Audit, new(DateTimeOffset.UtcNow, actor, "RetryRequested")] }, etag);
    }
}
