using System.Text.Json;
using System.Text.Json.Serialization;

namespace MobilityCommercial.Web.Models;

internal static class Json
{
    internal static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false,
        RespectRequiredConstructorParameters = true
    };

    internal static T Read<T>(string text) =>
        JsonSerializer.Deserialize<T>(text, Options) ?? throw new JsonException("Missing JSON object.");

    internal static T ReadSeed<T>(string text) =>
        JsonSerializer.Deserialize<T>(text, new JsonSerializerOptions(Options) { PropertyNamingPolicy = null })
        ?? throw new JsonException("Missing seed data.");

    internal static string Write<T>(T value) => JsonSerializer.Serialize(value, Options);
}

internal sealed record Product(int Id, string SourceId, string Version, string Name,
    string Category, string RangeStatement);
internal sealed record Opportunity(int Id, string SourceId, string ProductId, string Audience,
    string? RequiredUse, int? RequestedRangeKm, string SalesOwner, string MarketingOwner,
    decimal InternalMargin, decimal InternalDiscount, string Contact);
internal sealed record ApprovedClaim(int Id, string SourceId, string Version, string ProductId,
    string PermittedWording, string Caveat);
internal sealed record FixtureFile(string Name, string VersionId, string Sha256);
internal sealed record AgentInstall(string Name, string Version, string Id, string Model, string DefinitionSha256);
internal sealed record FixtureManifest(int SchemaVersion, string CompanyName, FixtureFile[] Files, AgentInstall[] Agents);
internal sealed record FixtureSnapshot(Product[] Products, Opportunity[] Opportunities,
    ApprovedClaim[] Claims, string ManifestSha256, AgentInstall[] Agents);
internal sealed record HandoffRequest(string OpportunityId, string Request);
internal sealed record SalesProjection(string OpportunityId, string ProductId, string Audience,
    string? RequiredUse, int? RequestedRangeKm);
internal sealed record SalesResult(string OpportunityId, string ProductId, string Fit,
    string[] SourceIds, string[] Unknowns);
internal sealed record MarketingResult(string ProductId, string[] ClaimIds, string[] SourceIds,
    bool ReviewRequired);
internal sealed record CoordinatorResult(string OpportunityId, string[] ClaimIds, bool ReviewRequired);
internal sealed record SourceReference(string SourceId, string Version);
internal sealed record AgentTrace(string AgentName, string AgentVersion, string AgentId,
    string ResponseId, int InputTokens, int OutputTokens, string[] Tools, long DurationMs);
internal sealed record ReviewPacket(string CompanyName, string CorrelationId, string OpportunityId,
    string ProductId, string Audience, string Fit, string[] Unknowns, string[] Draft,
    string[] Caveats, SourceReference[] Sources, string SalesOwner, string MarketingOwner,
    bool ReviewRequired, string FixtureManifestSha256, AgentTrace[] Trace);
internal sealed record Receipt(ReviewPacket Packet, string CanonicalPayload, string Sha256,
    string Signature, string KeyId, string Algorithm);
internal sealed record ToolCall(string CallId, string Name, string Arguments);
internal sealed record AgentTurn(string AgentId, string ResponseId, string Text,
    ToolCall[] Calls, int InputTokens, int OutputTokens);
internal sealed record AgentPin(string Name, string Version);
internal sealed record AgentInput(string Role, AgentPin Pin, string Prompt);

internal sealed class WorkflowException(int status, string code) : Exception(code)
{
    internal int Status { get; } = status;
    internal string Code { get; } = code;
}
