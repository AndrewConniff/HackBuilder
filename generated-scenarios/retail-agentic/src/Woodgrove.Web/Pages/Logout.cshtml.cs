using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Woodgrove.Web.Pages;

/// <summary>Explicit CSRF-protected session termination.</summary>
public sealed class LogoutModel : PageModel
{
    /// <summary>Rejects state-changing GET requests.</summary>
    public IActionResult OnGet() => StatusCode(405);

    /// <summary>Clears the authenticated local session.</summary>
    public async Task<IActionResult> OnPostAsync()
    {
        await HttpContext.SignOutAsync();
        return RedirectToPage("/Login");
    }
}
