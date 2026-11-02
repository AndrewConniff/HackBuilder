using System.Net;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using BankSupport.Web.Models;
using BankSupport.Web.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace BankSupport.Tests;

/// <summary>In-process HTTP tests exercise real cookie authentication, Razor CSRF and role policies.</summary>
public sealed class HttpSecurityTests
{
    /// <summary>Anonymous requests cannot view customer or representative pages.</summary>
    [Theory]
    [InlineData("/")]
    [InlineData("/Queue")]
    public async Task AnonymousIsRedirectedToLogin(string path)
    {
        await using var factory = new BankFactory();
        using var client = factory.Client();
        var response = await client.GetAsync(path);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.StartsWith("https://localhost/Login", response.Headers.Location?.ToString());
    }

    /// <summary>Missing antiforgery tokens cannot create conversations or authenticate.</summary>
    [Fact]
    public async Task ForgedLoginAndCustomerPostsAreDenied()
    {
        await using var factory = new BankFactory();
        using var client = factory.Client();
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsync("/Login",
            new FormUrlEncodedContent(new Dictionary<string, string>
            { ["username"] = "customer-1", ["password"] = factory.Password }))).StatusCode);
        await factory.LoginAsync(client);
        Assert.Equal(HttpStatusCode.BadRequest,
            (await client.PostAsync("/?handler=Start", new FormUrlEncodedContent([]))).StatusCode);
    }

    /// <summary>Secure cookies, logout and wrong-role denial preserve the intended role boundary.</summary>
    [Fact]
    public async Task CustomerLoginLogoutAndWrongRole()
    {
        await using var factory = new BankFactory();
        using var client = factory.Client();
        var login = await factory.LoginAsync(client);
        var cookie = string.Join(";", login.Headers.GetValues("Set-Cookie"));
        Assert.Contains("secure", cookie.ToLowerInvariant());
        Assert.Contains("httponly", cookie.ToLowerInvariant());
        Assert.Contains("samesite=strict", cookie.ToLowerInvariant());
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/")).StatusCode);
        var wrongRole = await client.GetAsync("/Queue");
        Assert.Equal(HttpStatusCode.Redirect, wrongRole.StatusCode);
        Assert.Contains("/Denied", wrongRole.Headers.Location?.ToString());
        Assert.Equal(HttpStatusCode.Forbidden, (await client.GetAsync("/Denied")).StatusCode);
        var logoutPage = await client.GetStringAsync("/Logout");
        var logout = await client.PostAsync("/Logout", BankFactory.Form(logoutPage));
        Assert.Equal(HttpStatusCode.Redirect, logout.StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
    }

    /// <summary>The fifth failed login locks the durable account, even when the next password is correct.</summary>
    [Fact]
    public async Task FiveFailuresLockAccount()
    {
        await using var factory = new BankFactory();
        using var client = factory.Client();
        for (var i = 0; i < 5; i++)
        {
            var html = await client.GetStringAsync("/Login");
            var failed = await client.PostAsync("/Login", BankFactory.Form(html,
                ("username", "customer-1"), ("password", "incorrect-test-password")));
            Assert.Equal(HttpStatusCode.Unauthorized, failed.StatusCode);
        }
        var locked = await factory.LoginAsync(client);
        Assert.Equal(HttpStatusCode.Unauthorized, locked.StatusCode);
        var saved = await factory.Store.GetAsync<LocalAccount>("users", "customer-1");
        Assert.True(saved!.Value.LockedUntil > DateTimeOffset.UtcNow);
    }

    /// <summary>Live HTTP case actions enforce customer isolation, current versions and the human queue.</summary>
    [Fact]
    public async Task CustomerStartsAndEscalatesCase()
    {
        await using var factory = new BankFactory();
        using var client = factory.Client();
        await factory.LoginAsync(client);
        var start = await client.PostAsync("/?handler=Start", BankFactory.Form(await client.GetStringAsync("/")));
        Assert.Equal(HttpStatusCode.Redirect, start.StatusCode);
        var location = start.Headers.Location!.ToString();
        var id = location.Split("id=")[1];
        var html = await client.GetStringAsync(location);
        var escalation = await client.PostAsync("/?handler=Send", BankFactory.Form(html,
            ("id", id), ("version", "0"), ("text", "Please investigate this activity"), ("human", "true")));
        Assert.Equal(HttpStatusCode.Redirect, escalation.StatusCode);
        Assert.Equal("AwaitingHuman", (await factory.Store.GetAsync<ServiceCase>("cases", id))!.Value.Status);
        var other = await factory.Workflow.StartAsync("customer-2", default);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync("/?id=" + other)).StatusCode);
    }

    /// <summary>Session revocation is verified against the durable account on each request.</summary>
    [Fact]
    public async Task ChangedStampRevokesExistingSession()
    {
        await using var factory = new BankFactory();
        using var client = factory.Client();
        await factory.LoginAsync(client);
        var saved = (await factory.Store.GetAsync<LocalAccount>("users", "customer-1"))!;
        await factory.Store.ReplaceAsync("users", "customer-1", saved.Value with { Stamp = "revoked" }, saved.ETag);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
    }
}

internal sealed class BankFactory : WebApplicationFactory<Program>
{
    internal readonly MemoryStore Store = new();
    internal string Password { get; } = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
    internal BankingWorkflow Workflow => Services.GetRequiredService<BankingWorkflow>();
    private readonly string keys = Path.Combine(Path.GetTempPath(), "bank-support-tests-" + Guid.NewGuid().ToString("N"));

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseSetting("SESSION_KEYS_PATH", keys);
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<IDocumentStore>();
            services.AddSingleton<IDocumentStore>(Store);
            services.RemoveAll<IFoundryGateway>();
            services.AddSingleton<IFoundryGateway>(new FakeFoundry());
        });
        var user = new LocalAccount("customer-1", "Airi Ilves", "Customer", "customer-1", "", "initial");
        Store.AddAsync("users", user.Username,
            user with { PasswordHash = new PasswordHasher<LocalAccount>().HashPassword(user, Password) }).GetAwaiter().GetResult();
    }

    internal HttpClient Client() => CreateClient(new WebApplicationFactoryClientOptions
    {
        BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false, HandleCookies = true
    });

    internal async Task<HttpResponseMessage> LoginAsync(HttpClient client) =>
        await client.PostAsync("/Login", Form(await client.GetStringAsync("/Login"),
            ("username", "customer-1"), ("password", Password)));

    internal static FormUrlEncodedContent Form(string html, params (string Key, string Value)[] fields)
    {
        var match = Regex.Match(html, "name=\"__RequestVerificationToken\"[^>]*value=\"([^\"]+)\"");
        Assert.True(match.Success, "Razor form did not include an antiforgery token.");
        var values = fields.ToDictionary(p => p.Key, p => p.Value);
        values["__RequestVerificationToken"] = WebUtility.HtmlDecode(match.Groups[1].Value);
        return new FormUrlEncodedContent(values);
    }

    public override async ValueTask DisposeAsync()
    {
        await base.DisposeAsync();
        if (Directory.Exists(keys)) Directory.Delete(keys, recursive: true);
    }
}
