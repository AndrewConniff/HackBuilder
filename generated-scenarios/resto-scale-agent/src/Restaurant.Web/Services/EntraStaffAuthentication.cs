using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>Configures single-tenant delegated API access at both web and internal chat boundaries.</summary>
public static class EntraStaffAuthentication
{
    /// <summary>Rejects foreign, expired, application-only, ID and unauthorized client tokens.</summary>
    public static void Configure(JwtBearerOptions options, IConfiguration configuration)
    {
        var tenant = configuration["STAFF_TENANT_ID"];
        var audience = configuration["STAFF_AUDIENCE"];
        var client = configuration["STAFF_CLIENT_ID"];
        var configured = Guid.TryParse(tenant, out _) && Guid.TryParse(audience, out _) && Guid.TryParse(client, out _);
        if (!configured && new[] { tenant, audience, client }.Any(value => !string.IsNullOrWhiteSpace(value)))
            throw new InvalidOperationException("Complete verified staff tenant, API audience and client IDs are required.");
        if (configured)
            options.Authority = $"https://login.microsoftonline.com/{tenant}/v2.0";
        options.MapInboundClaims = false;
        options.SaveToken = false;
        options.TokenValidationParameters = new()
        {
            ValidIssuer = $"https://login.microsoftonline.com/{tenant}/v2.0",
            ValidAudience = audience,
            ValidateIssuer = true, ValidateAudience = true, ValidateLifetime = true,
            ValidateIssuerSigningKey = true, RequireSignedTokens = true, RequireExpirationTime = true,
            ValidAlgorithms = [SecurityAlgorithms.RsaSha256],
            ClockSkew = TimeSpan.Zero, AuthenticationType = "staff", NameClaimType = "name", RoleClaimType = "roles"
        };
        options.Events = new()
        {
            OnMessageReceived = context =>
            {
                if (string.IsNullOrEmpty(context.Request.Headers.Authorization))
                    context.Token = context.Request.Cookies[StaffAuthentication.CookieName];
                return Task.CompletedTask;
            },
            OnTokenValidated = context =>
            {
                var principal = context.Principal!;
                if (!configured || principal.FindFirstValue("tid") != tenant
                    || principal.FindFirstValue("ver") != "2.0"
                    || principal.FindFirstValue("azp") != client
                    || !Guid.TryParse(principal.FindFirstValue("oid"), out _)
                    || !(principal.FindFirstValue("scp") ?? string.Empty).Split(' ').Contains("access_as_user"))
                {
                    context.Fail("A delegated access token for this staff API, tenant and client is required.");
                    return Task.CompletedTask;
                }
                // Only installed app roles grant floor access; arbitrary custom floor claims do not.
                foreach (var identity in principal.Identities)
                    foreach (var claim in identity.FindAll("floors").ToArray())
                        identity.RemoveClaim(claim);
                try { _ = Caller.From(principal); }
                catch (DomainException exception) { context.Fail(exception.Message); }
                return Task.CompletedTask;
            }
        };
    }
}
