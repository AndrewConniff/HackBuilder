using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace BankSupport.Web.Pages;

/// <summary>Explicit antiforgery-protected session termination.</summary>
public sealed class LogoutModel : PageModel
{
    /// <summary>Removes the session cookie without a state-changing GET.</summary>
    public async Task<IActionResult> OnPostAsync()
    {
        await HttpContext.SignOutAsync();
        return RedirectToPage("/Login");
    }
}
