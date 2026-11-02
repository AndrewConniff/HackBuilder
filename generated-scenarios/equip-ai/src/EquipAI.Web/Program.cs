using System.Security.Claims;
using System.Threading.RateLimiting;
using Azure;
using Azure.Identity;
using Azure.Storage.Blobs;
using EquipAI.Web.Models;
using EquipAI.Web.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.DataProtection.KeyManagement;
using Microsoft.AspNetCore.RateLimiting;

string[] installationModes = ["--prepare-accounts", "--install-accounts", "--reset-lockout",
    "--install-agent", "--probe-agent", "--publish-device", "--prepare-device"];
if (args.Count(argument => installationModes.Contains(argument)) > 1)
    throw new ArgumentException("Select only one installation operation.");
var builder = WebApplication.CreateBuilder(args.Where(argument => !installationModes.Contains(argument)).ToArray());
builder.Logging.AddFilter("Azure", LogLevel.Warning);
builder.Logging.AddFilter("System.ClientModel", LogLevel.Warning);
builder.Logging.AddFilter("Microsoft.AspNetCore", LogLevel.Warning);
if (args.Contains("--prepare-accounts"))
{
    LabAuthentication.PrepareAccess(builder.Configuration);
    return;
}
if (args.Contains("--install-accounts"))
{
    await AwaitInstallationRbacAsync(() => new BlobLabAccounts(builder.Configuration).InstallAsync(
        AgentContract.Required(builder.Configuration, "AccountSeed"), CancellationToken.None));
    return;
}
if (args.Contains("--reset-lockout"))
{
    await new BlobLabAccounts(builder.Configuration).ResetLockoutAsync(
        AgentContract.Required(builder.Configuration, "Username"), CancellationToken.None);
    return;
}
if (args.Contains("--install-agent"))
{
    await AwaitInstallationRbacAsync(() => AgentContract.InstallAsync(builder.Configuration, CancellationToken.None));
    return;
}
if (args.Contains("--probe-agent"))
{
    await AgentContract.ProbeAsync(builder.Configuration, CancellationToken.None);
    return;
}
if (args.Contains("--publish-device"))
{
    await DevicePublisher.PublishAsync(builder.Configuration, CancellationToken.None);
    return;
}
if (args.Contains("--prepare-device"))
{
    DevicePublisher.Prepare(builder.Configuration);
    return;
}

builder.Services.AddRazorPages();
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddSingleton(new Inventory(builder.Environment.ContentRootPath));
builder.Services.AddSingleton(service => new BlobServiceClient(
    new Uri(AgentContract.Required(builder.Configuration, "StorageEndpoint")), new DefaultAzureCredential())
    .GetBlobContainerClient("telemetry"));
builder.Services.AddSingleton<BlobTelemetry>();
builder.Services.AddSingleton<FoundryAgent>();
builder.Services.AddSingleton<BlobLabAccounts>();
builder.Services.AddSingleton<ILabAccounts>(services => services.GetRequiredService<BlobLabAccounts>());
builder.Services.AddSingleton<LabAuthentication>();
builder.Services.AddScoped<LabCookieEvents>();
builder.Services.AddDataProtection().SetApplicationName("equip-ai-local-accounts");
builder.Services.AddOptions<KeyManagementOptions>().Configure<BlobLabAccounts>((options, store) =>
    options.XmlRepository = store);
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-CSRF-TOKEN";
    options.Cookie.SecurePolicy = builder.Environment.IsDevelopment()
        ? CookieSecurePolicy.SameAsRequest : CookieSecurePolicy.Always;
});
builder.Services.AddAuthentication(LabAuthentication.Scheme).AddCookie(options =>
{
    options.Cookie.Name = "__Host-EquipAI";
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.ExpireTimeSpan = TimeSpan.FromHours(2);
    options.SlidingExpiration = false;
    options.EventsType = typeof(LabCookieEvents);
});
builder.Services.AddAuthorization(options => options.AddPolicy("Operations", policy =>
    policy.RequireAuthenticatedUser().RequireRole("Operations.Tacoma", "Operations.Statewide")));
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.AddPolicy("questions", context => RateLimitPartition.GetFixedWindowLimiter(
        context.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? context.Connection.RemoteIpAddress?.ToString() ?? "anonymous",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
    options.AddPolicy("login", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "anonymous",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 20, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 8192);
if (builder.Configuration["WorkerRole"] == "cleaner") builder.Services.AddHostedService<CleanupWorker>();
var app = builder.Build();
var buildId = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(
    File.ReadAllBytes(typeof(FoundryAgent).Assembly.Location)));
app.Use(async (context, next) =>
{
    context.Response.Headers.CacheControl = "no-store";
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; " +
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'";
    try { await next(context); }
    catch (ScenarioException error)
    {
        app.Logger.LogWarning("Request rejected: {Code}; correlation {Correlation}", error.Code, context.TraceIdentifier);
        context.Response.StatusCode = error.Status;
        await context.Response.WriteAsJsonAsync(new { error = error.Code, message = error.Message, correlationId = context.TraceIdentifier });
    }
    catch (Exception error) when (error is RequestFailedException or System.ClientModel.ClientResultException or
        Azure.Identity.AuthenticationFailedException or System.Text.Json.JsonException or OperationCanceledException)
    {
        int? dependencyStatus = error switch
        {
            RequestFailedException azure => azure.Status,
            System.ClientModel.ClientResultException client => client.Status,
            _ => null
        };
        app.Logger.LogError("Dependency/response failure: {Type}; HTTP {Status}; code {Code}; correlation {Correlation}",
            error.GetType().Name, dependencyStatus, DependencyCode(error), context.TraceIdentifier);
        context.Response.StatusCode = error is OperationCanceledException ? 504 : 502;
        await context.Response.WriteAsJsonAsync(new
        {
            error = "dependency_failure", message = "The request could not be completed; no equipment status is implied.",
            correlationId = context.TraceIdentifier
        });
    }
});
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
if (builder.Configuration["WorkerRole"] == "cleaner")
{
    app.MapGet("/health", () => Results.Ok(new { status = "process-running", role = "cleaner", buildId }));
}
else
{
    app.UseStaticFiles();
    app.MapRazorPages();
    app.MapGet("/health", () => Results.Ok(new
    {
        status = "process-running", cloudValidated = false, buildId,
        agentVersion = builder.Configuration["AgentVersion"]
    }));
    app.MapGet("/api/config", (HttpContext context, IAntiforgery antiforgery) => new
    {
        authentication = "local", configured = !string.IsNullOrEmpty(builder.Configuration["StorageEndpoint"]),
        authenticated = context.User.Identity?.IsAuthenticated == true,
        username = context.User.Identity?.Name,
        roles = context.User.FindAll(ClaimTypes.Role).Select(claim => claim.Value).ToArray(),
        csrfToken = string.IsNullOrEmpty(builder.Configuration["StorageEndpoint"])
            ? null : antiforgery.GetAndStoreTokens(context).RequestToken
    });
    app.MapPost("/api/login", async (LoginRequest request, HttpContext context,
        IAntiforgery antiforgery, LabAuthentication authentication) =>
    {
        await ValidateCsrfAsync(context, antiforgery);
        var principal = await authentication.AuthenticateAsync(request.Username, request.Password, context.RequestAborted);
        if (principal is null)
        {
            app.Logger.LogWarning("Local sign-in rejected; correlation {Correlation}", context.TraceIdentifier);
            throw new ScenarioException("login_failed", "Invalid credentials or account temporarily locked.", 401);
        }
        await context.SignInAsync(LabAuthentication.Scheme, principal);
        return Results.Ok(new { authenticated = true });
    }).RequireRateLimiting("login");
    app.MapPost("/api/logout", async (HttpContext context, IAntiforgery antiforgery) =>
    {
        await ValidateCsrfAsync(context, antiforgery);
        await context.SignOutAsync(LabAuthentication.Scheme);
        return Results.Ok(new { authenticated = false });
    }).RequireAuthorization("Operations");
    app.MapGet("/api/equipment", (ClaimsPrincipal user, Inventory inventory) =>
        inventory.Equipment.Where(e => SiteAccess.Sites(user).Contains(e.SiteId))).RequireAuthorization("Operations");
    app.MapPost("/api/chat", async (ChatRequest request, ClaimsPrincipal user, FoundryAgent agent,
        HttpContext context, IAntiforgery antiforgery) =>
    {
        await ValidateCsrfAsync(context, antiforgery);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
        timeout.CancelAfter(TimeSpan.FromSeconds(30));
        return Results.Ok(await agent.AskAsync(request.Question, user, timeout.Token));
    }).RequireAuthorization("Operations").RequireRateLimiting("questions");
    app.MapGet("/api/evidence/{siteId}/{deviceId}", async (
        string siteId, string deviceId, ClaimsPrincipal user, Inventory inventory, BlobTelemetry blobs,
        TimeProvider clock, CancellationToken token) =>
    {
        SiteAccess.Require(user, siteId);
        var data = await blobs.ReadAsync(token);
        return TelemetryEngine.Summarize(inventory, data.Readings, user,
            new TelemetryQuery(siteId, deviceId, 120), clock.GetUtcNow(), data.Invalid, data.ExpiredByDevice);
    }).RequireAuthorization("Operations").RequireRateLimiting("questions");
}
app.Run();

static string DependencyCode(Exception error)
{
    if (error is RequestFailedException azure) return azure.ErrorCode ?? "unspecified";
    if (error is not System.ClientModel.ClientResultException client ||
        client.GetRawResponse()?.Content is not { } content) return "unavailable";
    try
    {
        using var document = System.Text.Json.JsonDocument.Parse(content.ToMemory());
        var root = document.RootElement;
        if (root.ValueKind == System.Text.Json.JsonValueKind.Object &&
            root.TryGetProperty("error", out var detail) && detail.ValueKind == System.Text.Json.JsonValueKind.Object &&
            detail.TryGetProperty("code", out var code) && code.ValueKind == System.Text.Json.JsonValueKind.String &&
            code.GetString() is { Length: > 0 and <= 80 } value &&
            value.All(character => char.IsAsciiLetterOrDigit(character) || character is '_' or '-' or '.'))
            return value;
        return "no_safe_error_code";
    }
    catch (System.Text.Json.JsonException)
    {
        var body = content.ToString();
        if (body.Contains("Virtual Network/Firewall", StringComparison.OrdinalIgnoreCase))
            return "network_firewall_denied";
        if (body.Contains("nginx", StringComparison.OrdinalIgnoreCase)) return "nginx_forbidden";
        return "non_json_dependency_error";
    }
}

static async Task AwaitInstallationRbacAsync(Func<Task> operation)
{
    for (int attempt = 0; ; attempt++)
    {
        try { await operation(); return; }
        catch (Exception error) when (attempt < 29 &&
            (error is RequestFailedException { Status: 401 or 403 } or
                System.ClientModel.ClientResultException { Status: 401 or 403 }))
        {
            Console.Error.WriteLine($"Installation data-plane authorization not effective yet; retry {attempt + 1}/29.");
            await Task.Delay(TimeSpan.FromSeconds(10));
        }
    }
}

static async Task ValidateCsrfAsync(HttpContext context, IAntiforgery antiforgery)
{
    if (!Uri.TryCreate(context.Request.Headers.Origin.ToString(), UriKind.Absolute, out var origin) ||
        !string.Equals(origin.Authority, context.Request.Host.Value, StringComparison.OrdinalIgnoreCase) ||
        origin.Scheme != "https")
        throw new ScenarioException("origin_forbidden", "A same-origin HTTPS request is required.", 403);
    try { await antiforgery.ValidateRequestAsync(context); }
    catch (AntiforgeryValidationException)
    {
        throw new ScenarioException("csrf_failed", "Refresh the page before submitting this request.", 403);
    }
}
