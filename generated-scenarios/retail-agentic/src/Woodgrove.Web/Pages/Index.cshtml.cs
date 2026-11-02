using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Woodgrove.Web.Models;
using Woodgrove.Web.Services;

namespace Woodgrove.Web.Pages;

/// <summary>Scoped grocery cart, customer decisions and real-agent read-only chat.</summary>
public sealed class IndexModel(
    TableStorageDataService store, OrderWorkflow workflow, FoundryRuntime agents, ILogger<IndexModel> logger) : PageModel
{
    /// <summary>Gets the catalog read from the durable Azure backend.</summary>
    public Product[] Products { get; private set; } = [];
    /// <summary>Gets orders visible to the authenticated role.</summary>
    public GroceryOrder[] Orders { get; private set; } = [];
    /// <summary>Gets the selected, authorized order.</summary>
    public GroceryOrder? Selected { get; private set; }
    /// <summary>Gets an explicit user-visible policy error.</summary>
    public string? Error { get; private set; }
    /// <summary>Gets the real read-only assistant response, when one was requested.</summary>
    public string? Answer { get; private set; }
    /// <summary>Gets the actual Foundry response identifier for the displayed answer.</summary>
    public string? ResponseId { get; private set; }
    /// <summary>Gets whether the server-authenticated account is the demo operator.</summary>
    public bool IsOperator => User.IsInRole("Operator");
    private string Customer => User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? throw new PolicyException("A signed-in customer is required.");

    /// <summary>Loads the role-scoped catalog and order timeline.</summary>
    public Task<IActionResult> OnGetAsync(string? id) => GuardAsync(id, () => Task.CompletedTask);

    /// <summary>Creates a draft from explicit product quantities and server catalog prices.</summary>
    public async Task<IActionResult> OnPostCreateAsync(
        int[] productIds, int[] quantities, string[] exclusions, string slot, string requestId)
    {
        if (!User.IsInRole("Customer")) return Forbid();
        string? createdId = null;
        var result = await GuardAsync(null, async () =>
        {
            if (productIds.Length != quantities.Length || productIds.Length > 20 || requestId.Length > 64)
                throw new PolicyException("Invalid cart form.");
            if (exclusions.Length > 5 || exclusions.Any(x => x is not ("milk" or "peanuts" or "wheat" or "oats" or "sunflower")))
                throw new PolicyException("Select only the supported declared allergen exclusions.");
            var lines = productIds.Zip(quantities).Where(x => x.Second != 0)
                .Select(x => new CartLine(x.First, x.Second)).ToArray();
            var order = await store.CreateAsync(Customer, lines, slot, exclusions.Distinct().Order().ToArray(),
                requestId, HttpContext.RequestAborted);
            createdId = order.Id;
        });
        return createdId is null ? result : RedirectToPage(new { id = createdId });
    }

    /// <summary>Confirms exactly the displayed draft.</summary>
    public Task<IActionResult> OnPostConfirmAsync(string id, int version, string requestId) =>
        CustomerCommandAsync(id, () => workflow.ConfirmAsync(
            id, Customer, version, requestId, HttpContext.RequestAborted));

    /// <summary>Accepts or declines exactly the displayed customer proposal.</summary>
    public Task<IActionResult> OnPostDecideAsync(string id, string fingerprint, bool accept, string requestId) =>
        CustomerCommandAsync(id, () => workflow.DecideAsync(
            id, Customer, fingerprint, accept, requestId, HttpContext.RequestAborted));

    /// <summary>Cancels an undispatched order and reconciles its reservation.</summary>
    public Task<IActionResult> OnPostCancelAsync(string id, string requestId) =>
        CustomerCommandAsync(id, () => workflow.CancelAsync(id, Customer, requestId, HttpContext.RequestAborted));

    /// <summary>Retries a failed stage without clearing budgets or receipts.</summary>
    public Task<IActionResult> OnPostRetryAsync(string id, string requestId) =>
        CustomerCommandAsync(id, () => workflow.RetryAsync(id, Customer, requestId, HttpContext.RequestAborted));

    /// <summary>Invokes a real agent for an owned order without allowing chat to change its commitment.</summary>
    public Task<IActionResult> OnPostChatAsync(string id, string question) => GuardAsync(id, async () =>
    {
        var order = await store.OrderAsync(id, HttpContext.RequestAborted);
        CommercePolicy.Owns(order, Customer);
        (Answer, ResponseId) = await agents.AskAsync(order, question, HttpContext.RequestAborted);
    });

    /// <summary>Allows only the authenticated operator to inject or clear a synthetic exception.</summary>
    public Task<IActionResult> OnPostDisruptAsync(string id, string kind, string requestId)
    {
        if (!IsOperator) return Task.FromResult<IActionResult>(Forbid());
        return GuardAsync(id, async () =>
        {
            if (kind is not ("delay" or "tool-timeout" or "none"))
                throw new PolicyException("Unsupported synthetic exception.");
            await store.ChangeAsync(id, null, requestId, "fixture:" + kind, (order, _) =>
            {
                if (order.Status is "Dispatched" or "Delivered" or "Cancelled" or "AwaitingCustomer" or "Held")
                    throw new PolicyException("This checkpoint cannot accept a new fixture disruption.");
                return (order with
                {
                    Disruption = kind, Version = order.Version + 1,
                    Timeline = [.. order.Timeline, new(DateTimeOffset.UtcNow, "OperatorFixture",
                        $"Synthetic fixture set to {kind}; no customer approval or agent result was fabricated.")]
                }, []);
            }, HttpContext.RequestAborted);
        });
    }

    private Task<IActionResult> CustomerCommandAsync(string id, Func<Task<GroceryOrder>> action)
    {
        if (!User.IsInRole("Customer")) return Task.FromResult<IActionResult>(Forbid());
        return GuardAsync(id, async () => { await action(); });
    }

    private async Task<IActionResult> GuardAsync(string? id, Func<Task> action)
    {
        try
        {
            if (!ModelState.IsValid) throw new PolicyException("The submitted form is invalid.");
            await action();
            Products = await store.ProductsAsync(HttpContext.RequestAborted);
            Orders = await store.OrdersAsync(IsOperator ? null : Customer, HttpContext.RequestAborted);
            if (id is not null)
                Selected = Orders.SingleOrDefault(x => x.Id == id)
                    ?? throw new PolicyException("This order is not available to the signed-in account.");
        }
        catch (PolicyException ex)
        {
            Error = ex.Message;
            Response.StatusCode = 400;
            logger.LogWarning("A scoped grocery command was rejected: {Reason}", ex.Message);
        }
        return Page();
    }
}
