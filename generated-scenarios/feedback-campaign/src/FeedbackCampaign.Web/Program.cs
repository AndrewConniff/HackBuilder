using System.Security.Claims;
using System.Threading.RateLimiting;
using Azure.Core;
using Azure.Identity;
using FeedbackCampaign.Web;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.RateLimiting;

if (args.FirstOrDefault() == "--provision-lab-accounts")
{
    await LabAccountProvisioner.Run(args);
    return;
}

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddRazorPages();
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton<LabAuthentication>();
builder.Services.AddScoped<LabCookieEvents>();
var keyDirectory = string.IsNullOrEmpty(Environment.GetEnvironmentVariable("WEBSITE_INSTANCE_ID"))
    ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FeedbackCampaign", "keys")
    : Path.Combine(Environment.GetEnvironmentVariable("HOME")
        ?? throw new InvalidOperationException("App Service HOME is required for persistent session protection."), "data", "feedback-campaign-keys");
builder.Services.AddDataProtection().SetApplicationName("feedback-campaign-lab")
    .PersistKeysToFileSystem(new DirectoryInfo(keyDirectory));
builder.Services.AddAuthentication(LabAuthentication.Scheme).AddCookie(options =>
{
    options.LoginPath = "/Login";
    options.Cookie.Name = "__Host-FeedbackCampaign";
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.ExpireTimeSpan = TimeSpan.FromHours(4);
    options.SlidingExpiration = false;
    options.EventsType = typeof(LabCookieEvents);
});
builder.Services.AddAuthorization();
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-CSRF-TOKEN";
    options.Cookie.Name = "__Host-FeedbackCampaign-CSRF";
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
});
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
        context.Request.Path.Equals("/Login") && HttpMethods.IsPost(context.Request.Method)
            ? RateLimitPartition.GetFixedWindowLimiter(context.Connection.RemoteIpAddress?.ToString() ?? "unresolved-client",
                _ => new FixedWindowRateLimiterOptions { PermitLimit = 30, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 })
            : RateLimitPartition.GetNoLimiter("other"));
});
builder.Services.AddApplicationInsightsTelemetry();
builder.Services.AddSingleton<TokenCredential, ManagedIdentityCredential>();
builder.Services.AddSingleton<IStateStore, TableStateStore>();
builder.Services.AddSingleton<RuleService>();
builder.Services.AddSingleton<IFoundryAgent, FoundryAgent>();
builder.Services.AddSingleton<CampaignWorkflow>();
builder.Services.AddHttpClient("foundry", c => c.Timeout = TimeSpan.FromSeconds(65));
builder.Services.AddHostedService<QueueWorker>();
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 32768);
var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'";
    context.Response.Headers["Cache-Control"] = "no-store";
    if (!context.Request.Path.StartsWithSegments("/api")) { await next(); return; }
    try
    {
        if (context.User.Identity?.IsAuthenticated != true) { context.Response.StatusCode = 401; return; }
        if (HttpMethods.IsPost(context.Request.Method)
            && context.Request.Headers.Origin != $"{context.Request.Scheme}://{context.Request.Host}")
        { context.Response.StatusCode = 403; return; }
        if (HttpMethods.IsPost(context.Request.Method))
            await context.RequestServices.GetRequiredService<IAntiforgery>().ValidateRequestAsync(context);
        await next();
    }
    catch (AntiforgeryValidationException) { context.Response.StatusCode = 403; }
    catch (UnauthorizedAccessException) { context.Response.StatusCode = 403; }
    catch (ArgumentException ex) { context.Response.StatusCode = 400; await context.Response.WriteAsJsonAsync(new { error = ex.Message }); }
    catch (InvalidOperationException) { context.Response.StatusCode = 409; await context.Response.WriteAsJsonAsync(new { error = "Operation conflicts with current state or configuration; inspect service readiness." }); }
    catch (Azure.RequestFailedException ex) when (ex.Status == 412)
    { context.Response.StatusCode = 409; await context.Response.WriteAsJsonAsync(new { error = "Stale revision; refresh before retry." }); }
    catch (Exception error)
    {
        app.Logger.LogError("API dependency failed: {Category}", error.GetType().Name);
        context.Response.StatusCode = 503;
        await context.Response.WriteAsJsonAsync(new { error = "Dependency unavailable; no success was recorded." });
    }
});
app.UseStaticFiles();
app.MapRazorPages();
app.MapGet("/health", (IConfiguration config) => Results.Json(new
{
    configured = new[] { "TABLE_ENDPOINT", "SERVICEBUS_NAMESPACE", "FOUNDRY_PROJECT_ENDPOINT" }.All(k => !string.IsNullOrWhiteSpace(config[k])),
    runtimeValidated = false // Configuration is never a runtime acceptance receipt.
}));
app.MapGet("/api/me", (HttpContext ctx) => new { name = ctx.User.Identity!.Name, roles = ctx.User.FindAll(ClaimTypes.Role).Select(c => c.Value) });
app.MapGet("/api/csrf", (HttpContext ctx, IAntiforgery antiforgery) =>
    new { token = antiforgery.GetAndStoreTokens(ctx).RequestToken });
app.MapPost("/api/logout", async (HttpContext ctx) =>
{
    await ctx.SignOutAsync(LabAuthentication.Scheme);
    return Results.Ok(new { signedOut = true });
});
app.MapGet("/api/cases", async (HttpContext ctx, IStateStore store) =>
{
    PlatformPrincipal.RequireAny(ctx, "CampaignOperator", "ProductManager", "ConflictResolutionSpecialist");
    var cases = await store.List<Case>("cases");
    return cases.Where(c => ctx.User.IsInRole("CampaignOperator") || ctx.User.IsInRole(c.Value.Owner)).Take(200);
});
app.MapPost("/api/posts", async (Post post, HttpContext ctx, CampaignWorkflow workflow) =>
{
    PlatformPrincipal.RequireAny(ctx, "CampaignOperator");
    return await workflow.Submit(post, ctx.User.Identity!.Name!);
});
app.MapPost("/api/cases/{id}/review", async (string id, ReviewRequest request, HttpContext ctx, CampaignWorkflow workflow) =>
{
    await workflow.Review(id, request.ETag, request.Reply, ctx.User.Identity!.Name!,
        ctx.User.FindAll(ClaimTypes.Role).Select(c => c.Value).ToArray());
    return Results.Accepted();
});
app.MapPost("/api/cases/{id}/retry", async (string id, Revision request, HttpContext ctx, CampaignWorkflow workflow) =>
{
    PlatformPrincipal.RequireAny(ctx, "CampaignOperator");
    await workflow.Retry(id, request.ETag, ctx.User.Identity!.Name!);
    return Results.Accepted();
});
app.MapGet("/api/rules", async (HttpContext ctx, IStateStore store) =>
{
    PlatformPrincipal.RequireAny(ctx, "CampaignOperator", "ControlAdmin", "ProductManager", "ConflictResolutionSpecialist");
    return new { active = await store.Get<ActiveRules>("config", "active"), versions = await store.List<Rules>("rules") };
});
app.MapPost("/api/rules", async (Rules request, HttpContext ctx, RuleService rules) =>
{
    PlatformPrincipal.RequireAny(ctx, "ControlAdmin");
    await rules.Save(request with { Author = ctx.User.Identity!.Name! });
    return Results.Created();
});
app.MapPost("/api/rules/promote", async (Promotion request, HttpContext ctx, RuleService rules) =>
{
    PlatformPrincipal.RequireAny(ctx, "ControlAdmin");
    await rules.Promote(request.Version, ctx.User.Identity!.Name!, request.Reason, request.ETag);
    return Results.Accepted();
});
app.MapPost("/api/chat", async (ChatRequest request, HttpContext ctx, IFoundryAgent agent, CancellationToken ct) =>
{
    PlatformPrincipal.RequireAny(ctx, "CampaignOperator", "ProductManager", "ConflictResolutionSpecialist");
    if (string.IsNullOrWhiteSpace(request.Message) || request.Message.Length > 2000) throw new ArgumentException("Chat requires 1-2000 characters.");
    var response = await agent.Chat(request.Message, ct);
    return new { response.Text, response.ResponseId, grounding = "campaign-policy-v1" };
});
app.Run();

public sealed record ReviewRequest(string ETag, string Reply);
public sealed record Revision(string ETag);
public sealed record Promotion(string Version, string Reason, string ETag);
public sealed record ChatRequest(string Message);
public partial class Program;

public static class PlatformPrincipal
{
    public static void RequireAny(HttpContext ctx, params string[] roles)
    {
        if (!roles.Any(ctx.User.IsInRole)) throw new UnauthorizedAccessException();
    }
}
