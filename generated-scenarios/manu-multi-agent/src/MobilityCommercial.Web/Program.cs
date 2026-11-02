using System.ClientModel;
using System.Security.Claims;
using System.Text.Json;
using Azure;
using Azure.Core;
using Azure.Identity;
using Azure.Security.KeyVault.Keys.Cryptography;
using Azure.Storage.Blobs;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using MobilityCommercial.Web.Models;
using MobilityCommercial.Web.Services;

var builder = WebApplication.CreateBuilder(args);
var settings = AppSettings.Load(builder.Configuration);
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 128 * 1024);
builder.Logging.AddFilter("Azure", LogLevel.Warning);
builder.Logging.AddFilter("System.Net.Http", LogLevel.Warning);
builder.Services.AddSingleton(settings);
builder.Services.AddSingleton<TokenCredential>(new DefaultAzureCredential(new DefaultAzureCredentialOptions
{
    ManagedIdentityClientId = settings.ClientId,
    ExcludeInteractiveBrowserCredential = true,
    Diagnostics = { IsLoggingContentEnabled = false }
}));
builder.Services.AddSingleton(provider => new BlobServiceClient(settings.BlobEndpoint,
    provider.GetRequiredService<TokenCredential>(), new BlobClientOptions { Retry = { MaxRetries = 0 } }));
builder.Services.AddSingleton(provider => new CryptographyClient(settings.KeyUri,
    provider.GetRequiredService<TokenCredential>(), new CryptographyClientOptions { Retry = { MaxRetries = 0 } }));
builder.Services.AddSingleton<IFixtures, BlobFixtures>();
builder.Services.AddSingleton<IAgentGateway, FoundryGateway>();
builder.Services.AddSingleton<IReceiptSigner, KeyVaultReceiptSigner>();
builder.Services.AddSingleton<HandoffService>();
builder.Services.Configure<RouteHandlerOptions>(options => options.ThrowOnBadRequest = true);
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.UnmappedMemberHandling = System.Text.Json.Serialization.JsonUnmappedMemberHandling.Disallow;
    options.SerializerOptions.RespectRequiredConstructorParameters = true;
    options.SerializerOptions.PropertyNameCaseInsensitive = false;
});
builder.Services.AddRazorPages(options => options.Conventions.AuthorizeFolder("/"));
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(options =>
{
    options.Authority = $"https://login.microsoftonline.com/{settings.TenantId}/v2.0";
    options.Audience = settings.Audience;
    options.MapInboundClaims = false;
    options.IncludeErrorDetails = false;
    options.TokenValidationParameters = new()
    {
        ValidateIssuer = true,
        ValidIssuer = options.Authority,
        ValidateAudience = true,
        ValidAudience = settings.Audience,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        RequireSignedTokens = true,
        RequireExpirationTime = true,
        ValidAlgorithms = [SecurityAlgorithms.RsaSha256],
        ClockSkew = TimeSpan.FromSeconds(30)
    };
});
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("gateway", policy => policy.RequireAuthenticatedUser()
        .RequireAssertion(context => BackendIdentity.IsGateway(context.User, settings)));
    options.DefaultPolicy = options.GetPolicy("gateway")!;
    options.FallbackPolicy = options.DefaultPolicy;
});
var app = builder.Build();
app.Use(async (context, next) =>
{
    // APIM supplies a GUID; direct callers cannot inject log text or reuse a different shape.
    var supplied = context.Request.Headers["x-correlation-id"].ToString();
    var correlation = Guid.TryParse(supplied, out var parsed) ? parsed.ToString() : Guid.NewGuid().ToString();
    context.TraceIdentifier = correlation;
    context.Response.Headers["x-correlation-id"] = correlation;
    context.Response.Headers["Cache-Control"] = "no-store";
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'";
    try
    {
        await next(context);
        if (context.Response.StatusCode >= 400 && !context.Response.HasStarted)
        {
            var code = context.Response.StatusCode switch
            {
                400 => "invalid_request",
                401 => "authentication_required",
                403 => "gateway_identity_required",
                404 => "route_not_found",
                405 => "method_not_allowed",
                413 => "request_too_large",
                415 => "unsupported_content_type",
                429 => "request_throttled",
                _ => "request_failed"
            };
            context.Response.ContentLength = null;
            await context.Response.WriteAsJsonAsync(new {
                code, correlationId = correlation });
        }
    }
    catch (Exception exception) when (!context.Response.HasStarted)
    {
        var (status, code) = exception switch
        {
            WorkflowException problem => (problem.Status, problem.Code),
            BadHttpRequestException bad => (bad.StatusCode, "invalid_request"),
            JsonException => (400, "invalid_json"),
            FormatException => (400, "invalid_encoding"),
            RequestFailedException => (503, "azure_dependency_unavailable"),
            ClientResultException => (502, "foundry_dependency_failed"),
            AuthenticationFailedException => (503, "managed_identity_unavailable"),
            OperationCanceledException => (504, "request_cancelled"),
            _ => (500, "unexpected_application_error")
        };
        app.Logger.LogWarning("Request failed code {Code} type {Type} correlation {CorrelationId}",
            code, exception.GetType().Name, correlation);
        context.Response.StatusCode = status;
        await context.Response.WriteAsJsonAsync(new { code, correlationId = correlation });
    }
});
app.UseAuthentication();
app.UseAuthorization();
// Static resources are explicit authenticated endpoints; UseStaticFiles would bypass fallback authorization.
foreach (var name in new[] { "app.css", "app.js" })
{
    var fileName = name;
    app.MapGet($"/{name}", () => Results.File(
        Path.Combine(app.Environment.WebRootPath, fileName),
        fileName.EndsWith(".css", StringComparison.Ordinal) ? "text/css" : "text/javascript"))
        .RequireAuthorization("gateway");
}
app.MapRazorPages();
app.MapGet("/api/opportunities", async (IFixtures data, CancellationToken cancellation) =>
    Results.Ok((await data.GetAsync(cancellation)).Opportunities.Select(HandoffService.Project)));
app.MapGet("/api/products", async (IFixtures data, CancellationToken cancellation) =>
    Results.Ok((await data.GetAsync(cancellation)).Products));
app.MapGet("/api/claims", async (IFixtures data, CancellationToken cancellation) =>
    Results.Ok((await data.GetAsync(cancellation)).Claims));
app.MapPost("/api/handoffs", async (HandoffRequest request, HandoffService service, HttpContext context) =>
    Results.Ok(await service.RunAsync(request, context.TraceIdentifier, context.RequestAborted)));
app.MapPost("/api/receipts/verify", async (Receipt receipt, IReceiptSigner signer, HttpContext context) =>
{
    var valid = await signer.VerifyAsync(receipt, context.RequestAborted);
    if (!valid) throw new WorkflowException(400, "receipt_signature_invalid");
    return Results.Ok(new { valid = true, correlationId = context.TraceIdentifier });
});

if (args.Contains("--check-configuration", StringComparer.Ordinal))
{
    Console.WriteLine("Configuration valid. No Azure calls performed.");
    return;
}
await app.RunAsync();

/// <summary>Entry point exposed for isolated application integration tests.</summary>
public partial class Program { }

namespace MobilityCommercial.Web.Services
{
    internal static class BackendIdentity
    {
        internal static bool IsGateway(ClaimsPrincipal user, AppSettings configuration) =>
            user.FindAll("oid").Count() == 1 && user.FindAll("tid").Count() == 1
            && user.FindFirstValue("oid") == configuration.GatewayObjectId
            && user.FindFirstValue("tid") == configuration.TenantId;
    }
}
