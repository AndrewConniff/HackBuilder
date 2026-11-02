using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Woodgrove.Web.Models;
using Woodgrove.Web.Services;

namespace Woodgrove.Web.Pages;

/// <summary>Local-account sign-in with Razor antiforgery and durable lockout.</summary>
public sealed class LoginModel(LocalAccounts accounts) : PageModel
{
    /// <summary>Gets or sets the local deployment username.</summary>
    [BindProperty, Required, StringLength(80)]
    public string Username { get; set; } = string.Empty;

    /// <summary>Gets or sets the submitted password; it is never persisted as page state.</summary>
    [BindProperty, Required, StringLength(256)]
    public string Password { get; set; } = string.Empty;

    /// <summary>Authenticates and creates a bounded secure session.</summary>
    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) { Response.StatusCode = 400; return Page(); }
        try
        {
            var principal = await accounts.AuthenticateAsync(Username, Password, HttpContext.RequestAborted);
            await HttpContext.SignInAsync(principal, new AuthenticationProperties { IsPersistent = false });
            return RedirectToPage("/Index");
        }
        catch (PolicyException ex)
        {
            ModelState.AddModelError(string.Empty, ex.Message);
            ModelState.Remove(nameof(Password));
            Password = string.Empty;
            Response.StatusCode = 400;
            return Page();
        }
    }
}
