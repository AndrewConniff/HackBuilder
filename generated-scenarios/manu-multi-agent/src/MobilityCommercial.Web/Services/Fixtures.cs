using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Azure.Storage.Blobs;
using MobilityCommercial.Web.Models;

namespace MobilityCommercial.Web.Services;

internal interface IFixtures
{
    Task<FixtureSnapshot> GetAsync(CancellationToken cancellationToken);
}

internal sealed class BlobFixtures(BlobServiceClient service, AppSettings settings) : IFixtures
{
    private readonly SemaphoreSlim gate = new(1, 1);
    private FixtureSnapshot? cached;

    public async Task<FixtureSnapshot> GetAsync(CancellationToken cancellationToken)
    {
        await gate.WaitAsync(cancellationToken);
        try
        {
            if (cached is not null) return cached;
            var container = service.GetBlobContainerClient(settings.Container);
            async Task<byte[]> Download(string name, string? version = null)
            {
                var blob = container.GetBlobClient(name);
                if (version is not null) blob = blob.WithVersion(version);
                var properties = await blob.GetPropertiesAsync(cancellationToken: cancellationToken);
                if (properties.Value.ContentLength > 128 * 1024)
                    throw new WorkflowException(503, "fixture_too_large");
                var response = await blob.DownloadContentAsync(cancellationToken);
                return response.Value.Content.ToArray();
            }
            var manifestBytes = await Download($"manifests/{settings.ManifestHash}.json");
            RequireHash(manifestBytes, settings.ManifestHash);
            var manifest = Json.Read<FixtureManifest>(Encoding.UTF8.GetString(manifestBytes));
            if (manifest.SchemaVersion != 1 || manifest.CompanyName != "Adventure Works Cycles"
                || manifest.Files is null || manifest.Agents is null
                || manifest.Files.Length != 3 || manifest.Agents.Length != 3
                || manifest.Files.Any(f => f is null) || manifest.Agents.Any(a => a is null)
                || manifest.Agents.Select(a => a.Name).Distinct().Count() != 3)
                throw new WorkflowException(503, "invalid_fixture_manifest");
            foreach (var pin in new[] { settings.Sales, settings.Marketing, settings.Coordinator })
            {
                var agent = manifest.Agents.SingleOrDefault(a => a.Name == pin.Name && a.Version == pin.Version);
                if (agent is null || string.IsNullOrWhiteSpace(agent.Id) || agent.Model != settings.Model)
                    throw new WorkflowException(503, "agent_installation_mismatch");
            }
            async Task<T[]> Read<T>(string name)
            {
                var file = manifest.Files.SingleOrDefault(f => f.Name == name);
                if (file is null || string.IsNullOrWhiteSpace(file.VersionId))
                    throw new WorkflowException(503, "missing_fixture_version");
                var data = await Download(name, file.VersionId);
                RequireHash(data, file.Sha256);
                return Json.ReadSeed<T[]>(Encoding.UTF8.GetString(data));
            }
            var snapshot = new FixtureSnapshot(await Read<Product>("products.json"),
                await Read<Opportunity>("opportunities.json"), await Read<ApprovedClaim>("claims.json"),
                settings.ManifestHash, manifest.Agents);
            Validate(snapshot);
            return cached = snapshot;
        }
        catch (JsonException) { throw new WorkflowException(503, "invalid_fixture_json"); }
        finally { gate.Release(); }
    }

    internal static void RequireHash(byte[] bytes, string expected)
    {
        if (!string.Equals(Convert.ToHexStringLower(SHA256.HashData(bytes)), expected, StringComparison.Ordinal))
            throw new WorkflowException(503, "fixture_integrity_failed");
    }

    internal static void Validate(FixtureSnapshot data)
    {
        if (data.Products is null || data.Opportunities is null || data.Claims is null
            || data.Products.Length != 3 || data.Opportunities.Length != 4 || data.Claims.Length != 3
            || data.Products.Any(p => p is null) || data.Opportunities.Any(o => o is null) || data.Claims.Any(c => c is null)
            || data.Products.Select(p => p.SourceId).Distinct().Count() != 3
            || data.Opportunities.Select(p => p.SourceId).Distinct().Count() != 4
            || data.Claims.Select(p => p.SourceId).Distinct().Count() != 3
            || data.Claims.Any(c => !data.Products.Any(p => p.SourceId == c.ProductId)
                || string.IsNullOrWhiteSpace(c.Version) || string.IsNullOrWhiteSpace(c.PermittedWording))
            || data.Opportunities.Any(o => o.SalesOwner != "Airi Ilves" || o.MarketingOwner != "Hasan Ibrahimov"))
            throw new WorkflowException(503, "invalid_fixture_schema");
    }
}
