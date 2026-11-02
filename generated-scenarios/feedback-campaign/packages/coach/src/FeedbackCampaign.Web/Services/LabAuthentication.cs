using System.Security.Claims;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;

namespace FeedbackCampaign.Web;

/// <summary>Durable lab identity; passwords are stored only as salted Identity hashes.</summary>
public sealed record LabAccount(string Username, string PasswordHash, string[] Roles, string SecurityStamp,
    int FailedAttempts = 0, DateTimeOffset? LockedUntil = null);

/// <summary>Authenticates provisioned lab accounts without a directory dependency.</summary>
public sealed class LabAuthentication(IStateStore store, TimeProvider clock)
{
    /// <summary>Cookie scheme shared by login, logout and protected APIs.</summary>
    public const string Scheme = CookieAuthenticationDefaults.AuthenticationScheme;
    private readonly PasswordHasher<LabAccount> hasher = new();
    private readonly LabAccount dummy = new("unknown", string.Empty, [], string.Empty);
    private readonly string dummyHash = new PasswordHasher<LabAccount>().HashPassword(
        new("unknown", string.Empty, [], string.Empty), Convert.ToBase64String(RandomNumberGenerator.GetBytes(24)));

    /// <summary>Verifies a password and atomically records failures or clears an expired lockout.</summary>
    public async Task<ClaimsPrincipal?> Authenticate(string username, string password)
    {
        if (string.IsNullOrWhiteSpace(username) || username.Length > 80
            || string.IsNullOrEmpty(password) || password.Length > 256)
            return null;
        var key = username.Trim().ToLowerInvariant();
        if (!key.All(c => char.IsAsciiLetterOrDigit(c) || c == '-')) return null;
        var row = await store.Get<LabAccount>("accounts", key);
        var account = row?.Value ?? dummy;
        var verified = hasher.VerifyHashedPassword(account, row is null ? dummyHash : account.PasswordHash, password);
        if (row is null || account.LockedUntil > clock.GetUtcNow()) return null;
        if (verified == PasswordVerificationResult.Failed)
        {
            var failures = account.LockedUntil is not null ? 1 : account.FailedAttempts + 1;
            await store.Replace("accounts", key, account with
            {
                FailedAttempts = failures,
                LockedUntil = failures >= 5 ? clock.GetUtcNow().AddMinutes(15) : null
            }, row.ETag);
            return null;
        }
        var updated = account with
        {
            FailedAttempts = 0,
            LockedUntil = null,
            PasswordHash = verified == PasswordVerificationResult.SuccessRehashNeeded
                ? hasher.HashPassword(account, password) : account.PasswordHash
        };
        await store.Replace("accounts", key, updated, row.ETag);
        return Principal(updated);
    }

    /// <summary>Rejects sessions after account rotation or a change of assigned roles.</summary>
    public async Task<bool> IsCurrent(ClaimsPrincipal principal)
    {
        var username = principal.FindFirstValue(ClaimTypes.NameIdentifier);
        if (username is null) return false;
        var row = await store.Get<LabAccount>("accounts", username);
        return row is not null
            && row.Value.SecurityStamp == principal.FindFirstValue("lab-stamp")
            && row.Value.Roles.Order().SequenceEqual(principal.FindAll(ClaimTypes.Role).Select(c => c.Value).Order());
    }

    private static ClaimsPrincipal Principal(LabAccount account) => new(new ClaimsIdentity(
        new[] { new Claim(ClaimTypes.NameIdentifier, account.Username), new Claim(ClaimTypes.Name, account.Username),
            new Claim("lab-stamp", account.SecurityStamp) }
            .Concat(account.Roles.Select(role => new Claim(ClaimTypes.Role, role))), Scheme));
}

/// <summary>Validates each authenticated session against the durable account record.</summary>
public sealed class LabCookieEvents(LabAuthentication authentication) : CookieAuthenticationEvents
{
    /// <inheritdoc />
    public override async Task ValidatePrincipal(CookieValidatePrincipalContext context)
    {
        if (context.Principal is null || !await authentication.IsCurrent(context.Principal))
        {
            context.RejectPrincipal();
            await context.HttpContext.SignOutAsync(LabAuthentication.Scheme);
        }
    }

    /// <inheritdoc />
    public override Task RedirectToLogin(RedirectContext<CookieAuthenticationOptions> context)
    {
        if (context.Request.Path.StartsWithSegments("/api")) context.Response.StatusCode = 401;
        else context.Response.Redirect(context.RedirectUri);
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public override Task RedirectToAccessDenied(RedirectContext<CookieAuthenticationOptions> context)
    {
        context.Response.StatusCode = 403;
        return Task.CompletedTask;
    }
}
