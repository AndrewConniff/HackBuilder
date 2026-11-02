using System.ClientModel;
using System.Text.Json;
using Azure;
using Woodgrove.Web.Models;

namespace Woodgrove.Web.Services;

/// <summary>Claims durable work with renewable leases and at most three active agent stages.</summary>
public sealed class FulfillmentWorker(
    TableStorageDataService store, FoundryRuntime agents, ILogger<FulfillmentWorker> logger) : BackgroundService
{
    private readonly string owner = Guid.NewGuid().ToString("N");

    /// <summary>Polls persisted work; customer waits hold no model requests or in-memory continuation.</summary>
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            var orders = await store.OrdersAsync(null, stoppingToken);
            await Parallel.ForEachAsync(
                orders.Where(x => x.Status is "Confirmed" or "ReadyForDispatch" or "Dispatched" ||
                    x.Status == "AwaitingCustomer" && x.Proposal?.ExpiresAt <= DateTimeOffset.UtcNow),
                new ParallelOptions { MaxDegreeOfParallelism = 3, CancellationToken = stoppingToken },
                ProcessAsync);
            await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
        }
    }

    private async ValueTask ProcessAsync(GroceryOrder order, CancellationToken stoppingToken)
    {
        if (!await store.LeaseAsync(order.Id, owner, stoppingToken))
            return;
        using var active = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
        var renewal = RenewAsync(order.Id, active);
        try
        {
            if (order.Status == "AwaitingCustomer" && order.Proposal is { } proposal)
            {
                await store.ChangeAsync(order.Id, null, "expire-" + proposal.Fingerprint, proposal.Fingerprint,
                    (current, _) => (CommercePolicy.Expire(current, proposal.Fingerprint, DateTimeOffset.UtcNow), []),
                    active.Token);
            }
            else if (order.Status == "Dispatched")
            {
                if (order.DeliveryDueAt is null || order.DeliveryDueAt > DateTimeOffset.UtcNow)
                    return;
                await store.ChangeAsync(order.Id, null, "synthetic-delivery", "synthetic-delivery", (current, _) =>
                {
                    if (current.Status != "Dispatched" || current.Stage != 3 ||
                        current.DeliveryDueAt is null || current.DeliveryDueAt > DateTimeOffset.UtcNow)
                        throw new PolicyException("The synthetic delivery event is not valid for this state.");
                    return (current with
                    {
                        Status = "Delivered", Version = current.Version + 1,
                        Timeline = [.. current.Timeline, new(DateTimeOffset.UtcNow, "Delivered",
                            "Validated synthetic carrier event; no physical shipment was created.")]
                    }, []);
                }, active.Token);
            }
            else
                await agents.RunStageAsync(order, owner, active.Token);
        }
        catch (OperationCanceledException) when (!stoppingToken.IsCancellationRequested)
        {
            logger.LogWarning("Order {OrderId} stage timed out or lost its lease", order.Id);
            await FailAsync(order, "Stage timed out or worker lease was lost.", stoppingToken);
        }
        catch (Exception ex) when (ex is PolicyException or RequestFailedException or ClientResultException or
                                   JsonException or KeyNotFoundException or InvalidOperationException)
        {
            logger.LogError("Order {OrderId} stage failed: {ErrorType}; no success was inferred", order.Id, ex.GetType().Name);
            await FailAsync(order, ex is PolicyException ? ex.Message : "Agent/data operation failed; inspect correlated operator logs.",
                stoppingToken);
        }
        finally
        {
            await active.CancelAsync();
            await renewal;
        }
    }

    private async Task RenewAsync(string id, CancellationTokenSource active)
    {
        try
        {
            while (!active.IsCancellationRequested)
            {
                await Task.Delay(TimeSpan.FromSeconds(10), active.Token);
                if (!await store.LeaseAsync(id, owner, active.Token))
                {
                    logger.LogError("Order {OrderId} worker lease renewal was rejected", id);
                    await active.CancelAsync();
                }
            }
        }
        catch (OperationCanceledException) when (active.IsCancellationRequested)
        {
            logger.LogDebug("Order {OrderId} lease renewal stopped", id);
        }
    }

    private async Task FailAsync(GroceryOrder attempted, string message, CancellationToken cancellation)
    {
        var current = await store.OrderAsync(attempted.Id, cancellation);
        if (current.Stage != attempted.Stage || current.Status is not ("Confirmed" or "ReadyForDispatch"))
        {
            logger.LogWarning("Order {OrderId} state changed; late failure cannot overwrite its newer checkpoint", current.Id);
            return;
        }
        try
        {
            await store.ChangeAsync(current.Id, null, "failure-" + Guid.NewGuid().ToString("N"), "failure", (order, _) =>
            {
                if (order.Stage != current.Stage || order.Version != current.Version)
                    throw new PolicyException("A newer checkpoint superseded the failed attempt.");
                return (order with
                {
                    Status = "Failed", Version = order.Version + 1,
                    Timeline = [.. order.Timeline, new(DateTimeOffset.UtcNow, "Failed", message)]
                }, []);
            }, cancellation);
        }
        catch (PolicyException)
        {
            logger.LogWarning("Order {OrderId} changed concurrently while recording failure; no state was overwritten", current.Id);
        }
    }
}
