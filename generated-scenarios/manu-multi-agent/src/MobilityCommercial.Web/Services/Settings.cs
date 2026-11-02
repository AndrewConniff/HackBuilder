using System.Text.RegularExpressions;
using MobilityCommercial.Web.Models;

namespace MobilityCommercial.Web.Services;

internal sealed record AppSettings(Uri ProjectEndpoint, string Model, AgentPin Sales,
    AgentPin Marketing, AgentPin Coordinator, Uri BlobEndpoint, string Container,
    string ManifestHash, Uri KeyUri, string TenantId, string Audience, string GatewayObjectId,
    string ClientId)
{
    internal static AppSettings Load(IConfiguration config)
    {
        string Required(string key) => !string.IsNullOrWhiteSpace(config[key])
            ? config[key]! : throw new InvalidOperationException($"Required setting missing: {key}");
        string GuidValue(string key) => Guid.TryParse(Required(key), out var value) && value != Guid.Empty
            ? value.ToString() : throw new InvalidOperationException($"Invalid GUID setting: {key}");
        Uri Endpoint(string key) => Uri.TryCreate(Required(key), UriKind.Absolute, out var uri)
            && uri.Scheme == "https" && string.IsNullOrEmpty(uri.Query) && string.IsNullOrEmpty(uri.Fragment)
            && string.IsNullOrEmpty(uri.UserInfo)
                ? uri : throw new InvalidOperationException($"Invalid HTTPS endpoint: {key}");
        AgentPin Pin(string role, string expectedName)
        {
            var name = Required($"Foundry:{role}AgentName");
            var version = Required($"Foundry:{role}AgentVersion");
            if (name != expectedName || !Regex.IsMatch(version, @"^[1-9][0-9]*$"))
                throw new InvalidOperationException($"Invalid pinned {role} agent.");
            return new(name, version);
        }
        var project = Endpoint("Foundry:ProjectEndpoint");
        if (!project.Host.EndsWith(".services.ai.azure.com", StringComparison.Ordinal)
            || !Regex.IsMatch(project.AbsolutePath, @"^/api/projects/[a-zA-Z0-9_-]+$"))
            throw new InvalidOperationException("New Foundry project endpoint required.");
        var key = Endpoint("Signing:KeyUri");
        if (!key.Host.EndsWith(".vault.azure.net", StringComparison.Ordinal)
            || !Regex.IsMatch(key.AbsolutePath, @"^/keys/[a-zA-Z0-9-]+/[a-zA-Z0-9]+$"))
            throw new InvalidOperationException("A versioned Key Vault key URI is required.");
        var blob = Endpoint("Fixtures:BlobEndpoint");
        if (!blob.Host.EndsWith(".blob.core.windows.net", StringComparison.Ordinal)
            || blob.AbsolutePath != "/")
            throw new InvalidOperationException("Azure Blob service endpoint required.");
        var manifestHash = Required("Fixtures:ManifestSha256");
        if (!Regex.IsMatch(manifestHash, @"^[a-fA-F0-9]{64}$"))
            throw new InvalidOperationException("Fixture manifest SHA-256 required.");
        if (Required("Fixtures:ContainerName") != "synthetic-fixtures"
            || Required("Signing:Algorithm") != "PS256")
            throw new InvalidOperationException("Unsupported fixture container or signing algorithm.");
        foreach (var (name, limit) in new (string, int)[] {
            ("MaxInputCharacters", 4000), ("MaxOutputTokens", 800), ("MaxResponsesRequests", 7),
            ("MaxCumulativeTokens", 30000), ("DeadlineSeconds", 90), ("MaxConcurrentHandoffs", 4) })
            if (Required($"Limits:{name}") != limit.ToString(System.Globalization.CultureInfo.InvariantCulture))
                throw new InvalidOperationException($"Confirmed runtime limit required: {name}");
        var tenant = GuidValue("BackendAuth:TenantId");
        if (Required("BackendAuth:Authority") != $"https://login.microsoftonline.com/{tenant}/v2.0")
            throw new InvalidOperationException("Single-tenant v2 authority required.");
        return new(project, Required("Foundry:ModelDeployment"), Pin("Sales", "sales-fit"),
            Pin("Marketing", "marketing-claims"), Pin("Coordinator", "handoff-coordinator"),
            blob, "synthetic-fixtures", manifestHash.ToLowerInvariant(), key, tenant,
            GuidValue("BackendAuth:Audience"), GuidValue("BackendAuth:GatewayObjectId"),
            GuidValue("AZURE_CLIENT_ID"));
    }
}
