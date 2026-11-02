using System.Text.Json;
using Azure.Identity;
using HospitalityFeedback.Web.Models;
using HospitalityFeedback.Web.Services;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace HospitalityFeedback.Tests;

[CollectionDefinition("Azurite", DisableParallelization = true)]
public sealed class AzuriteCollection : ICollectionFixture<AzuriteFixture>;

public sealed class AzuriteFixture : IAsyncLifetime
{
    public FeedbackOptions Options { get; } = new() { UseAzurite = true };
    public StorageRepository Store { get; }
    public AzuriteFixture() => Store = new(Options, new DefaultAzureCredential());
    public async Task InitializeAsync()
    {
        if (Environment.GetEnvironmentVariable("RUN_AZURITE_TESTS") != "1")
            throw new InvalidOperationException("Run unit filter only, or start Azurite and set RUN_AZURITE_TESTS=1.");
        foreach (var container in new[] { Store.Raw, Store.Processed, Store.Status, Store.Audit })
        {
            await container.DeleteIfExistsAsync();
            await container.CreateIfNotExistsAsync();
        }
        await Store.InitializeLocalAsync(CancellationToken.None);
        await Store.Queue.ClearMessagesAsync();
        await Store.Poison.ClearMessagesAsync();
    }
    public async Task DisposeAsync()
    {
        // Dedicated loopback emulator only. Never run this fixture against an Azure endpoint.
        foreach (var container in new[] { Store.Raw, Store.Processed, Store.Status, Store.Audit })
            await container.DeleteIfExistsAsync();
        await Store.Queue.DeleteIfExistsAsync();
        await Store.Poison.DeleteIfExistsAsync();
    }
}

[Collection("Azurite")]
[Trait("Category", "Azurite")]
public sealed class StorageTests(AzuriteFixture fixture)
{
    [Fact]
    public async Task QueueToBlobPreservesUnicodeAndCorrelation()
    {
        var input = DomainTests.Sample("HF-9101");
        var accepted = await fixture.Store.IngestAsync(input, CancellationToken.None);
        var raw = await StorageRepository.ReadAsync<RawFeedback>(
            fixture.Store.Raw.GetBlobClient(input.FeedbackId + ".json"), CancellationToken.None);
        Assert.Equal(input.Text, raw!.Feedback.Text);
        var worker = new QueueWorker(fixture.Store, fixture.Options, NullLogger<QueueWorker>.Instance);
        var received = await fixture.Store.Queue.ReceiveMessageAsync();
        Assert.NotNull(received.Value);
        await worker.HandleAsync(received.Value, CancellationToken.None);
        var evidence = await StorageRepository.ReadAsync<Evidence>(
            fixture.Store.Processed.GetBlobClient(input.FeedbackId + ".json"), CancellationToken.None);
        Assert.Equal(input, evidence!.Feedback);
        Assert.Equal(accepted.CorrelationId, evidence.CorrelationId);
        var status = await StorageRepository.ReadAsync<ProcessingStatus>(
            fixture.Store.Status.GetBlobClient(input.FeedbackId + ".json"), CancellationToken.None);
        Assert.Equal("completed", status!.State);
    }

    [Fact]
    public async Task DuplicatesAreIdempotentAndCollisionsConflict()
    {
        var input = DomainTests.Sample("HF-9102");
        var accepted = await fixture.Store.IngestAsync(input, CancellationToken.None);
        var duplicate = await fixture.Store.IngestAsync(input, CancellationToken.None);
        Assert.True(duplicate.Duplicate);
        Assert.Equal(accepted.CorrelationId, duplicate.CorrelationId);
        await Assert.ThrowsAsync<ConflictException>(() =>
            fixture.Store.IngestAsync(input with { Text = "Changed" }, CancellationToken.None));
        var work = new WorkItem(input.FeedbackId, accepted.CorrelationId);
        Assert.True(await fixture.Store.ProcessAsync(work, 1, CancellationToken.None));
        var first = await fixture.Store.Processed.GetBlobClient(input.FeedbackId + ".json").DownloadContentAsync();
        Assert.True(await fixture.Store.ProcessAsync(work, 2, CancellationToken.None));
        var second = await fixture.Store.Processed.GetBlobClient(input.FeedbackId + ".json").DownloadContentAsync();
        Assert.Equal(first.Value.Content.ToString(), second.Value.Content.ToString());
        await fixture.Store.Queue.ClearMessagesAsync();
    }

    [Fact]
    public async Task MalformedQueueMessageIsDurablyPoisoned()
    {
        await fixture.Store.Queue.ClearMessagesAsync();
        await fixture.Store.Queue.SendMessageAsync("not valid json");
        var received = await fixture.Store.Queue.ReceiveMessageAsync();
        await new QueueWorker(fixture.Store, fixture.Options, NullLogger<QueueWorker>.Instance)
            .HandleAsync(received.Value, CancellationToken.None);
        Assert.True((await fixture.Store.Audit.GetBlobClient(
            "poison-" + received.Value.MessageId + ".json").ExistsAsync()).Value);
        var poison = await fixture.Store.Poison.ReceiveMessageAsync();
        using var json = JsonDocument.Parse(poison.Value.Body.ToString());
        Assert.Equal("JsonException", json.RootElement.GetProperty("errorCode").GetString());
        Assert.DoesNotContain("not valid json", poison.Value.Body.ToString());
    }

    [Fact]
    public async Task SourceMismatchCannotPoisonValidFeedback()
    {
        await fixture.Store.Queue.ClearMessagesAsync();
        var input = DomainTests.Sample("HF-9103");
        var accepted = await fixture.Store.IngestAsync(input, CancellationToken.None);
        await fixture.Store.Queue.ClearMessagesAsync();
        await fixture.Store.Queue.SendMessageAsync(JsonSerializer.Serialize(
            new WorkItem(input.FeedbackId, Guid.NewGuid().ToString("N")), Rules.Json));
        var received = await fixture.Store.Queue.ReceiveMessageAsync();
        await new QueueWorker(fixture.Store, fixture.Options, NullLogger<QueueWorker>.Instance)
            .HandleAsync(received.Value, CancellationToken.None);
        Assert.Null(await StorageRepository.ReadAsync<ProcessingStatus>(
            fixture.Store.Status.GetBlobClient(input.FeedbackId + ".json"), CancellationToken.None));
        Assert.True(await fixture.Store.ProcessAsync(new(input.FeedbackId, accepted.CorrelationId), 1,
            CancellationToken.None));
    }

    [Fact]
    public async Task FilteredEvidenceRetainsSourceLanguage()
    {
        var input = DomainTests.Sample("HF-9104") with { Category = "noise" };
        var accepted = await fixture.Store.IngestAsync(input, CancellationToken.None);
        await fixture.Store.ProcessAsync(new(input.FeedbackId, accepted.CorrelationId), 1, CancellationToken.None);
        var selected = await fixture.Store.EvidenceAsync(new("Summarize", "fr", "noise", ["ja"]),
            CancellationToken.None);
        Assert.Contains(selected, e => e.Feedback.FeedbackId == input.FeedbackId && e.Feedback.Text == input.Text);
        Assert.All(selected, e => Assert.Equal("ja", e.Feedback.Language));
        await fixture.Store.Queue.ClearMessagesAsync();
    }

    [Fact]
    public async Task RawOutboxReconcilesAnInterruptedEnqueue()
    {
        await fixture.Store.Queue.ClearMessagesAsync();
        var input = DomainTests.Sample("HF-9201");
        var correlation = Guid.NewGuid().ToString("N");
        await StorageRepository.WriteAsync(fixture.Store.Raw.GetBlobClient(input.FeedbackId + ".json"),
            new RawFeedback(input, Rules.Hash(input), correlation, DateTimeOffset.UtcNow.AddMinutes(-1)),
            CancellationToken.None);
        await fixture.Store.ReconcileAsync(CancellationToken.None);
        var messages = await fixture.Store.Queue.PeekMessagesAsync(32);
        Assert.Contains(messages.Value, m => m.Body.ToString().Contains(input.FeedbackId, StringComparison.Ordinal));
        await fixture.Store.ProcessAsync(new(input.FeedbackId, correlation), 1, CancellationToken.None);
        await fixture.Store.Queue.ClearMessagesAsync();
    }

    [Fact]
    public async Task TransientMissingSourceRetriesThenPoisonsAtBound()
    {
        await fixture.Store.Queue.ClearMessagesAsync();
        await fixture.Store.Queue.SendMessageAsync(JsonSerializer.Serialize(
            new WorkItem("HF-9299", Guid.NewGuid().ToString("N")), Rules.Json));
        var worker = new QueueWorker(fixture.Store, fixture.Options, NullLogger<QueueWorker>.Instance);
        string? messageId = null;
        for (var attempt = 1; attempt <= fixture.Options.MaxDeliveryAttempts; attempt++)
        {
            var received = await fixture.Store.Queue.ReceiveMessageAsync();
            messageId = received.Value.MessageId;
            Assert.Equal(attempt, received.Value.DequeueCount);
            await worker.HandleAsync(received.Value, CancellationToken.None);
            if (attempt < fixture.Options.MaxDeliveryAttempts)
                await fixture.Store.Queue.UpdateMessageAsync(received.Value.MessageId, received.Value.PopReceipt,
                    received.Value.Body, TimeSpan.Zero);
        }
        Assert.Empty((await fixture.Store.Queue.PeekMessagesAsync()).Value);
        Assert.True((await fixture.Store.Audit.GetBlobClient("poison-" + messageId + ".json").ExistsAsync()).Value);
    }

    [Fact]
    public async Task EvidenceLimitFailsExplicitlyInsteadOfSilentlyTruncating()
    {
        foreach (var id in new[] { "HF-9301", "HF-9302" })
        {
            var input = DomainTests.Sample(id);
            var accepted = await fixture.Store.IngestAsync(input, CancellationToken.None);
            await fixture.Store.ProcessAsync(new(id, accepted.CorrelationId), 1, CancellationToken.None);
        }
        var limited = new StorageRepository(new FeedbackOptions { UseAzurite = true, MaxEvidenceRecords = 1 },
            new DefaultAzureCredential());
        var error = await Assert.ThrowsAsync<InputException>(() =>
            limited.EvidenceAsync(new("Summarize"), CancellationToken.None));
        Assert.Equal("dataset_limit", error.Code);
        await fixture.Store.Queue.ClearMessagesAsync();
    }
}
