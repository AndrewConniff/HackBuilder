using System.Security.Cryptography;
using System.Text;

namespace FeedbackCampaign.Web;

public sealed record Post(string SourceId, string PosterName, string Contact, string Campaign, string Subject, string Body)
{
    public string CaseId => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(SourceId))).ToLowerInvariant();
    public void Validate()
    {
        if (new[] { SourceId, PosterName, Contact, Campaign, Subject, Body }.Any(string.IsNullOrWhiteSpace)
            || SourceId.Length > 128 || PosterName.Length > 120 || Contact.Length > 254
            || Campaign.Length > 100 || Subject.Length > 200 || Body.Length > 6000
            || !Contact.Contains('@') || Contact.Contains('\n') || Contact.Contains('\r'))
            throw new ArgumentException("A bounded source ID, poster, contact, campaign, subject and body are required.");
    }
}

public sealed record Scores(double Positive, double Negative, double Neutral)
{
    public void Validate()
    {
        if (new[] { Positive, Negative, Neutral }.Any(v => !double.IsFinite(v) || v < 0 || v > 1)
            || Math.Abs(Positive + Negative + Neutral - 1) > .02)
            throw new ArgumentException("Invalid sentiment vector; no action is permitted.");
    }
}

public sealed record Analysis(Scores Overall, Scores Company, Scores Product, string Assessment,
    string Investigation, string FutureAction, string Draft, string PolicyCitation)
{
    public void Validate()
    {
        Overall.Validate(); Company.Validate(); Product.Validate();
        if (new[] { Assessment, Investigation, FutureAction, Draft }.Any(string.IsNullOrWhiteSpace)
            || new[] { Assessment, Investigation, FutureAction, Draft }.Any(v => v.Length > 4000)
            || PolicyCitation != "campaign-policy-v1")
            throw new ArgumentException("Agent response lacks bounded fields or a valid policy citation.");
    }
}

public sealed record Rules(string Version, double PositiveThreshold, double NegativeThreshold,
    bool ProductRouting, double ProductNegativeThreshold, string Author, string Reason)
{
    public static Rules Initial => new("v1", .80, .89, false, .80, "installation", "Original intake rule; illustrative 80% negative is not active.");
    public void Validate()
    {
        if (string.IsNullOrWhiteSpace(Version) || Version.Length > 80 || !Version.All(c => char.IsAsciiLetterOrDigit(c) || c == '-')
            || new[] { PositiveThreshold, NegativeThreshold, ProductNegativeThreshold }.Any(v => !double.IsFinite(v) || v < .5 || v > 1)
            || string.IsNullOrWhiteSpace(Author) || string.IsNullOrWhiteSpace(Reason) || Reason.Length > 500)
            throw new ArgumentException("Rules need a safe version, thresholds in [0.5,1], author and reason.");
    }
}

public static class Control
{
    public static string Route(Analysis analysis, Rules rules)
    {
        analysis.Validate(); rules.Validate();
        if (analysis.Overall.Positive >= rules.PositiveThreshold) return "Auto";
        if (analysis.Overall.Negative >= rules.NegativeThreshold
            || rules.ProductRouting && analysis.Product.Negative >= rules.ProductNegativeThreshold)
            return "ProductManager";
        return "ConflictResolutionSpecialist";
    }

    public static void RequireReviewer(Case item, string[] roles)
    {
        if (item.Status != "AwaitingHuman") throw new InvalidOperationException("Case is not awaiting human review.");
        if (!roles.Contains(item.Owner)) throw new UnauthorizedAccessException("The assigned reviewer role is required.");
    }
}

public sealed record Audit(DateTimeOffset At, string Actor, string Action);
public sealed record Case(string Id, Post Post, Rules Rules, string Status, string Owner,
    Analysis? Analysis, string? AgentResponseId, string? Reply, string? Error, List<Audit> Audit);
public sealed record Versioned<T>(T Value, string ETag);
public sealed record ActiveRules(string Version, string PromotedBy, string Reason, List<Audit>? History = null);
