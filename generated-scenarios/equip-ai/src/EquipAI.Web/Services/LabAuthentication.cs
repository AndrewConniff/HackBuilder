using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using Azure;
using Azure.Identity;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using EquipAI.Web.Models;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection.Repositories;
using Microsoft.AspNetCore.Identity;

namespace EquipAI.Web.Services;

internal sealed record LabAccount(string Username, string PasswordHash, string[] Roles, string SecurityStamp,
    int FailedAttempts = 0, DateTimeOffset? LockedUntil = null);
internal sealed record AccountRow(LabAccount Account, ETag ETag);
internal sealed record LoginRequest(string Username, string Password);

internal interface ILabAccounts
{
    Task<AccountRow?> ReadAsync(string username, CancellationToken token);
    Task ReplaceAsync(LabAccount account, ETag etag, CancellationToken token);
}

internal sealed class BlobLabAccounts(IConfiguration config) : ILabAccounts, IXmlRepository
{
    private readonly Lazy<BlobContainerClient> container = new(() => new BlobServiceClient(
        new Uri(AgentContract.Required(config, "StorageEndpoint")), new DefaultAzureCredential())
        .GetBlobContainerClient("accounts"));

    /// <summary>Reads a provisioned account; only a genuine missing blob is treated as absent.</summary>
    public async Task<AccountRow?> ReadAsync(string username, CancellationToken token)
    {
        try
        {
            var result = await container.Value.GetBlobClient($"users/{username}.json").DownloadContentAsync(token);
            return new(result.Value.Content.ToObjectFromJson<LabAccount>()
                ?? throw new InvalidDataException("Invalid account record."), result.Value.Details.ETag);
        }
        catch (RequestFailedException error) when (error.Status == 404) { return null; }
    }

    /// <summary>Atomically replaces the exact account version, preventing lost lockout updates.</summary>
    public async Task ReplaceAsync(LabAccount account, ETag etag, CancellationToken token) =>
        await container.Value.GetBlobClient($"users/{account.Username}.json").UploadAsync(
            BinaryData.FromObjectAsJson(account),
            new BlobUploadOptions { Conditions = new BlobRequestConditions { IfMatch = etag } }, token);

    /// <summary>Loads persisted session keys from the account-only container.</summary>
    public IReadOnlyCollection<XElement> GetAllElements() => container.Value.GetBlobs(
        BlobTraits.None, BlobStates.None, "keys/", CancellationToken.None)
        .Select(blob => XElement.Parse(container.Value.GetBlobClient(blob.Name).DownloadContent().Value.Content.ToString()))
        .ToArray();

    /// <summary>Writes each immutable framework key under its own unique blob name.</summary>
    public void StoreElement(XElement element, string friendlyName) =>
        container.Value.GetBlobClient($"keys/{Guid.NewGuid():N}.xml")
            .Upload(BinaryData.FromString(element.ToString(SaveOptions.DisableFormatting)), overwrite: false);

    internal async Task InstallAsync(string seedPath, CancellationToken token)
    {
        var accounts = JsonSerializer.Deserialize<LabAccount[]>(await File.ReadAllTextAsync(seedPath, token))
            ?? throw new InvalidDataException("Missing account seed.");
        if (accounts.Length != LabAuthentication.ProvisionedRoles.Count ||
            accounts.Select(account => account.Username).Distinct().Count() != accounts.Length)
            throw new InvalidDataException("Incomplete or duplicate account seed.");
        foreach (var account in accounts)
        {
            if (!LabAuthentication.ProvisionedRoles.TryGetValue(account.Username, out var roles) ||
                !account.Roles.SequenceEqual(roles) || string.IsNullOrWhiteSpace(account.PasswordHash) ||
                string.IsNullOrWhiteSpace(account.SecurityStamp))
                throw new InvalidDataException("Invalid provisioned account or role boundary.");
            var current = await ReadAsync(account.Username, token);
            if (current is not null)
            {
                if (current.Account.SecurityStamp != account.SecurityStamp ||
                    !current.Account.Roles.SequenceEqual(account.Roles))
                    throw new InvalidDataException("Existing account differs from this deployment; explicit rotation required.");
                continue;
            }
            await container.Value.GetBlobClient($"users/{account.Username}.json").UploadAsync(
                BinaryData.FromObjectAsJson(account),
                new BlobUploadOptions { Conditions = new BlobRequestConditions { IfNoneMatch = ETag.All } }, token);
        }
        Console.WriteLine("Local accounts installed through managed identity; no passwords returned.");
    }

    internal async Task ResetLockoutAsync(string username, CancellationToken token)
    {
        if (!LabAuthentication.ProvisionedRoles.ContainsKey(username))
            throw new InvalidDataException("Only a provisioned scenario account can be reset.");
        var row = await ReadAsync(username, token)
            ?? throw new InvalidDataException("The scenario account is not installed.");
        await ReplaceAsync(row.Account with { FailedAttempts = 0, LockedUntil = null }, row.ETag, token);
        Console.WriteLine("EQUIP_LOCKOUT_RESET_OK");
    }
}

internal sealed class LabAuthentication(ILabAccounts store, TimeProvider clock)
{
    internal const string Scheme = CookieAuthenticationDefaults.AuthenticationScheme;
    internal static readonly IReadOnlyDictionary<string, string[]> ProvisionedRoles =
        new Dictionary<string, string[]>
        {
            ["tacoma-support"] = ["Operations.Tacoma"],
            ["statewide-lead"] = ["Operations.Statewide"],
            ["coach"] = ["Operations.Statewide", "Coach"]
        };
    private readonly PasswordHasher<LabAccount> hasher = new();
    private readonly LabAccount dummy = new("unknown", string.Empty, [], string.Empty);
    private readonly string dummyHash = new PasswordHasher<LabAccount>().HashPassword(
        new("unknown", string.Empty, [], string.Empty), Convert.ToHexString(RandomNumberGenerator.GetBytes(24)));

    internal async Task<ClaimsPrincipal?> AuthenticateAsync(string username, string password, CancellationToken token)
    {
        if (string.IsNullOrWhiteSpace(username) || username.Length > 80 ||
            string.IsNullOrEmpty(password) || password.Length > 256)
            return null;
        var key = username.Trim().ToLowerInvariant();
        if (!key.All(c => char.IsAsciiLetterOrDigit(c) || c == '-')) return null;
        for (int attempt = 0; attempt < 5; attempt++)
        {
            var row = await store.ReadAsync(key, token);
            var account = row?.Account ?? dummy;
            var verified = hasher.VerifyHashedPassword(account, row is null ? dummyHash : account.PasswordHash, password);
            if (row is null || account.LockedUntil > clock.GetUtcNow()) return null;
            var failed = verified == PasswordVerificationResult.Failed;
            var failures = account.LockedUntil is not null ? 1 : account.FailedAttempts + 1;
            var updated = failed ? account with
            {
                FailedAttempts = failures,
                LockedUntil = failures >= 5 ? clock.GetUtcNow().AddMinutes(15) : null
            } : account with
            {
                FailedAttempts = 0, LockedUntil = null,
                PasswordHash = verified == PasswordVerificationResult.SuccessRehashNeeded
                    ? hasher.HashPassword(account, password) : account.PasswordHash
            };
            try { await store.ReplaceAsync(updated, row.ETag, token); }
            catch (RequestFailedException error) when (error.Status == 412) { continue; }
            if (failed) return null;
            return new ClaimsPrincipal(new ClaimsIdentity(
                new[] { new Claim(ClaimTypes.NameIdentifier, updated.Username),
                    new Claim(ClaimTypes.Name, updated.Username), new Claim("lab-stamp", updated.SecurityStamp) }
                    .Concat(updated.Roles.Select(role => new Claim(ClaimTypes.Role, role))), Scheme));
        }
        throw new ScenarioException("account_busy", "Concurrent sign-in attempts; try again shortly.", 409);
    }

    internal async Task<bool> IsCurrentAsync(ClaimsPrincipal principal, CancellationToken token)
    {
        var username = principal.FindFirstValue(ClaimTypes.NameIdentifier);
        if (username is null) return false;
        var row = await store.ReadAsync(username, token);
        return row is not null && row.Account.SecurityStamp == principal.FindFirstValue("lab-stamp") &&
            row.Account.Roles.Order().SequenceEqual(principal.FindAll(ClaimTypes.Role).Select(c => c.Value).Order());
    }

    internal static void PrepareAccess(IConfiguration config)
    {
        var directory = AgentContract.Required(config, "AccessDirectory");
        var seedPath = Path.Combine(directory, "account-seed.json");
        var participantPath = Path.Combine(directory, "participant-access.json");
        var coachPath = Path.Combine(directory, "coach-access.json");
        var present = new[] { seedPath, participantPath, coachPath }.Count(File.Exists);
        if (present == 3) { Console.WriteLine("Existing deployment-specific private access files reused."); return; }
        if (present != 0) throw new InvalidDataException("Incomplete private credential set; explicit recovery required.");
        Directory.CreateDirectory(directory);
        var hashes = new List<LabAccount>();
        var participants = new List<object>();
        var coaches = new List<object>();
        foreach (var (username, roles) in ProvisionedRoles)
        {
            var password = Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
            var account = new LabAccount(username, string.Empty, roles, Guid.NewGuid().ToString("N"));
            hashes.Add(account with { PasswordHash = new PasswordHasher<LabAccount>().HashPassword(account, password) });
            (username == "coach" ? coaches : participants).Add(new { username, password, roles });
        }
        foreach (var (path, accounts) in new[] { (participantPath, participants), (coachPath, coaches) })
            File.WriteAllText(path, JsonSerializer.Serialize(new
            {
                scenario = "equip-ai", generatedAtUtc = DateTimeOffset.UtcNow,
                loginPath = "/", credentialHandling = "Private deployment access. Do not publish or copy to other teams.",
                accounts
            }, new JsonSerializerOptions { WriteIndented = true }));
        File.WriteAllText(seedPath, JsonSerializer.Serialize(hashes));
        Console.WriteLine("Unique private participant/coach access files and salted installation seed prepared.");
    }
}

internal sealed class LabCookieEvents(LabAuthentication authentication) : CookieAuthenticationEvents
{
    /// <inheritdoc />
    public override async Task ValidatePrincipal(CookieValidatePrincipalContext context)
    {
        if (context.Principal is null ||
            !await authentication.IsCurrentAsync(context.Principal, context.HttpContext.RequestAborted))
        {
            context.RejectPrincipal();
            await context.HttpContext.SignOutAsync(LabAuthentication.Scheme);
        }
    }

    /// <inheritdoc />
    public override Task RedirectToLogin(RedirectContext<CookieAuthenticationOptions> context)
    {
        context.Response.StatusCode = 401;
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public override Task RedirectToAccessDenied(RedirectContext<CookieAuthenticationOptions> context)
    {
        context.Response.StatusCode = 403;
        return Task.CompletedTask;
    }
}
