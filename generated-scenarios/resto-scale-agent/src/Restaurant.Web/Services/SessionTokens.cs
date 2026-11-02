using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Azure.Core;
using Azure.Security.KeyVault.Keys;
using Azure.Security.KeyVault.Keys.Cryptography;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>Public-only representation of a versioned guest-session verification key.</summary>
public sealed record PublicSessionKey(string Version, string N, string E);

/// <summary>Key Vault guest signing and cached public-key verification, including internal chat revalidation.</summary>
public sealed class SessionTokens(IConfiguration configuration, TokenCredential credential,
    IMemoryCache cache, IHttpClientFactory http, TimeProvider clock)
{
    private const string Issuer = "fourth-coffee-guest";
    private const string Audience = "restaurant-guest";

    /// <summary>Issues a short-lived scoped token using the managed-identity-accessible Key Vault signing key.</summary>
    public async Task<string> Issue(Visit visit, CancellationToken token)
    {
        var client = new KeyClient(new Uri(Required("KEY_VAULT_URI")), credential);
        var key = (await client.GetKeyAsync("guest-session", cancellationToken: token)).Value;
        var header = Base64UrlEncoder.Encode(JsonSerializer.SerializeToUtf8Bytes(new
            { alg = "RS256", typ = "JWT", kid = key.Properties.Version }));
        var payload = Base64UrlEncoder.Encode(JsonSerializer.SerializeToUtf8Bytes(new
        {
            iss = Issuer, aud = Audience, sub = $"guest:{visit.id}", visit = visit.id,
            nbf = clock.GetUtcNow().ToUnixTimeSeconds(), exp = clock.GetUtcNow().AddHours(1).ToUnixTimeSeconds()
        }));
        var body = $"{header}.{payload}";
        var signer = new CryptographyClient(key.Id, credential);
        var signature = await signer.SignDataAsync(SignatureAlgorithm.RS256, Encoding.ASCII.GetBytes(body), token);
        return $"{body}.{Base64UrlEncoder.Encode(signature.Signature)}";
    }

    /// <summary>Retrieves a retained key version; only the transaction identity needs Key Vault access.</summary>
    public async Task<PublicSessionKey> PublicKey(string version, CancellationToken token)
    {
        ValidateVersion(version);
        var key = (await new KeyClient(new Uri(Required("KEY_VAULT_URI")), credential)
            .GetKeyAsync("guest-session", version, token)).Value;
        return new(version, Base64UrlEncoder.Encode(key.Key.N), Base64UrlEncoder.Encode(key.Key.E));
    }

    /// <summary>Validates signature, issuer, audience, expiry and required visit scope.</summary>
    public async Task<ClaimsPrincipal> Validate(string token, CancellationToken cancellation)
    {
        var handler = new JsonWebTokenHandler { MaximumTokenSizeInBytes = 8192 };
        if (!handler.CanReadToken(token)) throw new DomainException(401, "Malformed guest token.");
        var jwt = handler.ReadJsonWebToken(token);
        ValidateVersion(jwt.Kid);
        var key = await cache.GetOrCreateAsync($"guest-key:{jwt.Kid}", async entry =>
        {
            entry.AbsoluteExpirationRelativeToNow = TimeSpan.FromMinutes(10);
            if (configuration["APP_ROLE"] != "chat") return await PublicKey(jwt.Kid, cancellation);
            var baseUrl = Required("TRANSACTION_BASE_URL").TrimEnd('/');
            return await http.CreateClient("internal").GetFromJsonAsync<PublicSessionKey>(
                $"{baseUrl}/api/session/keys/{jwt.Kid}", cancellation)
                ?? throw new InvalidDataException("Transaction service returned no verification key.");
        }) ?? throw new InvalidDataException("No guest verification key.");
        var securityKey = new RsaSecurityKey(new RSAParameters
            { Modulus = Base64UrlEncoder.DecodeBytes(key.N), Exponent = Base64UrlEncoder.DecodeBytes(key.E) });
        var result = await handler.ValidateTokenAsync(token, new TokenValidationParameters
        {
            ValidIssuer = Issuer, ValidAudience = Audience, IssuerSigningKey = securityKey,
            ValidAlgorithms = [SecurityAlgorithms.RsaSha256], ValidateIssuer = true, ValidateAudience = true,
            ValidateLifetime = true, RequireExpirationTime = true, RequireSignedTokens = true,
            ClockSkew = TimeSpan.FromSeconds(15)
        });
        if (!result.IsValid || !result.ClaimsIdentity.HasClaim(c => c.Type == "visit"))
            throw new DomainException(401, "Invalid or expired guest token.");
        return new(new ClaimsIdentity(result.ClaimsIdentity.Claims, "guest"));
    }

    private string Required(string name) => configuration[name]
        ?? throw new InvalidOperationException($"Required configuration {name} is missing.");

    private static void ValidateVersion(string version)
    {
        if (version.Length != 32 || version.Any(c => !char.IsAsciiHexDigit(c)))
            throw new DomainException(401, "Invalid guest signing-key version.");
    }
}

/// <summary>Authenticates guest cookies or guest bearer proofs without accepting staff claims from them.</summary>
public sealed class GuestAuthenticationHandler(
    IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger,
    UrlEncoder encoder, SessionTokens sessions)
    : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    /// <summary>Validates proof under the guest-specific issuer and signing key.</summary>
    protected override async Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var authorization = Request.Headers.Authorization.ToString();
        var token = authorization.StartsWith("Bearer ", StringComparison.Ordinal)
            ? authorization[7..] : Request.Cookies["restaurant-session"];
        if (string.IsNullOrEmpty(token)) return AuthenticateResult.NoResult();
        try
        {
            var principal = await sessions.Validate(token, Context.RequestAborted);
            return AuthenticateResult.Success(new(principal, "guest"));
        }
        catch (DomainException exception) when (exception.Status == 401)
        {
            Logger.LogWarning("Guest authentication rejected: {Reason}", exception.Message);
            return AuthenticateResult.Fail(exception.Message);
        }
    }
}
