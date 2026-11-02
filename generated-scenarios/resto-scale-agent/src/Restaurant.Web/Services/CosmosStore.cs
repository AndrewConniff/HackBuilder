using System.Net;
using System.Text.Json;
using Microsoft.Azure.Cosmos;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>Cosmos persistence with conditional same-partition batches and no in-memory runtime fallback.</summary>
public sealed class CosmosStore(CosmosClient client, IConfiguration configuration, ILogger<CosmosStore> logger)
{
    /// <summary>Gets the transactional container.</summary>
    public Container Transactions { get; } = client.GetContainer(
        configuration["COSMOS_DATABASE"] ?? "restaurant", "transactions");

    /// <summary>Gets the catalog and private shared protection-key container.</summary>
    public Container Catalog { get; } = client.GetContainer(
        configuration["COSMOS_DATABASE"] ?? "restaurant", "catalog");

    /// <summary>Gets the rebuildable operational reporting container.</summary>
    public Container Reporting { get; } = client.GetContainer(
        configuration["COSMOS_DATABASE"] ?? "restaurant", "reporting");

    /// <summary>Reads an optional item and its concurrency token.</summary>
    public static async Task<(T Item, string ETag)?> Read<T>(Container container, string id, string partition,
        CancellationToken cancellationToken)
    {
        try
        {
            var response = await container.ReadItemAsync<T>(id, new(partition), cancellationToken: cancellationToken);
            return (response.Resource, response.ETag);
        }
        catch (CosmosException exception) when (exception.StatusCode == HttpStatusCode.NotFound)
        {
            return null;
        }
    }

    /// <summary>Executes a bounded indexed query with parameterized predicates.</summary>
    public async Task<T[]> Query<T>(Container container, QueryDefinition query, int limit, CancellationToken token)
    {
        using var iterator = container.GetItemQueryIterator<T>(query, requestOptions: new() { MaxItemCount = limit });
        var result = new List<T>();
        while (iterator.HasMoreResults && result.Count < limit)
        {
            var page = await iterator.ReadNextAsync(token);
            logger.LogInformation("Cosmos query consumed {RequestCharge} RU", page.RequestCharge);
            result.AddRange(page.Take(limit - result.Count));
        }
        return result.ToArray();
    }

    /// <summary>Returns the versioned server-side menu.</summary>
    public async Task<MenuItem[]> Menu(CancellationToken token)
    {
        var result = await Read<JsonElement>(Catalog, "menu", "menu", token)
            ?? throw new DomainException(503, "Menu has not been initialized.");
        return result.Item.GetProperty("Items").Deserialize<MenuItem[]>()
            ?? throw new InvalidDataException("Invalid persisted menu.");
    }

    /// <summary>Returns one required visit and its ETag.</summary>
    public async Task<(Visit Item, string ETag)> Visit(string id, CancellationToken token) =>
        await Read<Visit>(Transactions, id, $"visit:{id}", token)
            ?? throw new DomainException(404, "Visit not found or still preparing.");

    /// <summary>Commits a batch and maps explicit contention or transient failure.</summary>
    public async Task Commit(TransactionalBatch batch, CancellationToken token)
    {
        using var response = await batch.ExecuteAsync(token);
        logger.LogInformation("Cosmos batch status {Status}; {RequestCharge} RU", response.StatusCode, response.RequestCharge);
        if (!response.IsSuccessStatusCode)
        {
            if (response.StatusCode is HttpStatusCode.Conflict or HttpStatusCode.PreconditionFailed)
                throw new DomainException(409, "Concurrent change or duplicate key; refresh and retry with the same key.");
            throw new CosmosException("Transaction batch failed.", response.StatusCode, 0,
                response.ActivityId, response.RequestCharge);
        }
    }
}
