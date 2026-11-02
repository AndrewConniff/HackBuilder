using BankSupport.Web.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.RateLimiting;

namespace BankSupport.Web.Pages;

/// <summary>Local account sign-in with antiforgery, rate limiting and durable lockout.</summary>
[EnableRateLimiting("login")]
public sealed class LoginModel(LocalAuthentication authentication) : PageModel
{
    /// <summary>Non-sensitive sign-in error for the current attempt.</summary>
    public string Error { get; private set; } = string.Empty;

    /// <summary>Authenticates using the account's server-assigned role.</summary>
    public async Task<IActionResult> OnPostAsync(string username, string password, CancellationToken ct)
    {
        if (string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
        {
            Response.StatusCode = 400;
            Error = "Username and password are required.";
            return Page();
        }
        var principal = await authentication.LoginAsync(username, password, ct);
        if (principal is null)
        {
            Response.StatusCode = 401;
            Error = "Sign-in failed or account is temporarily locked.";
            return Page();
        }
        await HttpContext.SignInAsync(principal, new AuthenticationProperties { IsPersistent = false });
        return RedirectToPage(principal.IsInRole("Customer") ? "/Index" : "/Queue");
    }
}
