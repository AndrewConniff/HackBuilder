using System.Security.Cryptography;
using System.Text;
using Azure;
using Azure.AI.Projects;
using Azure.AI.Projects.Agents;
using Azure.Identity;
using Azure.Security.KeyVault.Keys;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using MobilityCommercial.Web.Models;
using OpenAI.Responses;

if (args.Length != 2 || args[0] != "--execute-authorized-installation")
{
    Console.Error.WriteLine("Usage: --execute-authorized-installation <scenario-root>. Requires separately recorded exact-scope cloud/directory permissions and private network access. No cloud operations performed.");
    return 2;
}
var root = Path.GetFullPath(args[1]);
if (!File.Exists(Path.Combine(root, "scenario-manifest.json")))
    throw new InvalidOperationException("Scenario root with manifest required.");
string Env(string name) => Environment.GetEnvironmentVariable(name)
    ?? throw new InvalidOperationException($"Missing authorized installation setting: {name}");
var tenantId = Env("AZURE_TENANT_ID");
var subscriptionId = Env("AZURE_SUBSCRIPTION_ID");
if (!Guid.TryParse(tenantId, out _) || !Guid.TryParse(subscriptionId, out _))
    throw new InvalidOperationException("Explicit authorized tenant/subscription required.");
var credential = new AzureCliCredential(new AzureCliCredentialOptions { TenantId = tenantId });
var project = new AIProjectClient(new Uri(Env("FOUNDRY_PROJECT_ENDPOINT")), credential);
var model = Env("FOUNDRY_MODEL_DEPLOYMENT");
var blobService = new BlobServiceClient(new Uri(Env("FIXTURE_BLOB_ENDPOINT")), credential);
var container = blobService.GetBlobContainerClient("synthetic-fixtures");
// The container/versioning/roles are foundation resources: installation must not create or widen them.
T[] ReadSeed<T>(string name) => Json.ReadSeed<T[]>(File.ReadAllText(
    Path.Combine(root, "src", "MobilityCommercial.Web", "SeedData", name)));
MobilityCommercial.Web.Services.BlobFixtures.Validate(new(
    ReadSeed<Product>("products.json"), ReadSeed<Opportunity>("opportunities.json"),
    ReadSeed<ApprovedClaim>("claims.json"), string.Empty, []));
var agentInstalls = new List<AgentInstall>();
var installationDirectory = Path.Combine(root, ".installation");
Directory.CreateDirectory(installationDirectory);
foreach (var fileName in new[] { "sales-fit", "marketing-claims", "handoff-coordinator" })
{
    var bytes = await File.ReadAllBytesAsync(Path.Combine(root, "src", "agents", fileName + ".json"));
    var definition = Json.Read<Definition>(Encoding.UTF8.GetString(bytes));
    if (definition.Name != fileName) throw new InvalidOperationException("Agent definition name mismatch.");
    var hash = Convert.ToHexStringLower(SHA256.HashData(bytes.Concat(Encoding.UTF8.GetBytes(model)).ToArray()));
    DeclarativeAgentDefinition agentDefinition = new(model) { Instructions = definition.Instructions };
    foreach (var tool in definition.Tools)
    {
        if (tool is not ("get_opportunity" or "get_product" or "get_approved_claims"))
            throw new InvalidOperationException("Unknown installation function.");
        agentDefinition.Tools.Add(ResponseTool.CreateFunctionTool(tool,
            BinaryData.FromString("""{"type":"object","properties":{"id":{"type":"string"}},"required":["id"],"additionalProperties":false}"""),
            strictModeEnabled: true, functionDescription: tool switch {
                "get_opportunity" => "Read the supplied opportunity ID; returns a minimized synthetic needs projection.",
                "get_product" => "Read the supplied product ID and exact versioned product evidence.",
                _ => "Read approved versioned claims for the supplied product ID."
            }));
    }
    var options = new ProjectsAgentVersionCreationOptions(agentDefinition);
    options.Metadata["abc-scenario"] = "manu-multi-agent";
    options.Metadata["abc-definition-sha256"] = hash;
    ProjectsAgentVersion? installed = null;
    try
    {
        await foreach (var version in project.AgentAdministrationClient.GetAgentVersionsAsync(fileName))
        {
            if (!version.Metadata.TryGetValue("abc-scenario", out var scenario) || scenario != "manu-multi-agent")
                throw new InvalidOperationException("Unowned existing agent name; target review required.");
            if (version.Metadata.TryGetValue("abc-definition-sha256", out var existingHash) && existingHash == hash)
                installed ??= version;
        }
    }
    catch (System.ClientModel.ClientResultException exception) when (exception.Status == 404) { }
    installed ??= await project.AgentAdministrationClient.CreateAgentVersionAsync(fileName, options);
    agentInstalls.Add(new(installed.Name, installed.Version, installed.Id, model, hash));
}
var files = new List<FixtureFile>();
foreach (var name in new[] { "products.json", "opportunities.json", "claims.json" })
{
    var bytes = await File.ReadAllBytesAsync(Path.Combine(root, "src", "MobilityCommercial.Web", "SeedData", name));
    var hash = Convert.ToHexStringLower(SHA256.HashData(bytes));
    var blob = container.GetBlobClient(name);
    string? versionId = null;
    try
    {
        var content = await blob.DownloadContentAsync();
        if (Convert.ToHexStringLower(SHA256.HashData(content.Value.Content.ToArray())) == hash)
            versionId = content.Value.Details.VersionId
                ?? throw new InvalidOperationException("Existing fixture is not versioned.");
    }
    catch (RequestFailedException exception) when (exception.Status == 404) { }
    if (versionId is null)
    {
        var upload = await blob.UploadAsync(BinaryData.FromBytes(bytes), new BlobUploadOptions
        {
            HttpHeaders = new() { ContentType = "application/json" },
            Metadata = new Dictionary<string, string> { ["abc-scenario"] = "manu-multi-agent", ["sha256"] = hash }
        });
        versionId = upload.Value.VersionId
            ?? throw new InvalidOperationException("Blob upload did not return an immutable version.");
    }
    files.Add(new(name, versionId, hash));
}
var manifest = new FixtureManifest(1, "Adventure Works Cycles", files.ToArray(), agentInstalls.ToArray());
var manifestBytes = Encoding.UTF8.GetBytes(Json.Write(manifest));
var manifestHash = Convert.ToHexStringLower(SHA256.HashData(manifestBytes));
var manifestBlob = container.GetBlobClient($"manifests/{manifestHash}.json");
try { await manifestBlob.UploadAsync(BinaryData.FromBytes(manifestBytes), overwrite: false); }
catch (RequestFailedException exception) when (exception.Status == 409)
{
    var existing = await manifestBlob.DownloadContentAsync();
    if (!existing.Value.Content.ToArray().SequenceEqual(manifestBytes))
        throw new InvalidOperationException("Manifest content-address collision.");
}
var keyUri = new Uri(Env("SIGNING_KEY_URI"));
var keySegments = keyUri.AbsolutePath.Split('/', StringSplitOptions.RemoveEmptyEntries);
if (keySegments.Length is not (2 or 3) || keySegments[0] != "keys")
    throw new InvalidOperationException("Key URI must identify the authorized foundation signing key.");
var key = await new KeyClient(new Uri(keyUri.GetLeftPart(UriPartial.Authority)), credential)
    .GetKeyAsync(keySegments[1], keySegments.Length == 3 ? keySegments[2] : null);
var output = new
{
    schemaVersion = 1,
    scenario = "manu-multi-agent",
    installedAtUtc = DateTimeOffset.UtcNow,
    subscriptionId,
    tenantId,
    fixtureManifestSha256 = manifestHash,
    signingKeyUri = key.Value.Id.AbsoluteUri,
    signingKeyVersion = key.Value.Properties.Version,
    agents = agentInstalls
};
await File.WriteAllTextAsync(Path.Combine(installationDirectory, "installation.json"), Json.Write(output));
Console.WriteLine("Installation recorded privately in .installation\\installation.json. This is not live acceptance or deployment approval.");
return 0;

internal sealed record Definition(string Name, string Role, string Instructions, string[] Tools,
    string OutputContract, string Knowledge, string Safety);
