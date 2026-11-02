using System.Text;
using System.Text.Json;
using Azure;
using Azure.Data.Tables;
using BankSupport.Web.Models;

namespace BankSupport.Web.Services;

/// <summary>Durable documents with conditional replacement and explicit missing-record semantics.</summary>
public interface IDocumentStore
{
    /// <summary>Reads one document without substituting a default for a missing record.</summary>
    Task<Stored<T>?> GetAsync<T>(string partition, string id, CancellationToken ct = default);
    /// <summary>Lists all documents within the requested partition.</summary>
    Task<IReadOnlyList<T>> ListAsync<T>(string partition, CancellationToken ct = default);
    /// <summary>Creates a document only when it does not exist.</summary>
    Task AddAsync<T>(string partition, string id, T value, CancellationToken ct = default);
    /// <summary>Replaces a document only if its concurrency token still matches.</summary>
    Task ReplaceAsync<T>(string partition, string id, T value, string etag, CancellationToken ct = default);
}

/// <summary>Azure Table implementation using Entra credentials, never service keys.</summary>
public sealed class DocumentStore(TableClient table) : IDocumentStore
{
    /// <inheritdoc />
    public async Task<Stored<T>?> GetAsync<T>(string partition, string id, CancellationToken ct = default)
    {
        var result = await table.GetEntityIfExistsAsync<TableEntity>(partition, id, cancellationToken: ct);
        if (!result.HasValue) return null;
        var row = result.Value ?? throw new InvalidDataException("Azure Table returned an empty entity.");
        return new Stored<T>(Deserialize<T>(row.GetString("Payload")), row.ETag.ToString());
    }

    /// <inheritdoc />
    public async Task<IReadOnlyList<T>> ListAsync<T>(string partition, CancellationToken ct = default)
    {
        var result = new List<T>();
        await foreach (var row in table.QueryAsync<TableEntity>(
            TableClient.CreateQueryFilter($"PartitionKey eq {partition}"), cancellationToken: ct))
            result.Add(Deserialize<T>(row.GetString("Payload")));
        return result;
    }

    /// <inheritdoc />
    public async Task AddAsync<T>(string partition, string id, T value, CancellationToken ct = default)
    {
        try { await table.AddEntityAsync(Entity(partition, id, value), ct); }
        catch (RequestFailedException ex) when (ex.Status == 409)
        { throw new BusinessException(409, "This operation already exists. Refresh before continuing."); }
    }

    /// <inheritdoc />
    public async Task ReplaceAsync<T>(string partition, string id, T value, string etag, CancellationToken ct = default)
    {
        try { await table.UpdateEntityAsync(Entity(partition, id, value), new ETag(etag), TableUpdateMode.Replace, ct); }
        catch (RequestFailedException ex) when (ex.Status == 412)
        { throw new BusinessException(409, "The record changed. Refresh before trying again."); }
    }

    private static T Deserialize<T>(string json) =>
        JsonSerializer.Deserialize<T>(json) ?? throw new InvalidDataException("Stored document is invalid.");

    private static TableEntity Entity<T>(string partition, string id, T value)
    {
        var json = JsonSerializer.Serialize(value);
        if (Encoding.UTF8.GetByteCount(json) > 28000)
            throw new BusinessException(400, "Conversation storage limit reached. Start a new conversation.");
        return new TableEntity(partition, id) { ["Payload"] = json };
    }
}
