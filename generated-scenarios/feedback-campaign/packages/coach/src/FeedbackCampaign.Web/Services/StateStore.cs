using System.Text.Json;
using Azure;
using Azure.Core;
using Azure.Data.Tables;

namespace FeedbackCampaign.Web;

public interface IStateStore
{
    Task<Versioned<T>?> Get<T>(string partition, string key);
    Task<bool> Add<T>(string partition, string key, T value);
    Task Replace<T>(string partition, string key, T value, string etag);
    Task<IReadOnlyList<Versioned<T>>> List<T>(string partition);
}

public sealed class TableStateStore(IConfiguration config, TokenCredential credential) : IStateStore
{
    private TableClient? client;
    private TableClient Client => client ??= new TableClient(
        new Uri(config["TABLE_ENDPOINT"] ?? throw new InvalidOperationException("TABLE_ENDPOINT not configured.")),
        "campaignstate", credential);
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public async Task<Versioned<T>?> Get<T>(string partition, string key)
    {
        var response = await Client.GetEntityIfExistsAsync<TableEntity>(partition, key);
        return response.HasValue ? Decode<T>(response.Value!) : null;
    }

    public async Task<bool> Add<T>(string partition, string key, T value)
    {
        try { await Client.AddEntityAsync(Encode(partition, key, value)); return true; }
        catch (RequestFailedException ex) when (ex.Status == 409) { return false; }
    }

    public async Task Replace<T>(string partition, string key, T value, string etag) =>
        await Client.UpdateEntityAsync(Encode(partition, key, value), new ETag(etag), TableUpdateMode.Replace);

    public async Task<IReadOnlyList<Versioned<T>>> List<T>(string partition)
    {
        var values = new List<Versioned<T>>();
        await foreach (var row in Client.QueryAsync<TableEntity>(TableClient.CreateQueryFilter($"PartitionKey eq {partition}"), 200))
        {
            values.Add(Decode<T>(row));
        }
        return values;
    }

    private static TableEntity Encode<T>(string partition, string key, T value)
    {
        var payload = JsonSerializer.Serialize(value, Json);
        // Table string property limit is 64 KiB UTF-16.
        if (payload.Length > 30000) throw new ArgumentException("Case payload exceeds the durable record limit.");
        return new TableEntity(partition, key) { ["Payload"] = payload };
    }
    private static Versioned<T> Decode<T>(TableEntity row) =>
        new(JsonSerializer.Deserialize<T>(row.GetString("Payload"), Json)!, row.ETag.ToString());
}

public sealed class RuleService(IStateStore store)
{
    public async Task<Rules> Current()
    {
        var pointer = await store.Get<ActiveRules>("config", "active")
            ?? throw new InvalidOperationException("Control rules not initialized.");
        return (await store.Get<Rules>("rules", pointer.Value.Version)
            ?? throw new InvalidOperationException("Active Control version not found.")).Value;
    }

    public async Task Save(Rules rules)
    {
        rules.Validate();
        if (!await store.Add("rules", rules.Version, rules))
            throw new InvalidOperationException("Immutable version already exists; choose a new version.");
    }

    public async Task Promote(string version, string actor, string reason, string etag)
    {
        if (string.IsNullOrWhiteSpace(reason) || reason.Length > 500)
            throw new ArgumentException("A bounded promotion reason is required.");
        _ = await store.Get<Rules>("rules", version) ?? throw new ArgumentException("Unknown rule version.");
        var current = await store.Get<ActiveRules>("config", "active")
            ?? throw new InvalidOperationException("Active rules are not initialized.");
        await store.Replace("config", "active", new ActiveRules(version, actor, reason,
            [.. current.Value.History ?? [], new(DateTimeOffset.UtcNow, actor, $"Promoted:{version}:{reason}")]), etag);
    }
}
