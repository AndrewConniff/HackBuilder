using System.Security.Cryptography;
using System.Text.Json;
using Azure.Identity;
using Microsoft.AspNetCore.Identity;

namespace FeedbackCampaign.Web;

/// <summary>Produces private, deployment-specific access files and installs password hashes only.</summary>
public static class LabAccountProvisioner
{
    private sealed record AccessAccount(string Username, string Password, string[] Roles);
    private sealed record AccessFile(string ApplicationUrl, string Notice, AccessAccount[] Accounts);

    /// <summary>Installs lab identities under existing scoped storage rights; never prints passwords.</summary>
    public static async Task Run(string[] args)
    {
        if (args.Length != 4) throw new ArgumentException("Expected provision command, private directory, Table endpoint and application URL.");
        var directory = Path.GetFullPath(args[1]);
        if (Path.GetFileName(directory) != ".private")
            throw new ArgumentException("Access files must be written to the scenario .private directory, never published source.");
        var config = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["TABLE_ENDPOINT"] = args[2] }).Build();
        var store = new TableStateStore(config, new AzureCliCredential());
        Directory.CreateDirectory(directory);
        foreach (var (file, definitions) in new[]
        {
            ("participant-access.json", new[]
            {
                ("campaign-operator", new[] { "CampaignOperator" }),
                ("product-manager", new[] { "ProductManager" }),
                ("conflict-specialist", new[] { "ConflictResolutionSpecialist" })
            }),
            ("coach-access.json", new[]
            {
                ("coach", new[] { "CampaignOperator", "ProductManager", "ConflictResolutionSpecialist", "ControlAdmin" })
            })
        })
        {
            var path = Path.Combine(directory, file);
            AccessFile access;
            if (File.Exists(path))
            {
                access = JsonSerializer.Deserialize<AccessFile>(await File.ReadAllTextAsync(path), TableStateStore.Json)
                    ?? throw new InvalidOperationException("Private access file is invalid; restore its protected copy.");
            }
            else
            {
                foreach (var (username, _) in definitions)
                    if (await store.Get<LabAccount>("accounts", username) is not null)
                        throw new InvalidOperationException("An installed account has no local access file. Restore the private file; passwords cannot be recovered from hashes.");
                access = new(args[3], "PRIVATE live lab credentials. Do not commit, publish, put in a learner starter, or share coach access with participants. Synthetic reference only.",
                    definitions.Select(d => new AccessAccount(d.Item1,
                        Convert.ToBase64String(RandomNumberGenerator.GetBytes(24)), d.Item2)).ToArray());
                var options = new FileStreamOptions { Mode = FileMode.CreateNew, Access = FileAccess.Write, Share = FileShare.None };
                if (!OperatingSystem.IsWindows()) options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
                await using var stream = new FileStream(path, options);
                await JsonSerializer.SerializeAsync(stream, access, new JsonSerializerOptions(TableStateStore.Json) { WriteIndented = true });
            }
            if (access.ApplicationUrl != args[3] || access.Accounts.Length != definitions.Length)
                throw new InvalidOperationException("Private access file does not match this deployment.");
            foreach (var (username, roles) in definitions)
            {
                var credential = access.Accounts.Single(a => a.Username == username);
                if (!credential.Roles.SequenceEqual(roles) || credential.Password.Length < 24)
                    throw new InvalidOperationException("Private access account definition does not match its reviewed role.");
                var account = new LabAccount(username, string.Empty, roles, Guid.NewGuid().ToString("N"));
                var hasher = new PasswordHasher<LabAccount>();
                var existing = await store.Get<LabAccount>("accounts", username);
                if (existing is not null)
                {
                    if (!existing.Value.Roles.SequenceEqual(roles)
                        || hasher.VerifyHashedPassword(existing.Value, existing.Value.PasswordHash, credential.Password) == PasswordVerificationResult.Failed)
                        throw new InvalidOperationException("Installed account differs from its private receipt; refusing to overwrite credentials or roles.");
                    continue;
                }
                if (!await store.Add("accounts", username, account with { PasswordHash = hasher.HashPassword(account, credential.Password) }))
                    throw new InvalidOperationException("Concurrent account installation detected; verify before retrying.");
            }
        }
        Console.WriteLine("Four role-scoped lab accounts installed; private participant and coach access files saved. No plaintext password uploaded.");
    }
}
