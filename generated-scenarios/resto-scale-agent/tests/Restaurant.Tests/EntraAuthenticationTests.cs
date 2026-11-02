using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using Restaurant.Web.Models;
using Restaurant.Web.Services;
using Xunit;

namespace Restaurant.Tests;

/// <summary>Real JWT middleware with offline test keys; no Entra sign-in or cloud success is implied.</summary>
public sealed class EntraAuthenticationTests
{
    private const string Tenant = "00000000-0000-0000-0000-000000000001";
    private const string Api = "00000000-0000-0000-0000-000000000002";
    private const string Client = "00000000-0000-0000-0000-000000000003";
    private const string Subject = "00000000-0000-0000-0000-000000000004";
    private static readonly RsaSecurityKey Key = new(RSA.Create(2048)) { KeyId = "offline-test-only" };
    private static readonly string Issuer = $"https://login.microsoftonline.com/{Tenant}/v2.0";

    private static WebApplicationFactory<Program> Factory(string role = "web") =>
        new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Testing");
            foreach (var (key, value) in new Dictionary<string, string?>
            {
                ["STAFF_AUTH_MODE"] = "entra", ["STAFF_TENANT_ID"] = Tenant,
                ["STAFF_AUDIENCE"] = Api, ["STAFF_CLIENT_ID"] = Client, ["APP_ROLE"] = role,
                ["COSMOS_ENDPOINT"] = string.Empty
            })
                builder.UseSetting(key, value);
            builder.ConfigureServices(services => services.PostConfigure<JwtBearerOptions>("staff", options =>
            {
                var metadata = new OpenIdConnectConfiguration { Issuer = Issuer };
                metadata.SigningKeys.Add(Key);
                options.ConfigurationManager = new StaticConfigurationManager<OpenIdConnectConfiguration>(metadata);
            }));
        });

    private static string Token(string? change = null)
    {
        var claims = new Dictionary<string, object>
        {
            ["sub"] = Subject, ["oid"] = Subject, ["tid"] = Tenant, ["ver"] = "2.0", ["azp"] = Client,
            ["scp"] = "access_as_user", ["roles"] = new[] { "Server", "Floor.3" }, ["name"] = "Hasan Ibrahimov"
        };
        switch (change)
        {
            case "tenant": claims["tid"] = Client; break;
            case "client": claims["azp"] = Api; break;
            case "id-token": claims.Remove("scp"); break;
            case "scope": claims["scp"] = "unrelated"; break;
            case "role": claims["roles"] = new[] { "Floor.3" }; break;
            case "floor": claims["roles"] = new[] { "Server" }; claims["floors"] = "1,2,3,4,5"; break;
            case "oid": claims.Remove("oid"); break;
        }
        return new JsonWebTokenHandler().CreateToken(new SecurityTokenDescriptor
        {
            Issuer = change == "issuer" ? "https://foreign.invalid" : Issuer,
            Audience = change == "audience" ? Client : Api,
            NotBefore = DateTime.UtcNow.AddMinutes(-10),
            Expires = DateTime.UtcNow.AddMinutes(change == "expired" ? -1 : 10),
            Claims = claims,
            SigningCredentials = new(change == "signature"
                ? new RsaSecurityKey(RSA.Create(2048)) : Key, SecurityAlgorithms.RsaSha256)
        });
    }

    /// <summary>Issuer, tenant, audience, expiry, signature, delegated scope, client and app roles fail closed.</summary>
    [Theory]
    [InlineData("tenant")]
    [InlineData("issuer")]
    [InlineData("audience")]
    [InlineData("expired")]
    [InlineData("signature")]
    [InlineData("id-token")]
    [InlineData("scope")]
    [InlineData("client")]
    [InlineData("role")]
    [InlineData("floor")]
    [InlineData("oid")]
    public async Task InvalidStaffTokensAreRejectedAtBothBoundaries(string change)
    {
        foreach (var role in new[] { "web", "chat" })
        {
            await using var factory = Factory(role);
            using var client = factory.CreateClient(new() { BaseAddress = new("https://localhost") });
            client.DefaultRequestHeaders.Authorization = new("Bearer", Token(change));
            var response = role == "web" ? await client.GetAsync("/api/staff/session")
                : await client.PostAsJsonAsync("/api/chat", new { message = "Read kitchen status" });
            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        }
    }

    /// <summary>Verified access tokens yield server-owned role/floor scope and secure bounded cookie sessions.</summary>
    [Fact]
    public async Task EntraCookieExchangeRevalidatesTokenAndRequiresCsrf()
    {
        await using var factory = Factory();
        using var client = factory.CreateClient(new() { BaseAddress = new("https://localhost") });
        var proof = Token();
        client.DefaultRequestHeaders.Authorization = new("Bearer", proof);
        Assert.Equal(HttpStatusCode.Forbidden, (await client.PostAsJsonAsync("/api/staff/session", new { })).StatusCode);
        var csrf = await client.GetFromJsonAsync<JsonElement>("/api/session/csrf");
        client.DefaultRequestHeaders.Add("X-CSRF-TOKEN", csrf.GetProperty("token").GetString());
        var login = await client.PostAsJsonAsync("/api/staff/session", new { role = "Manager", floors = new[] { 1 } });
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var cookie = login.Headers.GetValues("Set-Cookie").Single(value => value.StartsWith(StaffAuthentication.CookieName + "="));
        Assert.Contains("secure", cookie);
        Assert.Contains("httponly", cookie);
        Assert.Contains("samesite=strict", cookie);
        Assert.DoesNotContain(proof, await login.Content.ReadAsStringAsync());
        client.DefaultRequestHeaders.Authorization = null;
        var me = await client.GetFromJsonAsync<JsonElement>("/api/staff/session");
        Assert.Equal("Server", me.GetProperty("role").GetString());
        Assert.Equal([3], me.GetProperty("floors").EnumerateArray().Select(item => item.GetInt32()));
        Assert.Equal(HttpStatusCode.OK, (await client.PostAsJsonAsync("/api/staff/logout", new { })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/staff/session")).StatusCode);
    }

    /// <summary>Synthetic secrets, even when present, cannot activate a fallback on deployed hosts.</summary>
    [Theory]
    [InlineData("Production", null)]
    [InlineData("Testing", "deployed-identity")]
    public void SyntheticModeCannotRunOnDeployment(string environment, string? identity)
    {
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["STAFF_AUTH_MODE"] = "synthetic-local", ["AZURE_CLIENT_ID"] = identity
        }).Build();
        Assert.Throws<InvalidOperationException>(() => new StaffAuthentication(configuration, TimeProvider.System,
            new StaffAuthenticationTests.LocalEnvironment { EnvironmentName = environment }));
    }

    /// <summary>A synthetic issuer cannot authenticate through the default Entra middleware.</summary>
    [Fact]
    public async Task SyntheticStaffIssuerIsRejectedInEntraMode()
    {
        await using var factory = Factory();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", "synthetic-proof");
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync("/api/staff/session")).StatusCode);
    }

    /// <summary>The web proxy forwards the original verified bearer, not browser-provided role/floor headers.</summary>
    [Fact]
    public async Task StaffProofPropagatesToInternalChatWithoutReissuance()
    {
        var transport = new CaptureChat();
        await using var factory = Factory().WithWebHostBuilder(builder =>
        {
            builder.UseSetting("CHAT_BASE_URL", "https://internal-chat.invalid");
            builder.ConfigureServices(services => services.AddHttpClient("internal")
                .ConfigurePrimaryHttpMessageHandler(() => transport));
        });
        using var client = factory.CreateClient(new() { BaseAddress = new("https://localhost") });
        var proof = Token();
        client.DefaultRequestHeaders.Authorization = new("Bearer", proof);
        client.DefaultRequestHeaders.Add("X-Staff-Role", "Manager");
        Assert.Equal(HttpStatusCode.OK,
            (await client.PostAsJsonAsync("/api/chat", new { message = "Read kitchen status" })).StatusCode);
        Assert.Equal(proof, transport.Proof);
        Assert.False(transport.RoleHeaderForwarded);
    }

    private sealed class CaptureChat : HttpMessageHandler
    {
        public string? Proof { get; private set; }
        public bool RoleHeaderForwarded { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            Proof = request.Headers.Authorization?.Parameter;
            RoleHeaderForwarded = request.Headers.Contains("X-Staff-Role");
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
                { Content = JsonContent.Create(new { TransportOnly = true }) });
        }
    }
}
