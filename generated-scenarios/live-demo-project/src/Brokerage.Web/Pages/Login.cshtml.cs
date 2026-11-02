using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Brokerage.Web.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Brokerage.Web.Pages;

/// <summary>Authenticates deployment-specific local demonstration accounts.</summary>
public class LoginModel(IServiceProvider services, ILogger<LoginModel> logger) : PageModel
{
    /// <summary>Gets or sets the local account identifier.</summary>
    [BindProperty, Required, StringLength(100)]
    public string Username { get; set; } = string.Empty;

    /// <summary>Gets or sets the password for this request only.</summary>
    [BindProperty, Required, StringLength(200)]
    public string Password { get; set; } = string.Empty;

    /// <summary>Validates credentials and establishes a bounded server-assigned-role session.</summary>
    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid)
        {
            return Page();
        }
        var account = await services.GetRequiredService<BrokerageStore>().LoginAsync(Username, Password);
        if (account is null)
        {
            logger.LogWarning("Local login denied. Reference {Correlation}", HttpContext.TraceIdentifier);
            ModelState.AddModelError(string.Empty, "Sign-in failed or this account is temporarily locked.");
            Response.StatusCode = 401;
            return Page();
        }
        var identity = new ClaimsIdentity([
            new(ClaimTypes.NameIdentifier, account.Id),
            new(ClaimTypes.Name, account.Name),
            new(ClaimTypes.Role, account.Role)
        ], CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme,
            new ClaimsPrincipal(identity), new AuthenticationProperties { IsPersistent = false });
        return RedirectToPage(account.Role == "Coach" ? "/Desk" : "/Index");
    }

    /// <summary>Revokes the current local browser session.</summary>
    public async Task<IActionResult> OnPostLogoutAsync()
    {
        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        return RedirectToPage("/Login");
    }
}
