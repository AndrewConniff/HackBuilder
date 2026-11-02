using System.Xml.Linq;
using Microsoft.AspNetCore.DataProtection.Repositories;

namespace Restaurant.Web.Services;

/// <summary>Shares antiforgery protection keys across web replicas using Cosmos encryption at rest and existing data RBAC.</summary>
public sealed class CosmosKeyRepository(CosmosStore store) : IXmlRepository
{
    /// <summary>Loads only this application's retained key ring, never profile or shared filesystem paths.</summary>
    public IReadOnlyCollection<XElement> GetAllElements()
    {
        // Data Protection's repository contract is synchronous; key-ring reads are cached by the framework.
        var keys = store.Query<KeyDocument>(store.Catalog,
            new("SELECT TOP 250 * FROM c WHERE c.aggregateKey = 'data-protection' AND c.Type = 'protection-key'"),
            250, CancellationToken.None).GetAwaiter().GetResult();
        if (keys.Length == 250) throw new InvalidDataException("Protection key ring exceeded its reviewed bound.");
        return keys.Select(key => XElement.Parse(key.Xml)).ToArray();
    }

    /// <summary>Creates an immutable key document in the shared encrypted account.</summary>
    public void StoreElement(XElement element, string friendlyName) =>
        store.Catalog.CreateItemAsync(new KeyDocument(
            friendlyName, "data-protection", "protection-key", element.ToString(SaveOptions.DisableFormatting)),
            new("data-protection")).GetAwaiter().GetResult();

    private sealed record KeyDocument(string id, string aggregateKey, string Type, string Xml);
}
