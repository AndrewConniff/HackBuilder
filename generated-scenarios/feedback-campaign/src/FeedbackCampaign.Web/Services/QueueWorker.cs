using System.Text.Json;
using Azure.Core;
using Azure.Messaging.ServiceBus;

namespace FeedbackCampaign.Web;

public sealed class QueueWorker(IServiceProvider services, IConfiguration config, TokenCredential credential,
    ILogger<QueueWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (string.IsNullOrWhiteSpace(config["SERVICEBUS_NAMESPACE"]))
        {
            logger.LogWarning("Queue worker unavailable: endpoints are not configured.");
            return;
        }
        await using var bus = new ServiceBusClient(config["SERVICEBUS_NAMESPACE"], credential);
        await using var receiver = bus.CreateReceiver("posts");
        await using var sender = bus.CreateSender("replies");
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var scope = services.CreateScope();
                var store = scope.ServiceProvider.GetRequiredService<IStateStore>();
                var workflow = scope.ServiceProvider.GetRequiredService<CampaignWorkflow>();
                var message = await receiver.ReceiveMessageAsync(TimeSpan.FromSeconds(2), stoppingToken);
                if (message is not null)
                {
                    try
                    {
                        var post = JsonSerializer.Deserialize<Post>(message.Body.ToString(), TableStateStore.Json)
                            ?? throw new ArgumentException("Empty post.");
                        await workflow.Submit(post, "ServiceBus");
                        await receiver.CompleteMessageAsync(message, stoppingToken);
                    }
                    catch (ArgumentException)
                    {
                        await receiver.DeadLetterMessageAsync(message, "InvalidPost", cancellationToken: stoppingToken);
                    }
                    catch (Exception ex) when (ex is not OperationCanceledException)
                    {
                        logger.LogWarning("Inbound processing failed: {Category}", ex.GetType().Name);
                        await receiver.AbandonMessageAsync(message, cancellationToken: stoppingToken);
                    }
                }
                foreach (var stored in await store.List<Case>("cases"))
                {
                    if (stored.Value.Status == "Received") await workflow.Process(stored, stoppingToken);
                    if (stored.Value.Status != "PendingSend") continue;
                    var item = stored.Value;
                    await sender.SendMessageAsync(new ServiceBusMessage(BinaryData.FromObjectAsJson(new
                    {
                        item.Post.SourceId, item.Post.PosterName, item.Post.Contact, item.Post.Campaign,
                        item.Post.Subject, Body = item.Reply, CaseId = item.Id, RuleVersion = item.Rules.Version
                    }))
                    {
                        MessageId = $"reply-{item.Id}", CorrelationId = item.Id,
                        ContentType = "application/json"
                    }, stoppingToken);
                    await store.Replace("cases", item.Id, item with { Status = "Queued",
                        Audit = [.. item.Audit, new(DateTimeOffset.UtcNow, "Outbox", "AcceptedByReplyStream")] }, stored.ETag);
                    logger.LogInformation("Reply stream accepted case {CaseId}", item.Id);
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception ex) { logger.LogError("Workflow tick failed: {Category}", ex.GetType().Name); }
            await Task.Delay(TimeSpan.FromSeconds(3), stoppingToken);
        }
    }
}
