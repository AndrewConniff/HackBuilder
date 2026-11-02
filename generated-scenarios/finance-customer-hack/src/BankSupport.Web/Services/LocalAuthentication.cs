using System.Security.Claims;
using BankSupport.Web.Models;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;

namespace BankSupport.Web.Services;

/// <summary>Server-assigned local roles, framework hashes and durable login lockout.</summary>
public sealed class LocalAuthentication(IDocumentStore store, ILogger<LocalAuthentication> logger)
{
    /// <summary>Validates an account and atomically updates its failed-login or successful-login state.</summary>
    public async Task<ClaimsPrincipal?> LoginAsync(string username, string password, CancellationToken ct)
    {
        username = username.Trim().ToLowerInvariant();
        if (!System.Text.RegularExpressions.Regex.IsMatch(username, "^[a-z0-9-]{1,40}$") || password.Length > 256)
            throw new BusinessException(400, "Invalid sign-in input.");
        var saved = await store.GetAsync<LocalAccount>("users", username, ct);
        var hasher = new PasswordHasher<LocalAccount>();
        if (saved is null)
        {
            logger.LogWarning("Unknown local sign-in attempt");
            return null;
        }
        var user = saved.Value;
        if (user.LockedUntil > DateTimeOffset.UtcNow)
        {
            logger.LogWarning("Locked local account sign-in rejected");
            return null;
        }
        var result = hasher.VerifyHashedPassword(user, user.PasswordHash, password);
        if (result == PasswordVerificationResult.Failed)
        {
            var failures = user.LockedUntil.HasValue ? 1 : user.Failures + 1;
            await store.ReplaceAsync("users", username, user with
            {
                Failures = failures,
                LockedUntil = failures >= 5 ? DateTimeOffset.UtcNow.AddMinutes(15) : null
            }, saved.ETag, ct);
            logger.LogWarning("Local sign-in failed");
            return null;
        }
        var refreshed = user with
        {
            Failures = 0, LockedUntil = null,
            PasswordHash = result == PasswordVerificationResult.SuccessRehashNeeded
                ? hasher.HashPassword(user, password) : user.PasswordHash
        };
        await store.ReplaceAsync("users", username, refreshed, saved.ETag, ct);
        return new ClaimsPrincipal(new ClaimsIdentity(new[]
        {
            new Claim(ClaimTypes.NameIdentifier, user.Username), new Claim(ClaimTypes.Name, user.DisplayName),
            new Claim(ClaimTypes.Role, user.Role), new Claim("customer", user.CustomerId),
            new Claim("stamp", user.Stamp)
        }, CookieAuthenticationDefaults.AuthenticationScheme));
    }

    /// <summary>Rejects revoked sessions and changed role assignments on every authenticated request.</summary>
    public async Task ValidateAsync(CookieValidatePrincipalContext context)
    {
        var username = context.Principal?.FindFirstValue(ClaimTypes.NameIdentifier);
        var user = username is null ? null : await store.GetAsync<LocalAccount>("users", username, context.HttpContext.RequestAborted);
        if (user is null || user.Value.Stamp != context.Principal?.FindFirstValue("stamp")
            || user.Value.Role != context.Principal?.FindFirstValue(ClaimTypes.Role)
            || user.Value.CustomerId != context.Principal?.FindFirstValue("customer"))
            context.RejectPrincipal();
    }
}
