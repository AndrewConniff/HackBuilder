using Azure;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using EquipAI.Web.Models;

namespace EquipAI.Web.Services;

internal sealed record TelemetrySnapshot(
    Reading[] Readings, int Invalid, DateTimeOffset LoadedAtUtc, IReadOnlyDictionary<string, int> ExpiredByDevice);

internal sealed class TelemetryCacheBudget
{
    internal const long Limit = 512L * 1024 * 1024;
    // Reserve source/decoder buffers; per-record estimates include strings, indexes and deduplication overhead.
    private long reserved = 256L * 1024 * 1024;

    internal void Add(Reading reading)
    {
        var estimate = 512L + 4L * (reading.DeviceId.Length + reading.MessageId.Length + reading.OperatingState.Length);
        if (Interlocked.Add(ref reserved, estimate) > Limit)
            throw new ScenarioException("cache_limit", "Telemetry exceeds the conservative 512 MiB cache budget.");
    }
}

internal sealed class BlobTelemetry(BlobContainerClient container, TimeProvider clock, ILogger<BlobTelemetry> logger)
{
    private readonly SemaphoreSlim gate = new(1);
    private TelemetrySnapshot? snapshot;
    private const long ByteLimit = 128L * 1024 * 1024;
    private const int BlobLimit = 1024;

    internal async Task<TelemetrySnapshot> ReadAsync(CancellationToken cancellationToken)
    {
        await gate.WaitAsync(cancellationToken);
        try
        {
            var now = clock.GetUtcNow();
            if (snapshot is not null && now - snapshot.LoadedAtUtc < TimeSpan.FromSeconds(30)) return snapshot;
            snapshot = null;
            var blobs = new List<BlobItem>();
            long bytes = 0;
            // Hour prefixes include skew/late batching overlap; exact observation validity is checked after parsing.
            for (var hour = now.AddHours(-3); hour <= now; hour = hour.AddHours(1))
            {
                var prefix = hour.ToString("yyyy/MM/dd/HH/", System.Globalization.CultureInfo.InvariantCulture);
                await foreach (var blob in container.GetBlobsAsync(
                    BlobTraits.None, BlobStates.None, prefix, cancellationToken))
                {
                    bytes += blob.Properties.ContentLength ?? ByteLimit + 1;
                    if (blobs.Count >= BlobLimit || bytes > ByteLimit)
                        throw new ScenarioException("retrieval_limit", "Telemetry scan exceeds 1,024 blobs or 128 MiB.");
                    blobs.Add(blob);
                }
            }
            var results = new (Reading[] Events, int Invalid, Dictionary<string, int> Expired)[blobs.Count];
            var budget = new TelemetryCacheBudget();
            await Parallel.ForEachAsync(Enumerable.Range(0, blobs.Count),
                new ParallelOptions { MaxDegreeOfParallelism = 8, CancellationToken = cancellationToken },
                async (index, token) => results[index] = await ParseBlobAsync(blobs[index], now, token, budget));
            var readings = TelemetryEngine.Deduplicate(results.SelectMany(r => r.Events));
            var expired = results.SelectMany(result => result.Expired).GroupBy(pair => pair.Key)
                .ToDictionary(group => group.Key, group => group.Sum(pair => pair.Value), StringComparer.Ordinal);
            snapshot = new(readings, results.Sum(r => r.Invalid), now, expired);
            logger.LogInformation("Telemetry scan completed: {BlobCount} blobs, {EventCount} events, {Invalid} rejected",
                blobs.Count, readings.Length, snapshot.Invalid);
            return snapshot;
        }
        finally { gate.Release(); }
    }

    private async Task<(Reading[] Events, int Invalid, Dictionary<string, int> Expired)> ParseBlobAsync(
        BlobItem item, DateTimeOffset now, CancellationToken token, TelemetryCacheBudget? budget = null)
    {
        if (item.Properties.ContentLength is not { } lengthLimit || lengthLimit > 10 * 1024 * 1024)
            throw new ScenarioException("oversize_batch", "A routed batch exceeds the 10 MiB ingestion limit.");
        var client = container.GetBlobClient(item.Name);
        var response = await client.DownloadStreamingAsync(new BlobDownloadOptions
        {
            Conditions = new BlobRequestConditions { IfMatch = item.Properties.ETag }
        }, token);
        await using var stream = response.Value.Content;
        using var reader = new StreamReader(stream);
        var events = new List<Reading>();
        var expired = new Dictionary<string, int>(StringComparer.Ordinal);
        int invalid = 0;
        long length = 0;
        while (await reader.ReadLineAsync(token) is { } line)
        {
            length += System.Text.Encoding.UTF8.GetByteCount(line) + 1;
            if (length > (item.Properties.ContentLength ?? 0) + 1 || line.Length > 64 * 1024)
                throw new ScenarioException("oversize_blob", "Telemetry blob/record exceeded its declared bounds.");
            if (string.IsNullOrWhiteSpace(line)) continue;
            try
            {
                var reading = TelemetryEngine.ParseEnvelope(line, now);
                if (budget is null || reading.ObservedAtUtc > now.AddHours(-2))
                {
                    budget?.Add(reading);
                    events.Add(reading);
                }
                else
                    expired[reading.DeviceId] = expired.GetValueOrDefault(reading.DeviceId) + 1;
            }
            catch (Exception error) when (error is System.Text.Json.JsonException or InvalidDataException or
                FormatException or KeyNotFoundException or InvalidOperationException)
            {
                invalid++;
            }
            if (events.Count > 250_000)
                throw new ScenarioException("oversize_batch", "A telemetry batch exceeded the event limit.");
        }
        return (events.ToArray(), invalid, expired);
    }

    internal async Task<int> CleanupAsync(CancellationToken token)
    {
        var now = clock.GetUtcNow();
        int deleted = 0;
        await foreach (var blob in container.GetBlobsAsync(cancellationToken: token))
        {
            if (blob.Properties.LastModified is not { } modified || modified > now.AddMinutes(-5)) continue;
            var parsed = await ParseBlobAsync(blob, now, token);
            var latest = parsed.Events.Length == 0 ? modified : parsed.Events.Max(r => r.ObservedAtUtc);
            if (!CanDelete(modified, latest, parsed.Invalid, now)) continue;
            try
            {
                await container.GetBlobClient(blob.Name).DeleteAsync(DeleteSnapshotsOption.None,
                    new BlobRequestConditions { IfMatch = blob.Properties.ETag }, token);
                deleted++;
            }
            catch (RequestFailedException conflict) when (conflict.Status is 404 or 412)
            {
                logger.LogWarning("Cleanup skipped changed or already deleted batch; status {Status}", conflict.Status);
            }
        }
        logger.LogInformation("Cleanup completed: {Deleted} expired batches", deleted);
        return deleted;
    }

    internal static bool CanDelete(DateTimeOffset modified, DateTimeOffset latest, int invalid, DateTimeOffset now) =>
        modified <= now.AddMinutes(-5) && latest <= now.AddMinutes(-125) &&
        (invalid == 0 || modified <= now.AddMinutes(-130));
}

internal sealed class CleanupWorker(BlobTelemetry blobs, ILogger<CleanupWorker> logger) : BackgroundService
{
    /// <summary>Deletes only expired batches; dependency failures are explicit and retried on the next interval.</summary>
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try { await blobs.CleanupAsync(stoppingToken); }
            catch (Exception error) when (error is RequestFailedException or IOException or ScenarioException)
            {
                logger.LogError("Cleanup failed: {ErrorType}; physical retention target is not met", error.GetType().Name);
            }
            await Task.Delay(TimeSpan.FromMinutes(5), stoppingToken);
        }
    }
}
