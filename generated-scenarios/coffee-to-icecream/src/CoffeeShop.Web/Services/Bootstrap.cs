using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Azure;
using Azure.AI.Projects;
using Azure.AI.Projects.Agents;
using Azure.Data.Tables;
using Azure.Identity;
using System.ClientModel;
using CoffeeShop.Web.Models;

namespace CoffeeShop.Web.Services;

/// <summary>Installs target-owned accounts, fixtures and version-selected agents during authorized setup only.</summary>
public static class Bootstrap
{
    /// <summary>Consumes private destination credentials and never adopts another scenario's agent ownership.</summary>
    public static async Task RunAsync(IConfiguration config, string root)
    {
        // Called only by explicitly authorized postprovision automation; never during an HTTP request.
        var credential = new AzureCliCredential();
        var table = new TableClient(new Uri(config["Storage:Endpoint"]
            ?? throw new InvalidOperationException("Storage endpoint is required.")), "IceCreamBackOffice", credential);
        await table.CreateIfNotExistsAsync();
        var accessFile = Environment.GetEnvironmentVariable("ICECREAM_ACCESS_FILE")
            ?? throw new InvalidOperationException("Private destination access file is required.");
        if (Path.GetFullPath(accessFile).StartsWith(Path.GetFullPath(root), StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Credential file must be outside application content.");
        var installedAccess = JsonSerializer.Deserialize<InstallationAccount[]>(await File.ReadAllTextAsync(accessFile))
            ?? throw new InvalidOperationException("Invalid private account installation file.");
        if (installedAccess.Length != 12 || installedAccess.Select(row => row.Username).Distinct().Count() != 12)
            throw new InvalidOperationException("Twelve unique destination accounts are required.");
        var storeIds = Enumerable.Range(1, 10).Select(index => $"{index:000}").ToArray();
        foreach (var entry in installedAccess)
        {
            var expected = entry.Role == "StoreManager"
                ? storeIds.Where(id => entry.Username == $"store{id}").ToArray()
                : entry.Username == "areanorth" ? storeIds[..5]
                : entry.Username == "areasouth" ? storeIds[5..] : [];
            if (entry.Password.Length < 24 || expected.Length == 0 || !entry.Stores.SequenceEqual(expected)
                || entry.Role is not ("StoreManager" or "AreaManager"))
                throw new InvalidOperationException("Invalid destination credential or account scope.");
            var account = LocalAccounts.Create(entry.Username, entry.Password, entry.Role, entry.Stores);
            var existing = await table.GetEntityIfExistsAsync<TableEntity>("accounts", account.Username);
            if (existing.HasValue)
            {
                var installed = JsonSerializer.Deserialize<LocalAccount>(existing.Value!.GetString("Payload"))
                    ?? throw new InvalidOperationException("Invalid installed account.");
                if (installed.Role != account.Role || !installed.Stores.SequenceEqual(account.Stores)
                    || !LocalAccounts.PasswordMatches(installed, entry.Password))
                    throw new InvalidOperationException("Existing account differs from approved installation.");
            }
            else await table.AddEntityAsync(TableAccountRepository.Entity(account));
        }
        var json = await File.ReadAllTextAsync(Path.Combine(root, "SeedData", "stores.json"));
        var snapshots = JsonSerializer.Deserialize<Models.StoreSnapshot[]>(json)!;
        foreach (var snapshot in snapshots)
        {
            var verified = DailyOperations.Calculate(snapshot.Store, snapshot.Version,
                snapshot.Input ?? throw new InvalidOperationException("Missing recipe fixture."));
            if (verified.Ledger != snapshot.Ledger || !verified.Stock.SequenceEqual(snapshot.Stock))
                throw new InvalidOperationException("Fixture totals differ from deterministic calculation.");
            try
            {
                await table.AddEntityAsync(new TableEntity(snapshot.Store.StoreId, "snapshot")
                {
                    ["Payload"] = JsonSerializer.Serialize(snapshot)
                });
            }
            catch (RequestFailedException error) when (error.Status == 409) { /* Never overwrite live stock. */ }
        }
        var project = new AIProjectClient(new Uri(config["Foundry:Endpoint"]!), credential);
        var outputs = new Dictionary<string, string>();
        foreach (var role in new[] { "stock", "margin", "close" })
        {
            var instructions = await File.ReadAllTextAsync(Path.Combine(root, "Agents", $"{role}.md"));
            var model = config["Foundry:Model"]!;
            var digest = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(model + instructions)));
            var name = $"coffee-to-icecream-{role}";
            ProjectsAgentVersion? match = null;
            try
            {
                await foreach (var existing in project.AgentAdministrationClient.GetAgentVersionsAsync(name))
                {
                    if (!existing.Metadata.TryGetValue("owner", out var owner) || owner != "coffee-to-icecream")
                        throw new InvalidOperationException("Refusing to adopt an unowned agent.");
                    if (existing.Metadata.TryGetValue("digest", out var hash) && hash == digest) match = existing;
                }
            }
            catch (ClientResultException error) when (error.Status == 404) { /* First installation. */ }
            if (match is null)
            {
                var options = new ProjectsAgentVersionCreationOptions(
                    new DeclarativeAgentDefinition(model) { Instructions = instructions });
                options.Metadata["owner"] = "coffee-to-icecream";
                options.Metadata["digest"] = digest;
                match = (await project.AgentAdministrationClient.CreateAgentVersionAsync(name, options)).Value;
            }
            await project.AgentAdministrationClient.PatchAgentAsync(name, new PatchAgentOptions
            {
                AgentEndpoint = new AgentEndpointConfiguration
                {
                    VersionSelector = new([new FixedRatioVersionSelectionRule(match.Version, 100)]),
                    ProtocolConfiguration = new() { Responses = new() }
                }
            });
            outputs[$"Foundry__{role}__Name"] = match.Name;
            outputs[$"Foundry__{role}__Version"] = match.Version;
            outputs[$"Foundry__{role}__Id"] = match.Id;
        }
        var outputFile = Environment.GetEnvironmentVariable("ICECREAM_AGENT_OUTPUT")
            ?? throw new InvalidOperationException("Private installation output path is required.");
        await File.WriteAllTextAsync(outputFile,
            JsonSerializer.Serialize(outputs, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("Initialized table fixtures without overwriting existing stock; captured real agent IDs/versions.");
    }

    private sealed record InstallationAccount(string Username, string Password, string Role, string[] Stores);
}
