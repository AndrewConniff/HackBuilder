using Azure.Core;
using Azure.Identity;

namespace Restaurant.Web.Services;

/// <summary>Defers identity configuration until an actual Azure operation, keeping unconfigured public shells accessible.</summary>
public sealed class RuntimeIdentityCredential(IConfiguration configuration) : TokenCredential
{
    private readonly Lazy<ManagedIdentityCredential> credential = new(() =>
        new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(
            configuration["AZURE_CLIENT_ID"]
                ?? throw new InvalidOperationException("AZURE_CLIENT_ID is required for runtime managed identity."))));

    /// <summary>Obtains a token only through the configured user-assigned runtime identity.</summary>
    public override AccessToken GetToken(TokenRequestContext requestContext, CancellationToken cancellationToken) =>
        credential.Value.GetToken(requestContext, cancellationToken);

    /// <summary>Obtains a token asynchronously without falling back to developer or shared CLI accounts.</summary>
    public override ValueTask<AccessToken> GetTokenAsync(TokenRequestContext requestContext, CancellationToken cancellationToken) =>
        credential.Value.GetTokenAsync(requestContext, cancellationToken);
}
