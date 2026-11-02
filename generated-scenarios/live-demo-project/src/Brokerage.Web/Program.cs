using Azure.Core;
using Azure.Identity;
using Brokerage.Web.Services;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;

var builder = WebApplication.CreateBuilder(args);
var dataPath = builder.Configuration["DataPath"]
    ?? (builder.Environment.IsDevelopment()
        ? Path.Combine(builder.Environment.ContentRootPath, "App_Data")
        : throw new InvalidOperationException("DataPath must name the persistent deployment directory."));
Directory.CreateDirectory(dataPath);
builder.Services.AddSingleton(new BrokerageStore(dataPath));
builder.Services.AddDataProtection()
    .SetApplicationName("live-demo-project")
    .PersistKeysToFileSystem(new DirectoryInfo(Path.Combine(dataPath, "keys")));
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme).AddCookie(options =>
{
    options.LoginPath = "/Login";
    options.AccessDeniedPath = "/Denied";
    options.Cookie.Name = "__Host-Brokerage";
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.ExpireTimeSpan = TimeSpan.FromMinutes(30);
    options.SlidingExpiration = false;
});
builder.Services.AddAuthorization();
builder.Services.AddRazorPages(options =>
{
    options.Conventions.AuthorizeFolder("/");
    options.Conventions.AllowAnonymousToPage("/Login");
    options.Conventions.AllowAnonymousToPage("/Error");
    options.Conventions.AuthorizePage("/Desk", "Representative");
});
builder.Services.AddAuthorizationBuilder().AddPolicy("Representative", policy => policy.RequireRole("Coach"));
builder.Services.AddSingleton<TokenCredential>(_ => new ManagedIdentityCredential());
builder.Services.AddHttpClient<FoundrySelector>(client => client.Timeout = TimeSpan.FromSeconds(30));
builder.Services.AddScoped<IAnswerSelector>(provider => provider.GetRequiredService<FoundrySelector>());

var app = builder.Build();
var accessDirectory = builder.Configuration["PrivateAccessPath"]
    ?? Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, "..", "..", ".private"));
if (args.Contains("--initialize", StringComparer.Ordinal))
{
    await app.Services.GetRequiredService<BrokerageStore>().InitializeAsync(
        Path.Combine(app.Environment.ContentRootPath, "SeedData", "knowledge.json"),
        accessDirectory);
    return;
}
if (builder.Configuration.GetValue<bool>("BootstrapAccounts") && !File.Exists(Path.Combine(dataPath, "state.json")))
{
    await app.Services.GetRequiredService<BrokerageStore>().InitializeAsync(
        Path.Combine(app.Environment.ContentRootPath, "SeedData", "knowledge.json"), accessDirectory);
}
app.UseExceptionHandler("/Error");
if (!app.Environment.IsDevelopment())
{
    app.UseHsts();
}
app.UseHttpsRedirection();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.Use(async (context, next) =>
{
    context.Response.Headers.ContentSecurityPolicy =
        "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; form-action 'self'";
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    await next();
});
app.MapStaticAssets();
app.MapRazorPages().WithStaticAssets();
app.Run();
