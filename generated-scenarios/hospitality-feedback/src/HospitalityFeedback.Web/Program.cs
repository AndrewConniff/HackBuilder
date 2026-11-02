using System.Security.Claims;
using System.Threading.RateLimiting;
using Azure.Core;
using Azure.Identity;
using HospitalityFeedback.Web.Models;
using HospitalityFeedback.Web.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
var settings = builder.Configuration.GetSection("Feedback").Get<FeedbackOptions>() ?? new();
var local = builder.Environment.IsDevelopment() && settings.UseAzurite && settings.LocalAnonymous;
if ((settings.UseAzurite || settings.LocalAnonymous) && !builder.Environment.IsDevelopment())
    throw new ConfigurationException("Azurite and anonymous mode are Development-only.");
if (settings.MaxEvidenceRecords is < 1 or > 100 || settings.MaxDeliveryAttempts is < 1 or > 10)
    throw new ConfigurationException("Invalid evidence or delivery limits.");
if (!local && (string.IsNullOrWhiteSpace(settings.TenantId) || string.IsNullOrWhiteSpace(settings.Audience)
    || settings.OperatorObjectIds.Length == 0))
    throw new ConfigurationException("Configure tenant, API audience and operator object IDs.");

builder.Services.AddSingleton(settings);
builder.Services.AddSingleton<TokenCredential>(_ => builder.Environment.IsDevelopment()
    ? new DefaultAzureCredential()
    : new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(
        builder.Configuration["AZURE_CLIENT_ID"]
        ?? throw new ConfigurationException("Configure AZURE_CLIENT_ID for the runtime identity."))));
builder.Services.AddSingleton<StorageRepository>();
builder.Services.AddHttpClient<FoundryAgent>(c => c.Timeout = TimeSpan.FromSeconds(75));
builder.Services.AddHostedService<QueueWorker>();
builder.Services.AddRazorPages();
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(o =>
{
    o.Authority = $"https://login.microsoftonline.com/{settings.TenantId}/v2.0";
    o.Audience = settings.Audience;
    o.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true, ValidateAudience = true, ValidateLifetime = true,
        NameClaimType = "oid", RoleClaimType = "roles"
    };
    o.MapInboundClaims = false;
});
builder.Services.AddAuthorization(o => o.AddPolicy("operator", p =>
{
    p.RequireAuthenticatedUser();
    p.RequireAssertion(c => c.User.FindFirstValue("tid") == settings.TenantId
        && settings.OperatorObjectIds.Contains(c.User.FindFirstValue("oid"), StringComparer.OrdinalIgnoreCase)
        && (c.User.FindFirstValue("scp")?.Split(' ').Contains("access_as_user") == true
            || c.User.IsInRole("Feedback.Operator")));
}));
builder.Services.AddRateLimiter(o =>
{
    o.RejectionStatusCode = 429;
    o.AddPolicy("chat", context => RateLimitPartition.GetFixedWindowLimiter(
        context.User.FindFirstValue("oid") ?? "local", _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0
        }));
});
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 32768);
var app = builder.Build();

if (args.Contains("--setup-agent") || args.Contains("--probe-model"))
{
    var agent = app.Services.GetRequiredService<FoundryAgent>();
    if (args.Contains("--setup-agent"))
    {
        await agent.EnsureAgentAsync(CancellationToken.None);
        Console.WriteLine($"Agent ready: {settings.AgentName}");
    }
    else Console.WriteLine(await agent.ProbeModelAsync(CancellationToken.None));
    return;
}

app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'";
    if (context.Request.Path.StartsWithSegments("/api")) context.Response.Headers.CacheControl = "no-store";
    if (local && context.Connection.RemoteIpAddress is { } ip && !System.Net.IPAddress.IsLoopback(ip))
    {
        context.Response.StatusCode = 403;
        return;
    }
    try { await next(); }
    catch (InputException ex)
    {
        context.Response.StatusCode = 400;
        await context.Response.WriteAsJsonAsync(new { error = ex.Code, detail = ex.Message });
    }
    catch (ConflictException)
    {
        context.Response.StatusCode = 409;
        await context.Response.WriteAsJsonAsync(new { error = "payload_conflict" });
    }
    catch (GroundingException)
    {
        context.Response.StatusCode = 502;
        await context.Response.WriteAsJsonAsync(new { error = "ungrounded_or_incomplete_agent_response" });
    }
    catch (Exception ex) when (ex is ConfigurationException or Azure.RequestFailedException
        or HttpRequestException or Azure.Identity.AuthenticationFailedException or TaskCanceledException)
    {
        app.Logger.LogWarning("Request dependency failed: {Type}.", ex.GetType().Name);
        context.Response.StatusCode = 503;
        await context.Response.WriteAsJsonAsync(new { error = "dependency_unavailable", mockFallback = false });
    }
});
if (!app.Environment.IsDevelopment()) app.UseHsts();
app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
app.MapRazorPages();
var api = app.MapGroup("/api");
if (!local) api.RequireAuthorization("operator");

api.MapPost("/feedback", async (FeedbackInput input, StorageRepository store, CancellationToken ct) =>
    Results.Accepted($"/api/status/{input.FeedbackId}", await store.IngestAsync(input, ct)));
api.MapGet("/status", async (StorageRepository store, CancellationToken ct) => await store.StatusAsync(ct));
api.MapGet("/status/{id}", async (string id, StorageRepository store, CancellationToken ct) =>
{
    if (!Rules.ValidId(id)) throw new InputException("invalid_id", "Invalid feedback ID.");
    var raw = await StorageRepository.ReadAsync<RawFeedback>(store.Raw.GetBlobClient(id + ".json"), ct);
    if (raw is null) return Results.NotFound();
    return Results.Ok(await StorageRepository.ReadAsync<ProcessingStatus>(store.Status.GetBlobClient(id + ".json"), ct)
        ?? new ProcessingStatus(id, raw.CorrelationId, "queued", raw.ReceivedAt, 0));
});
api.MapGet("/evidence/{id}", async (string id, StorageRepository store, CancellationToken ct) =>
{
    if (!Rules.ValidId(id)) throw new InputException("invalid_id", "Invalid feedback ID.");
    var result = await StorageRepository.ReadAsync<Evidence>(store.Processed.GetBlobClient(id + ".json"), ct);
    return result is null ? Results.NotFound() : Results.Ok(result);
});
api.MapPost("/chat", async (ChatRequest request, StorageRepository store, FoundryAgent agent, CancellationToken ct) =>
{
    Rules.Validate(request);
    var evidence = await store.EvidenceAsync(request, ct);
    var result = await agent.ChatAsync(request, evidence, ct);
    await StorageRepository.WriteAsync(store.Audit.GetBlobClient("chat-" + Guid.NewGuid().ToString("N") + ".json"),
        new { result.AgentName, result.ResponseId, result.EvidenceScope, result.CheckedAtUtc,
            CitationIds = result.Result.Citations.Select(c => c.FeedbackId), result.Result.InsufficientEvidence }, ct);
    return Results.Ok(result);
}).RequireRateLimiting("chat");
app.Run();

public partial class Program;
