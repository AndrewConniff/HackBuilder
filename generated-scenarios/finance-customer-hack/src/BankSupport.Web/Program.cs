using System.Threading.RateLimiting;
using Azure.Core;
using Azure.Data.Tables;
using Azure.Identity;
using BankSupport.Web.Models;
using BankSupport.Web.Services;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);
var installing = args.Contains("--install");
TokenCredential credential = installing
    ? new AzureCliCredential() : new ManagedIdentityCredential(ManagedIdentityId.SystemAssigned);
builder.Services.AddSingleton(credential);
builder.Services.AddSingleton(_ => new TableClient(
    new Uri(builder.Configuration["STORAGE_TABLE_ENDPOINT"]
        ?? throw new InvalidOperationException("STORAGE_TABLE_ENDPOINT is required.")), "bankstate", credential));
builder.Services.AddSingleton<IDocumentStore, DocumentStore>();
builder.Services.AddSingleton<LocalAuthentication>();
builder.Services.AddSingleton<BankingWorkflow>();
builder.Services.AddHttpClient<IFoundryGateway, FoundryGateway>(http => http.Timeout = TimeSpan.FromSeconds(50));
if (!installing && !builder.Environment.IsEnvironment("Testing"))
    builder.Services.AddApplicationInsightsTelemetry(options => options.Credential = credential);
builder.Services.AddRazorPages(options =>
{
    options.Conventions.AuthorizeFolder("/");
    options.Conventions.AllowAnonymousToPage("/Login");
    options.Conventions.AllowAnonymousToPage("/Error");
    options.Conventions.AuthorizePage("/Index", "Customer");
    options.Conventions.AuthorizePage("/Queue", "Representative");
});
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("Customer", p => p.RequireRole("Customer"));
    options.AddPolicy("Representative", p => p.RequireRole("Representative"));
});
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
{
    options.LoginPath = "/Login";
    options.AccessDeniedPath = "/Denied";
    options.Cookie.Name = "__Host-bank";
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.ExpireTimeSpan = TimeSpan.FromHours(4);
    options.SlidingExpiration = false;
    options.Events.OnValidatePrincipal = context =>
        context.HttpContext.RequestServices.GetRequiredService<LocalAuthentication>().ValidateAsync(context);
});
builder.Services.AddAntiforgery(options => options.Cookie.SecurePolicy = CookieSecurePolicy.Always);
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("login", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 20, Window = TimeSpan.FromMinutes(1), QueueLimit = 0
        }));
});
if (!installing)
{
    var keys = builder.Configuration["SESSION_KEYS_PATH"]
        ?? throw new InvalidOperationException("SESSION_KEYS_PATH must identify persistent private storage.");
    Directory.CreateDirectory(keys);
    if (!OperatingSystem.IsWindows())
        File.SetUnixFileMode(keys, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
    builder.Services.AddDataProtection().SetApplicationName("finance-customer-hack")
        .PersistKeysToFileSystem(new DirectoryInfo(keys));
}

var app = builder.Build();
if (app.Environment.IsEnvironment("Testing"))
    app.Logger.LogWarning("Telemetry export is disabled in the explicit local Testing environment.");
if (installing)
{
    await Installer.RunAsync(app.Services, app.Environment.ContentRootPath, CancellationToken.None);
    return;
}
app.Use(async (context, next) =>
{
    context.Response.Headers.ContentSecurityPolicy =
        "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Strict-Transport-Security"] = "max-age=31536000";
    context.Response.Headers.CacheControl = "no-store";
    try { await next(context); }
    catch (BusinessException ex)
    {
        app.Logger.LogWarning("Business operation rejected: {Status} {Message}", ex.StatusCode, ex.Message);
        context.Response.StatusCode = ex.StatusCode;
        await context.Response.WriteAsync(ex.Message);
    }
    catch (Exception ex) when (ex is Azure.RequestFailedException or Azure.Identity.AuthenticationFailedException)
    {
        app.Logger.LogError(ex, "Azure dependency unavailable");
        context.Response.StatusCode = 503;
        await context.Response.WriteAsync("Azure dependency unavailable. Contact the operator with the request time.");
    }
});
app.UseStaticFiles();
app.UseRouting();
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();
app.MapRazorPages();
app.Run();

/// <summary>Application entry point exposed for in-process HTTP integration tests.</summary>
public partial class Program;
