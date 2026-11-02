using System.Text.Json;
using Azure;
using Azure.Core;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using Azure.Storage.Blobs.Specialized;
using Azure.Storage.Queues;
using HospitalityFeedback.Web.Models;

namespace HospitalityFeedback.Web.Services;

public sealed class StorageRepository
{
    public BlobContainerClient Raw { get; }
    public BlobContainerClient Processed { get; }
    public BlobContainerClient Status { get; }
    public BlobContainerClient Audit { get; }
    public QueueClient Queue { get; }
    public QueueClient Poison { get; }
    private readonly FeedbackOptions options;

    public StorageRepository(FeedbackOptions options, TokenCredential credential)
    {
        this.options = options;
        BlobServiceClient blobs;
        QueueServiceClient queues;
        var queueOptions = new QueueClientOptions { MessageEncoding = QueueMessageEncoding.Base64 };
        if (options.UseAzurite)
        {
            blobs = new BlobServiceClient("UseDevelopmentStorage=true");
            queues = new QueueServiceClient("UseDevelopmentStorage=true", queueOptions);
        }
        else
        {
            if (!Uri.TryCreate(options.BlobEndpoint, UriKind.Absolute, out var blob)
                || !Uri.TryCreate(options.QueueEndpoint, UriKind.Absolute, out var queue)
                || blob.Scheme != "https" || queue.Scheme != "https")
                throw new ConfigurationException("Configure HTTPS Blob and Queue endpoints. No local fallback.");
            blobs = new BlobServiceClient(blob, credential);
            queues = new QueueServiceClient(queue, credential, queueOptions);
        }
        Raw = blobs.GetBlobContainerClient("raw");
        Processed = blobs.GetBlobContainerClient("processed");
        Status = blobs.GetBlobContainerClient("status");
        Audit = blobs.GetBlobContainerClient("audit");
        Queue = queues.GetQueueClient(options.QueueName);
        Poison = queues.GetQueueClient(options.PoisonQueueName);
    }

    public async Task InitializeLocalAsync(CancellationToken ct)
    {
        // Azure resources are provisioned by Bicep, not opportunistically created by the app.
        if (!options.UseAzurite) return;
        foreach (var container in new[] { Raw, Processed, Status, Audit })
            await container.CreateIfNotExistsAsync(cancellationToken: ct);
        await Queue.CreateIfNotExistsAsync(cancellationToken: ct);
        await Poison.CreateIfNotExistsAsync(cancellationToken: ct);
    }

    public static async Task<T?> ReadAsync<T>(BlobClient blob, CancellationToken ct)
    {
        try
        {
            var download = await blob.DownloadContentAsync(ct);
            return JsonSerializer.Deserialize<T>(download.Value.Content.ToString(), Rules.Json);
        }
        catch (RequestFailedException ex) when (ex.Status == 404) { return default; }
    }

    public static Task WriteAsync<T>(BlobClient blob, T value, CancellationToken ct) =>
        blob.UploadAsync(BinaryData.FromObjectAsJson(value, Rules.Json), overwrite: true, cancellationToken: ct);

    public async Task<IngestResult> IngestAsync(FeedbackInput input, CancellationToken ct)
    {
        Rules.Validate(input);
        var rawBlob = Raw.GetBlobClient(input.FeedbackId + ".json");
        var envelope = new RawFeedback(input, Rules.Hash(input), Guid.NewGuid().ToString("N"), DateTimeOffset.UtcNow);
        var duplicate = false;
        try
        {
            await rawBlob.UploadAsync(BinaryData.FromObjectAsJson(envelope, Rules.Json),
                new BlobUploadOptions { Conditions = new BlobRequestConditions { IfNoneMatch = ETag.All } }, ct);
        }
        catch (RequestFailedException ex) when (ex.Status is 409 or 412)
        {
            envelope = await ReadAsync<RawFeedback>(rawBlob, ct)
                ?? throw new InvalidOperationException("Existing raw record disappeared.");
            if (envelope.PayloadHash != Rules.Hash(input)) throw new ConflictException();
            duplicate = true;
        }
        var status = await ReadAsync<ProcessingStatus>(Status.GetBlobClient(input.FeedbackId + ".json"), ct);
        if (status?.State is "completed" or "poisoned")
            return new(input.FeedbackId, envelope.CorrelationId, status.State, duplicate);
        // Raw blob is the durable outbox. Reconciliation resends if this enqueue fails.
        await Queue.SendMessageAsync(JsonSerializer.Serialize(
            new WorkItem(input.FeedbackId, envelope.CorrelationId), Rules.Json), cancellationToken: ct);
        return new(input.FeedbackId, envelope.CorrelationId, status?.State ?? "queued", duplicate);
    }

    public async Task<IReadOnlyList<Evidence>> EvidenceAsync(ChatRequest request, CancellationToken ct)
    {
        var evidence = new List<Evidence>();
        var scanned = 0;
        await foreach (var item in Processed.GetBlobsAsync(cancellationToken: ct))
        {
            // Explicitly refuse an incomplete all-dataset claim; use an index for larger workloads.
            if (++scanned > options.MaxEvidenceRecords)
                throw new InputException("dataset_limit", "Dataset exceeds bounded reference capacity; add an index.");
            var record = await ReadAsync<Evidence>(Processed.GetBlobClient(item.Name), ct);
            if (record is null) continue;
            if (request.Category is not null && record.Feedback.Category != request.Category) continue;
            if (request.Languages is { Length: > 0 } && !request.Languages.Contains(record.Feedback.Language)) continue;
            evidence.Add(record);
        }
        return evidence.OrderBy(e => e.Feedback.FeedbackId, StringComparer.Ordinal).ToArray();
    }

    public async Task<IReadOnlyList<ProcessingStatus>> StatusAsync(CancellationToken ct)
    {
        var results = new List<ProcessingStatus>();
        await foreach (var item in Raw.GetBlobsAsync(cancellationToken: ct))
        {
            if (results.Count >= options.MaxEvidenceRecords) break;
            var raw = await ReadAsync<RawFeedback>(Raw.GetBlobClient(item.Name), ct);
            if (raw is null) continue;
            var status = await ReadAsync<ProcessingStatus>(Status.GetBlobClient(item.Name), ct);
            results.Add(status ?? new(raw.Feedback.FeedbackId, raw.CorrelationId, "queued", raw.ReceivedAt, 0));
        }
        return results;
    }

    public async Task ReconcileAsync(CancellationToken ct)
    {
        var scanned = 0;
        await foreach (var item in Raw.GetBlobsAsync(cancellationToken: ct))
        {
            if (++scanned > options.MaxEvidenceRecords) return;
            var raw = await ReadAsync<RawFeedback>(Raw.GetBlobClient(item.Name), ct);
            if (raw is null || raw.ReceivedAt > DateTimeOffset.UtcNow.AddSeconds(-30)) continue;
            var state = await ReadAsync<ProcessingStatus>(Status.GetBlobClient(item.Name), ct);
            if (state?.State is "completed" or "poisoned") continue;
            await Queue.SendMessageAsync(JsonSerializer.Serialize(
                new WorkItem(raw.Feedback.FeedbackId, raw.CorrelationId), Rules.Json), cancellationToken: ct);
        }
    }

    public async Task<bool> ProcessAsync(WorkItem work, int attempts, CancellationToken ct)
    {
        if (!Rules.ValidId(work.FeedbackId) || !Guid.TryParseExact(work.CorrelationId, "N", out _))
            throw new InputException("invalid_envelope", "Invalid work envelope.");
        var rawBlob = Raw.GetBlobClient(work.FeedbackId + ".json");
        BlobLeaseClient lease = rawBlob.GetBlobLeaseClient();
        try { await lease.AcquireAsync(TimeSpan.FromSeconds(60), cancellationToken: ct); }
        catch (RequestFailedException ex) when (ex.Status == 409) { return false; }
        try
        {
            var raw = await ReadAsync<RawFeedback>(rawBlob, ct)
                ?? throw new InputException("missing_raw", "Raw source missing.");
            if (raw.CorrelationId != work.CorrelationId)
                throw new InputException("correlation_mismatch", "Correlation does not match raw source.");
            Rules.Validate(raw.Feedback);
            if (Rules.Hash(raw.Feedback) != raw.PayloadHash)
                throw new InputException("hash_mismatch", "Source hash mismatch.");
            var statusBlob = Status.GetBlobClient(work.FeedbackId + ".json");
            var status = await ReadAsync<ProcessingStatus>(statusBlob, ct);
            if (status?.State == "poisoned") return true;
            if (!(await Processed.GetBlobClient(work.FeedbackId + ".json").ExistsAsync(ct)).Value)
            {
                await WriteAsync(statusBlob, new ProcessingStatus(work.FeedbackId, work.CorrelationId,
                    "processing", DateTimeOffset.UtcNow, attempts), ct);
                await Processed.GetBlobClient(work.FeedbackId + ".json").UploadAsync(
                    BinaryData.FromObjectAsJson(new Evidence(raw.Feedback, work.CorrelationId, DateTimeOffset.UtcNow),
                        Rules.Json),
                    new BlobUploadOptions { Conditions = new BlobRequestConditions { IfNoneMatch = ETag.All } }, ct);
            }
            await WriteAsync(statusBlob, new ProcessingStatus(work.FeedbackId, work.CorrelationId,
                "completed", DateTimeOffset.UtcNow, attempts), ct);
            return true;
        }
        finally
        {
            try { await lease.ReleaseAsync(cancellationToken: CancellationToken.None); }
            catch (RequestFailedException) { /* Lease expiry is recoverable; processed writes are conditional. */ }
        }
    }
}
