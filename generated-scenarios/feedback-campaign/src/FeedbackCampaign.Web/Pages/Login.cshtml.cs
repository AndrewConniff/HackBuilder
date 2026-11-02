using Azure;
using Azure.Identity;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace FeedbackCampaign.Web.Pages;

/// <summary>Local lab sign-in with antiforgery, durable account lockout and signed cookies.</summary>
public sealed class LoginModel(LabAuthentication authentication, ILogger<LoginModel> logger) : PageModel
{
    /// <summary>Installer-issued lab username.</summary>
    [BindProperty]
    public string Username { get; set; } = string.Empty;

    /// <summary>Transient password; never rendered back to the page or logged.</summary>
    [BindProperty]
    public string Password { get; set; } = string.Empty;

    /// <summary>Authenticates the assigned account without an external consent flow.</summary>
    public async Task<IActionResult> OnPostAsync()
    {
        try
        {
            if (!ModelState.IsValid) return Rejected();
            var principal = await authentication.Authenticate(Username, Password);
            if (principal is null) return Rejected();
            await HttpContext.SignInAsync(LabAuthentication.Scheme, principal,
                new AuthenticationProperties { IsPersistent = false });
            return LocalRedirect("/");
        }
        catch (RequestFailedException error) when (error.Status == 412)
        {
            logger.LogWarning("Concurrent lab sign-in update; retry required.");
            Response.StatusCode = 409;
            ModelState.AddModelError(string.Empty, "Sign-in changed concurrently. Please retry.");
            return Page();
        }
        catch (Exception error) when (error is RequestFailedException or AuthenticationFailedException)
        {
            logger.LogError("Lab sign-in storage dependency failed: {Category}", error.GetType().Name);
            Response.StatusCode = 503;
            ModelState.AddModelError(string.Empty, "Sign-in service is unavailable. No session was created.");
            return Page();
        }
        finally
        {
            Password = string.Empty;
            ModelState.Remove(nameof(Password));
        }
    }

    private PageResult Rejected()
    {
        Response.StatusCode = 401;
        ModelState.AddModelError(string.Empty, "Sign-in failed. Verify your issued credentials or wait 15 minutes if locked.");
        return Page();
    }
}
