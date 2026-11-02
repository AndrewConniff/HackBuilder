using System.Threading.RateLimiting;
using Azure.Core;
using Azure.Identity;
using Brokerage.Web;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton(sp => WorkloadSettings.Load(sp.GetRequiredService<IConfiguration>()));
builder.Services.AddSingleton<TokenCredential>(sp => args.Contains("--initialize", StringComparer.Ordinal)
    ? new AzureCliCredential()
    : new ManagedIdentityCredential(ManagedIdentityId.FromUserAssignedClientId(
        sp.GetRequiredService<WorkloadSettings>().ClientId)));
builder.Services.AddSingleton<AzureBrokerage>();
builder.Services.AddSingleton<IChatBackend>(sp => sp.GetRequiredService<AzureBrokerage>());
builder.Services.AddSingleton<ChatService>();
builder.Services.AddRazorPages();
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<UpstreamExceptionHandler>();
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer();
builder.Services.AddOptions<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme)
    .Configure<WorkloadSettings>((options, settings) =>
{
    options.Authority = $"https://login.microsoftonline.com/{settings.TenantId}/v2.0";
    options.Audience = settings.BackendAudience;
    options.MapInboundClaims = false;
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,
        ValidIssuers =
        [
            $"https://login.microsoftonline.com/{settings.TenantId}/v2.0",
            $"https://sts.windows.net/{settings.TenantId}/"
        ],
        ValidateAudience = true,
        ValidAudiences = [settings.BackendAudience, settings.BackendAudience.Replace("api://", string.Empty)],
        ValidateLifetime = true,
        ClockSkew = TimeSpan.FromSeconds(30)
    };
});
builder.Services.AddAuthorizationBuilder().AddPolicy("GatewayOnly", policy =>
    policy.RequireAuthenticatedUser()
          .RequireAssertion(context =>
          {
              if (context.Resource is not HttpContext http) return false;
              var settings = http.RequestServices.GetRequiredService<WorkloadSettings>();
              return context.User.HasClaim("tid", settings.TenantId)
                  && context.User.HasClaim("oid", settings.GatewayPrincipalId);
          }));
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddConcurrencyLimiter("chat", limit =>
    {
        limit.PermitLimit = 8;
        limit.QueueLimit = 0;
        limit.QueueProcessingOrder = QueueProcessingOrder.OldestFirst;
    });
});
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 8192);

var app = builder.Build();
_ = app.Services.GetRequiredService<WorkloadSettings>();
if (args.Contains("--initialize", StringComparer.Ordinal))
{
    await app.Services.GetRequiredService<AzureBrokerage>().InitializeAsync(CancellationToken.None);
    return;
}
app.UseExceptionHandler();
app.Use(async (context, next) =>
{
    context.Response.Headers.ContentSecurityPolicy =
        "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'";
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers.CacheControl = "no-store";
    await next(context);
});
app.UseAuthentication();
app.UseAuthorization();
app.Use(async (context, next) =>
{
    if (Guid.TryParse(context.Request.Headers["X-Correlation-ID"], out var correlationId))
        context.TraceIdentifier = correlationId.ToString();
    await next(context);
});
app.UseRateLimiter();
app.MapStaticAssets().RequireAuthorization("GatewayOnly");
app.MapRazorPages().RequireAuthorization("GatewayOnly");
app.MapPost("/api/chat", async (ChatRequest request, ChatService chat, HttpContext context) =>
{
    if (string.IsNullOrWhiteSpace(request.Message) || request.Message.Length > 2000)
        return Results.Problem(statusCode: 400, title: "Message must contain 1 to 2000 characters.");
    using var timeout = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
    timeout.CancelAfter(TimeSpan.FromSeconds(60));
    var reply = await chat.SendAsync(request.Message, context.TraceIdentifier, timeout.Token);
    return Results.Ok(reply);
}).RequireAuthorization("GatewayOnly").RequireRateLimiting("chat");
app.Run();

/// <summary>Application entry point exposed for in-process acceptance tests.</summary>
public partial class Program;
