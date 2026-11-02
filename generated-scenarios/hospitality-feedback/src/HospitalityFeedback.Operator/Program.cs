using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Azure.Core;
using Azure.Identity;

var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var guardStart = new ProcessStartInfo("python") { WorkingDirectory = root, UseShellExecute = false };
guardStart.ArgumentList.Add(Path.Combine(root, "scripts", "scenario_identity.py"));
guardStart.ArgumentList.Add("guard");
using (var guard = Process.Start(guardStart) ?? throw new InvalidOperationException("Cannot start consent guard."))
{
    await guard.WaitForExitAsync();
    if (guard.ExitCode != 0)
        throw new InvalidOperationException("Canonical exact-target authorization is required before operator sign-in.");
}
var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);
using var identity = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(root, ".local", "identity-outputs.json")));
using var scope = JsonDocument.Parse(identity.RootElement.GetProperty("scope").GetRawText());
var endpoint = Environment.GetEnvironmentVariable("SERVICE_WEB_ENDPOINT")
    ?? throw new InvalidOperationException("The deployed SERVICE_WEB_ENDPOINT output is required.");
var appName = Environment.GetEnvironmentVariable("AZURE_WEBAPP_NAME")
    ?? throw new InvalidOperationException("The deployed AZURE_WEBAPP_NAME output is required.");
if (!Uri.TryCreate(endpoint, UriKind.Absolute, out var uri) || uri.Scheme != "https"
    || uri.Host != $"{appName}.azurewebsites.net" || !uri.IsDefaultPort || uri.UserInfo.Length != 0)
    throw new InvalidOperationException("Authenticated operator validation requires the deployed HTTPS endpoint.");
using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(5));
var token = Environment.GetEnvironmentVariable("FEEDBACK_API_TOKEN");
if (string.IsNullOrWhiteSpace(token))
{
    if (!args.Contains("--interactive"))
        throw new InvalidOperationException(
            "Operator sign-in required. Run this helper with --interactive in an authorized interactive session, "
            + "or supply an approved FEEDBACK_API_TOKEN to the deployment process. No token is logged or persisted.");
    var credential = new InteractiveBrowserCredential(new InteractiveBrowserCredentialOptions
    {
        TenantId = scope.RootElement.GetProperty("tenantId").GetString(),
        ClientId = identity.RootElement.GetProperty("operatorClientId").GetString(),
        RedirectUri = new Uri("http://localhost"),
        DisableAutomaticAuthentication = false
    });
    var delegatedScope = identity.RootElement.GetProperty("delegatedScope").GetString()
        ?? throw new InvalidOperationException("Installed delegated scope is missing.");
    token = (await credential.GetTokenAsync(new TokenRequestContext([delegatedScope]), timeout.Token)).Token;
}
using var handler = new HttpClientHandler { AllowAutoRedirect = false };
using var client = new HttpClient(handler) { BaseAddress = uri, Timeout = TimeSpan.FromSeconds(90) };
client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
using var fixtures = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(root, "data", "feedback.json")));
foreach (var fixture in fixtures.RootElement.EnumerateArray())
{
    using var accepted = await client.PostAsJsonAsync("/api/feedback", fixture, timeout.Token);
    if (accepted.StatusCode != HttpStatusCode.Accepted)
        throw new InvalidOperationException($"Fixture ingestion failed: {(int)accepted.StatusCode}");
}
var deadline = DateTimeOffset.UtcNow.AddSeconds(75);
while (true)
{
    using var statuses = await client.GetAsync("/api/status", timeout.Token);
    statuses.EnsureSuccessStatusCode();
    using var body = JsonDocument.Parse(await statuses.Content.ReadAsStringAsync(timeout.Token));
    var completed = body.RootElement.EnumerateArray()
        .Where(s => s.GetProperty("state").GetString() == "completed")
        .Select(s => s.GetProperty("feedbackId").GetString()).ToHashSet();
    if (fixtures.RootElement.EnumerateArray().All(f => completed.Contains(f.GetProperty("feedbackId").GetString())))
        break;
    if (DateTimeOffset.UtcNow >= deadline)
        throw new InvalidOperationException("Not all fixtures completed within 75 seconds.");
    await Task.Delay(500, timeout.Token);
}
foreach (var fixture in fixtures.RootElement.EnumerateArray())
{
    var id = fixture.GetProperty("feedbackId").GetString();
    using var evidence = await client.GetAsync($"/api/evidence/{id}", timeout.Token);
    evidence.EnsureSuccessStatusCode();
    using var body = JsonDocument.Parse(await evidence.Content.ReadAsStringAsync(timeout.Token));
    var actual = body.RootElement.GetProperty("feedback");
    foreach (var field in new[] { "feedbackId", "guestId", "guestName", "text", "language" })
        if (actual.GetProperty(field).GetString() != fixture.GetProperty(field).GetString())
            throw new InvalidOperationException($"Original-language/provenance mismatch: {id}/{field}");
}
using var positive = await client.PostAsJsonAsync("/api/chat", new
{
    question = "Compare housekeeping, check-in, noise, breakfast and staff-service feedback. "
        + "Recommend specific operational improvements with original-language source excerpts.",
    responseLanguage = "en"
}, timeout.Token);
positive.EnsureSuccessStatusCode();
using var grounded = JsonDocument.Parse(await positive.Content.ReadAsStringAsync(timeout.Token));
if (grounded.RootElement.GetProperty("result").GetProperty("citations").GetArrayLength() == 0)
    throw new InvalidOperationException("Grounded application chat returned no citations.");
using var negative = await client.PostAsJsonAsync("/api/chat", new
{
    question = "What were the hotel's occupancy rate and revenue last month?", responseLanguage = "en"
}, timeout.Token);
negative.EnsureSuccessStatusCode();
using var unsupported = JsonDocument.Parse(await negative.Content.ReadAsStringAsync(timeout.Token));
if (!unsupported.RootElement.GetProperty("result").GetProperty("insufficientEvidence").GetBoolean())
    throw new InvalidOperationException("Unsupported occupancy/revenue question was not refused.");
using var anonymous = new HttpClient { BaseAddress = uri };
using var denied = await anonymous.GetAsync("/api/status", timeout.Token);
if (denied.StatusCode != HttpStatusCode.Unauthorized)
    throw new InvalidOperationException("Anonymous API access was not denied with HTTP 401.");
var report = new
{
    scope = "authenticated_reference_installation_smoke_only", checkedAtUtc = DateTimeOffset.UtcNow,
    applicationUrl = uri.ToString(), fixturesCompleted = 12,
    checks = new { ingestion = true, originalLanguageAndProvenance = true, agentApplicationChat = true,
        unsupportedMetricsRefused = true, anonymousDenied = true },
    independentModelProbe = false, fullRuntimeAcceptance = false,
    limitation = "Review actual semantic grounding and independent model inference separately; no suitability approval.",
    positive = grounded.RootElement.Clone(), negative = unsupported.RootElement.Clone()
};
await File.WriteAllTextAsync(Path.Combine(root, "evidence", "reference-installation-smoke.json"),
    JsonSerializer.Serialize(report, new JsonSerializerOptions(options) { WriteIndented = true }) + "\n");
Console.WriteLine("Authenticated reference installation smoke passed; complete live acceptance is still required.");
