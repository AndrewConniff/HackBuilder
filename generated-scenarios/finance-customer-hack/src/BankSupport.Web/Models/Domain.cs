namespace BankSupport.Web.Models;

/// <summary>Catalog-backed local account with a durable revocation and lockout record.</summary>
public sealed record LocalAccount(
    string Username, string DisplayName, string Role, string CustomerId, string PasswordHash,
    string Stamp, int Failures = 0, DateTimeOffset? LockedUntil = null);

/// <summary>Read-only synthetic banking record, with amounts represented in integer cents.</summary>
public sealed record BankRecord(int Id, string CustomerId, string Kind, long AmountCents, string Detail, string Date);

/// <summary>Authoritative synthetic banking policy.</summary>
public sealed record Policy(string Id, string Title, string Text);

/// <summary>Bounded customer or representative message.</summary>
public sealed record Message(string Role, string Text, DateTimeOffset At);

/// <summary>Execution metadata, excluding prompts, credentials and hidden reasoning.</summary>
public sealed record AgentReceipt(string Name, string Version, string ResponseId, string Route, string[] Sources);

/// <summary>Immutable durable case state. The storage ETag independently guards every replacement.</summary>
public sealed record ServiceCase(
    string Id, string CustomerId, string Status, string Owner, int Version,
    DateTimeOffset UpdatedAt, Message[] Messages, AgentReceipt[] Receipts, string Error = "");

/// <summary>Stored value and its optimistic-concurrency token.</summary>
public sealed record Stored<T>(T Value, string ETag);

/// <summary>Installed agent versions and ownership signature.</summary>
public sealed record AgentConfiguration(string TriageVersion, string KnowledgeVersion, string DefinitionDigest);

/// <summary>Typed triage result from the actual Foundry response.</summary>
public sealed record RouteDecision(string Route);

/// <summary>Grounded specialist result from the actual Foundry response.</summary>
public sealed record KnowledgeAnswer(string Answer, string[] Sources, bool Escalate);

/// <summary>Business rejection that must be displayed with a non-success HTTP status.</summary>
public sealed class BusinessException(int statusCode, string message) : Exception(message)
{
    /// <summary>HTTP status appropriate to the rejected operation.</summary>
    public int StatusCode { get; } = statusCode;
}
