using System.Security.Claims;
using Azure.Identity;
using Azure.Storage.Blobs;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using TeachingReview.Web.Services;

var builder = WebApplication.CreateBuilder(args.Where(argument =>
    argument is not ("--initialize-local" or "--initialize" or "--create-agents")).ToArray());
var local = builder.Configuration["StorageMode"] == "Local";
if (local && !builder.Environment.IsDevelopment() && !builder.Environment.IsEnvironment("Testing"))
    throw new InvalidOperationException("Local storage is restricted to explicit development/test runs.");
var privateDirectory = Path.GetFullPath(builder.Configuration["PrivateDirectory"]
    ?? Path.Combine(builder.Environment.ContentRootPath, "..", "..", ".private"));
builder.Configuration["PrivateDirectory"] = privateDirectory;
if (args.Contains("--initialize-local"))
{
    if (!local) throw new InvalidOperationException("Explicit Local storage mode is required.");
    await Initialization.RunAsync(builder.Environment.ContentRootPath, builder.Configuration, true);
    return;
}
if (args.Contains("--initialize"))
{
    if (local) throw new InvalidOperationException("Cloud initialization cannot use Local storage.");
    await Initialization.RunAsync(builder.Environment.ContentRootPath, builder.Configuration, false);
    return;
}
if (args.Contains("--create-agents"))
{
    if (local) throw new InvalidOperationException("Agent installation requires an explicit cloud configuration.");
    Initialization.CreateAgents(builder.Configuration);
    return;
}
var protection = builder.Services.AddDataProtection().SetApplicationName("tue28seven-teaching-review");
if (local)
{
    Directory.CreateDirectory(privateDirectory);
    protection.PersistKeysToFileSystem(new DirectoryInfo(Path.Combine(privateDirectory, "keys")));
    builder.Services.AddSingleton<IStateStore>(new LocalStateStore(Path.Combine(privateDirectory, "state.json")));
}
else
{
    var endpoint = builder.Configuration["Storage:Endpoint"]
        ?? throw new InvalidOperationException("Storage:Endpoint must be configured; no local fallback exists.");
    if (string.IsNullOrWhiteSpace(builder.Configuration["Foundry:Endpoint"]))
        throw new InvalidOperationException("Foundry:Endpoint must be configured.");
    var service = new BlobServiceClient(new Uri(endpoint), new DefaultAzureCredential());
    protection.PersistKeysToAzureBlobStorage(service.GetBlobContainerClient("keys").GetBlobClient("keys.xml"));
    builder.Services.AddSingleton<IStateStore>(new BlobStateStore(
        service.GetBlobContainerClient("workflow").GetBlobClient("state.json")));
}
builder.Services.AddSingleton<IReviewer, FoundryReviewer>();
builder.Services.AddSingleton<WorkflowService>();
builder.Services.AddSingleton<AccountService>();
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
{
    options.LoginPath = "/Login";
    options.AccessDeniedPath = "/Login";
    options.Cookie.Name = "__Host-TeachingReview";
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.ExpireTimeSpan = TimeSpan.FromMinutes(30);
    options.SlidingExpiration = false;
    options.Events.OnValidatePrincipal = async context =>
    {
        var state = await context.HttpContext.RequestServices.GetRequiredService<IStateStore>().ReadAsync(
            context.HttpContext.RequestAborted);
        var account = state.State.Teachers.SingleOrDefault(x =>
            x.Id.ToString() == context.Principal?.FindFirstValue(ClaimTypes.NameIdentifier));
        if (account is null || account.Role != context.Principal?.FindFirstValue(ClaimTypes.Role))
        {
            context.RejectPrincipal();
            await context.HttpContext.SignOutAsync();
        }
    };
});
builder.Services.AddAuthorization();
builder.Services.AddRazorPages(options =>
{
    options.Conventions.AuthorizeFolder("/");
    options.Conventions.AllowAnonymousToPage("/Login");
    options.Conventions.AllowAnonymousToPage("/Error");
});
builder.Services.Configure<Microsoft.AspNetCore.Http.Features.FormOptions>(options =>
    options.ValueLengthLimit = 16000);
var app = builder.Build();
app.UseExceptionHandler("/Error");
if (!app.Environment.IsDevelopment()) app.UseHsts();
app.UseHttpsRedirection();
app.Use(async (context, next) =>
{
    context.Response.Headers.ContentSecurityPolicy =
        "default-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers.CacheControl = "no-store";
    await next();
});
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.MapStaticAssets();
app.MapRazorPages().WithStaticAssets();
app.Run();

/// <summary>Exposes the application entry point to integration tests.</summary>
public partial class Program;
