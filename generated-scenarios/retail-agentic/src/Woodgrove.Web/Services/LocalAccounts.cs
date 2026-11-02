using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using System.Security.AccessControl;
using System.Security.Principal;
using Azure;
using Azure.Data.Tables;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.Options;
using Woodgrove.Web.Models;

namespace Woodgrove.Web.Services;

/// <summary>Local app identities with durable password hashes, lockout and server-assigned roles.</summary>
public sealed class LocalAccounts(TableServiceClient service, ILogger<LocalAccounts> logger)
{
    private readonly TableClient table = service.GetTableClient("Accounts");
    private readonly PasswordHasher<string> hasher = new(Options.Create(
        new PasswordHasherOptions { IterationCount = 210_000 }));

    /// <summary>Checks local credentials, counting failed attempts with optimistic concurrency.</summary>
    public async Task<ClaimsPrincipal> AuthenticateAsync(string username, string password, CancellationToken cancellation)
    {
        username = username.ToLowerInvariant();
        if (username.Length is < 1 or > 80 || password.Length > 256 ||
            username.Any(c => !char.IsAsciiLetterOrDigit(c) && c != '-'))
            throw new PolicyException("Invalid username or password.");
        var row = await table.GetEntityIfExistsAsync<TableEntity>(
            "accounts", username.ToLowerInvariant(), cancellationToken: cancellation);
        if (!row.HasValue || row.Value is not { } account)
        {
            logger.LogWarning("Sign-in rejected for an unknown account");
            throw new PolicyException("Invalid username or password.");
        }
        if (account.GetDateTimeOffset("LockedUntil") > DateTimeOffset.UtcNow)
            throw new PolicyException("Sign-in is temporarily locked. Try again after 15 minutes.");
        var verified = hasher.VerifyHashedPassword(username, account.GetString("PasswordHash")!, password);
        var failures = verified == PasswordVerificationResult.Failed
            ? account.GetInt32("Failures")!.Value + 1 : 0;
        account["Failures"] = failures;
        account["LockedUntil"] = failures >= 5
            ? DateTimeOffset.UtcNow.AddMinutes(15) : DateTimeOffset.UnixEpoch;
        try { await table.UpdateEntityAsync(account, account.ETag, TableUpdateMode.Replace, cancellation); }
        catch (RequestFailedException ex) when (ex.Status == 412)
        {
            logger.LogWarning("Concurrent sign-in update rejected");
            throw new PolicyException("Another sign-in changed this account. Retry.");
        }
        if (verified == PasswordVerificationResult.Failed)
        {
            logger.LogWarning("Local sign-in failed; durable lockout counter updated");
            throw new PolicyException("Invalid username or password.");
        }
        return new(new ClaimsIdentity(
        [
            new(ClaimTypes.NameIdentifier, username),
            new(ClaimTypes.Name, account.GetString("DisplayName")!),
            new(ClaimTypes.Role, account.GetString("Role")!),
            new("stamp", account.GetString("Stamp")!)
        ], CookieAuthenticationDefaults.AuthenticationScheme));
    }

    /// <summary>Rejects cookies whose durable account or security stamp no longer matches.</summary>
    public async Task ValidateAsync(CookieValidatePrincipalContext context)
    {
        var principal = context.Principal;
        var id = principal?.FindFirstValue(ClaimTypes.NameIdentifier);
        if (id is null || principal is null) { context.RejectPrincipal(); return; }
        var row = await table.GetEntityIfExistsAsync<TableEntity>("accounts", id);
        if (!row.HasValue || row.Value is not { } account ||
            principal.FindFirstValue("stamp") != account.GetString("Stamp") ||
            !principal.IsInRole(account.GetString("Role")!))
        {
            logger.LogWarning("An invalid durable session was rejected");
            context.RejectPrincipal();
        }
    }

    /// <summary>Creates destination-specific local accounts once and writes separate private access notes.</summary>
    public async Task InstallAsync(string privateDirectory, CancellationToken cancellation)
    {
        await table.CreateIfNotExistsAsync(cancellation);
        Directory.CreateDirectory(privateDirectory);
        if (OperatingSystem.IsWindows())
        {
            var permissions = new DirectorySecurity();
            permissions.SetAccessRuleProtection(true, false);
            permissions.AddAccessRule(new FileSystemAccessRule(
                WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("No Windows user SID."),
                FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit,
                PropagationFlags.None, AccessControlType.Allow));
            new DirectoryInfo(privateDirectory).SetAccessControl(permissions);
        }
        else
            File.SetUnixFileMode(privateDirectory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        foreach (var (id, name, role) in new[]
        {
            ("customer-001", "Airi Ilves", "Customer"),
            ("customer-002", "Hasan Ibrahimov", "Customer"),
            ("operator-001", "Nemanja Milatovic", "Operator")
        })
        {
            var file = Path.Combine(privateDirectory, id + "-access.json");
            var existing = await table.GetEntityIfExistsAsync<TableEntity>("accounts", id, cancellationToken: cancellation);
            if (existing.HasValue)
            {
                if (!File.Exists(file))
                    throw new InvalidOperationException("An installed account has no private access receipt; do not silently reset it.");
                var receipt = JsonSerializer.Deserialize<AccessReceipt>(await File.ReadAllTextAsync(file, cancellation))
                    ?? throw new InvalidOperationException("The private access receipt is invalid.");
                var account = existing.Value
                    ?? throw new InvalidOperationException("The existing account response has no durable record.");
                if (receipt.Username != id || receipt.Role != role || string.IsNullOrWhiteSpace(receipt.Password) ||
                    account.GetString("Role") != role || account.GetString("DisplayName") != name ||
                    hasher.VerifyHashedPassword(id, account.GetString("PasswordHash")!, receipt.Password)
                        == PasswordVerificationResult.Failed)
                    throw new InvalidOperationException("The private receipt does not match the durable account; reconcile explicitly.");
                continue;
            }
            if (File.Exists(file))
                throw new InvalidOperationException("An access receipt exists without its account. Operator reconciliation is required.");
            var password = Convert.ToBase64String(RandomNumberGenerator.GetBytes(30)) + "!aA1";
            var entry = new TableEntity("accounts", id)
            {
                ["DisplayName"] = name, ["Role"] = role, ["PasswordHash"] = hasher.HashPassword(id, password),
                ["Failures"] = 0, ["LockedUntil"] = DateTimeOffset.UnixEpoch, ["Stamp"] = Guid.NewGuid().ToString("N")
            };
            await using (var stream = new FileStream(file, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                await JsonSerializer.SerializeAsync(stream, new { Username = id, Password = password, Role = role }, cancellationToken: cancellation);
            if (!OperatingSystem.IsWindows())
                File.SetUnixFileMode(file, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            await table.AddEntityAsync(entry, cancellation);
            logger.LogInformation("Installed local {Role} account; credentials retained only in private access file", role);
        }
    }

    private sealed record AccessReceipt(string Username, string Password, string Role);
}
