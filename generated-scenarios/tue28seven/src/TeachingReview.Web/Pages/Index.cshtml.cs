using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using TeachingReview.Web.Models;
using TeachingReview.Web.Services;

namespace TeachingReview.Web.Pages;

/// <summary>Displays assigned teaching materials and executes human-controlled handoffs.</summary>
public sealed class IndexModel : PageModel
{
    internal List<Material> Materials { get; private set; } = [];

    /// <summary>Loads materials assigned to the signed-in teacher.</summary>
    public async Task OnGetAsync()
    {
        var actor = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        var snapshot = await HttpContext.RequestServices.GetRequiredService<IStateStore>()
            .ReadAsync(HttpContext.RequestAborted);
        Materials = snapshot.State.Materials.Where(x =>
            x.AuthorId == actor || x.PeerId == actor || x.LeadId == actor).ToList();
    }

    /// <summary>Applies an authorized version-bound workflow action.</summary>
    public async Task<IActionResult> OnPostAsync(int id, int version, string action, string? text)
    {
        try
        {
            await HttpContext.RequestServices.GetRequiredService<WorkflowService>().ExecuteAsync(
                int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!), id, version, action, text,
                HttpContext.RequestAborted);
            return RedirectToPage();
        }
        catch (WorkflowException error)
        {
            HttpContext.RequestServices.GetRequiredService<ILogger<IndexModel>>().LogWarning(
                error, "Rejected workflow action {Action} on {MaterialId}", action, id);
            ModelState.AddModelError(string.Empty, error.Message);
            Response.StatusCode = StatusCodes.Status409Conflict;
            await OnGetAsync();
            return Page();
        }
    }

    /// <summary>Ends the authenticated session after antiforgery validation.</summary>
    public async Task<IActionResult> OnPostLogoutAsync()
    {
        await HttpContext.SignOutAsync();
        return RedirectToPage("/Login");
    }
}
