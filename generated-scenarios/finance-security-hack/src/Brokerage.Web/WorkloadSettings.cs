namespace Brokerage.Web;

/// <summary>Required nonsecret deployment settings; absence is a startup error.</summary>
public sealed record WorkloadSettings(
    string ClientId, string TenantId, string GatewayPrincipalId, string BackendAudience,
    string ProjectEndpoint, string AgentName, string AgentVersion, string ModelDeployment,
    string FaqBlobUrl, string SigningKeyUrl)
{
    /// <summary>Loads configuration without falling back to public endpoints or developer credentials.</summary>
    public static WorkloadSettings Load(IConfiguration config)
    {
        string Required(string key) => !string.IsNullOrWhiteSpace(config[key])
            ? config[key]!
            : throw new InvalidOperationException($"Required configuration is missing: {key}");
        string Https(string key)
        {
            var value = Required(key);
            if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps)
                throw new InvalidOperationException($"{key} must be an absolute HTTPS URL.");
            return value;
        }
        return new(Required("AZURE_CLIENT_ID"), Required("AZURE_TENANT_ID"),
            Required("GATEWAY_PRINCIPAL_ID"), Required("BACKEND_AUDIENCE"),
            Https("FOUNDRY_PROJECT_ENDPOINT"), Required("FOUNDRY_AGENT_NAME"),
            Required("FOUNDRY_AGENT_VERSION"), Required("MODEL_DEPLOYMENT"),
            Https("FAQ_BLOB_URL"), Https("SIGNING_KEY_URL"));
    }
}
