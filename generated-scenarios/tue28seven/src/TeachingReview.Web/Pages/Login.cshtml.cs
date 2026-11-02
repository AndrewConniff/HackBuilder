using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using TeachingReview.Web.Models;
using TeachingReview.Web.Services;

namespace TeachingReview.Web.Pages;

/// <summary>Authenticates server-assigned local teacher accounts.</summary>
public sealed class LoginModel : PageModel
{
    /// <summary>Gets or sets the local account name.</summary>
    [BindProperty]
    public string Username { get; set; } = string.Empty;

    /// <summary>Gets or sets the transient password, never persisted by the page.</summary>
    [BindProperty]
    public string Password { get; set; } = string.Empty;

    /// <summary>Validates credentials and issues a bounded secure session.</summary>
    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) return Page();
        if (Username.Length > 80 || Password.Length > 200)
        {
            HttpContext.RequestServices.GetRequiredService<ILogger<LoginModel>>()
                .LogWarning("Rejected over-limit login input");
            ModelState.AddModelError(string.Empty, "Account name or password exceeds the permitted length.");
            return Page();
        }
        Teacher? teacher;
        try
        {
            teacher = await HttpContext.RequestServices.GetRequiredService<AccountService>()
                .LoginAsync(Username, Password, HttpContext.RequestAborted);
        }
        catch (WorkflowException error)
        {
            HttpContext.RequestServices.GetRequiredService<ILogger<LoginModel>>().LogWarning(
                error, "Concurrent account update during sign-in");
            ModelState.AddModelError(string.Empty, "Account changed during sign-in; please retry.");
            return Page();
        }
        if (teacher is null)
        {
            ModelState.AddModelError(string.Empty, "Sign-in failed or account is temporarily locked.");
            return Page();
        }
        var identity = new ClaimsIdentity([
            new(ClaimTypes.NameIdentifier, teacher.Id.ToString()),
            new(ClaimTypes.Name, teacher.FullName),
            new(ClaimTypes.Role, teacher.Role)
        ], CookieAuthenticationDefaults.AuthenticationScheme);
        await HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme,
            new ClaimsPrincipal(identity), new AuthenticationProperties { IsPersistent = false });
        return RedirectToPage("/Index");
    }
}
