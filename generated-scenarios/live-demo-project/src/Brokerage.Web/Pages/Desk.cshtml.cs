using System.Security.Claims;
using Brokerage.Web.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Brokerage.Web.Pages;

/// <summary>Provides the representative-owned support queue and response actions.</summary>
public class DeskModel(IServiceProvider services, ILogger<DeskModel> logger) : PageModel
{
    private readonly BrokerageStore store = services.GetRequiredService<BrokerageStore>();
    internal List<Conversation> Cases { get; private set; } = [];
    internal string? Error { get; private set; }

    /// <summary>Loads pending, claimed and resolved human cases.</summary>
    public async Task OnGetAsync() => Cases = await store.QueueAsync();

    /// <summary>Applies an authorized representative action to the expected revision.</summary>
    public async Task<IActionResult> OnPostAsync(string id, int revision, string action, string? text)
    {
        try
        {
            await store.ApplyAsync(id, User.FindFirstValue(ClaimTypes.NameIdentifier)!, true, revision, action, text);
            return RedirectToPage();
        }
        catch (Exception exception) when (exception is AccessException or InputException or StateConflictException)
        {
            logger.LogWarning(exception, "Representative action rejected for {Case}", id);
            Error = exception.Message;
            Response.StatusCode = exception is AccessException ? 403 : exception is StateConflictException ? 409 : 400;
            Cases = await store.QueueAsync();
            return Page();
        }
    }
}
