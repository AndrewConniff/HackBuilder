using System.Security.Claims;
using BankSupport.Web.Models;
using BankSupport.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace BankSupport.Web.Pages;

/// <summary>Customer-owned synthetic records and bounded banking chat.</summary>
public sealed class IndexModel(BankingWorkflow workflow) : PageModel
{
    /// <summary>Current authorized conversation.</summary>
    public ServiceCase? Conversation { get; private set; }
    /// <summary>Current customer's read-only banking records.</summary>
    public IReadOnlyList<BankRecord> Records { get; private set; } = [];
    private string Customer => User.FindFirstValue("customer")
        ?? throw new BusinessException(403, "Customer identity is missing.");

    /// <summary>Displays only server-selected customer data.</summary>
    public async Task OnGetAsync(string? id, CancellationToken ct)
    {
        Records = await workflow.RecordsAsync(Customer, ct);
        if (id is not null) Conversation = (await workflow.OwnAsync(id, Customer, ct)).Value;
    }

    /// <summary>Starts a separate automated conversation through a state-changing POST.</summary>
    public async Task<IActionResult> OnPostStartAsync(CancellationToken ct) =>
        RedirectToPage(new { id = await workflow.StartAsync(Customer, ct) });

    /// <summary>Sends a normal message or explicitly requests human service.</summary>
    public async Task<IActionResult> OnPostSendAsync(string id, int version, string text, bool human, CancellationToken ct)
    {
        await workflow.SendAsync(id, Customer, version, text, human, ct);
        return RedirectToPage(new { id });
    }

    /// <summary>Escalates a stale interrupted turn without fabricating a response.</summary>
    public async Task<IActionResult> OnPostRecoverAsync(string id, int version, CancellationToken ct)
    {
        await workflow.RecoverAsync(id, Customer, version, ct);
        return RedirectToPage(new { id });
    }
}
