using System.Globalization;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using EquipAI.Web.Models;

namespace EquipAI.Web.Services;

internal static class TelemetryEngine
{
    internal static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    internal static Reading ParseEnvelope(string line, DateTimeOffset now)
    {
        using var envelope = JsonDocument.Parse(line);
        var root = envelope.RootElement;
        var system = root.GetProperty("SystemProperties");
        var device = system.GetProperty("connectionDeviceId").GetString();
        var enqueued = root.TryGetProperty("EnqueuedTimeUtc", out var stamp)
            ? stamp.GetDateTimeOffset() : system.GetProperty("enqueuedTime").GetDateTimeOffset();
        var body = root.GetProperty("Body");
        Reading? reading;
        if (body.ValueKind == JsonValueKind.Object) reading = body.Deserialize<Reading>(Json);
        else if (body.ValueKind == JsonValueKind.String)
        {
            var content = body.GetString() ?? throw new InvalidDataException("Missing routed event body.");
            // IoT JSON routing emits base64 when content encoding/type were not set on the device message.
            reading = content.TrimStart().StartsWith('{')
                ? JsonSerializer.Deserialize<Reading>(content, Json)
                : JsonSerializer.Deserialize<Reading>(Convert.FromBase64String(content), Json);
        }
        else throw new InvalidDataException("Unsupported routed event body.");
        if (reading is null || reading.SchemaVersion != 1 || reading.DeviceId != device ||
            string.IsNullOrWhiteSpace(device) || device.Length > 128 ||
            string.IsNullOrWhiteSpace(reading.MessageId) || reading.MessageId.Length > 128 ||
            reading.Sequence < 0 || reading.ObservedAtUtc.Offset != TimeSpan.Zero ||
            enqueued > now.AddMinutes(2) || reading.ObservedAtUtc > now.AddMinutes(2) ||
            reading.ObservedAtUtc > enqueued.AddMinutes(2) ||
            !double.IsFinite(reading.TemperatureC) || reading.TemperatureC is < -50 or > 200 ||
            !double.IsFinite(reading.VibrationMmPerSecond) || reading.VibrationMmPerSecond is < 0 or > 100 ||
            !double.IsFinite(reading.PressureBar) || reading.PressureBar is < 0 or > 500 ||
            reading.OperatingState is not ("running" or "idle" or "stopped"))
            throw new InvalidDataException("Invalid device identity, schema, clock or measurement.");
        return reading;
    }

    internal static bool IsFresh(Reading reading, DateTimeOffset now) =>
        reading.ObservedAtUtc > now.AddHours(-2) && reading.ObservedAtUtc <= now;

    internal static Reading[] Deduplicate(IEnumerable<Reading> readings) =>
        readings.GroupBy(r => (r.DeviceId, r.MessageId))
            .Select(group =>
            {
                if (group.Distinct().Skip(1).Any())
                    throw new ScenarioException("conflicting_replay", "Conflicting replayed telemetry; evidence rejected.");
                return group.First();
            }).ToArray();

    internal static ToolResult Summarize(
        Inventory inventory, IEnumerable<Reading> readings, ClaimsPrincipal user,
        TelemetryQuery query, DateTimeOffset now, int invalid,
        IReadOnlyDictionary<string, int>? excludedExpired = null)
    {
        SiteAccess.Require(user, query.SiteId);
        if (query.Minutes is < 1 or > 120)
            throw new ScenarioException("invalid_window", "Choose a UTC window from 1 to 120 minutes.", 400);
        var equipment = inventory.Equipment.Where(e => e.SiteId == query.SiteId &&
            (query.DeviceId is null || e.DeviceId == query.DeviceId)).ToArray();
        if (equipment.Length == 0)
            throw new ScenarioException("unknown_equipment", "Unknown equipment; specify an exact authorized device.", 404);
        if (equipment.Length > 20)
            throw new ScenarioException("narrow_scope", "Narrow the query to at most 20 equipment items.");
        var start = now.AddMinutes(-query.Minutes);
        var selected = equipment.Select(e => e.DeviceId).ToHashSet(StringComparer.Ordinal);
        var scoped = readings.Where(r => selected.Contains(r.DeviceId)).ToArray();
        var fresh = Deduplicate(scoped.Where(r =>
            IsFresh(r, now) && r.ObservedAtUtc >= start));
        var evidence = new List<Evidence>();
        var missing = new List<string>();
        foreach (var item in equipment)
        {
            var events = fresh.Where(r => r.DeviceId == item.DeviceId)
                .OrderBy(r => r.ObservedAtUtc).ThenBy(r => r.Sequence).ToArray();
            if (events.Length == 0) { missing.Add(item.DeviceId); continue; }
            var first = events[0];
            var last = events[^1];
            var identity = string.Join('|', events.Select(r =>
                $"{r.DeviceId}:{r.MessageId}:{r.ObservedAtUtc.ToString("O", CultureInfo.InvariantCulture)}"));
            var id = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(identity)))[..20];
            evidence.Add(new(id, item.DeviceId, item.SiteId, first.ObservedAtUtc, last.ObservedAtUtc,
                events.Length, events.Max(r => r.TemperatureC), events.Max(r => r.VibrationMmPerSecond),
                last.VibrationMmPerSecond - first.VibrationMmPerSecond, events.Min(r => r.PressureBar),
                last.ObservedAtUtc <= now.AddMinutes(-5) ? "stale" : last.OperatingState));
        }
        var warnings = missing.Select(id => $"{id}: no fresh telemetry; offline or missing").ToList();
        if (invalid > 0) warnings.Add("Invalid ingestion records were rejected; coverage may be incomplete.");
        return new(
            evidence.Count == 0 ? "no_fresh_data" : warnings.Count > 0 ? "partial" : "ok",
            now, start, now, evidence, evidence.Select(e => e.EvidenceId).ToArray(),
            new { expectedDevices = equipment.Length, reportingDevices = evidence.Count, missingDevices = missing,
                expiredReadingsExcluded = scoped.Where(reading => reading.ObservedAtUtc <= now.AddHours(-2))
                    .Select(reading => (reading.DeviceId, reading.MessageId)).Distinct().Count() +
                    selected.Sum(device => excludedExpired?.GetValueOrDefault(device) ?? 0) },
            warnings.ToArray());
    }
}
