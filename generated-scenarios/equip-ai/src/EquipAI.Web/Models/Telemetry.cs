using System.Security.Claims;
using System.Text.Json;

namespace EquipAI.Web.Models;

internal sealed record Equipment(int Id, string DeviceId, string Name, string SiteId);
internal sealed record Reading(
    int SchemaVersion, string MessageId, string DeviceId, DateTimeOffset ObservedAtUtc,
    long Sequence, double TemperatureC, double VibrationMmPerSecond, double PressureBar, string OperatingState);
internal sealed record TelemetryQuery(string SiteId, string? DeviceId, int Minutes);
internal sealed record ChatRequest(string Question);
internal sealed record Evidence(
    string EvidenceId, string DeviceId, string SiteId, DateTimeOffset FirstObservedAtUtc,
    DateTimeOffset LastObservedAtUtc, int Count, double TemperatureMaxC,
    double VibrationMaxMmPerSecond, double VibrationChangeMmPerSecond, double PressureMinBar, string Status);
internal sealed record ToolResult(
    string Status, DateTimeOffset AsOfUtc, DateTimeOffset WindowStartUtc, DateTimeOffset WindowEndUtc,
    IReadOnlyList<Evidence> Equipment, string[] EvidenceIds, object Coverage, string[] Warnings);
internal sealed class ScenarioException(string code, string message, int status = 422) : Exception(message)
{
    internal string Code { get; } = code;
    internal int Status { get; } = status;
}

internal static class SiteAccess
{
    internal static readonly string[] AllSites = ["seattle", "tacoma", "everett", "spokane", "yakima"];

    internal static string[] Sites(ClaimsPrincipal user)
    {
        if (user.IsInRole("Operations.Statewide")) return AllSites;
        if (user.IsInRole("Operations.Tacoma")) return ["tacoma"];
        throw new ScenarioException("role_required", "An assigned Operations role is required.", 403);
    }

    internal static void Require(ClaimsPrincipal user, string siteId)
    {
        if (!Sites(user).Contains(siteId, StringComparer.Ordinal))
            throw new ScenarioException("site_forbidden", "This site is outside your assigned Operations scope.", 403);
    }
}

internal sealed class Inventory
{
    internal IReadOnlyList<Equipment> Equipment { get; }

    internal Inventory(string root)
    {
        var path = Path.Combine(root, "SeedData", "equipment.json");
        Equipment = JsonSerializer.Deserialize<Equipment[]>(File.ReadAllText(path))
            ?? throw new InvalidDataException("Equipment inventory is invalid.");
        if (Equipment.Count == 0 || Equipment.Select(e => e.DeviceId).Distinct().Count() != Equipment.Count ||
            Equipment.Any(e => !SiteAccess.AllSites.Contains(e.SiteId)))
            throw new InvalidDataException("Equipment inventory must have unique devices and valid sites.");
    }
}
