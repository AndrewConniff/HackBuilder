using System.Security.Cryptography;
using System.Text.Json;
using Azure.Storage.Queues.Models;
using HospitalityFeedback.Web.Models;

namespace HospitalityFeedback.Web.Services;

public sealed class QueueWorker(StorageRepository store, FeedbackOptions options, ILogger<QueueWorker> logger)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var lastReconcile = DateTimeOffset.MinValue;
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await store.InitializeLocalAsync(stoppingToken);
                if (DateTimeOffset.UtcNow - lastReconcile > TimeSpan.FromSeconds(30))
                {
                    await store.ReconcileAsync(stoppingToken);
                    lastReconcile = DateTimeOffset.UtcNow;
                }
                var messages = await store.Queue.ReceiveMessagesAsync(4, TimeSpan.FromSeconds(90), stoppingToken);
                foreach (var message in messages.Value) await HandleAsync(message, stoppingToken);
                await Task.Delay(TimeSpan.FromSeconds(2), stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception ex)
            {
                // Never log feedback text, tokens, or dependency bodies.
                logger.LogError("Queue iteration failed ({Type}); retry in five seconds.", ex.GetType().Name);
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
        }
    }

    public async Task HandleAsync(QueueMessage message, CancellationToken ct)
    {
        WorkItem? work = null;
        try
        {
            work = JsonSerializer.Deserialize<WorkItem>(message.Body.ToString(), Rules.Json)
                ?? throw new InputException("invalid_envelope", "Null envelope.");
            // Processing is Storage-only, bounded, and normally subsecond.
            // Visibility is 90s; lease is 60s; writes are idempotent if dependencies exceed those limits.
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(ct);
            deadline.CancelAfter(TimeSpan.FromSeconds(45));
            if (!await store.ProcessAsync(work, (int)message.DequeueCount, deadline.Token)) return;
            await store.Queue.DeleteMessageAsync(message.MessageId, message.PopReceipt, ct);
            logger.LogInformation("Processed {FeedbackId}, correlation {CorrelationId}, attempt {Attempt}.",
                work.FeedbackId, work.CorrelationId, message.DequeueCount);
        }
        catch (Exception ex) when (ex is not OperationCanceledException || !ct.IsCancellationRequested)
        {
            var permanent = ex is InputException or JsonException;
            var code = ex is InputException input ? input.Code : ex.GetType().Name;
            if (!permanent && message.DequeueCount < options.MaxDeliveryAttempts)
            {
                logger.LogWarning("Retry {MessageId}, attempt {Attempt}, code {Code}.",
                    message.MessageId, message.DequeueCount, code);
                return; // Visibility timeout makes the message available again.
            }
            var digest = Convert.ToHexStringLower(SHA256.HashData(message.Body.ToArray()));
            var failure = new
            {
                message.MessageId, PayloadHash = digest, ErrorCode = code,
                Attempts = message.DequeueCount, CheckedAtUtc = DateTimeOffset.UtcNow
            };
            // Durable poison evidence precedes poison enqueue and source deletion.
            await StorageRepository.WriteAsync(store.Audit.GetBlobClient("poison-" + message.MessageId + ".json"),
                failure, ct);
            await store.Poison.SendMessageAsync(JsonSerializer.Serialize(failure, Rules.Json), cancellationToken: ct);
            if (work is not null && Rules.ValidId(work.FeedbackId))
            {
                var raw = await StorageRepository.ReadAsync<RawFeedback>(
                    store.Raw.GetBlobClient(work.FeedbackId + ".json"), ct);
                // Malicious/stale messages cannot poison a different correlation's valid event.
                if (raw is not null && raw.CorrelationId == work.CorrelationId)
                    await StorageRepository.WriteAsync(store.Status.GetBlobClient(work.FeedbackId + ".json"),
                        new ProcessingStatus(work.FeedbackId, work.CorrelationId, "poisoned",
                            DateTimeOffset.UtcNow, (int)message.DequeueCount, code), ct);
            }
            await store.Queue.DeleteMessageAsync(message.MessageId, message.PopReceipt, ct);
            logger.LogWarning("Poisoned {MessageId}, attempt {Attempt}, code {Code}.",
                message.MessageId, message.DequeueCount, code);
        }
    }
}
