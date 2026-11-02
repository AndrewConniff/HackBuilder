using System.Net;
using System.Text.Json;
using Azure.Messaging.ServiceBus;
using Microsoft.Azure.Cosmos;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>A conditional dispatcher lease prevents aggregate versions being sent by competing workers out of order.</summary>
public sealed record DispatchLease(string id, string aggregateKey, string Type, DateTimeOffset ExpiresAt);

/// <summary>Durable per-ticket sequence evidence, independent of transport duplicate-detection retention.</summary>
public sealed record DeliverySequence(string id, string aggregateKey, string Type, int Sequence);

/// <summary>Dispatches outbox work and consumes sessions using durable inbox receipts and explicit failures.</summary>
public sealed class KitchenWorker(CosmosStore store, ServiceBusClient broker,
    IConfiguration configuration, TimeProvider clock, ILogger<KitchenWorker> logger) : BackgroundService
{
    private readonly string queue = configuration["SERVICE_BUS_QUEUE"] ?? "kitchen";
    private DateTimeOffset nextRecovery;

    /// <summary>Runs independent bounded dispatch and consumer tasks for the worker role.</summary>
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await using var sender = broker.CreateSender(queue);
        await using var processor = broker.CreateSessionProcessor(queue, new()
        {
            AutoCompleteMessages = false, MaxConcurrentSessions = 8, MaxConcurrentCallsPerSession = 1,
            SessionIdleTimeout = TimeSpan.FromSeconds(10), MaxAutoLockRenewalDuration = TimeSpan.FromMinutes(2)
        });
        processor.ProcessMessageAsync += Consume;
        processor.ProcessErrorAsync += args =>
        {
            logger.LogError(args.Exception, "Broker consumer failed in {Source}; queue {Queue}", args.ErrorSource, queue);
            return Task.CompletedTask;
        };
        await processor.StartProcessingAsync(stoppingToken);
        try
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                    var pending = await store.Query<Outbox>(store.Transactions,
                        new("SELECT TOP 50 * FROM c WHERE c.Type = 'outbox' AND c.Status = 'pending' ORDER BY c.CreatedAt"),
                        50, stoppingToken);
                    foreach (var partition in pending.Select(item => item.aggregateKey).Distinct())
                        await Dispatch(partition, sender, stoppingToken);
                    if (clock.GetUtcNow() >= nextRecovery)
                    {
                        nextRecovery = clock.GetUtcNow().AddSeconds(5);
                        await Recovery(sender, stoppingToken);
                    }
                    await Task.Delay(TimeSpan.FromMilliseconds(250), stoppingToken);
                }
                catch (Exception exception) when (exception is CosmosException or ServiceBusException or DomainException)
                {
                    logger.LogError(exception, "Durable dispatch failed; pending work is retained for retry");
                    await Task.Delay(TimeSpan.FromSeconds(2), stoppingToken);
                }
                catch (OperationCanceledException exception) when (!stoppingToken.IsCancellationRequested)
                {
                    logger.LogError(exception, "Dispatch lease deadline exceeded; durable work remains pending for retry");
                }
            }
        }
        finally
        {
            await processor.StopProcessingAsync(CancellationToken.None);
        }
    }

    private async Task Recovery(ServiceBusSender sender, CancellationToken token)
    {
        await using var peek = broker.CreateReceiver(queue, new ServiceBusReceiverOptions { SubQueue = SubQueue.DeadLetter });
        var letters = await peek.PeekMessagesAsync(100, cancellationToken: token);
        await store.Reporting.UpsertItemAsync(new
        {
            id = "deadletters", aggregateKey = "operations", Type = "deadletter-observation",
            CheckedAt = clock.GetUtcNow(), Limit = 100, Truncated = letters.Count == 100,
            Messages = letters.Select(message => new
                { message.MessageId, message.SessionId, message.DeadLetterReason, message.SequenceNumber })
        }, new("operations"), cancellationToken: token);
        var requests = await store.Query<ReplayRequest>(store.Reporting, new QueryDefinition(
            "SELECT TOP 10 * FROM c WHERE c.Type = 'replay-request' AND (c.Status = 'pending' OR "
            + "(c.Status = 'processing' AND c.LeaseUntil < @now))").WithParameter("@now", clock.GetUtcNow()), 10, token);
        foreach (var request in requests)
        {
            var stored = await CosmosStore.Read<ReplayRequest>(store.Reporting, request.id, "operations", token);
            if (stored is null) continue;
            try
            {
                await store.Reporting.ReplaceItemAsync(request with
                    { Status = "processing", LeaseUntil = clock.GetUtcNow().AddMinutes(1) },
                    request.id, new("operations"), new() { IfMatchEtag = stored.Value.ETag }, token);
            }
            catch (CosmosException exception) when (exception.StatusCode == HttpStatusCode.PreconditionFailed)
            {
                logger.LogDebug("Another worker owns replay {RequestId}", request.id);
                continue;
            }
            {
                await using var receiver = broker.CreateReceiver(queue,
                    new ServiceBusReceiverOptions { SubQueue = SubQueue.DeadLetter });
                var messages = await receiver.ReceiveMessagesAsync(100, TimeSpan.FromSeconds(1), token);
                var match = messages.SingleOrDefault(message =>
                    message.MessageId == request.MessageId && message.SessionId == request.SessionId);
                if (match is not null)
                {
                    await sender.SendMessageAsync(new(match.Body)
                    {
                        MessageId = $"replay:{request.id}", SessionId = match.SessionId,
                        ContentType = match.ContentType, Subject = match.Subject, CorrelationId = match.CorrelationId
                    }, token);
                    await receiver.CompleteMessageAsync(match, token);
                }
                foreach (var message in messages.Where(message => message != match))
                    await receiver.AbandonMessageAsync(message, cancellationToken: token);
                await store.Reporting.ReplaceItemAsync(request with
                {
                    Status = match is null ? "failed" : "replayed",
                    Failure = match is null ? "Message not found within the bounded first 100 DLQ messages; inspect recovery evidence." : null
                }, request.id, new("operations"), cancellationToken: token);
                if (match is null) logger.LogError("Replay {RequestId} failed: message not found within bounded session read", request.id);
                else logger.LogInformation("Manager-requested replay {RequestId} acknowledged; durable inbox still prevents duplicate effects", request.id);
            }
        }
    }

    private async Task Dispatch(string partition, ServiceBusSender sender, CancellationToken token)
    {
        var existing = await CosmosStore.Read<DispatchLease>(store.Transactions, "dispatch-lease", partition, token);
        if (existing is not null && existing.Value.Item.ExpiresAt > clock.GetUtcNow()) return;
        var lease = new DispatchLease("dispatch-lease", partition, "dispatch-lease", clock.GetUtcNow().AddSeconds(60));
        ItemResponse<DispatchLease> acquired;
        try
        {
            acquired = existing is null
                ? await store.Transactions.CreateItemAsync(lease, new(partition), cancellationToken: token)
                : await store.Transactions.ReplaceItemAsync(lease, lease.id, new(partition),
                    new() { IfMatchEtag = existing.Value.ETag }, token);
        }
        catch (CosmosException exception) when (exception.StatusCode is HttpStatusCode.Conflict or HttpStatusCode.PreconditionFailed)
        {
            logger.LogDebug("Another dispatcher owns partition lease");
            return;
        }
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
        deadline.CancelAfter(TimeSpan.FromSeconds(45));
        var pending = await store.Query<Outbox>(store.Transactions,
            new QueryDefinition("SELECT TOP 50 * FROM c WHERE c.aggregateKey = @partition AND c.Type = 'outbox' "
                + "AND c.Status = 'pending' ORDER BY c.Version")
                .WithParameter("@partition", partition), 50, deadline.Token);
        foreach (var item in pending.OrderBy(item => item.Version))
        {
            var stored = await CosmosStore.Read<Outbox>(store.Transactions, item.id, partition, deadline.Token);
            if (stored is null || stored.Value.Item.Status != "pending") continue;
            await sender.SendMessageAsync(new(BinaryData.FromObjectAsJson(item))
            {
                MessageId = item.id, SessionId = item.SessionId, CorrelationId = item.EntityId,
                Subject = item.Kind, ContentType = "application/json"
            }, deadline.Token);
            await store.Transactions.ReplaceItemAsync(item with { Status = "sent" }, item.id, new(partition),
                new() { IfMatchEtag = stored.Value.ETag }, deadline.Token);
            logger.LogInformation("Outbox {EventId} acknowledged by broker", item.id);
        }
        await store.Transactions.ReplaceItemAsync(lease with { ExpiresAt = clock.GetUtcNow() },
            lease.id, new(partition), new() { IfMatchEtag = acquired.ETag }, deadline.Token);
    }

    private async Task Consume(ProcessSessionMessageEventArgs args)
    {
        var token = args.CancellationToken;
        var message = args.Message.Body.ToObjectFromJson<Outbox>()
            ?? throw new InvalidDataException("Kitchen message has no event.");
        var partition = $"visit:{message.EntityId}";
        var inboxId = $"inbox:{message.id}";
        var inbox = await CosmosStore.Read<JsonElement>(store.Transactions, inboxId, partition, token);
        if (inbox is null)
        {
            if (message.Kind == "reservation")
            {
                var slot = await CosmosStore.Read<Slot>(store.Transactions, "slot", message.aggregateKey, token)
                    ?? throw new InvalidDataException("Reservation event has no authoritative allocation.");
                var allocation = slot.Item.Allocations.Single(a => a.VisitId == message.EntityId);
                var visit = new Visit(message.EntityId, partition, "visit", 1, message.EntityId,
                    message.aggregateKey[5..], allocation.Floor, allocation.Seats, allocation.GuestName,
                    allocation.AccessHash, "Reserved", [], false, null,
                    message.LegacyReferenceId ?? $"synthetic-v1:{message.EntityId}");
                await store.Commit(store.Transactions.CreateTransactionalBatch(new(partition))
                    .CreateItem(visit).CreateItem(new { id = inboxId, aggregateKey = partition, Type = "inbox" }), token);
            }
            else
            {
                var (visit, etag) = await store.Visit(message.EntityId, token);
                var batch = store.Transactions.CreateTransactionalBatch(new(partition))
                    .CreateItem(new { id = inboxId, aggregateKey = partition, Type = "inbox" });
                if (message.Kind == "cancel")
                {
                    if (visit.Status != "Cancelled")
                        throw new DomainException(409, "Cancellation compensation requires a cancelled reservation.");
                    await ReleaseAllocation(visit, token);
                    batch.ReplaceItem(visit.id, visit with
                    {
                        AllocationReleased = true, Version = visit.Version + 1
                    }, new() { IfMatchEtag = etag });
                }
                if (message.Sequence > 0)
                {
                    var sequenceId = $"delivery:{message.SessionId}";
                    var prior = await CosmosStore.Read<DeliverySequence>(store.Transactions, sequenceId, partition, token);
                    if (message.Sequence != (prior?.Item.Sequence ?? 0) + 1)
                        throw new DomainException(409, "Ticket sequence gap; retain message for ordered retry.");
                    var next = new DeliverySequence(sequenceId, partition, "delivery-sequence", message.Sequence);
                    if (prior is null) batch.CreateItem(next);
                    else batch.ReplaceItem(sequenceId, next, new() { IfMatchEtag = prior.Value.ETag });
                }
                if (message.Kind == "order")
                {
                    var updated = visit with { Version = visit.Version + 1,
                        Tickets = visit.Tickets.Select(t => t.Id == message.SessionId ? t with { Dispatched = true } : t).ToArray() };
                    batch.ReplaceItem(visit.id, updated, new() { IfMatchEtag = etag });
                }
                await store.Commit(batch, token);
            }
        }
        var current = (await store.Visit(message.EntityId, token)).Item;
        // The projection is rebuildable; the transactional visit and durable inbox remain authoritative.
        await store.Reporting.UpsertItemAsync(new
        {
            id = current.id, aggregateKey = $"floor:{current.Floor}", Type = "visit-summary",
            current.Floor, current.Version, current.Status, TicketCount = current.Tickets.Length,
            PendingDispatch = current.Tickets.Count(t => !t.Dispatched), UpdatedAt = clock.GetUtcNow()
        }, new($"floor:{current.Floor}"), cancellationToken: token);
        await args.CompleteMessageAsync(args.Message, token);
        logger.LogInformation("Kitchen event {EventId} applied or durably deduplicated", message.id);
    }

    private async Task ReleaseAllocation(Visit visit, CancellationToken token)
    {
        var partition = $"slot:{visit.Slot}";
        var receiptId = $"release:{visit.id}";
        if (await CosmosStore.Read<JsonElement>(store.Transactions, receiptId, partition, token) is not null) return;
        var slot = await CosmosStore.Read<Slot>(store.Transactions, "slot", partition, token)
            ?? throw new DomainException(409, "Cancellation allocation is missing; manual reconciliation is required.");
        if (!slot.Item.Allocations.Any(allocation => allocation.VisitId == visit.id))
            throw new DomainException(409, "Allocation is absent without a release receipt; reconcile before retry.");
        var released = slot.Item with
        {
            Version = slot.Item.Version + 1,
            Allocations = slot.Item.Allocations.Where(allocation => allocation.VisitId != visit.id).ToArray()
        };
        // The slot receipt makes a crash between the two partitions safe to retry without releasing twice.
        await store.Commit(store.Transactions.CreateTransactionalBatch(new(partition))
            .ReplaceItem("slot", released, new() { IfMatchEtag = slot.ETag })
            .CreateItem(new { id = receiptId, aggregateKey = partition, Type = "capacity-release",
                VisitId = visit.id, At = clock.GetUtcNow() }), token);
    }
}
