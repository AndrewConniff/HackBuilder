using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using TeachingReview.Web.Models;
using TeachingReview.Web.Services;
using Xunit;

namespace TeachingReview.Tests;

/// <summary>Checks deterministic human gates without claiming live Foundry validation.</summary>
public sealed class WorkflowTests
{
    private static SchoolState Seed() => new([
        new(1, "author", "Airi Ilves", "Author", string.Empty),
        new(2, "peer", "Hasan Ibrahimov", "Peer", string.Empty),
        new(3, "lead", "Nemanja Milatovic", "Lead", string.Empty)
    ], [new(1, "Evidence lesson", "Synthetic evidence", "R1: cite evidence.", 1, 2, 3)]);

    private sealed class MemoryStore : IStateStore
    {
        private SchoolState state = Seed();
        private int revision;
        public Task<Snapshot> ReadAsync(CancellationToken cancellationToken = default) =>
            Task.FromResult(new Snapshot(JsonSerializer.Deserialize<SchoolState>(JsonSerializer.Serialize(state))!,
                revision.ToString()));
        public Task WriteAsync(SchoolState value, string expected, CancellationToken cancellationToken = default)
        {
            if (expected != revision.ToString()) throw new WorkflowException("Conflict");
            state = JsonSerializer.Deserialize<SchoolState>(JsonSerializer.Serialize(value))!;
            revision++;
            return Task.CompletedTask;
        }
    }

    private sealed class TestReviewer(bool fail = false) : IReviewer
    {
        internal int Calls;
        public Task<ReviewReceipt> ReviewAsync(string kind, Material material, CancellationToken cancellationToken)
        {
            Calls++;
            if (fail && kind == "Accessibility") throw new InvalidDataException("Test-only review failure");
            return Task.FromResult(new ReviewReceipt(kind, $"test-{kind}:1", $"test-response-{Calls}", "R1 evidence"));
        }
    }

    /// <summary>Verifies the complete sequence, including required re-review after revision.</summary>
    [Fact]
    public async Task CurrentReviewedVersionCanBeApprovedAndRevisionInvalidatesIt()
    {
        var store = new MemoryStore();
        var reviewer = new TestReviewer();
        var service = new WorkflowService(store, reviewer, NullLogger<WorkflowService>.Instance);
        await service.ExecuteAsync(1, 1, 1, "Review", null);
        await service.ExecuteAsync(2, 1, 1, "Feedback", "Add a clearer evidence explanation.");
        await service.ExecuteAsync(1, 1, 1, "Revise", "Revised synthetic evidence");
        Assert.Equal("Draft", (await store.ReadAsync()).State.Materials[0].Stage);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(3, 1, 2, "Approve", null));
        await service.ExecuteAsync(1, 1, 2, "Review", null);
        await service.ExecuteAsync(2, 1, 2, "Feedback", "Evidence clarified.");
        await service.ExecuteAsync(1, 1, 2, "SendToLead", null);
        await service.ExecuteAsync(3, 1, 2, "Approve", null);
        var approved = (await store.ReadAsync()).State.Materials[0];
        Assert.Equal("Approved", approved.Stage);
        Assert.Equal(4, reviewer.Calls);
        Assert.Equal(2, approved.Reviews.Count);
        Assert.Contains(approved.History, x => x.Action == "Superseded version" &&
            x.Evidence.Contains("Synthetic evidence") && x.Evidence.Contains("test-response-"));
        await service.ExecuteAsync(1, 1, 2, "Revise", "Further changed text");
        var changed = (await store.ReadAsync()).State.Materials[0];
        Assert.Equal(3, changed.Version);
        Assert.Empty(changed.Reviews);
        Assert.Contains(changed.History, x => x.Action == "Approve" && x.Version == 2);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(3, 1, 2, "Approve", null));
    }

    /// <summary>Rejects role escalation, missing review and invalid action requests.</summary>
    [Theory]
    [InlineData(1, "Approve")]
    [InlineData(2, "Review")]
    [InlineData(3, "Revise")]
    [InlineData(3, "Approve")]
    [InlineData(1, "SendToLead")]
    [InlineData(2, "Feedback")]
    [InlineData(1, "Unknown")]
    [InlineData(99, "Review")]
    public async Task InvalidActionsDoNotChangeState(int actor, string action)
    {
        var store = new MemoryStore();
        var service = new WorkflowService(store, new TestReviewer(), NullLogger<WorkflowService>.Instance);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(actor, 1, 1, action, "test"));
        Assert.Equal("Draft", (await store.ReadAsync()).State.Materials[0].Stage);
    }

    /// <summary>Ensures partial agent success blocks handoff and retries are bounded.</summary>
    [Fact]
    public async Task PartialReviewFailureIsVisibleAndBounded()
    {
        var store = new MemoryStore();
        var reviewer = new TestReviewer(true);
        var service = new WorkflowService(store, reviewer, NullLogger<WorkflowService>.Instance);
        for (var attempt = 0; attempt < 3; attempt++)
            await service.ExecuteAsync(1, 1, 1, "Review", null);
        var material = (await store.ReadAsync()).State.Materials[0];
        Assert.Equal("Failed", material.Stage);
        Assert.Single(material.Reviews);
        Assert.NotEmpty(material.Failure);
        Assert.Equal(6, reviewer.Calls);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(1, 1, 1, "Review", null));
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(2, 1, 1, "Feedback", "test"));
    }

    /// <summary>Rejects missing grounding before calling any model.</summary>
    [Fact]
    public async Task MissingRubricDoesNotInvokeAgents()
    {
        var store = new MemoryStore();
        var snapshot = await store.ReadAsync();
        snapshot.State.Materials[0] = snapshot.State.Materials[0] with { Rubric = string.Empty };
        await store.WriteAsync(snapshot.State, snapshot.Revision);
        var reviewer = new TestReviewer();
        var service = new WorkflowService(store, reviewer, NullLogger<WorkflowService>.Instance);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(1, 1, 1, "Review", null));
        Assert.Equal(0, reviewer.Calls);
    }

    /// <summary>Checks exact material limits before model execution.</summary>
    [Theory]
    [InlineData(12000, true)]
    [InlineData(12001, false)]
    public async Task MaterialLimitIsExact(int length, bool accepted)
    {
        var store = new MemoryStore();
        var snapshot = await store.ReadAsync();
        snapshot.State.Materials[0] = snapshot.State.Materials[0] with { Text = new string('x', length) };
        await store.WriteAsync(snapshot.State, snapshot.Revision);
        var reviewer = new TestReviewer();
        var service = new WorkflowService(store, reviewer, NullLogger<WorkflowService>.Instance);
        if (accepted)
        {
            await service.ExecuteAsync(1, 1, 1, "Review", null);
            Assert.Equal(2, reviewer.Calls);
        }
        else
        {
            await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(1, 1, 1, "Review", null));
            Assert.Equal(0, reviewer.Calls);
        }
    }

    /// <summary>Checks abandoned attempts require expiry and an authorized author.</summary>
    [Fact]
    public async Task AbandonedReviewRequiresExplicitRecoveryAfterExpiry()
    {
        var store = new MemoryStore();
        var snapshot = await store.ReadAsync();
        snapshot.State.Materials[0].Stage = "Reviewing";
        snapshot.State.Materials[0].History.Add(new(DateTimeOffset.UtcNow, 1, 1, "Review started"));
        await store.WriteAsync(snapshot.State, snapshot.Revision);
        var service = new WorkflowService(store, new TestReviewer(), NullLogger<WorkflowService>.Instance);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(1, 1, 1, "Recover", null));
        snapshot = await store.ReadAsync();
        snapshot.State.Materials[0].History[0] = new(DateTimeOffset.UtcNow.AddMinutes(-4), 1, 1, "Review started");
        await store.WriteAsync(snapshot.State, snapshot.Revision);
        await Assert.ThrowsAsync<WorkflowException>(() => service.ExecuteAsync(2, 1, 1, "Recover", null));
        await service.ExecuteAsync(1, 1, 1, "Recover", null);
        Assert.Equal("Failed", (await store.ReadAsync()).State.Materials[0].Stage);
    }

    /// <summary>Checks persisted-store optimistic concurrency and restart behavior.</summary>
    [Fact]
    public async Task LocalStorePreservesDataAndRejectsStaleWrite()
    {
        var directory = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "state.json");
        try
        {
            await File.WriteAllTextAsync(path, JsonSerializer.Serialize(Seed()));
            var store = new LocalStateStore(path);
            var a = await store.ReadAsync();
            var b = await store.ReadAsync();
            a.State.Materials[0].Stage = "NeedsRevision";
            await store.WriteAsync(a.State, a.Revision);
            await Assert.ThrowsAsync<WorkflowException>(() => store.WriteAsync(b.State, b.Revision));
            Assert.Equal("NeedsRevision", (await new LocalStateStore(path).ReadAsync()).State.Materials[0].Stage);
        }
        finally
        {
            File.Delete(path);
            Directory.Delete(directory);
        }
    }
}
