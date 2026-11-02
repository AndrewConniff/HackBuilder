using System.Security.Claims;
using System.Text.Json;
using System.Threading.RateLimiting;
using Azure;
using Azure.Core;
using Azure.Identity;
using Azure.Messaging.ServiceBus;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.DataProtection.KeyManagement;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Azure.Cosmos;
using Microsoft.IdentityModel.JsonWebTokens;
using Restaurant.Web.Models;
using Restaurant.Web.Services;

var builder = WebApplication.CreateBuilder(args);
var role = builder.Configuration["APP_ROLE"] ?? "web";
if (role is not ("web" or "chat" or "worker"))
    throw new InvalidOperationException("APP_ROLE must be web, chat or worker.");
var initialize = args.Contains("--initialize");
var importLegacy = args.Contains("--import-legacy");
builder.Services.AddSingleton<TimeProvider>(TimeProvider.System);
builder.Services.AddSingleton<TokenCredential>(_ => initialize || importLegacy
    ? new AzureCliCredential(new AzureCliCredentialOptions
    {
        TenantId = builder.Configuration["INITIALIZER_TENANT_ID"]
            ?? throw new InvalidOperationException("INITIALIZER_TENANT_ID is required for scoped initialization."),
        Subscription = builder.Configuration["INITIALIZER_SUBSCRIPTION_ID"]
            ?? throw new InvalidOperationException("INITIALIZER_SUBSCRIPTION_ID is required for scoped initialization.")
    })
    : new RuntimeIdentityCredential(builder.Configuration));
builder.Services.AddSingleton(service => new CosmosClient(
    !string.IsNullOrWhiteSpace(builder.Configuration["COSMOS_ENDPOINT"])
        ? builder.Configuration["COSMOS_ENDPOINT"] : throw new InvalidOperationException("COSMOS_ENDPOINT is required."),
    service.GetRequiredService<TokenCredential>(), new CosmosClientOptions
    { UseSystemTextJsonSerializerWithOptions = new JsonSerializerOptions(), MaxRetryAttemptsOnRateLimitedRequests = 3 }));
builder.Services.AddSingleton(service => new ServiceBusClient(
    builder.Configuration["SERVICE_BUS_NAMESPACE"] ?? throw new InvalidOperationException("SERVICE_BUS_NAMESPACE is required."),
    service.GetRequiredService<TokenCredential>()));
builder.Services.AddSingleton<CosmosStore>();
builder.Services.AddSingleton<RestaurantService>();
builder.Services.AddSingleton<OperationsService>();
builder.Services.AddSingleton<LegacyImport>();
builder.Services.AddSingleton<SessionTokens>();
var syntheticStaff = builder.Configuration["STAFF_AUTH_MODE"] == "synthetic-local";
if (syntheticStaff)
{
    _ = new StaffAuthentication(builder.Configuration, TimeProvider.System, builder.Environment);
    builder.Services.AddSingleton<StaffAuthentication>();
}
else if (builder.Configuration["STAFF_AUTH_MODE"] is { Length: > 0 } mode && mode != "entra")
    throw new InvalidOperationException("STAFF_AUTH_MODE must be entra or isolated synthetic-local.");
builder.Services.AddSingleton<AgentRuntime>();
builder.Services.AddMemoryCache();
builder.Services.AddHttpClient("internal", client => client.Timeout = TimeSpan.FromSeconds(30));
builder.Services.AddRazorPages();
builder.Services.AddAntiforgery(options => options.HeaderName = "X-CSRF-TOKEN");
var dataProtection = builder.Services.AddDataProtection().SetApplicationName("resto-scale-agent");
if (string.IsNullOrWhiteSpace(builder.Configuration["COSMOS_ENDPOINT"]))
    dataProtection.UseEphemeralDataProtectionProvider();
else
    builder.Services.AddOptions<KeyManagementOptions>().Configure<CosmosStore>((options, store) =>
        options.XmlRepository = new CosmosKeyRepository(store));
builder.Services.AddProblemDetails();
var authentication = builder.Services.AddAuthentication("caller")
    .AddPolicyScheme("caller", "Verified restaurant caller", options =>
    {
        options.ForwardDefaultSelector = context =>
        {
            var proof = context.Request.Headers.Authorization.ToString();
            if (proof.StartsWith("Bearer ", StringComparison.Ordinal))
            {
                var token = proof[7..];
                var handler = new JsonWebTokenHandler();
                return handler.CanReadToken(token) && handler.ReadJsonWebToken(token).Issuer == "fourth-coffee-guest"
                    ? "guest" : "staff";
            }
            return context.Request.Cookies.ContainsKey(StaffAuthentication.CookieName) ? "staff" : "guest";
        };
    })
    .AddScheme<AuthenticationSchemeOptions, GuestAuthenticationHandler>("guest", _ => { });
if (syntheticStaff)
    authentication.AddScheme<AuthenticationSchemeOptions, StaffAuthenticationHandler>("staff", _ => { });
else
    authentication.AddJwtBearer("staff", options => EntraStaffAuthentication.Configure(options, builder.Configuration));
builder.Services.AddAuthorization();
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.AddPolicy("entry", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new() { PermitLimit = 12, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
    options.AddPolicy("reservation", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new() { PermitLimit = 600, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
    if (role == "chat")
        options.GlobalLimiter = PartitionedRateLimiter.CreateChained(
            PartitionedRateLimiter.Create<HttpContext, string>(context => context.Request.Path == "/api/chat"
                ? RateLimitPartition.GetFixedWindowLimiter("chat", _ => new()
                    { PermitLimit = 2, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 })
                : RateLimitPartition.GetNoLimiter("other")),
            PartitionedRateLimiter.Create<HttpContext, string>(context => context.Request.Path == "/api/chat"
                ? RateLimitPartition.GetConcurrencyLimiter("chat", _ => new()
                    { PermitLimit = 1, QueueLimit = 1, QueueProcessingOrder = QueueProcessingOrder.OldestFirst })
                : RateLimitPartition.GetNoLimiter("other")));
});
if (!string.IsNullOrWhiteSpace(builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"]))
{
    builder.Services.AddApplicationInsightsTelemetry();
    builder.Services.AddOptions<Microsoft.ApplicationInsights.AspNetCore.Extensions.ApplicationInsightsServiceOptions>()
        .Configure<TokenCredential>((options, credential) => options.Credential = credential);
}
if (role == "worker" && !initialize && !importLegacy) builder.Services.AddHostedService<KitchenWorker>();
var app = builder.Build();
if (string.IsNullOrWhiteSpace(builder.Configuration["COSMOS_ENDPOINT"]))
    app.Logger.LogWarning("Shell-only mode: Cosmos configuration is absent; antiforgery keys are ephemeral and business services remain unavailable.");

if (initialize)
{
    var outputPath = builder.Configuration["AGENT_VERSIONS_OUTPUT"]
        ?? throw new InvalidOperationException("AGENT_VERSIONS_OUTPUT is required to retain installed versions.");
    await app.Services.GetRequiredService<RestaurantService>().Initialize(CancellationToken.None);
    var versions = await app.Services.GetRequiredService<AgentRuntime>().Install(CancellationToken.None);
    var result = JsonSerializer.Serialize(new { Initialized = true, AgentVersions = versions });
    await File.WriteAllTextAsync(outputPath, result);
    Console.WriteLine(result);
    return;
}
if (importLegacy)
{
    var path = builder.Configuration["LEGACY_IMPORT_PATH"]
        ?? throw new InvalidOperationException("LEGACY_IMPORT_PATH is required.");
    var output = builder.Configuration["LEGACY_IMPORT_OUTPUT"]
        ?? throw new InvalidOperationException("LEGACY_IMPORT_OUTPUT is required to retain synthetic access codes securely.");
    await app.Services.GetRequiredService<LegacyImport>().Run(path, output, CancellationToken.None);
    Console.WriteLine("Synthetic import completed. Results retained in the configured private output file.");
    return;
}

app.Use(async (context, next) =>
{
    var correlation = context.Request.Headers["X-Correlation-ID"].ToString();
    if (correlation.Length is > 0 and <= 80 && correlation.All(c => char.IsAsciiLetterOrDigit(c) || c is '-' or ':'))
        context.TraceIdentifier = correlation;
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' https://login.microsoftonline.com; "
        + "object-src 'none'; frame-ancestors 'none'; base-uri 'self'";
    context.Response.Headers.CacheControl = "no-store";
    try
    {
        await next();
    }
    catch (DomainException exception)
    {
        app.Logger.LogWarning("Business rejection {Status}: {Reason}; trace {TraceId}",
            exception.Status, exception.Message, context.TraceIdentifier);
        await Results.Problem(exception.Message, statusCode: exception.Status).ExecuteAsync(context);
    }
    catch (AntiforgeryValidationException exception)
    {
        app.Logger.LogWarning(exception, "CSRF validation failed; trace {TraceId}", context.TraceIdentifier);
        await Results.Problem("CSRF validation failed.", statusCode: 403).ExecuteAsync(context);
    }
    catch (JsonException exception)
    {
        app.Logger.LogWarning("Invalid structured input {ErrorType}; trace {TraceId}",
            exception.GetType().Name, context.TraceIdentifier);
        await Results.Problem("Invalid structured input; no successful action is claimed.",
            statusCode: 400).ExecuteAsync(context);
    }
    catch (Exception exception) when (exception is CosmosException or RequestFailedException or ServiceBusException
        or System.ClientModel.ClientResultException or HttpRequestException or InvalidOperationException)
    {
        app.Logger.LogError(exception, "Dependency unavailable; trace {TraceId}", context.TraceIdentifier);
        await Results.Problem("A required service is unavailable; no successful action is claimed.",
            statusCode: 503).ExecuteAsync(context);
    }
    catch (OperationCanceledException exception) when (!context.RequestAborted.IsCancellationRequested)
    {
        app.Logger.LogError(exception, "Dependency deadline exceeded; trace {TraceId}", context.TraceIdentifier);
        await Results.Problem("Operation deadline exceeded; refresh state before retrying.",
            statusCode: 503).ExecuteAsync(context);
    }
});
app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();
app.MapGet("/health/live", () => Results.Ok(new { Role = role, Live = true }));
app.MapGet("/health/ready", async (IServiceProvider services, CancellationToken token) =>
{
    if (role == "chat")
    {
        var names = new[] { "FOUNDRY_PROJECT_ENDPOINT", "AGENT_GUEST_VERSION", "AGENT_STAFF_VERSION", "AGENT_KITCHEN_VERSION" };
        return names.All(name => !string.IsNullOrWhiteSpace(builder.Configuration[name]))
            ? Results.Ok(new { Role = role }) : Results.Problem("Agent configuration is incomplete.", statusCode: 503);
    }
    await services.GetRequiredService<CosmosStore>().Transactions.ReadContainerAsync(cancellationToken: token);
    return Results.Ok(new { Role = role });
});

if (role == "web")
{
    app.MapRazorPages();
    app.MapGet("/api/session/csrf", (HttpContext context, IAntiforgery antiforgery) =>
        Results.Ok(new { Token = antiforgery.GetAndStoreTokens(context).RequestToken }));
    app.MapGet("/api/staff/config", () =>
        Guid.TryParse(builder.Configuration["STAFF_CLIENT_ID"], out _)
        && Guid.TryParse(builder.Configuration["STAFF_TENANT_ID"], out _)
        && Guid.TryParse(builder.Configuration["STAFF_AUDIENCE"], out _)
            ? Results.Ok(new { ClientId = builder.Configuration["STAFF_CLIENT_ID"],
                TenantId = builder.Configuration["STAFF_TENANT_ID"],
                Scope = $"api://{builder.Configuration["STAFF_AUDIENCE"]}/access_as_user" })
            : Results.Problem("Entra staff sign-in is not configured. No synthetic fallback is available.", statusCode: 503));
    if (syntheticStaff)
        app.MapPost("/api/staff/session", async (StaffLogin request, HttpContext context,
        IAntiforgery antiforgery, StaffAuthentication staff) =>
    {
        await antiforgery.ValidateRequestAsync(context);
        var proof = staff.Login(request.EmployeeId, request.Password);
        context.Response.Cookies.Delete("restaurant-session");
        context.Response.Cookies.Append(StaffAuthentication.CookieName, proof,
            new() { HttpOnly = true, Secure = true, Path = "/", SameSite = SameSiteMode.Strict,
                MaxAge = TimeSpan.FromMinutes(30) });
        context.Response.Headers.CacheControl = "no-store";
        return Results.Ok(new { Authenticated = true, DemoOnly = true, ExpiresInSeconds = 1800 });
        }).RequireRateLimiting("entry");
    else
        app.MapPost("/api/staff/session", async (HttpContext context, IAntiforgery antiforgery) =>
        {
            await antiforgery.ValidateRequestAsync(context);
            var result = await context.AuthenticateAsync("staff");
            if (!result.Succeeded || result.Principal is null) return Results.Unauthorized();
            var proof = context.Request.Headers.Authorization.ToString();
            if (!proof.StartsWith("Bearer ", StringComparison.Ordinal)) return Results.Unauthorized();
            var expires = new JsonWebTokenHandler().ReadJsonWebToken(proof[7..]).ValidTo;
            context.Response.Cookies.Delete("restaurant-session");
            context.Response.Cookies.Append(StaffAuthentication.CookieName, proof[7..],
                new() { HttpOnly = true, Secure = true, Path = "/", SameSite = SameSiteMode.Strict,
                    Expires = new DateTimeOffset(expires < DateTime.UtcNow.AddMinutes(30)
                        ? expires : DateTime.UtcNow.AddMinutes(30), TimeSpan.Zero) });
            return Results.Ok(new { Authenticated = true, DemoOnly = false });
        }).RequireRateLimiting("entry");
    app.MapPost("/api/staff/logout", async (HttpContext context, IAntiforgery antiforgery) =>
    {
        await antiforgery.ValidateRequestAsync(context);
        context.Response.Cookies.Delete(StaffAuthentication.CookieName,
            new() { HttpOnly = true, Secure = true, Path = "/", SameSite = SameSiteMode.Strict });
        return Results.Ok(new { SignedOut = true });
    });
    app.MapGet("/api/staff/session", (HttpContext context) =>
        context.User.Identity?.AuthenticationType == "staff"
            ? Results.Ok(new { EmployeeId = context.User.FindFirstValue("sub"),
                Name = context.User.FindFirstValue("name"), Role = Caller.From(context.User).Role,
                Floors = Caller.From(context.User).Floors })
            : Results.Unauthorized()).RequireAuthorization();
    app.MapGet("/api/session/keys/{version}", (string version, SessionTokens sessions, CancellationToken token) =>
        sessions.PublicKey(version, token)).RequireRateLimiting("entry");
    app.MapPost("/api/reservations", async (ReservationRequest request, HttpContext context,
        IAntiforgery antiforgery, RestaurantService service, CancellationToken token) =>
    {
        await antiforgery.ValidateRequestAsync(context);
        return await service.Reserve(request, token);
    }).RequireRateLimiting("reservation");
    app.MapPost("/api/session", async (LoginRequest request, HttpContext context,
        IAntiforgery antiforgery, RestaurantService service, SessionTokens sessions, CancellationToken token) =>
    {
        await antiforgery.ValidateRequestAsync(context);
        var visit = await service.Login(request.VisitId, request.AccessCode, token);
        context.Response.Cookies.Delete(StaffAuthentication.CookieName,
            new() { Secure = true, Path = "/", SameSite = SameSiteMode.Strict });
        context.Response.Cookies.Append("restaurant-session", await sessions.Issue(visit, token),
            new() { HttpOnly = true, Secure = true, SameSite = SameSiteMode.Strict, MaxAge = TimeSpan.FromHours(1) });
        return Results.Ok(new { VisitId = visit.id });
    }).RequireRateLimiting("entry");
    app.MapGet("/api/menu", (CosmosStore store, CancellationToken token) => store.Menu(token));
    app.MapGet("/api/policy", async (CosmosStore store, CancellationToken token) =>
        (await CosmosStore.Read<JsonElement>(store.Catalog, "policy", "policy", token))?.Item
            ?? throw new DomainException(503, "Policy has not been initialized."));
    app.MapGet("/api/visits/{id}", (string id, HttpContext context, RestaurantService service, CancellationToken token) =>
        service.View(id, Caller.From(context.User), token)).RequireAuthorization();
    app.MapGet("/api/board", (string slot, int? floor, HttpContext context, RestaurantService service, CancellationToken token) =>
        service.Board(Caller.From(context.User), slot, floor, token)).RequireAuthorization();
    app.MapGet("/api/management", (HttpContext context, OperationsService service, CancellationToken token) =>
        service.View(Caller.From(context.User), token)).RequireAuthorization();
    app.MapPost("/api/replay", async (ReplayInput request, HttpContext context, IAntiforgery antiforgery,
        OperationsService service, CancellationToken token) =>
    {
        await ValidateWrite(context, antiforgery);
        return await service.RequestReplay(request.MessageId, request.SessionId, Caller.From(context.User), token);
    }).RequireAuthorization();
    app.MapPost("/api/previews", async (Command command, HttpContext context, IAntiforgery antiforgery,
        RestaurantService service, CancellationToken token) =>
    {
        await ValidateWrite(context, antiforgery);
        return await service.Preview(command, Caller.From(context.User), token);
    }).RequireAuthorization();
    app.MapPost("/api/reservation-previews", async (ReservationProposal proposal, HttpContext context,
        IAntiforgery antiforgery, RestaurantService service, CancellationToken token) =>
    {
        await ValidateWrite(context, antiforgery);
        return await service.PreviewReservation(proposal, Caller.From(context.User), token);
    }).RequireAuthorization();
    app.MapPost("/api/reservation-confirm", async (ReservationConfirmation request, HttpContext context,
        IAntiforgery antiforgery, RestaurantService service, CancellationToken token) =>
    {
        await ValidateWrite(context, antiforgery);
        return await service.ConfirmReservation(request.Slot, request.PreviewId, Caller.From(context.User), token);
    }).RequireAuthorization();
    app.MapPost("/api/confirm", async (ConfirmRequest request, HttpContext context, IAntiforgery antiforgery,
        RestaurantService service, CancellationToken token) =>
    {
        await ValidateWrite(context, antiforgery);
        return await service.Confirm(request.VisitId, request.PreviewId, request.RequestId, Caller.From(context.User), token);
    }).RequireAuthorization();
    app.MapPost("/api/chat", async (ChatRequest request, HttpContext context, IAntiforgery antiforgery,
        IHttpClientFactory http, CancellationToken token) =>
    {
        await ValidateWrite(context, antiforgery);
        _ = Caller.From(context.User);
        var baseUrl = builder.Configuration["CHAT_BASE_URL"]
            ?? throw new InvalidOperationException("CHAT_BASE_URL is required.");
        using var message = new HttpRequestMessage(HttpMethod.Post, baseUrl.TrimEnd('/') + "/api/chat")
            { Content = JsonContent.Create(request) };
        message.Headers.Authorization = new("Bearer", Proof(context));
        message.Headers.Add("X-Correlation-ID", context.TraceIdentifier);
        using var response = await http.CreateClient("internal").SendAsync(message, token);
        var content = await response.Content.ReadAsStringAsync(token);
        return Results.Content(content, "application/json", statusCode: (int)response.StatusCode);
    }).RequireAuthorization();
}
else if (role == "chat")
{
    app.MapPost("/api/chat", (ChatRequest request, HttpContext context, AgentRuntime agents, CancellationToken token) =>
        agents.Turn(request, Caller.From(context.User), Proof(context),
            context.TraceIdentifier, token)).RequireAuthorization();
}
app.Run();

static async Task ValidateWrite(HttpContext context, IAntiforgery antiforgery)
{
    if (string.IsNullOrEmpty(context.Request.Headers.Authorization))
        await antiforgery.ValidateRequestAsync(context);
}

static string Proof(HttpContext context)
{
    var bearer = context.Request.Headers.Authorization.ToString();
    return bearer.StartsWith("Bearer ", StringComparison.Ordinal) ? bearer[7..]
        : context.Request.Cookies[StaffAuthentication.CookieName]
            ?? context.Request.Cookies["restaurant-session"] ?? throw new DomainException(401, "Caller proof required.");
}

/// <summary>A reservation access-code verification request.</summary>
public sealed record LoginRequest(string VisitId, string AccessCode);
/// <summary>Only credentials are accepted; roles and floors are never login inputs.</summary>
public sealed record StaffLogin(string EmployeeId, string Password);
/// <summary>Explicit confirmation of a previously reviewed action preview.</summary>
public sealed record ConfirmRequest(string VisitId, string PreviewId, string RequestId);
/// <summary>An explicit manager request for one dead-lettered message.</summary>
public sealed record ReplayInput(string MessageId, string SessionId);
/// <summary>Human confirmation of a caller-bound capacity preview.</summary>
public sealed record ReservationConfirmation(string Slot, string PreviewId);
/// <summary>Application entry point exposed for API contract tests.</summary>
public partial class Program;
