using System.Security.Claims;
using System.Threading.RateLimiting;
using Azure.Core;
using Azure.Identity;
using CoffeeShop.Web.Models;
using CoffeeShop.Web.Services;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddRazorPages();
builder.Services.AddSingleton<TokenCredential>(_ => builder.Environment.IsProduction()
    ? new ManagedIdentityCredential(ManagedIdentityId.SystemAssigned) : new DefaultAzureCredential());
builder.Services.AddSingleton<IRepository, TableRepository>();
builder.Services.AddSingleton<IAccountRepository, TableAccountRepository>();
builder.Services.AddSingleton<LocalAccounts>();
builder.Services.AddSingleton<StoreAccess>();
builder.Services.AddSingleton<OrderService>();
builder.Services.AddSingleton<IAgentGateway, FoundryGateway>();
builder.Services.AddSingleton<CloseService>();
var protection = builder.Services.AddDataProtection().SetApplicationName("coffee-shop");
if (builder.Environment.IsProduction())
{
    var home = Environment.GetEnvironmentVariable("HOME")
        ?? throw new InvalidOperationException("Shared App Service HOME is required for session keys.");
    protection.PersistKeysToFileSystem(new DirectoryInfo(Path.Combine(home, "coffee-shop-session-keys")));
}
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-CSRF-TOKEN";
    options.Cookie.Name = "__Host-CoffeeCsrf";
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
});
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
{
    options.Cookie.Name = "__Host-CoffeeSession";
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.ExpireTimeSpan = TimeSpan.FromMinutes(30);
    options.SlidingExpiration = false;
    options.Events.OnRedirectToLogin = context =>
    {
        context.Response.StatusCode = 401;
        return Task.CompletedTask;
    };
    options.Events.OnRedirectToAccessDenied = context =>
    {
        context.Response.StatusCode = 403;
        return Task.CompletedTask;
    };
    options.Events.OnValidatePrincipal = async context =>
    {
        var username = context.Principal?.FindFirstValue("oid");
        var stored = username is null ? null : await context.HttpContext.RequestServices
            .GetRequiredService<IAccountRepository>().FindAsync(username, context.HttpContext.RequestAborted);
        if (stored is null || stored.Value.SecurityStamp != context.Principal?.FindFirstValue("stamp")
            || stored.Value.LockedUntil > DateTimeOffset.UtcNow)
            context.RejectPrincipal();
    };
});
builder.Services.AddAuthorization(options => options.AddPolicy("Manager", policy => policy
    .RequireAuthenticatedUser().RequireRole("StoreManager", "AreaManager")));
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = 429;
    options.AddPolicy("signin", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
    options.AddPolicy("close", context => RateLimitPartition.GetFixedWindowLimiter(
        context.User.FindFirstValue("oid") ?? "anonymous",
        _ => new FixedWindowRateLimiterOptions { PermitLimit = 6, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});
var app = builder.Build();
if (args.Contains("--initialize"))
{
    await Bootstrap.RunAsync(app.Configuration, app.Environment.ContentRootPath);
    return;
}
app.UseExceptionHandler(handler => handler.Run(async context =>
{
    var error = context.Features.Get<Microsoft.AspNetCore.Diagnostics.IExceptionHandlerFeature>()?.Error;
    context.Response.StatusCode = error switch
    {
        UnauthorizedAccessException => 403,
        KeyNotFoundException => 404,
        InvalidOperationException => 409,
        ArgumentException => 400,
        OperationCanceledException => 504,
        _ => 503
    };
    await context.Response.WriteAsJsonAsync(new
    {
        error = context.Response.StatusCode switch
        {
            403 => "Store access denied.", 404 => "Required evidence not found.",
            409 => "Conflict or incomplete evidence. Refresh and retry.",
            400 => "Invalid request.", 504 => "Agent budget exhausted; no action committed.",
            _ => "Dependency unavailable; no successful close claimed."
        },
        traceId = context.TraceIdentifier
    });
}));
app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    if (context.Request.Path.StartsWithSegments("/api")) context.Response.Headers.CacheControl = "no-store";
    await next();
});
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.Use(async (context, next) =>
{
    if (context.Request.Path.StartsWithSegments("/api") && context.Request.Method == "POST")
    {
        try { await context.RequestServices.GetRequiredService<IAntiforgery>().ValidateRequestAsync(context); }
        catch (AntiforgeryValidationException)
        {
            app.Logger.LogWarning("Rejected request with invalid CSRF token at {Path}.", context.Request.Path);
            context.Response.StatusCode = 400;
            await context.Response.WriteAsJsonAsync(new { error = "Invalid CSRF token. Refresh and retry." });
            return;
        }
    }
    await next();
});
app.UseAuthorization();
app.UseRateLimiter();
app.MapRazorPages();
app.MapGet("/api/session", (HttpContext context, IAntiforgery antiforgery, StoreAccess access) => new
{
    authenticated = context.User.Identity?.IsAuthenticated == true,
    username = context.User.Identity?.Name,
    stores = context.User.Identity?.IsAuthenticated == true ? access.Grants(context.User) : [],
    csrfToken = antiforgery.GetAndStoreTokens(context).RequestToken
});
app.MapPost("/api/auth/login", async (LoginRequest request, HttpContext context, LocalAccounts accounts) =>
{
    var account = await accounts.AuthenticateAsync(request.Username, request.Password, context.RequestAborted);
    if (account is null) return Results.Json(new { error = "Invalid credentials or account temporarily locked." },
        statusCode: 401);
    var claims = new List<Claim>
    {
        new("oid", account.Username), new(ClaimTypes.Name, account.Username),
        new(ClaimTypes.NameIdentifier, account.Username),
        new("roles", account.Role), new("stamp", account.SecurityStamp)
    };
    claims.AddRange(account.Stores.Select(store => new Claim("store", store)));
    await context.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme,
        new ClaimsPrincipal(new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme,
            ClaimTypes.Name, "roles")));
    return Results.Ok(new { username = account.Username });
}).RequireRateLimiting("signin");
app.MapPost("/api/auth/logout", async (HttpContext context) =>
{
    await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    return Results.Ok(new { signedOut = true });
}).RequireAuthorization("Manager");
var api = app.MapGroup("/api").RequireAuthorization("Manager");
api.MapGet("/stores", (ClaimsPrincipal user, StoreAccess access) => access.Grants(user));
api.MapGet("/stores/{storeId}", async (string storeId, ClaimsPrincipal user,
    StoreAccess access, IRepository repository, CancellationToken ct) =>
{
    access.Demand(user, storeId);
    return await repository.ReadAsync(storeId, ct);
});
api.MapPost("/orders/draft", async (DraftRequest request, ClaimsPrincipal user,
    OrderService orders, CancellationToken ct) => await orders.DraftAsync(user, request.StoreId, ct));
api.MapPost("/orders/{storeId}/{draftId}/approve", async (string storeId, string draftId,
    ApprovalRequest request, ClaimsPrincipal user, OrderService orders, CancellationToken ct) =>
{
    if (!request.Confirm) throw new ArgumentException("Explicit human confirmation required.");
    return await orders.ApproveAsync(user, storeId, draftId, ct);
});
api.MapPost("/chat", async (CloseRequest request, ClaimsPrincipal user,
    CloseService close, CancellationToken ct) => await close.RunAsync(user, request, ct))
    .RequireRateLimiting("close");
app.Run();

public partial class Program;

/// <summary>Credentials submitted only over HTTPS and never persisted as plaintext.</summary>
public sealed record LoginRequest(string? Username, string? Password);
