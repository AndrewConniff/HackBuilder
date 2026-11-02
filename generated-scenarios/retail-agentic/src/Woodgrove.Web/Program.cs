using System.Threading.RateLimiting;
using Azure.Core;
using Azure.Data.Tables;
using Azure.Identity;
using Azure.Storage.Blobs;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.RateLimiting;
using Woodgrove.Web.Services;

var builder = WebApplication.CreateBuilder(args);
var installing = builder.Configuration.GetValue<bool>("Install");
var installationIdentity = builder.Configuration["InstallationIdentity"] ?? "User";
if (installationIdentity is not ("User" or "ManagedIdentity"))
    throw new InvalidOperationException("InstallationIdentity must be User or ManagedIdentity.");
TokenCredential credential = installing && installationIdentity == "User"
    ? new AzureCliCredential() : new ManagedIdentityCredential(ManagedIdentityId.SystemAssigned);
var tableEndpoint = builder.Configuration["StorageTableEndpoint"];
if (string.IsNullOrWhiteSpace(tableEndpoint))
    throw new InvalidOperationException("StorageTableEndpoint is required; no local-data fallback is permitted.");
var blobEndpoint = builder.Configuration["StorageBlobEndpoint"];
if (string.IsNullOrWhiteSpace(blobEndpoint))
    throw new InvalidOperationException("StorageBlobEndpoint is required for durable session-key protection.");
if (!Uri.TryCreate(tableEndpoint, UriKind.Absolute, out var tableUri) || tableUri.Scheme != "https" ||
    !Uri.TryCreate(blobEndpoint, UriKind.Absolute, out var blobUri) || blobUri.Scheme != "https")
    throw new InvalidOperationException("Storage endpoints must be absolute HTTPS URLs.");
builder.Services.AddSingleton(credential);
builder.Services.AddSingleton(new TableServiceClient(tableUri, credential, new TableClientOptions
{
    Retry = { MaxRetries = 0 }
}));
builder.Services.AddSingleton(new BlobServiceClient(blobUri, credential));
builder.Services.AddSingleton<TableStorageDataService>();
builder.Services.AddSingleton<LocalAccounts>();
builder.Services.AddSingleton<FoundryRuntime>();
builder.Services.AddSingleton<OrderWorkflow>();
builder.Services.AddSingleton<ReferenceInstaller>();
if (!installing) builder.Services.AddApplicationInsightsTelemetry();
builder.Services.AddDataProtection().SetApplicationName("Woodgrove.Groceries")
    .PersistKeysToAzureBlobStorage(new Uri(blobUri, "session-keys/keyring.xml"), credential);
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
{
    options.LoginPath = "/Login";
    options.AccessDeniedPath = "/Denied";
    options.Cookie.Name = "__Host-Woodgrove";
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.ExpireTimeSpan = TimeSpan.FromMinutes(30);
    options.SlidingExpiration = false;
    options.Events.OnValidatePrincipal = context =>
        context.HttpContext.RequestServices.GetRequiredService<LocalAccounts>().ValidateAsync(context);
});
builder.Services.AddRazorPages(options =>
{
    options.Conventions.AuthorizeFolder("/");
    options.Conventions.AllowAnonymousToPage("/Login");
    options.Conventions.AllowAnonymousToPage("/Error");
});
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddFixedWindowLimiter("interactive", limiter =>
    {
        limiter.PermitLimit = 120;
        limiter.Window = TimeSpan.FromMinutes(1);
        limiter.QueueLimit = 0;
    });
});
if (!installing) builder.Services.AddHostedService<FulfillmentWorker>();

var app = builder.Build();
if (installing)
{
    var directory = builder.Configuration["AccessDirectory"]
        ?? throw new InvalidOperationException("AccessDirectory is required for private credential delivery.");
    if (!Path.IsPathFullyQualified(directory) || Path.GetFileName(directory) != ".private")
        throw new InvalidOperationException("AccessDirectory must be an absolute deployment-specific .private directory.");
    await app.Services.GetRequiredService<ReferenceInstaller>().InstallAsync(directory, CancellationToken.None);
    return;
}
app.UseExceptionHandler("/Error");
app.UseHsts();
app.UseHttpsRedirection();
app.Use(async (context, next) =>
{
    context.Response.Headers.ContentSecurityPolicy =
        "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'";
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    await next();
});
app.UseRouting();
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();
app.MapStaticAssets();
app.MapRazorPages()
    .RequireRateLimiting("interactive")
    .WithStaticAssets();
await app.RunAsync();

/// <summary>Exposes the application entry point to the separate HTTP test assembly.</summary>
public partial class Program { }
