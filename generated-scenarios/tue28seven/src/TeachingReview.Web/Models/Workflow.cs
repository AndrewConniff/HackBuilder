namespace TeachingReview.Web.Models;

internal sealed record Teacher(int Id, string Username, string FullName, string Role, string PasswordHash,
    int FailedLogins = 0, DateTimeOffset? LockedUntil = null);

internal sealed record ReviewReceipt(string Kind, string Agent, string ResponseId, string Findings);

internal sealed record AuditEntry(DateTimeOffset AtUtc, int ActorId, int Version, string Action, string Evidence = "");

internal sealed record Material(int Id, string Title, string Text, string Rubric, int AuthorId, int PeerId, int LeadId)
{
    public int Version { get; set; } = 1;
    public string Stage { get; set; } = "Draft";
    public int Attempts { get; set; }
    public string AttemptId { get; set; } = string.Empty;
    public List<ReviewReceipt> Reviews { get; set; } = [];
    public string Feedback { get; set; } = string.Empty;
    public string Failure { get; set; } = string.Empty;
    public List<AuditEntry> History { get; set; } = [];
}

internal sealed record SchoolState(List<Teacher> Teachers, List<Material> Materials);
internal sealed record Snapshot(SchoolState State, string Revision);
internal sealed class WorkflowException(string message) : Exception(message);
