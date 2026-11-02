using TeachingReview.Web.Models;

namespace TeachingReview.Web.Services;

internal sealed class WorkflowService(IStateStore store, IReviewer reviewer, ILogger<WorkflowService> logger)
{
    internal async Task ExecuteAsync(int actorId, int id, int expectedVersion, string action, string? text,
        CancellationToken cancellationToken = default)
    {
        var snapshot = await store.ReadAsync(cancellationToken);
        var actor = snapshot.State.Teachers.SingleOrDefault(x => x.Id == actorId)
            ?? throw new WorkflowException("Account is not authorized.");
        var material = snapshot.State.Materials.SingleOrDefault(x => x.Id == id)
            ?? throw new WorkflowException("Material is not available.");
        if (material.Version != expectedVersion)
            throw new WorkflowException("This material version is stale. Reload before deciding.");
        if (action == "Review")
        {
            Require(actor.Id == material.AuthorId && actor.Role == "Author", "Only the author can request review.");
            Require(material.Stage is "Draft" or "Failed", "Material is not ready for AI review.");
            Require(material.Attempts < 3, "Review retry limit reached. Revise the material before another attempt.");
            Require(!string.IsNullOrWhiteSpace(material.Text) && material.Text.Length <= 12000,
                "Material must contain 1-12,000 characters.");
            Require(!string.IsNullOrWhiteSpace(material.Rubric) && material.Rubric.Length <= 4000,
                "A rubric of 1-4,000 characters is required.");
            material.Stage = "Reviewing";
            material.Attempts++;
            material.AttemptId = Guid.NewGuid().ToString("N");
            material.Reviews.Clear();
            material.Failure = string.Empty;
            material.History.Add(new(DateTimeOffset.UtcNow, actorId, material.Version, "Review started"));
            await store.WriteAsync(snapshot.State, snapshot.Revision, cancellationToken);
            await CompleteReviewAsync(material, actorId);
            return;
        }
        switch (action)
        {
            case "Recover":
                Require(actor.Id == material.AuthorId && actor.Role == "Author", "Only the author can recover a review.");
                Require(material.Stage == "Reviewing" && material.History.Last().AtUtc <
                    DateTimeOffset.UtcNow.AddMinutes(-3), "Only an abandoned review older than three minutes can be recovered.");
                material.Stage = "Failed";
                material.Failure = "Abandoned review recovered. No success is assumed; request a fresh bounded attempt.";
                material.AttemptId = string.Empty;
                break;
            case "Feedback":
                Require(actor.Id == material.PeerId && actor.Role == "Peer", "Only the assigned peer can give feedback.");
                Require(material.Stage == "AwaitingPeer" && material.Reviews.Count == 2, "Both AI reviews are required.");
                Require(!string.IsNullOrWhiteSpace(text) && text.Length <= 4000, "Enter 1-4,000 characters of feedback.");
                material.Feedback = text!;
                material.Stage = "AwaitingAuthor";
                break;
            case "Revise":
                Require(actor.Id == material.AuthorId && actor.Role == "Author", "Only the author can revise.");
                Require(material.Stage != "Reviewing", "Wait for the current review to finish.");
                Require(!string.IsNullOrWhiteSpace(text) && text.Length <= 12000, "Enter 1-12,000 characters of material.");
                material.History.Add(new(DateTimeOffset.UtcNow, actorId, material.Version, "Superseded version",
                    System.Text.Json.JsonSerializer.Serialize(new
                    {
                        material.Text, material.Rubric, material.Reviews, material.Feedback
                    })));
                var revised = material with { Text = text! };
                revised.Version++;
                revised.Stage = "Draft";
                revised.Attempts = 0;
                revised.AttemptId = string.Empty;
                revised.Reviews.Clear();
                revised.Feedback = string.Empty;
                revised.Failure = string.Empty;
                snapshot.State.Materials[snapshot.State.Materials.IndexOf(material)] = revised;
                material = revised;
                break;
            case "SendToLead":
                Require(actor.Id == material.AuthorId && actor.Role == "Author", "Only the author can accept feedback.");
                Require(material.Stage == "AwaitingAuthor", "Peer feedback is required for this version.");
                material.Stage = "AwaitingLead";
                break;
            case "Approve":
            case "Reject":
                Require(actor.Id == material.LeadId && actor.Role == "Lead", "Only the assigned lead can decide.");
                Require(material.Stage == "AwaitingLead" && material.Reviews.Count == 2 &&
                    !string.IsNullOrWhiteSpace(material.Feedback), "Current AI and human reviews are required.");
                material.Stage = action == "Approve" ? "Approved" : "NeedsRevision";
                break;
            default:
                throw new WorkflowException("Unknown workflow action.");
        }
        material.History.Add(new(DateTimeOffset.UtcNow, actorId, material.Version, action));
        await store.WriteAsync(snapshot.State, snapshot.Revision, cancellationToken);
        logger.LogInformation("Material {MaterialId} version {Version}: {Action} by {ActorId}",
            id, material.Version, action, actorId);
    }

    private async Task CompleteReviewAsync(Material material, int actorId)
    {
        var receipts = new List<ReviewReceipt>();
        string failure = string.Empty;
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(120));
        try
        {
            foreach (var kind in new[] { "Curriculum", "Accessibility" })
                receipts.Add(await reviewer.ReviewAsync(kind, material, deadline.Token));
        }
        catch (Exception error) when (error is Azure.RequestFailedException or System.ClientModel.ClientResultException
            or OperationCanceledException or InvalidDataException or InvalidOperationException)
        {
            logger.LogError(error, "Review attempt {AttemptId} failed for material {MaterialId}",
                material.AttemptId, material.Id);
            failure = "AI review failed or timed out. Approval is blocked; inspect the correlation log and retry explicitly.";
        }
        using var persistDeadline = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var latest = await store.ReadAsync(persistDeadline.Token);
        var current = latest.State.Materials.Single(x => x.Id == material.Id);
        Require(current.Version == material.Version && current.AttemptId == material.AttemptId &&
            current.Stage == "Reviewing", "Review result belongs to a stale or superseded attempt.");
        current.Reviews = receipts;
        current.Stage = failure.Length == 0 ? "AwaitingPeer" : "Failed";
        current.Failure = failure;
        current.History.Add(new(DateTimeOffset.UtcNow, actorId, material.Version, current.Stage,
            System.Text.Json.JsonSerializer.Serialize(new { Receipts = receipts, Failure = failure })));
        await store.WriteAsync(latest.State, latest.Revision, persistDeadline.Token);
        logger.LogInformation("Review attempt {AttemptId} completed with {Stage}", material.AttemptId, current.Stage);
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new WorkflowException(message);
    }
}
