using Woodgrove.Web.Models;

namespace Woodgrove.Web.Services;

/// <summary>Customer-authorized commands; model output never substitutes for these decisions.</summary>
public sealed class OrderWorkflow(TableStorageDataService store)
{
    /// <summary>Confirms exactly the draft displayed to its owning customer.</summary>
    public Task<GroceryOrder> ConfirmAsync(
        string id, string customer, int version, string request, CancellationToken cancellation) =>
        store.ChangeAsync(id, customer, request, $"confirm:{version}", (order, products) =>
        {
            if (order.Status != "Draft" || order.Version != version)
                throw new PolicyException("This is not the exact draft you reviewed.");
            CommercePolicy.ValidSlot(order.Slot);
            if (CommercePolicy.Price(order.Lines, products) != order.TotalCents)
                throw new PolicyException("Catalog prices changed; review a new cart.");
            return (order with
            {
                Status = "Confirmed", Version = order.Version + 1,
                Timeline = [.. order.Timeline, new(DateTimeOffset.UtcNow, "Confirmed",
                    "Customer confirmed these exact items, total and delivery window.")]
            }, []);
        }, cancellation);

    /// <summary>Accepts an exact proposal or holds the order on an explicit decline.</summary>
    public Task<GroceryOrder> DecideAsync(
        string id, string customer, string fingerprint, bool accept, string request, CancellationToken cancellation) =>
        store.ChangeAsync(id, customer, request, $"decision:{fingerprint}:{accept}", (order, products) =>
        {
            if (accept)
                return (CommercePolicy.Accept(order, customer, fingerprint, products, DateTimeOffset.UtcNow), []);
            if (order.Status != "AwaitingCustomer" || order.Proposal?.Fingerprint != fingerprint)
                throw new PolicyException("There is no matching pending proposal to decline.");
            return (order with
            {
                Status = "Held", Proposal = null, Version = order.Version + 1,
                Timeline = [.. order.Timeline, new(DateTimeOffset.UtcNow, "Held",
                    "Customer declined the proposal; no changed commitment was executed.")]
            }, []);
        }, cancellation);

    /// <summary>Cancels an undispatched order and returns any reserved synthetic stock atomically.</summary>
    public Task<GroceryOrder> CancelAsync(string id, string customer, string request, CancellationToken cancellation) =>
        store.ChangeAsync(id, customer, request, "cancel", (order, products) =>
        {
            if (order.Status is "Dispatched" or "Delivered" or "Cancelled")
                throw new PolicyException("This order cannot be cancelled.");
            var stock = order.Stage >= 2 ? order.Lines.Select(line =>
            {
                var product = products.Single(x => x.Id == line.ProductId);
                return product with { Stock = checked(product.Stock + line.Quantity) };
            }).ToArray() : [];
            return (order with
            {
                Status = "Cancelled", Proposal = null, Version = order.Version + 1,
                AuthorizedCents = 0, RefundedCents = order.CapturedCents,
                Timeline = [.. order.Timeline, new(DateTimeOffset.UtcNow, "Cancelled",
                    "Customer cancelled; stock returned and any synthetic capture refunded atomically.")]
            }, stock);
        }, cancellation);

    /// <summary>Resumes only a failed stage, without clearing its durable model/tool budgets.</summary>
    public Task<GroceryOrder> RetryAsync(string id, string customer, string request, CancellationToken cancellation) =>
        store.ChangeAsync(id, customer, request, "retry", (order, _) =>
        {
            if (order.Status != "Failed" || order.Stage >= 3)
                throw new PolicyException("Only a failed agent stage can be retried.");
            return (order with
            {
                Status = order.Stage == 2 ? "ReadyForDispatch" : "Confirmed", Version = order.Version + 1,
                Timeline = [.. order.Timeline, new(DateTimeOffset.UtcNow, "Retry",
                    "Customer requested retry; existing receipts, reservations and budgets are retained.")]
            }, []);
        }, cancellation);
}
