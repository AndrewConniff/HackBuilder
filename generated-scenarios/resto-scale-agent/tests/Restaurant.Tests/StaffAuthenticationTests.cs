using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using Restaurant.Web.Models;
using Restaurant.Web.Services;
using Xunit;

namespace Restaurant.Tests;

/// <summary>Real local authentication tests. No Azure, alternate identity handler or deployed auth bypass.</summary>
public sealed class StaffAuthenticationTests
{
    private static readonly string Password = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
    private static readonly StaffConfiguration Settings = CreateSettings();

    private static StaffConfiguration CreateSettings()
    {
        var hasher = new PasswordHasher<StaffAccount>();
        var accounts = new[] { "Manager", "Host", "Server", "Kitchen" }.Select(role =>
        {
            var account = new StaffAccount(role.ToLowerInvariant() + "-001", "Synthetic fixture", role, [3], string.Empty);
            return account with { PasswordHash = hasher.HashPassword(account, Password) };
        }).ToArray();
        return new(Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)), Guid.NewGuid().ToString("N"), accounts);
    }

    private static StaffAuthentication Service(StaffConfiguration? settings = null, TimeProvider? clock = null) =>
        new(new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        { ["STAFF_AUTH_JSON"] = JsonSerializer.Serialize(settings ?? Settings),
            ["STAFF_AUTH_MODE"] = "synthetic-local" }).Build(), clock ?? TimeProvider.System, new LocalEnvironment());

    private static WebApplicationFactory<Program> Factory() =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            builder.UseEnvironment("Testing").UseSetting("STAFF_AUTH_MODE", "synthetic-local")
                .UseSetting("COSMOS_ENDPOINT", string.Empty)
                .ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(
                new Dictionary<string, string?> { ["STAFF_AUTH_JSON"] = JsonSerializer.Serialize(Settings),
                    ["STAFF_AUTH_MODE"] = "synthetic-local" })));

    private static HttpClient Client(WebApplicationFactory<Program> factory) =>
        factory.CreateClient(new() { BaseAddress = new Uri("https://localhost") });

    private static async Task Csrf(HttpClient client)
    {
        var json = await client.GetFromJsonAsync<JsonElement>("/api/session/csrf");
        client.DefaultRequestHeaders.Remove("X-CSRF-TOKEN");
        client.DefaultRequestHeaders.Add("X-CSRF-TOKEN", json.GetProperty("token").GetString());
    }

    /// <summary>Each password yields only its installed role; cross-floor and kitchen financial denials survive.</summary>
    [Theory]
    [InlineData("Manager")]
    [InlineData("Host")]
    [InlineData("Server")]
    [InlineData("Kitchen")]
    public async Task InstalledEmployeePermissionsRemainServerOwned(string role)
    {
        var service = Service();
        var principal = await service.Validate(service.Login(role.ToLowerInvariant() + "-001", Password));
        var caller = Caller.From(principal);
        Assert.Equal(role, caller.Role);
        Assert.Equal(role == "Manager" ? [1, 2, 3, 4, 5] : new[] { 3 }, caller.Floors);
        var visit = new Visit("v", "visit:v", "visit", 1, "r", "2026-10-24:1", 3, 1, "Airi Ilves",
            "unused", "Reserved", [], false, null, "synthetic");
        caller.Demand(visit);
        if (role != "Manager") Assert.Throws<DomainException>(() => caller.Demand(visit with { Floor = 2 }));
        if (role == "Kitchen") Assert.Throws<DomainException>(() => caller.Demand(visit, financial: true));
        if (role is "Kitchen" or "Host")
            Assert.Throws<DomainException>(() => Rules.Apply(visit with { Status = "Active" },
                new("settle", "v", 1), caller, [], DateTimeOffset.UtcNow));
    }

    /// <summary>Missing setup and wrong, unknown and case-changed credentials never authenticate.</summary>
    [Fact]
    public void NoCredentialOrConfigurationFallback()
    {
        var service = Service();
        foreach (var id in new[] { "manager-001", "unknown", "MANAGER-001" })
            Assert.Equal(401, Assert.Throws<DomainException>(() => service.Login(id, "wrong")).Status);
        var missing = new StaffAuthentication(new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["STAFF_AUTH_MODE"] = "synthetic-local" }).Build(),
            TimeProvider.System, new LocalEnvironment());
        Assert.Equal(503, Assert.Throws<DomainException>(() => missing.Login("manager-001", Password)).Status);
    }

    /// <summary>Expiry, signature, issuer, audience and installation reset are independently enforced.</summary>
    [Fact]
    public async Task ExpiredForeignForgedAndResetProofsFail()
    {
        var clock = new TestClock(DateTimeOffset.UtcNow);
        var service = Service(clock: clock);
        var proof = service.Login("server-001", Password);
        Assert.Equal("Server", Caller.From(await service.Validate(proof)).Role);
        clock.Now = clock.Now.AddMinutes(31);
        await Assert.ThrowsAsync<DomainException>(() => service.Validate(proof));
        await Assert.ThrowsAsync<DomainException>(() => Service(Settings with { Generation = "rotated" }).Validate(proof));
        await Assert.ThrowsAsync<DomainException>(() => Service().Validate(proof + "modified"));
        await Assert.ThrowsAsync<DomainException>(() => Service().Validate("unsigned-manager"));
        foreach (var (issuer, audience) in new[] { ("foreign", "resto-scale-agent-staff"),
            ("fourth-coffee-synthetic-staff", "foreign") })
            await Assert.ThrowsAsync<DomainException>(() => Service().Validate(SignedProof(issuer, audience)));
    }

    private static string SignedProof(string issuer = "fourth-coffee-synthetic-staff", string audience = "resto-scale-agent-staff") =>
        new JsonWebTokenHandler().CreateToken(new SecurityTokenDescriptor
        {
            Issuer = issuer, Audience = audience, NotBefore = DateTime.UtcNow, Expires = DateTime.UtcNow.AddMinutes(30),
            Claims = new Dictionary<string, object> {
                ["sub"] = "server-001", ["generation"] = Settings.Generation, ["roles"] = "Manager", ["floors"] = "1,2,3,4,5" },
            SigningCredentials = new(new SymmetricSecurityKey(Convert.FromBase64String(Settings.SigningKey)),
                SecurityAlgorithms.HmacSha256)
        });

    /// <summary>Even signed surplus role claims are ignored in favor of server records.</summary>
    [Fact]
    public async Task ProofCannotOverrideInstalledPermissions()
    {
        var caller = Caller.From(await Service().Validate(SignedProof()));
        Assert.Equal("Server", caller.Role);
        Assert.Equal([3], caller.Floors);
    }

    /// <summary>Exercises login, secure cookies, CSRF rebinding, identity view and logout on real middleware.</summary>
    [Fact]
    public async Task LoginCookieCsrfLogoutAndBrowserRoleForgery()
    {
        await using var factory = Factory();
        using var client = Client(factory);
        var denied = await client.PostAsJsonAsync("/api/staff/session", new { employeeId = "server-001", password = Password });
        Assert.Equal(HttpStatusCode.Forbidden, denied.StatusCode);
        await Csrf(client);
        var login = await client.PostAsJsonAsync("/api/staff/session",
            new { employeeId = "server-001", password = Password, role = "Manager", floors = new[] { 1, 2, 3, 4, 5 } });
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var cookie = login.Headers.GetValues("Set-Cookie").Single(v => v.StartsWith(StaffAuthentication.CookieName + "="));
        Assert.Contains("secure", cookie);
        Assert.Contains("httponly", cookie);
        Assert.Contains("samesite=strict", cookie);
        Assert.Contains("max-age=1800", cookie);
        Assert.DoesNotContain(Password, await login.Content.ReadAsStringAsync());
        var me = await client.GetFromJsonAsync<JsonElement>("/api/staff/session");
        Assert.Equal("Server", me.GetProperty("role").GetString());
        Assert.Equal(3, me.GetProperty("floors")[0].GetInt32());
        // CSRF token from the anonymous identity is not valid for a signed-in identity.
        Assert.Equal(HttpStatusCode.Forbidden,
            (await client.PostAsJsonAsync("/api/staff/logout", new { })).StatusCode);
        await Csrf(client);
        Assert.Equal(HttpStatusCode.OK, (await client.PostAsJsonAsync("/api/staff/logout", new { })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/staff/session")).StatusCode);
    }

    /// <summary>Bad passwords/unknown IDs have identical public failures and repeated attempts are throttled.</summary>
    [Fact]
    public async Task FailedLoginsAreGenericAndRateLimited()
    {
        await using var factory = Factory();
        using var client = Client(factory);
        await Csrf(client);
        string? first = null;
        for (var i = 0; i < 12; i++)
        {
            var response = await client.PostAsJsonAsync("/api/staff/session",
                new { employeeId = i % 2 == 0 ? "manager-001" : "unknown", password = "incorrect" });
            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
            var payload = await response.Content.ReadFromJsonAsync<JsonElement>();
            var detail = payload.GetProperty("detail").GetString();
            first ??= detail;
            Assert.Equal(first, detail);
        }
        Assert.Equal(HttpStatusCode.TooManyRequests,
            (await client.PostAsJsonAsync("/api/staff/session", new { employeeId = "manager-001", password = Password })).StatusCode);
    }

    /// <summary>A forwarded staff bearer is verified by the same implementation used on internal chat.</summary>
    [Fact]
    public async Task ForwardedProofAndForgedCookieAreNotTrustedByTransport()
    {
        await using var factory = Factory();
        using var client = Client(factory);
        client.DefaultRequestHeaders.Authorization = new("Bearer", Service().Login("kitchen-001", Password));
        var identity = await client.GetFromJsonAsync<JsonElement>("/api/staff/session");
        Assert.Equal("Kitchen", identity.GetProperty("role").GetString());
        client.DefaultRequestHeaders.Authorization = new("Bearer", "forged");
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/staff/session")).StatusCode);
        client.DefaultRequestHeaders.Authorization = null;
        client.DefaultRequestHeaders.Add("Cookie", $"{StaffAuthentication.CookieName}=forged");
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/staff/session")).StatusCode);
    }

    private sealed class TestClock(DateTimeOffset now) : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = now;
        public override DateTimeOffset GetUtcNow() => Now;
    }

    /// <summary>Explicit isolated host for the retained synthetic authentication tests.</summary>
    public sealed class LocalEnvironment : IHostEnvironment
    {
        /// <inheritdoc />
        public string EnvironmentName { get; set; } = "Testing";
        /// <inheritdoc />
        public string ApplicationName { get; set; } = "Restaurant.Tests";
        /// <inheritdoc />
        public string ContentRootPath { get; set; } = AppContext.BaseDirectory;
        /// <inheritdoc />
        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }
}
