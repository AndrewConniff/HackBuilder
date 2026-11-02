using System.Security.Claims;
using BankSupport.Web.Models;
using BankSupport.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace BankSupport.Web.Pages;

/// <summary>Human-service ownership with minimal unclaimed-case visibility.</summary>
public sealed class QueueModel(BankingWorkflow workflow) : PageModel
{
    /// <summary>Minimal queue entries, without transcripts or banking records.</summary>
    public IReadOnlyList<ServiceCase> Cases { get; private set; } = [];
    /// <summary>Conversation personally claimed by this representative.</summary>
    public ServiceCase? Conversation { get; private set; }
    private string Representative => User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? throw new BusinessException(403, "Representative identity is missing.");

    /// <summary>Lists cases and optionally reads the representative's own assigned conversation.</summary>
    public async Task OnGetAsync(string? id, CancellationToken ct)
    {
        Cases = await workflow.QueueAsync(ct);
        if (id is not null) Conversation = (await workflow.AssignedAsync(id, Representative, ct)).Value;
    }

    /// <summary>Claims an unowned case at its reviewed version.</summary>
    public async Task<IActionResult> OnPostClaimAsync(string id, int version, CancellationToken ct)
    {
        await workflow.ClaimAsync(id, Representative, version, ct);
        return RedirectToPage(new { id });
    }

    /// <summary>Replies to or closes only a personally claimed case.</summary>
    public async Task<IActionResult> OnPostReplyAsync(string id, int version, string text, bool close, CancellationToken ct)
    {
        await workflow.ReplyAsync(id, Representative, version, text, close, ct);
        return RedirectToPage(new { id });
    }
}
