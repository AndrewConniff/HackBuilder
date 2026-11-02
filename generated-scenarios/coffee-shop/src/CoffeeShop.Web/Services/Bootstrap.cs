using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Azure;
using Azure.AI.Projects;
using Azure.AI.Projects.Agents;
using Azure.Data.Tables;
using Azure.Identity;
using System.ClientModel;

namespace CoffeeShop.Web.Services;

public static class Bootstrap
{
    public static async Task RunAsync(IConfiguration config, string root)
    {
        // Called only by explicitly authorized postprovision automation; never during an HTTP request.
        var credential = new AzureCliCredential();
        var table = new TableClient(new Uri(config["Storage:Endpoint"]!), "CoffeeBackOffice", credential);
        await table.CreateIfNotExistsAsync();
        var storePassword = Environment.GetEnvironmentVariable("COFFEE_STORE_PASSWORD")
            ?? throw new InvalidOperationException("Store account installation password is required.");
        var areaPassword = Environment.GetEnvironmentVariable("COFFEE_AREA_PASSWORD")
            ?? throw new InvalidOperationException("Area account installation password is required.");
        foreach (var account in new[]
        {
            LocalAccounts.Create("storeman001", storePassword, "StoreManager", ["001"]),
            LocalAccounts.Create("storeman002", storePassword, "StoreManager", ["002"]),
            LocalAccounts.Create("petender", areaPassword, "AreaManager", ["001", "002"])
        })
        {
            var existing = await table.GetEntityIfExistsAsync<TableEntity>("accounts", account.Username);
            if (existing.HasValue)
            {
                var installed = JsonSerializer.Deserialize<LocalAccount>(existing.Value!.GetString("Payload"))
                    ?? throw new InvalidOperationException("Invalid installed account.");
                var password = account.Role == "AreaManager" ? areaPassword : storePassword;
                if (installed.Role != account.Role || !installed.Stores.SequenceEqual(account.Stores)
                    || !LocalAccounts.PasswordMatches(installed, password))
                    throw new InvalidOperationException("Existing account differs from approved installation.");
            }
            else await table.AddEntityAsync(TableAccountRepository.Entity(account));
        }
        var json = await File.ReadAllTextAsync(Path.Combine(root, "SeedData", "stores.json"));
        var snapshots = JsonSerializer.Deserialize<Models.StoreSnapshot[]>(json)!;
        foreach (var snapshot in snapshots)
        {
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
            var name = $"coffee-shop-{role}";
            ProjectsAgentVersion? match = null;
            try
            {
                await foreach (var existing in project.AgentAdministrationClient.GetAgentVersionsAsync(name))
                {
                    if (!existing.Metadata.TryGetValue("owner", out var owner) || owner != "coffee-shop")
                        throw new InvalidOperationException("Refusing to adopt an unowned agent.");
                    if (existing.Metadata.TryGetValue("digest", out var hash) && hash == digest) match = existing;
                }
            }
            catch (ClientResultException error) when (error.Status == 404) { /* First installation. */ }
            if (match is null)
            {
                var options = new ProjectsAgentVersionCreationOptions(
                    new DeclarativeAgentDefinition(model) { Instructions = instructions });
                options.Metadata["owner"] = "coffee-shop";
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
        await File.WriteAllTextAsync(Path.Combine(root, "agent-installation.json"),
            JsonSerializer.Serialize(outputs, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("Initialized table fixtures without overwriting existing stock; captured real agent IDs/versions.");
    }
}
