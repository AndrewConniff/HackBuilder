using System.Text.Json;
using Azure.Data.Tables;
using Azure.Storage.Blobs;
using Woodgrove.Web.Models;

namespace Woodgrove.Web.Services;

/// <summary>Explicit private-host installation, separate from ordinary web startup.</summary>
public sealed class ReferenceInstaller(
    TableServiceClient tables, BlobServiceClient blobs, LocalAccounts accounts, FoundryRuntime agents,
    IWebHostEnvironment environment, IConfiguration configuration)
{
    /// <summary>Installs exact fixtures, private accounts and versioned real agents idempotently.</summary>
    public async Task InstallAsync(string privateDirectory, CancellationToken cancellation)
    {
        var table = tables.GetTableClient("Commerce");
        await table.CreateIfNotExistsAsync(cancellation);
        await blobs.GetBlobContainerClient("session-keys").CreateIfNotExistsAsync(cancellationToken: cancellation);
        var file = Path.Combine(environment.ContentRootPath, "SeedData", "products.json");
        var products = JsonSerializer.Deserialize<Product[]>(await File.ReadAllTextAsync(file, cancellation))
            ?? throw new InvalidOperationException("Catalog fixtures are invalid.");
        if (products.Length is < 10 or > 20 || products.Select(x => x.Id).Distinct().Count() != products.Length)
            throw new InvalidOperationException("Install 10-20 distinct catalog fixtures.");
        foreach (var product in products)
        {
            var key = "product-" + product.Id.ToString("D3");
            var existing = await table.GetEntityIfExistsAsync<TableEntity>("store-001", key, cancellationToken: cancellation);
            if (!existing.HasValue)
                await table.AddEntityAsync(TableStorageDataService.Entity(key, product), cancellation);
        }
        await accounts.InstallAsync(privateDirectory, cancellation);
        await agents.InstallAsync(configuration["FoundryModelDeployment"]
            ?? throw new InvalidOperationException("FoundryModelDeployment is required."), cancellation);
    }
}
