using System.Security.Claims;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>Synthetic staff configuration; never populated from browser role or floor input.</summary>
public sealed record StaffAccount(string EmployeeId, string Name, string Role, int[] Floors, string PasswordHash);

/// <summary>Installation-scoped secret, delivered through protected configuration, not source control.</summary>
public sealed record StaffConfiguration(string SigningKey, string Generation, StaffAccount[] Employees);

/// <summary>Real demo-only password verification and short-lived, installation-scoped staff proofs.</summary>
public sealed class StaffAuthentication
{
    /// <summary>Host-only cookie shared by the staff authentication boundaries.</summary>
    public const string CookieName = "__Host-restaurant-staff";
    private const string Issuer = "fourth-coffee-synthetic-staff";
    private const string Audience = "resto-scale-agent-staff";
    private readonly StaffConfiguration? settings;
    private readonly TimeProvider clock;
    private readonly PasswordHasher<StaffAccount> hasher = new(Options.Create(new PasswordHasherOptions
        { IterationCount = 210_000 }));
    private readonly JsonWebTokenHandler handler = new() { MaximumTokenSizeInBytes = 8192 };

    /// <summary>Loads only operator-provided protected configuration; missing setup fails closed.</summary>
    public StaffAuthentication(IConfiguration configuration, TimeProvider clock, IHostEnvironment environment)
    {
        this.clock = clock;
        if (configuration["STAFF_AUTH_MODE"] != "synthetic-local"
            || !environment.IsEnvironment("Testing")
            || !string.IsNullOrWhiteSpace(configuration["AZURE_CLIENT_ID"])
            || !string.IsNullOrWhiteSpace(configuration["CONTAINER_APP_NAME"])
            || !string.IsNullOrWhiteSpace(configuration["COSMOS_ENDPOINT"]))
            throw new InvalidOperationException("Synthetic staff authentication is restricted to isolated local Testing hosts.");
        var json = configuration["STAFF_AUTH_JSON"];
        if (string.IsNullOrWhiteSpace(json) && configuration["STAFF_AUTH_FILE"] is { Length: > 0 } path)
            json = File.ReadAllText(path);
        if (string.IsNullOrWhiteSpace(json)) return;
        settings = JsonSerializer.Deserialize<StaffConfiguration>(json)
            ?? throw new InvalidOperationException("Synthetic staff configuration is invalid.");
        if (Convert.FromBase64String(settings.SigningKey).Length < 32
            || string.IsNullOrWhiteSpace(settings.Generation) || settings.Employees.Length == 0
            || settings.Employees.Select(a => a.EmployeeId).Distinct(StringComparer.Ordinal).Count() != settings.Employees.Length
            || settings.Employees.Any(a => string.IsNullOrWhiteSpace(a.EmployeeId) || string.IsNullOrWhiteSpace(a.PasswordHash)
                || a.Role is not ("Manager" or "Host" or "Server" or "Kitchen")
                || a.Floors.Length == 0 || a.Floors.Any(f => f is < 1 or > 5)))
            throw new InvalidOperationException("Synthetic staff configuration is invalid.");
    }

    /// <summary>Verifies an ASP.NET Identity V3 PBKDF2 hash and issues a nonrenewing 30-minute token.</summary>
    public string Login(string employeeId, string password)
    {
        if (settings is null) throw new DomainException(503, "Synthetic staff authentication is not installed.");
        if (string.IsNullOrWhiteSpace(employeeId) || password is null || password.Length is < 1 or > 256)
            throw new DomainException(401, "Invalid employee ID or password.");
        var account = settings.Employees.SingleOrDefault(a => a.EmployeeId == employeeId);
        // Unknown IDs perform the same expensive hash check; never expose whether an ID exists.
        var comparison = account ?? settings.Employees[0];
        var result = hasher.VerifyHashedPassword(comparison, comparison.PasswordHash, password);
        if (account is null || result == PasswordVerificationResult.Failed)
            throw new DomainException(401, "Invalid employee ID or password.");
        var now = clock.GetUtcNow().UtcDateTime;
        return handler.CreateToken(new SecurityTokenDescriptor
        {
            Issuer = Issuer, Audience = Audience, IssuedAt = now, NotBefore = now, Expires = now.AddMinutes(30),
            Claims = new Dictionary<string, object> { ["sub"] = account.EmployeeId, ["generation"] = settings.Generation },
            SigningCredentials = new(new SymmetricSecurityKey(Convert.FromBase64String(settings.SigningKey)),
                SecurityAlgorithms.HmacSha256)
        });
    }

    /// <summary>Checks signature, lifetime and installation generation; rebuilds permissions from server records.</summary>
    public async Task<ClaimsPrincipal> Validate(string proof)
    {
        if (settings is null) throw new DomainException(401, "Invalid or expired staff session.");
        var now = clock.GetUtcNow().UtcDateTime;
        var result = await handler.ValidateTokenAsync(proof, new TokenValidationParameters
        {
            ValidIssuer = Issuer, ValidAudience = Audience,
            IssuerSigningKey = new SymmetricSecurityKey(Convert.FromBase64String(settings.SigningKey)),
            ValidAlgorithms = [SecurityAlgorithms.HmacSha256], RequireSignedTokens = true,
            ValidateIssuer = true, ValidateAudience = true, ValidateLifetime = true, RequireExpirationTime = true,
            ClockSkew = TimeSpan.Zero,
            LifetimeValidator = (nbf, exp, _, _) => nbf.HasValue && exp.HasValue && nbf <= now && exp > now
        });
        if (!result.IsValid || !result.ClaimsIdentity.HasClaim("generation", settings.Generation))
            throw new DomainException(401, "Invalid or expired staff session.");
        var account = settings.Employees.SingleOrDefault(a =>
            a.EmployeeId == result.ClaimsIdentity.FindFirst("sub")?.Value)
            ?? throw new DomainException(401, "Invalid or expired staff session.");
        return new(new ClaimsIdentity(new[] {
            new Claim("sub", account.EmployeeId), new Claim("name", account.Name), new Claim("roles", account.Role)
        }.Concat(account.Floors.Select(f => new Claim("roles", $"Floor.{f}"))), "staff", "name", "roles"));
    }
}

/// <summary>Authenticates synthetic proofs only on explicitly isolated local test hosts.</summary>
public sealed class StaffAuthenticationHandler(
    IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder,
    StaffAuthentication staff) : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    protected override async Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var header = Request.Headers.Authorization.ToString();
        var proof = header.StartsWith("Bearer ", StringComparison.Ordinal)
            ? header[7..] : Request.Cookies[StaffAuthentication.CookieName];
        if (string.IsNullOrEmpty(proof)) return AuthenticateResult.NoResult();
        try { return AuthenticateResult.Success(new(await staff.Validate(proof), "staff")); }
        catch (DomainException) { return AuthenticateResult.Fail("Invalid or expired staff session."); }
    }
}
