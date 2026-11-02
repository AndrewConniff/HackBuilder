using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Azure;
using Azure.Storage.Blobs;
using EquipAI.Web.Models;
using EquipAI.Web.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Playwright;
using Microsoft.AspNetCore.Identity;

var workspace = Path.GetFullPath(args.FirstOrDefault() ?? throw new ArgumentException("Pass the scenario workspace."));
var webRoot = Path.Combine(workspace, "src", "EquipAI.Web");
Directory.CreateDirectory(Path.Combine(workspace, "local-evidence"));
if (args.Contains("--live-browser"))
{
    var access = JsonDocument.Parse(File.ReadAllText(Path.Combine(workspace, ".private", "participant-access.json")));
    var origin = access.RootElement.GetProperty("applicationUrl").GetString()
        ?? throw new InvalidDataException("Actual deployed login URL is missing from private access notes.");
    var browserChecks = new List<object>();
    using var livePlaywright = await Playwright.CreateAsync();
    await using var liveBrowser = await livePlaywright.Chromium.LaunchAsync(new()
    {
        Headless = true, ExecutablePath = Environment.GetEnvironmentVariable("EQUIP_BROWSER")
            ?? throw new ArgumentException("Set EQUIP_BROWSER to the approved existing Chromium executable.")
    });
    foreach (var account in access.RootElement.GetProperty("accounts").EnumerateArray())
    {
        var username = account.GetProperty("username").GetString()!;
        await using var context = await liveBrowser.NewContextAsync();
        var page = await context.NewPageAsync();
        try
        {
            await page.GotoAsync(origin);
            await page.Locator("#username").FillAsync(username);
            await page.Locator("#password").FillAsync(account.GetProperty("password").GetString()!);
            await page.Locator("#login").ClickAsync();
            await page.Locator("#login-form").WaitForAsync(new() { State = WaitForSelectorState.Hidden, Timeout = 30000 });
        }
        catch (PlaywrightException)
        {
            throw new InvalidOperationException("Live browser sign-in failed; private input omitted from diagnostics.");
        }
        if (!(await page.Locator("#status").InnerTextAsync()).Contains(username) ||
            await page.Locator("#send").IsDisabledAsync())
            throw new InvalidOperationException("Live UI did not enter the authenticated Operations state.");
        await page.Locator("#question").FillAsync(
            "Use GetEquipmentTelemetry for tacoma-pump-01 at tacoma over 120 minutes and cite exact evidence.");
        await page.Locator("#send").ClickAsync();
        await page.WaitForFunctionAsync(
            "() => document.getElementById('trace').textContent.startsWith('Agent equipment-operations/')",
            null, new() { Timeout = 45000 });
        if (string.IsNullOrWhiteSpace(await page.Locator("#evidence").InnerTextAsync()))
            throw new InvalidOperationException("Live UI displayed no grounded evidence.");
        foreach (var width in new[] { 1440, 390 })
        {
            await page.SetViewportSizeAsync(width, 900);
            if (await page.EvaluateAsync<bool>("document.documentElement.scrollWidth > window.innerWidth"))
                throw new InvalidOperationException($"Live page overflows at {width}px.");
            await page.ScreenshotAsync(new()
            {
                Path = Path.Combine(workspace, "local-evidence", "resume-20261026", $"{username}-{width}.png"),
                FullPage = true
            });
        }
        await page.Locator("#logout").ClickAsync();
        await page.Locator("#login-form").WaitForAsync(new() { State = WaitForSelectorState.Visible });
        if (!await page.Locator("#send").IsDisabledAsync())
            throw new InvalidOperationException("Live UI still permits submission after logout.");
        browserChecks.Add(new { username, login = true, groundedChat = true, responsiveWidths = new[] { 1440, 390 },
            logout = true, passed = true });
        Console.WriteLine($"PASS live browser login, grounded chat, responsive layout and logout: {username}");
    }
    File.WriteAllText(Path.Combine(workspace, "local-evidence", "resume-20261026", "live-browser-checks.json"),
        JsonSerializer.Serialize(new { checkedAtUtc = DateTimeOffset.UtcNow, passed = true, checks = browserChecks },
            new JsonSerializerOptions { WriteIndented = true }));
    return;
}
var inventory = new Inventory(webRoot);
var now = DateTimeOffset.Parse("2026-10-23T15:00:00Z");
var user = new ClaimsPrincipal(new ClaimsIdentity([new Claim("roles", "Operations.Tacoma")], "test", "name", "roles"));
int passed = 0;
var results = new List<object>();
void Check(string name, bool condition)
{
    if (!condition) throw new InvalidOperationException($"FAILED: {name}");
    passed++;
    results.Add(new { name, passed = true });
    Console.WriteLine($"PASS {name}");
}
var authClock = new LabTestClock(now);
var authAccount = new LabAccount("tacoma-support", string.Empty, ["Operations.Tacoma"], Guid.NewGuid().ToString("N"));
authAccount = authAccount with { PasswordHash = new PasswordHasher<LabAccount>().HashPassword(
    authAccount, "unit-test-only-not-a-deployed-password") };
var accounts = new LabTestAccounts(authAccount);
var authentication = new LabAuthentication(accounts, authClock);
Check("unknown local account denied", await authentication.AuthenticateAsync("unknown", "incorrect", default) is null);
for (int attempt = 0; attempt < 5; attempt++)
    Check($"bad local password {attempt + 1} denied",
        await authentication.AuthenticateAsync("tacoma-support", "incorrect", default) is null);
Check("correct password cannot bypass lockout", await authentication.AuthenticateAsync(
    "tacoma-support", "unit-test-only-not-a-deployed-password", default) is null);
authClock.Now = now.AddMinutes(16);
var signedIn = await authentication.AuthenticateAsync(
    "tacoma-support", "unit-test-only-not-a-deployed-password", default);
Check("local login after lockout preserves Tacoma-only role",
    signedIn is not null && SiteAccess.Sites(signedIn).SequenceEqual(["tacoma"]));
Check("current session validated against durable account",
    signedIn is not null && await authentication.IsCurrentAsync(signedIn, default));
accounts.Account = accounts.Account with { SecurityStamp = Guid.NewGuid().ToString("N") };
Check("rotated account invalidates old session",
    signedIn is not null && !await authentication.IsCurrentAsync(signedIn, default));
void Reject(string name, Action action, string? code = null)
{
    try { action(); }
    catch (Exception error) when (error is ScenarioException or InvalidDataException or FormatException)
    {
        Check(name, code is null || error is ScenarioException scenario && scenario.Code == code);
        return;
    }
    throw new InvalidOperationException($"FAILED: {name} did not reject invalid input.");
}
Reading Event(int minutes, double vibration = 4.2, string id = "m1") =>
    new(1, id, "tacoma-pump-01", now.AddMinutes(-minutes), minutes, 73, vibration, 8.2, "running");
string Envelope(Reading reading, bool base64 = false, string device = "tacoma-pump-01") =>
    JsonSerializer.Serialize(new
    {
        EnqueuedTimeUtc = now,
        SystemProperties = new { connectionDeviceId = device },
        Body = base64
            ? JsonSerializer.SerializeToElement(Convert.ToBase64String(
                Encoding.UTF8.GetBytes(JsonSerializer.Serialize(reading, TelemetryEngine.Json))))
            : JsonSerializer.SerializeToElement(reading, TelemetryEngine.Json)
    });
Check("25 site-owned equipment records", inventory.Equipment.Count == 25);
var publishedFixture = DevicePublisher.Fixture("tacoma-pump-01", now, "trend");
Check("real publisher fixture has two fresh readings and one expired reading",
    publishedFixture.Count(reading => TelemetryEngine.IsFresh(reading, now)) == 2 &&
    publishedFixture.Length == 3);
Check("real publisher fixture uses unique message IDs",
    publishedFixture.Select(reading => reading.MessageId).Distinct().Count() == 3);
Check("only Tacoma authorized", SiteAccess.Sites(user).SequenceEqual(["tacoma"]));
Reject("forged Spokane site denied", () => SiteAccess.Require(user, "spokane"), "site_forbidden");
Check("object routed envelope", TelemetryEngine.ParseEnvelope(Envelope(Event(1)), now) == Event(1));
Check("base64 routed envelope", TelemetryEngine.ParseEnvelope(Envelope(Event(1), true), now) == Event(1));
Reject("payload cannot spoof device", () => TelemetryEngine.ParseEnvelope(Envelope(Event(1), device: "spokane-pump-01"), now));
Reject("future skew over two minutes", () => TelemetryEngine.ParseEnvelope(Envelope(Event(-3)), now));
Reject("measurement range rejected", () => TelemetryEngine.ParseEnvelope(Envelope(Event(1) with { PressureBar = -1 }), now));
Check("exact 120-minute boundary excluded", !TelemetryEngine.IsFresh(Event(120), now));
Check("119-minute evidence included", TelemetryEngine.IsFresh(Event(119), now));
Check("replay deduplicated", TelemetryEngine.Deduplicate([Event(1), Event(1)]).Length == 1);
Reject("conflicting replay rejected", () => TelemetryEngine.Deduplicate([Event(1), Event(1, 9)]), "conflicting_replay");
var summary = TelemetryEngine.Summarize(inventory,
    [Event(29, 3, "first"), Event(1, 6, "last"), Event(120, 99, "expired")],
    user, new("tacoma", "tacoma-pump-01", 120), now, 0);
Check("deterministic vibration trend", summary.Equipment.Single().VibrationChangeMmPerSecond == 3);
Check("expired event cannot alter maximum", summary.Equipment.Single().VibrationMaxMmPerSecond == 6);
Check("scoped expiry diagnostic reports actual excluded records",
    JsonSerializer.SerializeToElement(summary.Coverage).GetProperty("expiredReadingsExcluded").GetInt32() == 1);
var prefiltered = TelemetryEngine.Summarize(inventory, [Event(1)], user,
    new("tacoma", "tacoma-pump-01", 120), now, 0,
    new Dictionary<string, int> { ["tacoma-pump-01"] = 7, ["spokane-pump-01"] = 99, ["tacoma-press-02"] = 88 });
Check("cache-filtered expiry counts survive without exposing other equipment",
    JsonSerializer.SerializeToElement(prefiltered.Coverage).GetProperty("expiredReadingsExcluded").GetInt32() == 7);
Check("exact count and temperature", summary.Equipment.Single().Count == 2 && summary.Equipment.Single().TemperatureMaxC == 73);
var stale = TelemetryEngine.Summarize(inventory, [Event(5)], user, new("tacoma", "tacoma-pump-01", 30), now, 0);
Check("five-minute stopped device is stale", stale.Equipment.Single().Status == "stale");
var empty = TelemetryEngine.Summarize(inventory, [Event(120)], user, new("tacoma", null, 120), now, 0);
Check("expired-only data reports gaps", empty.Status == "no_fresh_data" && empty.Warnings.Length == 5);
Reject("window over 120 rejected", () => TelemetryEngine.Summarize(inventory, [], user, new("tacoma", null, 121), now, 0));
Reject("unknown device clarified", () => TelemetryEngine.Summarize(inventory, [], user, new("tacoma", "unknown", 30), now, 0),
    "unknown_equipment");
var evidence = summary.Equipment.ToDictionary(e => e.EvidenceId);
FoundryAgent.ValidateFinal("answer", "Vibration rose 3 mm/s.", summary.EvidenceIds, evidence, now);
Check("verified citation accepted", true);
Reject("invented citation rejected", () => FoundryAgent.ValidateFinal("answer", "ok", ["invented"], evidence, now),
    "invalid_agent_output");
Reject("ungrounded answer rejected", () => FoundryAgent.ValidateFinal("answer", "healthy", [], evidence, now),
    "ungrounded_answer");
Reject("final-response freshness rechecked", () => FoundryAgent.ValidateFinal(
    "answer", "old", summary.EvidenceIds, evidence, now.AddMinutes(92)), "evidence_expired");
FoundryAgent.ValidateFinal("refusal", "No machine-control tools are provided.", [], evidence, now);
Check("advisory refusal permitted without fabricated readings", true);
Check("cleanup deletes fully expired settled batch", BlobTelemetry.CanDelete(now.AddMinutes(-6),
    now.AddMinutes(-126), 0, now));
Check("cleanup preserves active writer", !BlobTelemetry.CanDelete(now.AddMinutes(-1),
    now.AddMinutes(-126), 0, now));
Check("cleanup preserves fresh event in old batch", !BlobTelemetry.CanDelete(now.AddMinutes(-130),
    now.AddMinutes(-1), 0, now));
Check("invalid batch requires 130-minute quarantine", !BlobTelemetry.CanDelete(now.AddMinutes(-129),
    now.AddMinutes(-200), 1, now));
Check("cleanup recovers expired batch after outage", BlobTelemetry.CanDelete(now.AddHours(-5),
    now.AddHours(-5), 0, now));
var unusedBlob = new BlobTelemetry(new BlobContainerClient(new Uri("http://127.0.0.1:1/telemetry")),
    TimeProvider.System, NullLogger<BlobTelemetry>.Instance);
var toolAgent = new FoundryAgent(new ConfigurationBuilder().Build(), inventory, unusedBlob,
    TimeProvider.System, NullLogger<FoundryAgent>.Instance);
foreach (var toolCase in new[]
{
    ("unknown tool rejected without network", "DeleteEquipment", "{}", "unknown_tool"),
    ("tool site forgery rejected without network", "GetSiteStatus",
        "{\"siteId\":\"spokane\",\"minutes\":30}", "site_forbidden"),
    ("unexpected tool argument rejected", "GetSiteStatus",
        "{\"siteId\":\"tacoma\",\"minutes\":30,\"admin\":true}", "invalid_tool_arguments"),
    ("specific device cannot be null", "GetEquipmentTelemetry",
        "{\"siteId\":\"tacoma\",\"deviceId\":null,\"minutes\":30}", "invalid_tool_arguments"),
    ("array arguments rejected before network", "GetSiteStatus", "[]", "invalid_tool_arguments"),
    ("nonstring site rejected before network", "GetSiteStatus",
        "{\"siteId\":12,\"minutes\":30}", "invalid_tool_arguments"),
    ("fractional window rejected before network", "GetSiteStatus",
        "{\"siteId\":\"tacoma\",\"minutes\":1.5}", "invalid_tool_arguments"),
    ("oversize window rejected before retrieval", "GetSiteStatus",
        "{\"siteId\":\"tacoma\",\"minutes\":121}", "invalid_tool_arguments")
})
{
    try
    {
        await toolAgent.ExecuteToolAsync(toolCase.Item2, toolCase.Item3, user,
            new Dictionary<string, Evidence>(), CancellationToken.None);
        throw new InvalidOperationException($"{toolCase.Item1} failed.");
    }
    catch (ScenarioException error) { Check(toolCase.Item1, error.Code == toolCase.Item4); }
}
var cacheBudget = new TelemetryCacheBudget();
Reject("cache rejects estimates above 512 MiB", () =>
{
    for (int index = 0; index < 600_000; index++) cacheBudget.Add(Event(1));
}, "cache_limit");
var large = Enumerable.Range(0, 120_000).Select(index => Event(index % 120, 4.2, $"fleet-{index}")).ToArray();
var timer = Stopwatch.StartNew();
var fleet = TelemetryEngine.Summarize(inventory, large, user, new("tacoma", "tacoma-pump-01", 120), now, 0);
timer.Stop();
Check("120k-event deterministic aggregate under 30s", fleet.Equipment.Single().Count == 120_000 && timer.Elapsed.TotalSeconds < 30);
Console.WriteLine($"120k-event elapsed milliseconds: {timer.Elapsed.TotalMilliseconds:F1}");

var listener = new TcpListener(IPAddress.Loopback, 0);
listener.Start();
var port = ((IPEndPoint)listener.LocalEndpoint).Port;
listener.Stop();
var dll = Path.Combine(webRoot, "bin", "Debug", "net10.0", "EquipAI.Web.dll");
var start = new ProcessStartInfo("dotnet")
{
    WorkingDirectory = webRoot, UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true
};
start.ArgumentList.Add(dll);
start.ArgumentList.Add("--urls");
start.ArgumentList.Add($"http://127.0.0.1:{port}");
start.Environment["Entra__TenantId"] = string.Empty;
start.Environment["Entra__ApiClientId"] = string.Empty;
start.Environment["Entra__SpaClientId"] = string.Empty;
start.Environment["WorkerRole"] = "web";
start.Environment["StorageEndpoint"] = string.Empty;
using var server = Process.Start(start) ?? throw new InvalidOperationException("Could not start owned local web process.");
var output = server.StandardOutput.ReadToEndAsync();
var errors = server.StandardError.ReadToEndAsync();
try
{
    using var http = new HttpClient { BaseAddress = new Uri($"http://127.0.0.1:{port}"), Timeout = TimeSpan.FromSeconds(3) };
    bool ready = false;
    for (int attempt = 0; attempt < 50; attempt++)
    {
        if (server.HasExited) throw new InvalidOperationException($"Server exited: {await errors}");
        try { ready = (await http.GetAsync("/health")).IsSuccessStatusCode; }
        catch (HttpRequestException) { }
        if (ready) break;
        await Task.Delay(100);
    }
    Check("owned loopback server responds", ready);
    var homeResponse = await http.GetAsync("/");
    Check("branded Razor homepage", homeResponse.IsSuccessStatusCode &&
        (await homeResponse.Content.ReadAsStringAsync()).Contains("Adatum Corporation"));
    Check("CSP and no-store headers", homeResponse.Headers.Contains("Content-Security-Policy") &&
        homeResponse.Headers.CacheControl?.NoStore == true);
    Check("unauthenticated equipment is 401", (await http.GetAsync("/api/equipment")).StatusCode == HttpStatusCode.Unauthorized);
    Check("unauthenticated evidence is 401", (await http.GetAsync("/api/evidence/tacoma/tacoma-pump-01")).StatusCode ==
        HttpStatusCode.Unauthorized);
    Check("unauthenticated chat is 401", (await http.PostAsync("/api/chat", new StringContent(
        "{\"question\":\"status\"}", Encoding.UTF8, "application/json"))).StatusCode == HttpStatusCode.Unauthorized);
    using var playwright = await Playwright.CreateAsync();
    await using var browser = await playwright.Chromium.LaunchAsync(new()
    {
        Headless = true, ExecutablePath = Environment.GetEnvironmentVariable("EQUIP_BROWSER")
            ?? throw new ArgumentException("Set EQUIP_BROWSER to the approved existing Chromium executable.")
    });
    var page = await browser.NewPageAsync();
    await page.GotoAsync(http.BaseAddress.ToString());
    await page.GetByText("Local account storage is missing.", new() { Exact = false }).WaitForAsync();
    Check("missing configuration visibly disables sign-in", await page.Locator("#login").IsDisabledAsync());
    Check("missing configuration disables agent submission", await page.Locator("#send").IsDisabledAsync());
    foreach (var width in new[] { 1440, 390 })
    {
        await page.SetViewportSizeAsync(width, 900);
        Check($"no horizontal overflow at {width}px", await page.EvaluateAsync<bool>(
            "document.documentElement.scrollWidth <= window.innerWidth"));
        await page.ScreenshotAsync(new() { Path = Path.Combine(workspace, "local-evidence", $"shell-{width}.png"), FullPage = true });
    }
}
finally
{
    if (!server.HasExited) server.Kill(entireProcessTree: true);
    await server.WaitForExitAsync();
    Console.WriteLine(await output);
    Console.Error.WriteLine(await errors);
}
Directory.CreateDirectory(Path.Combine(workspace, "local-evidence"));
File.WriteAllText(Path.Combine(workspace, "local-evidence", "application-checks.json"),
    JsonSerializer.Serialize(new { checkedAtUtc = DateTimeOffset.UtcNow, passed, checks = results,
        largeFixtureElapsedMs = timer.Elapsed.TotalMilliseconds, liveAzureTested = false },
        new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"{passed} local checks passed; no live Azure calls or inference performed.");

internal sealed class LabTestClock(DateTimeOffset initial) : TimeProvider
{
    internal DateTimeOffset Now { get; set; } = initial;
    /// <inheritdoc />
    public override DateTimeOffset GetUtcNow() => Now;
}

internal sealed class LabTestAccounts(LabAccount initial) : ILabAccounts
{
    internal LabAccount Account { get; set; } = initial;
    private int version;
    /// <inheritdoc />
    public Task<AccountRow?> ReadAsync(string username, CancellationToken token) => Task.FromResult(
        username == Account.Username ? new AccountRow(Account, new ETag(version.ToString())) : null);
    /// <inheritdoc />
    public Task ReplaceAsync(LabAccount account, ETag etag, CancellationToken token)
    {
        if (etag != new ETag(version.ToString())) throw new RequestFailedException(412, "Concurrent account update.");
        Account = account;
        version++;
        return Task.CompletedTask;
    }
}
