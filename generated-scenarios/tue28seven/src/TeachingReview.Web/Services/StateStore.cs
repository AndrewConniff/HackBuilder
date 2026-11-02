using System.Text.Json;
using Azure;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using TeachingReview.Web.Models;

namespace TeachingReview.Web.Services;

internal interface IStateStore
{
    Task<Snapshot> ReadAsync(CancellationToken cancellationToken = default);
    Task WriteAsync(SchoolState state, string revision, CancellationToken cancellationToken = default);
}

internal sealed class BlobStateStore(BlobClient blob) : IStateStore
{
    public async Task<Snapshot> ReadAsync(CancellationToken cancellationToken = default)
    {
        var result = await blob.DownloadContentAsync(cancellationToken);
        var state = result.Value.Content.ToObjectFromJson<SchoolState>()
            ?? throw new InvalidDataException("Workflow storage is empty or invalid; initialization is required.");
        return new(state, result.Value.Details.ETag.ToString());
    }

    public async Task WriteAsync(SchoolState state, string revision, CancellationToken cancellationToken = default)
    {
        try
        {
            await blob.UploadAsync(BinaryData.FromObjectAsJson(state), new BlobUploadOptions
            {
                Conditions = new BlobRequestConditions { IfMatch = new ETag(revision) }
            }, cancellationToken);
        }
        catch (RequestFailedException error) when (error.Status == 412)
        {
            throw new WorkflowException("Another teacher changed the record. Reload before trying again.");
        }
    }
}

internal sealed class LocalStateStore(string path) : IStateStore
{
    private readonly SemaphoreSlim gate = new(1, 1);

    public async Task<Snapshot> ReadAsync(CancellationToken cancellationToken = default)
    {
        await gate.WaitAsync(cancellationToken);
        try
        {
            var json = await File.ReadAllTextAsync(path, cancellationToken);
            return new(JsonSerializer.Deserialize<SchoolState>(json)
                ?? throw new InvalidDataException("Local state is invalid."), Digest(json));
        }
        finally { gate.Release(); }
    }

    public async Task WriteAsync(SchoolState state, string revision, CancellationToken cancellationToken = default)
    {
        await gate.WaitAsync(cancellationToken);
        try
        {
            if (Digest(await File.ReadAllTextAsync(path, cancellationToken)) != revision)
                throw new WorkflowException("Another teacher changed the record. Reload before trying again.");
            var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                await File.WriteAllTextAsync(temporary, JsonSerializer.Serialize(state), cancellationToken);
                File.Move(temporary, path, true);
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
        finally { gate.Release(); }
    }

    private static string Digest(string value) =>
        Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(value)));
}
