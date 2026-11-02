using Azure;
using Azure.Core;
using Azure.Data.Tables;
using System.Text.RegularExpressions;

namespace Woodgrove.Tests;

internal sealed class MemoryTableService(MemoryTable table) : TableServiceClient
{
    public override TableClient GetTableClient(string tableName) => table;
}

internal sealed class MemoryTable : TableClient
{
    internal readonly Dictionary<string, TableEntity> Rows = [];
    internal readonly List<int> BatchSizes = [];
    private readonly object gate = new();
    private long revision;
    internal bool FailAfterCommit;

    internal void Put(TableEntity entity)
    {
        lock (gate)
        {
            entity.ETag = new ETag((++revision).ToString());
            Rows[entity.RowKey] = Clone(entity);
        }
    }

    public override Task<Response<T>> GetEntityAsync<T>(
        string partitionKey, string rowKey, IEnumerable<string>? select = null,
        CancellationToken cancellationToken = default)
    {
        lock (gate)
        {
            if (!Rows.TryGetValue(rowKey, out var entity)) throw new RequestFailedException(404, "Not found");
            return Task.FromResult(Response.FromValue(As<T>(Clone(entity)), new RawResponse()));
        }
    }

    public override Task<NullableResponse<T>> GetEntityIfExistsAsync<T>(
        string partitionKey, string rowKey, IEnumerable<string>? select = null,
        CancellationToken cancellationToken = default)
    {
        lock (gate)
        {
            NullableResponse<T> result = Rows.TryGetValue(rowKey, out var entity)
                ? new MaybeResponse<T>(As<T>(Clone(entity))) : new MaybeResponse<T>();
            return Task.FromResult(result);
        }
    }

    public override AsyncPageable<T> QueryAsync<T>(
        string? filter = null, int? maxPerPage = null, IEnumerable<string>? select = null,
        CancellationToken cancellationToken = default)
    {
        lock (gate)
        {
            var prefix = filter?.Contains("'product-'") == true ? "product-" : "order-";
            var customer = Regex.Match(filter ?? string.Empty, @"CustomerId eq '((?:[^']|'')*)'");
            var values = Rows.Values.Where(x => x.RowKey.StartsWith(prefix, StringComparison.Ordinal))
                .Where(x => !customer.Success || x.GetString("CustomerId") == customer.Groups[1].Value.Replace("''", "'"))
                .Select(x => As<T>(Clone(x))).ToArray();
            return AsyncPageable<T>.FromPages([Page<T>.FromValues(values, null, new RawResponse())]);
        }

    }

    public override Task<Response> AddEntityAsync<T>(T entity, CancellationToken cancellationToken = default)
    {
        lock (gate)
        {
            if (Rows.ContainsKey(entity.RowKey)) throw new RequestFailedException(409, "Exists");
            if (entity is not TableEntity row) throw new InvalidOperationException("Expected SDK TableEntity.");
            Put(row);
            return Task.FromResult<Response>(new RawResponse());
        }
    }

    public override Task<Response> UpdateEntityAsync<T>(
        T entity, ETag ifMatch, TableUpdateMode mode = TableUpdateMode.Merge, CancellationToken cancellationToken = default)
    {
        lock (gate)
        {
            if (!Rows.TryGetValue(entity.RowKey, out var current) || current.ETag != ifMatch)
                throw new RequestFailedException(412, "Conflict");
            if (entity is not TableEntity row || mode != TableUpdateMode.Replace)
                throw new InvalidOperationException("Expected an SDK TableEntity replacement.");
            Put(row);
            return Task.FromResult<Response>(new RawResponse());
        }
    }

    public override async Task<Response<IReadOnlyList<Response>>> SubmitTransactionAsync(
        IEnumerable<TableTransactionAction> transactionActions, CancellationToken cancellationToken = default)
    {
        await Task.Yield();
        lock (gate)
        {
            var actions = transactionActions.ToArray();
            Assert.InRange(actions.Length, 1, 100);
            Assert.Single(actions.Select(x => x.Entity.PartitionKey).Distinct());
            foreach (var action in actions)
            {
                var exists = Rows.TryGetValue(action.Entity.RowKey, out var current);
                if (action.ActionType == TableTransactionActionType.Add && exists)
                    throw new RequestFailedException(409, "Exists");
                if (action.ActionType == TableTransactionActionType.UpdateReplace &&
                    (!exists || current!.ETag != action.ETag))
                    throw new RequestFailedException(412, "Conflict");
            }
            foreach (var action in actions)
            {
                if (action.Entity is not TableEntity entity) throw new InvalidOperationException("Expected SDK TableEntity.");
                Put(entity);
            }
            BatchSizes.Add(actions.Length);
            if (FailAfterCommit)
            {
                FailAfterCommit = false;
                throw new RequestFailedException(409, "Ambiguous committed response");
            }
            IReadOnlyList<Response> results = actions.Select(_ => (Response)new RawResponse()).ToArray();
            return Response.FromValue(results, new RawResponse());
        }
    }

    private static T As<T>(TableEntity entity) where T : class =>
        entity is T value ? value : throw new InvalidOperationException("Unexpected test entity type.");

    internal static TableEntity Clone(TableEntity entity)
    {
        var clone = new TableEntity(entity.PartitionKey, entity.RowKey) { ETag = entity.ETag };
        foreach (var property in entity) clone[property.Key] = property.Value;
        return clone;
    }
}

internal sealed class MaybeResponse<T> : NullableResponse<T>
{
    private readonly T? value;
    internal MaybeResponse() { }
    internal MaybeResponse(T item) { value = item; HasValue = true; }
    public override bool HasValue { get; }
    public override T Value => HasValue ? value! : throw new InvalidOperationException("No value.");
    public override Response GetRawResponse() => new RawResponse();
}

internal sealed class RawResponse : Response
{
    public override int Status => 200;
    public override string ReasonPhrase => "OK";
    public override Stream? ContentStream { get; set; }
    public override string ClientRequestId { get; set; } = string.Empty;
    public override void Dispose() { }
    protected override bool ContainsHeader(string name) => false;
    protected override IEnumerable<HttpHeader> EnumerateHeaders() => [];
    protected override bool TryGetHeader(string name, out string value) { value = string.Empty; return false; }
    protected override bool TryGetHeaderValues(string name, out IEnumerable<string> values) { values = []; return false; }
}
