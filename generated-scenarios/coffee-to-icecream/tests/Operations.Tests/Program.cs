using System.Collections.Concurrent;
using System.Diagnostics;
using System.Security.Claims;
using System.Text.Json;
using CoffeeShop.Web.Models;
using CoffeeShop.Web.Services;
using Microsoft.Extensions.Logging.Abstractions;

var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var snapshots = JsonSerializer.Deserialize<StoreSnapshot[]>(await File.ReadAllTextAsync(
    Path.Combine(root, "src", "CoffeeShop.Web", "SeedData", "stores.json")))!;
var tests = 0;
void Check(bool valid, string description)
{
    if (!valid) throw new Exception($"FAILED: {description}");
    tests++;
    Console.WriteLine($"PASS {description}");
}
async Task Reject<T>(Func<Task> operation, string description) where T : Exception
{
    try { await operation(); }
    catch (T) { Check(true, description); return; }
    throw new Exception($"FAILED: {description} did not reject.");
}
Task Calculate(DayInput input)
{
    DailyOperations.Calculate(snapshots[0].Store, "test", input);
    return Task.CompletedTask;
}
ClaimsPrincipal User(string name, bool area, params string[] stores) => new(new ClaimsIdentity(
    new[] { new Claim("oid", name), new Claim("roles", area ? "AreaManager" : "StoreManager") }
        .Concat(stores.Select(store => new Claim("store", store))), "test", ClaimTypes.Name, "roles"));
var north = User("areanorth", true, "001", "002", "003", "004", "005");
var storeUser = User("store001", false, "001");
var access = new StoreAccess();
Check(snapshots.Length == 10 && snapshots.Count(s => s.Store.Area == "north") == 5, "ten stores, two areas");
foreach (var snapshot in snapshots)
{
    var actual = DailyOperations.Calculate(snapshot.Store, snapshot.Version, snapshot.Input!);
    Check(actual.Ledger == snapshot.Ledger && actual.Stock.SequenceEqual(snapshot.Stock),
        $"recipe/P&L fixture {snapshot.Store.StoreId}");
}
var first = snapshots[0];
Check(first.Stock[0].OnHand == 11.3m && first.Ledger.Cogs == 99.4m && first.Ledger.Waste == 3m
    && first.Ledger.NetSales == 598.5m && first.Ledger.Profit == 309.1m,
    "exact liters, sold COGS, separate spoilage and profit");
await Reject<ArgumentException>(() => Calculate(first.Input! with
{
    Sales = [new("unknown-product", 10, 4)]
}), "unknown recipe rejected");
await Reject<ArgumentException>(() => Calculate(first.Input! with
{
    Spoilage = [new("vanilla", "unit", 1)]
}), "unit mismatch rejected");
await Reject<ArgumentException>(() => Calculate(first.Input! with
{
    Spoilage = [new("vanilla", "L", 100)]
}), "negative closing stock rejected");
await Reject<ArgumentException>(() => Calculate(first.Input! with { Labor = -1 }), "negative costs rejected");
var repo = new TestRepository(snapshots);
var gateway = new TestGateway();
var service = new CloseService(access, repo, gateway, NullLogger<CloseService>.Instance);
await Reject<UnauthorizedAccessException>(() => service.RunAsync(storeUser, new(["002"], "explain"), default),
    "store boundary before retrieval and inference");
Check(repo.Reads == 0 && gateway.Calls == 0, "denied request caused no reads or calls");
await Reject<UnauthorizedAccessException>(() => service.RunAsync(north, new(["006"], "explain"), default),
    "area cannot access another area");
await Reject<ArgumentException>(() => service.RunAsync(north, new(["001", "001"], "explain"), default),
    "duplicate store partition rejected");
var one = await service.RunAsync(storeUser, new(["001"], "spoilage and variance"), default);
Check(one.Status == "AwaitingReview" && one.Assignments.Length == 2 && one.Agents.Length == 1,
    "one store generates two workers and synthesis");
using var oneSynthesis = JsonDocument.Parse(gateway.SynthesisEvidence!);
var ledgerEvidence = oneSynthesis.RootElement.GetProperty("AuthoritativeSnapshots");
Check(ledgerEvidence.GetArrayLength() == 1
    && ledgerEvidence[0].GetProperty("StoreId").GetString() == "001"
    && ledgerEvidence[0].GetProperty("Version").GetString() == first.Version
    && ledgerEvidence[0].GetProperty("Ledger").GetProperty("Waste").GetDecimal() == 3m
    && ledgerEvidence[0].GetProperty("Ledger").GetProperty("Profit").GetDecimal() == 309.1m
    && ledgerEvidence[0].GetProperty("Stock")[0].GetProperty("OnHand").GetDecimal() == 11.3m,
    "synthesis receives exact scoped ledger, recorded spoilage, profit and final closing stock");
var area = await service.RunAsync(north, new(["001", "002", "003", "004", "005"], "area close"), default);
Check(area.Assignments.Length == 10 && area.Agents.Length == 1
    && area.Evidence.All(s => s.Store.Area == "north"), "five stores generate ten workers without south evidence");
using var areaSynthesis = JsonDocument.Parse(gateway.SynthesisEvidence!);
Check(areaSynthesis.RootElement.GetProperty("AuthoritativeSnapshots").EnumerateArray()
    .Select(row => row.GetProperty("StoreId").GetString()).Order()
    .SequenceEqual(new[] { "001", "002", "003", "004", "005" }),
    "synthesis ledger grounding excludes unauthorized area stores");
Check(gateway.MaxActive <= 4, "four-worker per-request concurrency bound");
await Reject<UnauthorizedAccessException>(() => service.ReviewAsync(storeUser, area.CorrelationId, true, default),
    "store manager cannot review multi-store close");
await Reject<ArgumentException>(() => service.ReviewAsync(storeUser, one.CorrelationId, false, default),
    "close requires explicit human confirmation");
var reviewed = await service.ReviewAsync(storeUser, one.CorrelationId, true, default);
Check(reviewed.Status == "Reviewed" && reviewed.ReviewedBy == "store001", "human review persisted");
Check((await service.ReviewAsync(storeUser, one.CorrelationId, true, default)).ReviewedAt == reviewed.ReviewedAt,
    "review replay does not duplicate or change approval");
repo.Set(first with { Version = "changed" });
await Reject<InvalidOperationException>(() => service.ReviewAsync(north, area.CorrelationId, true, default),
    "changed evidence blocks close review");
repo.Set(first with { Ledger = first.Ledger with { Complete = false } });
var count = gateway.Calls;
await Reject<InvalidOperationException>(() => service.RunAsync(storeUser, new(["001"], "close"), default),
    "incomplete ledger blocks close");
Check(gateway.Calls == count, "incomplete evidence never invokes agent");
repo.Set(first);
gateway.FailDomain = "margin";
var persisted = repo.ReportCount;
await Reject<InvalidOperationException>(() => service.RunAsync(storeUser, new(["001"], "close"), default),
    "failed worker blocks synthesis/report");
Check(repo.ReportCount == persisted, "worker failure never persists success");
gateway.FailDomain = null;
gateway.DuplicateResponseId = true;
await Reject<InvalidOperationException>(() => service.RunAsync(storeUser, new(["001"], "close"), default),
    "duplicate worker receipt rejected");
gateway.DuplicateResponseId = false;
using (var cancelled = new CancellationTokenSource())
{
    cancelled.Cancel();
    await Reject<OperationCanceledException>(() => service.RunAsync(storeUser, new(["001"], "close"), cancelled.Token),
        "cancellation cannot become completed close");
}
var orders = new OrderService(access, repo);
var order = await orders.DraftAsync(storeUser, "001", default);
Check(order.Lines.All(line => line.Quantity > 0) && order.Total > 0, "positive deterministic recipe stock shortfalls");
var approved = await orders.ApproveAsync(storeUser, "001", order.DraftId, default);
Check(approved.Status == "Approved"
    && (await orders.ApproveAsync(storeUser, "001", order.DraftId, default)).ApprovedAt == approved.ApprovedAt,
    "internal order approval replay safe");
repo.Set(first with { Version = "new-draft" });
var stale = await orders.DraftAsync(storeUser, "001", default);
repo.Set(first with { Version = "newer" });
await Reject<InvalidOperationException>(() => orders.ApproveAsync(storeUser, "001", stale.DraftId, default),
    "stale order rejected");
repo.Set(first);
var csv = await File.ReadAllTextAsync(Path.Combine(root, "data", "day-001.csv"));
var packet = DailyOperations.Parse("001", csv);
Check(packet.Recipes.Length == 4 && packet.Sales.Length == 2, "CSV preserves recipe/sales contract");
await Reject<ArgumentException>(() => Task.Run(() => DailyOperations.Parse("002", csv)), "CSV store mismatch rejected");
await Reject<ArgumentException>(() => Task.Run(() => DailyOperations.Parse("001", csv.Replace(",L,", ",gallon,"))),
    "unsupported CSV unit rejected");
await Reject<ArgumentException>(() => Task.Run(() => DailyOperations.Parse("001", csv + csv.Split('\n')[1] + "\n")),
    "duplicate CSV row rejected");
var operations = new DailyOperations(access, repo);
await Reject<UnauthorizedAccessException>(() => operations.ImportAsync(storeUser, "002", new(first.Version, csv), default),
    "CSV authorization before import");
var imported = await operations.ImportAsync(storeUser, "001", new(first.Version, csv), default);
Check(imported.Version != first.Version && imported.Ledger == first.Ledger, "CSV recalculates exact P&L with new version");
await Reject<InvalidOperationException>(() => operations.ImportAsync(storeUser, "001", new(imported.Version, csv), default),
    "duplicate import never re-applies consumption");
repo.Set(first);
var concurrencyService = new CloseService(access, repo, new TestGateway(), NullLogger<CloseService>.Instance);
var watch = Stopwatch.StartNew();
var ten = await Task.WhenAll(Enumerable.Range(1, 10).Select(index =>
    concurrencyService.RunAsync(User($"store{index:000}", false, $"{index:000}"),
        new([$"{index:000}"], "daily close"), default)));
Check(ten.Length == 10 && ten.All(report => report.Status == "AwaitingReview"),
    "ten simultaneous managers accepted by local scheduler (not live latency evidence)");
var accounts = new TestAccounts();
var login = new LocalAccounts(accounts, NullLogger<LocalAccounts>.Instance);
var password = Convert.ToBase64String(System.Security.Cryptography.RandomNumberGenerator.GetBytes(32));
accounts.Account = LocalAccounts.Create("store001", password, "StoreManager", ["001"]);
Check(await login.AuthenticateAsync("store001", password, default) is not null, "salted password login");
Check(!accounts.Account.PasswordHash.Contains(password, StringComparison.Ordinal), "no plaintext password stored");
for (var index = 0; index < 5; index++) await login.AuthenticateAsync("store001", "incorrect", default);
Check(await login.AuthenticateAsync("store001", password, default) is null, "five failures enforce persistent lockout");
Console.WriteLine($"{tests} local assertions passed. Scheduler sample {watch.Elapsed.TotalMilliseconds:F0} ms; no Azure proof.");

/// <summary>Test-only repository with versioned semantics, never registered by the deployed app.</summary>
internal sealed class TestRepository(IEnumerable<StoreSnapshot> snapshots) : IRepository
{
    private readonly ConcurrentDictionary<string, StoreSnapshot> data = new(snapshots.ToDictionary(s => s.Store.StoreId));
    private readonly Dictionary<string, StoredOrder> orders = [];
    private readonly Dictionary<string, StoredClose> reports = [];
    private readonly HashSet<string> imports = [];
    private readonly object gate = new();
    private int reads;
    public int Reads => reads;
    public int ReportCount => reports.Count;
    public void Set(StoreSnapshot snapshot) => data[snapshot.Store.StoreId] = snapshot;
    public Task<StoreSnapshot> ReadAsync(string storeId, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested(); Interlocked.Increment(ref reads); return Task.FromResult(data[storeId]);
    }
    public Task<StoredOrder?> GetOrderAsync(string storeId, string draftId, CancellationToken ct)
    {
        lock (gate) return Task.FromResult(orders.GetValueOrDefault($"{storeId}-{draftId}"));
    }
    public Task<StoredOrder> AddOrderAsync(Order order, CancellationToken ct)
    {
        lock (gate)
        {
            var key = $"{order.StoreId}-{order.DraftId}";
            orders.TryAdd(key, new(order, Guid.NewGuid().ToString())); return Task.FromResult(orders[key]);
        }
    }
    public Task<bool> ReplaceOrderAsync(StoredOrder order, CancellationToken ct)
    {
        lock (gate)
        {
            var key = $"{order.Value.StoreId}-{order.Value.DraftId}";
            if (orders[key].ETag != order.ETag) return Task.FromResult(false);
            orders[key] = order with { ETag = Guid.NewGuid().ToString() }; return Task.FromResult(true);
        }
    }
    public Task<StoreSnapshot> ImportAsync(StoreSnapshot snapshot, string expectedVersion, string importId, CancellationToken ct)
    {
        lock (gate)
        {
            var key = $"{snapshot.Store.StoreId}-{importId}";
            if (imports.Contains(key) || data[snapshot.Store.StoreId].Version != expectedVersion)
                throw new InvalidOperationException("Stale or repeated import.");
            imports.Add(key); Set(snapshot); return Task.FromResult(snapshot);
        }
    }
    public Task SaveCloseAsync(CloseResult result, CancellationToken ct)
    {
        lock (gate) reports.Add(result.CorrelationId, new(result, Guid.NewGuid().ToString()));
        return Task.CompletedTask;
    }
    public Task<StoredClose> GetCloseAsync(string id, CancellationToken ct)
    {
        lock (gate) return Task.FromResult(reports[id]);
    }
    public Task ReviewCloseAsync(StoredClose report, CancellationToken ct)
    {
        lock (gate)
        {
            if (reports[report.Value.CorrelationId].ETag != report.ETag) throw new InvalidOperationException("Stale review.");
            reports[report.Value.CorrelationId] = report with { ETag = Guid.NewGuid().ToString() };
        }
        return Task.CompletedTask;
    }
}

/// <summary>Explicit test double for orchestration safety, not Foundry runtime or latency evidence.</summary>
internal sealed class TestGateway : IAgentGateway
{
    private int calls, active, maxActive;
    public int Calls => calls;
    public int MaxActive => maxActive;
    public string? FailDomain { get; set; }
    public bool DuplicateResponseId { get; set; }
    /// <summary>Retains the synthesis input for exact grounding-contract assertions.</summary>
    public string? SynthesisEvidence { get; private set; }
    public async Task<AgentReceipt> InvokeAsync(string agent, string evidence, CancellationToken ct)
    {
        if (agent == "close") SynthesisEvidence = evidence;
        Interlocked.Increment(ref calls);
        var current = Interlocked.Increment(ref active);
        InterlockedExtensions.Max(ref maxActive, current);
        try
        {
            await Task.Delay(10, ct);
            if (FailDomain == agent) throw new InvalidOperationException("Injected worker failure.");
            return new(agent, "test-only", DuplicateResponseId ? "duplicate" : Guid.NewGuid().ToString(), "Test evidence.");
        }
        finally { Interlocked.Decrement(ref active); }
    }
}

/// <summary>Test-only persistent account state.</summary>
internal sealed class TestAccounts : IAccountRepository
{
    public LocalAccount Account { get; set; } = null!;
    public Task<StoredAccount?> FindAsync(string username, CancellationToken ct) =>
        Task.FromResult<StoredAccount?>(username == Account.Username ? new(Account, "1") : null);
    public Task<bool> ReplaceAsync(StoredAccount account, CancellationToken ct)
    {
        Account = account.Value; return Task.FromResult(true);
    }
}

internal static class InterlockedExtensions
{
    public static void Max(ref int location, int value)
    {
        int current;
        do { current = Volatile.Read(ref location); if (current >= value) return; }
        while (Interlocked.CompareExchange(ref location, value, current) != current);
    }
}
