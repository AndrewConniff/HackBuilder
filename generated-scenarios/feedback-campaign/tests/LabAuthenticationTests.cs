using System.Net;
using System.Security.Claims;
using System.Text.Json;
using System.Text.RegularExpressions;
using FeedbackCampaign.Web;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace FeedbackCampaign.Tests;

public sealed class LabAuthenticationTests
{
    private const string Password = "test-only-password-not-a-live-credential";

    [Fact]
    public async Task PasswordHashAndDurableLockoutAreEnforced()
    {
        var store = await Store();
        var clock = new TestClock();
        var auth = new LabAuthentication(store, clock);
        Assert.NotEqual(Password, (await store.Get<LabAccount>("accounts", "product-manager"))!.Value.PasswordHash);
        for (var i = 0; i < 5; i++) Assert.Null(await auth.Authenticate("product-manager", "incorrect"));
        Assert.Null(await auth.Authenticate("product-manager", Password));
        Assert.Equal(clock.GetUtcNow().AddMinutes(15),
            (await store.Get<LabAccount>("accounts", "product-manager"))!.Value.LockedUntil);
        clock.Now = clock.Now.AddMinutes(16);
        var principal = await new LabAuthentication(store, clock).Authenticate("product-manager", Password);
        Assert.NotNull(principal);
        Assert.True(principal.IsInRole("ProductManager"));
        Assert.False(principal.IsInRole("ControlAdmin"));
        Assert.Equal(0, (await store.Get<LabAccount>("accounts", "product-manager"))!.Value.FailedAttempts);
    }

    [Theory]
    [InlineData("", "password")]
    [InlineData("../accounts", "password")]
    [InlineData("missing", "password")]
    [InlineData("product-manager", "")]
    public async Task InvalidOrUnknownCredentialsCannotCreatePrincipal(string username, string password)
    {
        var auth = new LabAuthentication(await Store(), TimeProvider.System);
        Assert.Null(await auth.Authenticate(username, password));
    }

    [Fact]
    public async Task StampOrRoleChangesInvalidateSession()
    {
        var store = await Store();
        var auth = new LabAuthentication(store, TimeProvider.System);
        var principal = (await auth.Authenticate("product-manager", Password))!;
        Assert.True(await auth.IsCurrent(principal));
        var row = (await store.Get<LabAccount>("accounts", "product-manager"))!;
        await store.Replace("accounts", "product-manager", row.Value with { Roles = ["ControlAdmin"] }, row.ETag);
        Assert.False(await auth.IsCurrent(principal));
        var changed = (await store.Get<LabAccount>("accounts", "product-manager"))!;
        await store.Replace("accounts", "product-manager",
            changed.Value with { Roles = ["ProductManager"], SecurityStamp = "rotated" }, changed.ETag);
        Assert.False(await auth.IsCurrent(principal));
    }

    [Fact]
    public async Task LoginUsesSecureCookieAndNeverReflectsPassword()
    {
        var store = await Store();
        await using var app = Factory(store);
        using var client = Client(app);
        var response = await Login(client, Password);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        var cookie = response.Headers.GetValues("Set-Cookie").Single(c => c.StartsWith("__Host-FeedbackCampaign="));
        Assert.Contains("secure", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("httponly", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("samesite=strict", cookie, StringComparison.OrdinalIgnoreCase);
        var me = await client.GetStringAsync("/api/me");
        Assert.Contains("ProductManager", me);
        Assert.DoesNotContain("ControlAdmin", me);
        Assert.DoesNotContain(Password, cookie);
    }

    [Fact]
    public async Task LoginRequiresAntiforgeryAndRejectsBadPasswordWithoutSession()
    {
        await using var app = Factory(await Store());
        using var client = Client(app);
        var missingToken = await client.PostAsync("/Login", new FormUrlEncodedContent(
            new Dictionary<string, string> { ["Username"] = "product-manager", ["Password"] = Password }));
        Assert.Equal(HttpStatusCode.BadRequest, missingToken.StatusCode);
        var invalid = await Login(client, "incorrect-secret-never-render");
        Assert.Equal(HttpStatusCode.Unauthorized, invalid.StatusCode);
        Assert.DoesNotContain("incorrect-secret-never-render", await invalid.Content.ReadAsStringAsync());
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/me")).StatusCode);
    }

    [Fact]
    public async Task AuthenticatedWritesRequireOriginAndCsrfAndKeepRoles()
    {
        var store = await Store();
        await using var app = Factory(store);
        using var client = Client(app);
        Assert.Equal(HttpStatusCode.Redirect, (await Login(client, Password)).StatusCode);
        var tokens = JsonDocument.Parse(await client.GetStringAsync("/api/csrf"));
        var csrf = tokens.RootElement.GetProperty("token").GetString();
        using var noOrigin = new HttpRequestMessage(HttpMethod.Post, "/api/logout") { Content = new StringContent("{}") };
        noOrigin.Headers.Add("X-CSRF-TOKEN", csrf);
        Assert.Equal(HttpStatusCode.Forbidden, (await client.SendAsync(noOrigin)).StatusCode);
        client.DefaultRequestHeaders.Add("Origin", "https://localhost");
        Assert.Equal(HttpStatusCode.Forbidden, (await client.PostAsync("/api/logout", new StringContent("{}"))).StatusCode);
        client.DefaultRequestHeaders.Add("X-CSRF-TOKEN", csrf);
        var promote = await client.PostAsync("/api/rules/promote", new StringContent(
            """{"version":"v2","reason":"not my role","etag":"1"}""", System.Text.Encoding.UTF8, "application/json"));
        Assert.Equal(HttpStatusCode.Forbidden, promote.StatusCode);
        var row = (await store.Get<LabAccount>("accounts", "product-manager"))!;
        await store.Replace("accounts", "product-manager", row.Value with { SecurityStamp = "rotated" }, row.ETag);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/cases")).StatusCode);
    }

    [Fact]
    public async Task LogoutEndsSessionAndLoginEndpointIsRateLimited()
    {
        await using var app = Factory(await Store());
        using var client = Client(app);
        await Login(client, Password);
        using var tokens = JsonDocument.Parse(await client.GetStringAsync("/api/csrf"));
        client.DefaultRequestHeaders.Add("Origin", "https://localhost");
        client.DefaultRequestHeaders.Add("X-CSRF-TOKEN", tokens.RootElement.GetProperty("token").GetString());
        Assert.Equal(HttpStatusCode.OK, (await client.PostAsync("/api/logout", new StringContent("{}"))).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/me")).StatusCode);
        for (var i = 0; i < 30; i++)
            await client.PostAsync("/Login", new FormUrlEncodedContent(new Dictionary<string, string>()));
        Assert.Equal(HttpStatusCode.TooManyRequests,
            (await client.PostAsync("/Login", new FormUrlEncodedContent(new Dictionary<string, string>()))).StatusCode);
    }

    private static WebApplicationFactory<Program> Factory(IStateStore store) =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseEnvironment("Testing").ConfigureServices(services => services.AddSingleton(store)));

    private static HttpClient Client(WebApplicationFactory<Program> app) => app.CreateClient(
        new WebApplicationFactoryClientOptions { BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false });

    private static async Task<HttpResponseMessage> Login(HttpClient client, string password)
    {
        var html = await client.GetStringAsync("/Login");
        var token = WebUtility.HtmlDecode(Regex.Match(html,
            "name=\"__RequestVerificationToken\"[^>]*value=\"([^\"]+)\"").Groups[1].Value);
        Assert.NotEmpty(token);
        return await client.PostAsync("/Login", new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["Username"] = "product-manager", ["Password"] = password, ["__RequestVerificationToken"] = token
        }));
    }

    private static async Task<WorkflowTests.MemoryStore> Store()
    {
        var store = new WorkflowTests.MemoryStore();
        var account = new LabAccount("product-manager", string.Empty, ["ProductManager"], "initial-stamp");
        await store.Add("accounts", account.Username,
            account with { PasswordHash = new PasswordHasher<LabAccount>().HashPassword(account, Password) });
        return store;
    }

    private sealed class TestClock : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = new(2026, 10, 25, 18, 0, 0, TimeSpan.Zero);
        public override DateTimeOffset GetUtcNow() => Now;
    }
}
