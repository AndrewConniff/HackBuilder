using System.Security.Cryptography;
using System.Text.Json;
using Azure;
using Azure.Core;
using Azure.Data.Tables;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;

namespace CoffeeShop.Web.Services;

/// <summary>A scenario-owned login with server-controlled store assignments and persistent lockout.</summary>
public sealed record LocalAccount(string Username, string PasswordHash, string Role, string[] Stores,
    string SecurityStamp, int FailedAttempts = 0, DateTimeOffset? LockedUntil = null);

/// <summary>An account and its concurrency token.</summary>
public sealed record StoredAccount(LocalAccount Value, string ETag);

/// <summary>Persists account state independently of web workers.</summary>
public interface IAccountRepository
{
    /// <summary>Looks up a normalized username without creating an account.</summary>
    Task<StoredAccount?> FindAsync(string username, CancellationToken ct);
    /// <summary>Updates account state only if the concurrency token still matches.</summary>
    Task<bool> ReplaceAsync(StoredAccount account, CancellationToken ct);
}

/// <summary>Stores password hashes and lockout state in the scenario's managed-identity-protected Table.</summary>
public sealed class TableAccountRepository(IConfiguration configuration, TokenCredential credential) : IAccountRepository
{
    private readonly TableClient client = new(new Uri(configuration["Storage:Endpoint"]
        ?? throw new InvalidOperationException("Storage endpoint not installed.")), "IceCreamBackOffice", credential);

    /// <inheritdoc />
    public async Task<StoredAccount?> FindAsync(string username, CancellationToken ct)
    {
        var entity = await client.GetEntityIfExistsAsync<TableEntity>("accounts", username, cancellationToken: ct);
        return entity.HasValue
            ? new(JsonSerializer.Deserialize<LocalAccount>(entity.Value!.GetString("Payload"))
                ?? throw new InvalidOperationException("Invalid account state."), entity.Value.ETag.ToString())
            : null;
    }

    /// <inheritdoc />
    public async Task<bool> ReplaceAsync(StoredAccount account, CancellationToken ct)
    {
        try
        {
            await client.UpdateEntityAsync(Entity(account.Value), new ETag(account.ETag), TableUpdateMode.Replace, ct);
            return true;
        }
        catch (RequestFailedException error) when (error.Status == 412) { return false; }
    }

    /// <summary>Creates the Table representation without storing plaintext credentials.</summary>
    public static TableEntity Entity(LocalAccount account) => new("accounts", account.Username)
    {
        ["Payload"] = JsonSerializer.Serialize(account)
    };
}

/// <summary>Verifies salted PBKDF2 hashes and enforces a shared five-attempt, fifteen-minute lockout.</summary>
public sealed class LocalAccounts(IAccountRepository repository, ILogger<LocalAccounts> logger)
{
    private static readonly PasswordHasher<LocalAccount> Hasher = new(Options.Create(
        new PasswordHasherOptions { IterationCount = 210_000 }));
    private static readonly LocalAccount Unknown = Create("unknown",
        Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)), "StoreManager", []);

    /// <summary>Creates a fresh salted hash and session-revocation stamp for installation.</summary>
    public static LocalAccount Create(string username, string password, string role, string[] stores)
    {
        var account = new LocalAccount(username, string.Empty, role, stores, Guid.NewGuid().ToString("N"));
        return account with { PasswordHash = Hasher.HashPassword(account, password) };
    }

    /// <summary>Checks a supplied password without exposing the persisted hash.</summary>
    public static bool PasswordMatches(LocalAccount account, string password) =>
        Hasher.VerifyHashedPassword(account, account.PasswordHash, password) != PasswordVerificationResult.Failed;

    /// <summary>Returns the server-owned account only after password and lockout checks succeed.</summary>
    public async Task<LocalAccount?> AuthenticateAsync(string? username, string? password, CancellationToken ct)
    {
        if (username is null || password is null || username.Length is < 1 or > 32 || password.Length is < 1 or > 128
            || !System.Text.RegularExpressions.Regex.IsMatch(username, "^[a-zA-Z][a-zA-Z0-9]{0,31}$"))
        {
            logger.LogWarning("Local sign-in rejected: invalid input.");
            return null;
        }
        username = username.ToLowerInvariant();
        for (var attempt = 0; attempt < 3; attempt++)
        {
            var stored = await repository.FindAsync(username, ct);
            var account = stored?.Value ?? Unknown;
            var matches = PasswordMatches(account, password);
            if (stored is null || account.LockedUntil > DateTimeOffset.UtcNow)
            {
                logger.LogWarning("Local sign-in rejected: unknown or locked account.");
                return null;
            }
            var failures = account.LockedUntil is not null ? 0 : account.FailedAttempts;
            var updated = matches
                ? account with { FailedAttempts = 0, LockedUntil = null }
                : account with
                {
                    FailedAttempts = failures + 1,
                    LockedUntil = failures + 1 >= 5 ? DateTimeOffset.UtcNow.AddMinutes(15) : null
                };
            if (!await repository.ReplaceAsync(new(updated, stored.ETag), ct)) continue;
            if (!matches) logger.LogWarning("Local sign-in rejected: invalid credentials.");
            return matches ? updated : null;
        }
        throw new InvalidOperationException("Concurrent login state changed; retry later.");
    }
}
