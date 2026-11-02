using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using MobilityCommercial.Web.Models;
using MobilityCommercial.Web.Services;
using Xunit;

namespace MobilityCommercial.Tests;

/// <summary>Runs the real HTTP pipeline with explicit isolated dependencies and local JWT signing keys.</summary>
public sealed class HttpTests
{
    /// <summary>All shell, asset and API routes require a valid backend gateway identity.</summary>
    [Theory]
    [InlineData("/")]
    [InlineData("/app.js")]
    [InlineData("/app.css")]
    [InlineData("/api/opportunities")]
    [InlineData("/api/products")]
    [InlineData("/api/claims")]
    public async Task AnonymousBackendAccessIsRejected(string path)
    {
        using var factory = new TestApplication();
        using var client = factory.CreateClient();
        var response = await client.GetAsync(path);
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.Contains("authentication_required", body);
        Assert.True(response.Headers.Contains("x-correlation-id"));
    }

    /// <summary>Cryptographic issuer, audience, lifetime, signature and exact identity checks are enforced.</summary>
    [Theory]
    [InlineData("issuer", HttpStatusCode.Unauthorized)]
    [InlineData("audience", HttpStatusCode.Unauthorized)]
    [InlineData("expired", HttpStatusCode.Unauthorized)]
    [InlineData("signature", HttpStatusCode.Unauthorized)]
    [InlineData("object", HttpStatusCode.Forbidden)]
    [InlineData("tenant", HttpStatusCode.Forbidden)]
    public async Task InvalidTokensAreRejected(string fault, HttpStatusCode expected)
    {
        using var factory = new TestApplication();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", factory.Token(fault));
        var response = await client.GetAsync("/api/products");
        Assert.True(expected == response.StatusCode, $"Expected {expected}, actual {response.StatusCode}: {factory.AuthFailure}");
    }

    /// <summary>Exercises the real Razor shell, minimized reads, handoff and verification routes.</summary>
    [Fact]
    public async Task GatewayCanUseAllApprovedRoutes()
    {
        using var factory = new TestApplication();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", factory.Token());
        client.DefaultRequestHeaders.Add("x-correlation-id", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var page = await client.GetAsync("/");
        Assert.True(page.StatusCode == HttpStatusCode.OK, factory.AuthFailure);
        Assert.Contains("Adventure Works Cycles", await page.Content.ReadAsStringAsync());
        Assert.Contains("default-src 'self'", page.Headers.GetValues("Content-Security-Policy").Single());
        foreach (var asset in new[] { "/app.js", "/app.css" })
            Assert.Equal(HttpStatusCode.OK, (await client.GetAsync(asset)).StatusCode);
        var data = await client.GetStringAsync("/api/opportunities");
        Assert.DoesNotContain("internalMargin", data);
        Assert.DoesNotContain("contact", data);
        var response = await client.PostAsJsonAsync("/api/handoffs", new { opportunityId = "opp-002", request = "Prepare handoff" });
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var receipt = Json.Read<Receipt>(await response.Content.ReadAsStringAsync());
        var export = Environment.GetEnvironmentVariable("ABCBUILDER_APPLICATION_UI_EXPORT");
        if (!string.IsNullOrWhiteSpace(export))
        {
            Directory.CreateDirectory(export);
            await File.WriteAllTextAsync(Path.Combine(export, "index.html"), await page.Content.ReadAsStringAsync());
            await File.WriteAllTextAsync(Path.Combine(export, "opportunities.json"), data);
            await File.WriteAllTextAsync(Path.Combine(export, "products.json"), await client.GetStringAsync("/api/products"));
            await File.WriteAllTextAsync(Path.Combine(export, "claims.json"), await client.GetStringAsync("/api/claims"));
            await File.WriteAllTextAsync(Path.Combine(export, "receipt.json"), Json.Write(receipt));
        }
        Assert.Equal("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", receipt.Packet.CorrelationId);
        var verify = await client.PostAsJsonAsync("/api/receipts/verify", receipt);
        Assert.Equal(HttpStatusCode.OK, verify.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/receipts/verify",
            receipt with { Packet = receipt.Packet with { MarketingOwner = "tampered" } })).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await client.GetAsync("/api/tools/execute")).StatusCode);
    }

    /// <summary>Missing configuration has no demo fallback.</summary>
    [Fact]
    public void UnconfiguredStartupFailsExplicitly() =>
        Assert.Throws<InvalidOperationException>(() => AppSettings.Load(new ConfigurationBuilder().Build()));

    /// <summary>Malformed requests and missing product evidence return safe non-success errors.</summary>
    [Fact]
    public async Task RequestFailuresAreExplicitAndCorrelated()
    {
        using var factory = new TestApplication();
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", factory.Token());
        var unknown = await client.PostAsJsonAsync("/api/handoffs", new { opportunityId = "opp-004", request = "Prepare" });
        Assert.Equal(HttpStatusCode.NotFound, unknown.StatusCode);
        Assert.Contains("unknown_product", await unknown.Content.ReadAsStringAsync());
        var malformed = await client.PostAsync("/api/handoffs", new StringContent("{", System.Text.Encoding.UTF8, "application/json"));
        Assert.Equal(HttpStatusCode.BadRequest, malformed.StatusCode);
        Assert.Contains("correlationId", await malformed.Content.ReadAsStringAsync());
    }

    internal sealed class TestApplication : WebApplicationFactory<Program>
    {
        internal string AuthFailure = string.Empty;
        private static readonly RSA SigningRsa = RSA.Create(2048);
        private static readonly RsaSecurityKey SigningKey = new(SigningRsa) { KeyId = "isolated-test-key" };

        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder.UseEnvironment("Production");
            var settings = WorkflowTests.Settings;
            var values = new Dictionary<string, string> {
                ["Foundry:ProjectEndpoint"] = settings.ProjectEndpoint.AbsoluteUri,
                ["Foundry:ModelDeployment"] = settings.Model,
                ["Foundry:SalesAgentName"] = settings.Sales.Name, ["Foundry:SalesAgentVersion"] = settings.Sales.Version,
                ["Foundry:MarketingAgentName"] = settings.Marketing.Name, ["Foundry:MarketingAgentVersion"] = settings.Marketing.Version,
                ["Foundry:CoordinatorAgentName"] = settings.Coordinator.Name, ["Foundry:CoordinatorAgentVersion"] = settings.Coordinator.Version,
                ["Fixtures:BlobEndpoint"] = settings.BlobEndpoint.AbsoluteUri,
                ["Fixtures:ContainerName"] = settings.Container, ["Fixtures:ManifestSha256"] = settings.ManifestHash,
                ["Signing:KeyUri"] = settings.KeyUri.AbsoluteUri, ["Signing:Algorithm"] = "PS256",
                ["BackendAuth:TenantId"] = settings.TenantId, ["BackendAuth:Audience"] = settings.Audience,
                ["BackendAuth:GatewayObjectId"] = settings.GatewayObjectId,
                ["BackendAuth:Authority"] = $"https://login.microsoftonline.com/{settings.TenantId}/v2.0",
                ["AZURE_CLIENT_ID"] = settings.ClientId,
                ["Limits:MaxInputCharacters"] = "4000", ["Limits:MaxOutputTokens"] = "800",
                ["Limits:MaxResponsesRequests"] = "7", ["Limits:MaxCumulativeTokens"] = "30000",
                ["Limits:DeadlineSeconds"] = "90", ["Limits:MaxConcurrentHandoffs"] = "4"
            };
            foreach (var (key, value) in values) builder.UseSetting(key, value);
            builder.ConfigureServices(services =>
            {
                services.RemoveAll<IFixtures>();
                services.RemoveAll<IAgentGateway>();
                services.RemoveAll<IReceiptSigner>();
                services.AddSingleton<IFixtures, WorkflowTests.TestFixtures>();
                services.AddSingleton<IAgentGateway>(new WorkflowTests.TestGateway("opp-002"));
                services.AddSingleton<IReceiptSigner, WorkflowTests.TestSigner>();
                services.PostConfigure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme, options =>
                {
                    options.Configuration = new OpenIdConnectConfiguration { Issuer = options.Authority };
                    options.Configuration.SigningKeys.Add(SigningKey);
                    options.ConfigurationManager =
                        new Microsoft.IdentityModel.Protocols.StaticConfigurationManager<OpenIdConnectConfiguration>(options.Configuration);
                    options.TokenValidationParameters.IssuerSigningKey = SigningKey;
                    options.Events.OnAuthenticationFailed = context =>
                    {
                        AuthFailure = context.Exception.GetType().Name + ": " + context.Exception.Message;
                        return Task.CompletedTask;
                    };
                });
            });
        }

        internal string Token(string fault = "")
        {
            using var wrongRsa = RSA.Create(2048);
            var key = fault == "signature" ? new RsaSecurityKey(wrongRsa) { KeyId = "wrong-key" } : SigningKey;
            var settings = WorkflowTests.Settings;
            var now = DateTime.UtcNow;
            var token = new JwtSecurityToken(
                issuer: fault == "issuer" ? "https://wrong.invalid/" : $"https://login.microsoftonline.com/{settings.TenantId}/v2.0",
                audience: fault == "audience" ? "wrong-audience" : settings.Audience,
                claims: [new Claim("oid", fault == "object" ? settings.ClientId : settings.GatewayObjectId),
                    new Claim("tid", fault == "tenant" ? settings.ClientId : settings.TenantId)],
                notBefore: now.AddHours(-2),
                expires: fault == "expired" ? now.AddHours(-1) : now.AddMinutes(5),
                signingCredentials: new SigningCredentials(key, SecurityAlgorithms.RsaSha256));
            lock (SigningRsa) return new JwtSecurityTokenHandler().WriteToken(token);
        }
    }
}
