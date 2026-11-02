using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Brokerage.Web;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace Brokerage.Tests;

public sealed class ChatTests
{
    [Fact]
    public async Task ReceiptSignsExactAnswerAndCitesInstalledSource()
    {
        var backend = new TestBackend();
        var service = new ChatService(backend, NullLogger<ChatService>.Instance);
        var reply = await service.SendAsync("What is a limit order?", "local-test", CancellationToken.None);
        Assert.Equal(["FAQ-02"], reply.Sources);
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(reply.Answer))), reply.Digest);
        Assert.Equal(backend.SignedDigest, Convert.FromHexString(reply.Digest));
        Assert.Equal("response-test", reply.AgentResponseId);
    }

    [Fact]
    public async Task UnknownCitationFailsRatherThanReturningFabricatedEvidence()
    {
        var backend = new TestBackend { Answer = "Invented fee [FAQ-99]" };
        var service = new ChatService(backend, NullLogger<ChatService>.Instance);
        await Assert.ThrowsAsync<InvalidDataException>(() =>
            service.SendAsync("fees?", "local-test", CancellationToken.None));
    }

    [Fact]
    public async Task UpstreamFailureNeverReturnsMockSuccess()
    {
        var backend = new TestBackend { Fail = true };
        var service = new ChatService(backend, NullLogger<ChatService>.Instance);
        await Assert.ThrowsAsync<InvalidDataException>(() =>
            service.SendAsync("question", "local-test", CancellationToken.None));
    }

    [Theory]
    [InlineData("/")]
    [InlineData("/site.css")]
    public async Task BackendRejectsAnonymousRequests(string path)
    {
        await using var host = new TestHost();
        Assert.Equal(HttpStatusCode.Unauthorized, (await host.CreateClient().GetAsync(path)).StatusCode);
    }

    [Fact]
    public async Task BackendRejectsAnonymousChat()
    {
        await using var host = new TestHost();
        var response = await host.CreateClient().PostAsJsonAsync("/api/chat", new { message = "order types?" });
        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public void MissingConfigurationIsAnExplicitStartupFailure()
    {
        Assert.Throws<InvalidOperationException>(() =>
            WorkloadSettings.Load(new ConfigurationBuilder().Build()));
    }

    [Fact]
    public void InstallationFixturesAreCopiedWithTheApplication()
    {
        var source = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "SeedData", "brokerage-faq.md"));
        Assert.Contains("FAQ-01", source);
        Assert.Contains("FAQ-12", source);
        Assert.Contains("Adatum Corporation", source);
        Assert.True(File.Exists(Path.Combine(AppContext.BaseDirectory, "SeedData", "agent-instructions.txt")));
    }

    [Fact]
    public async Task GatewayTokenCanLoadUiAndSendAQuestion()
    {
        await using var host = new TestHost();
        var client = host.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", host.Token());
        var correlation = Guid.NewGuid().ToString();
        client.DefaultRequestHeaders.Add("X-Correlation-ID", correlation);
        Assert.Contains("Adatum Corporation", await client.GetStringAsync("/"));
        var response = await client.PostAsJsonAsync("/api/chat", new { message = "limit orders?" });
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var reply = await response.Content.ReadFromJsonAsync<ChatReply>();
        Assert.Equal(correlation, reply!.CorrelationId);
        Assert.Equal(["FAQ-02"], reply.Sources);
    }

    [Theory]
    [InlineData("wrong-identity", HttpStatusCode.Forbidden)]
    [InlineData("wrong-tenant", HttpStatusCode.Forbidden)]
    [InlineData("wrong-audience", HttpStatusCode.Unauthorized)]
    [InlineData("expired", HttpStatusCode.Unauthorized)]
    [InlineData("wrong-issuer", HttpStatusCode.Unauthorized)]
    public async Task BackendEnforcesIdentityTokenBoundaries(string failure, HttpStatusCode expected)
    {
        await using var host = new TestHost();
        var client = host.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", host.Token(failure));
        Assert.Equal(expected, (await client.GetAsync("/")).StatusCode);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task AuthorizedInvalidQuestionReturnsExplicitBadRequest(string message)
    {
        await using var host = new TestHost();
        var client = host.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", host.Token());
        var result = await client.PostAsJsonAsync("/api/chat", new { message });
        Assert.Equal(HttpStatusCode.BadRequest, result.StatusCode);
    }

    [Fact]
    public async Task AuthorizedOversizedQuestionReturnsBadRequest()
    {
        await using var host = new TestHost();
        var client = host.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", host.Token());
        var result = await client.PostAsJsonAsync("/api/chat", new { message = new string('a', 2001) });
        Assert.Equal(HttpStatusCode.BadRequest, result.StatusCode);
    }

    [Fact]
    public async Task UpstreamFailureIsAnExplicitSanitizedHttpFailure()
    {
        await using var host = new TestHost(failBackend: true);
        var client = host.CreateClient();
        client.DefaultRequestHeaders.Authorization = new("Bearer", host.Token());
        var result = await client.PostAsJsonAsync("/api/chat", new { message = "limits?" });
        Assert.Equal(HttpStatusCode.BadGateway, result.StatusCode);
        var body = await result.Content.ReadAsStringAsync();
        Assert.Contains("correlationId", body);
        Assert.DoesNotContain("test upstream", body);
    }
}

internal sealed class TestBackend : IChatBackend
{
    internal string Answer { get; init; } = "A limit sets an acceptable price [FAQ-02]. Educational only.";
    internal bool Fail { get; init; }
    internal byte[]? SignedDigest { get; private set; }
    public Task<string> ReadFaqAsync(CancellationToken cancellationToken) =>
        Task.FromResult("FAQ-02 Limit orders may never execute.");
    public Task<AgentAnswer> InvokeAsync(string message, string source, CancellationToken cancellationToken) =>
        Fail ? throw new InvalidDataException("test upstream failure") : Task.FromResult(new AgentAnswer(Answer, "response-test"));
    public Task<ReceiptSignature> SignAsync(byte[] digest, CancellationToken cancellationToken)
    {
        SignedDigest = digest;
        return Task.FromResult(new ReceiptSignature("test-signature", "https://test.vault.azure.net/keys/receipt/version"));
    }
}

internal sealed class TestHost(bool failBackend = false) : WebApplicationFactory<Program>
{
    private const string Tenant = "22222222-2222-2222-2222-222222222222";
    private const string Gateway = "33333333-3333-3333-3333-333333333333";
    private const string Audience = "api://44444444-4444-4444-4444-444444444444";
    private static readonly SymmetricSecurityKey TestKey = new(
        Encoding.UTF8.GetBytes("local-test-only-signing-material-not-a-production-key-01234567890123456789"));

    internal string Token(string failure = "")
    {
        var now = DateTime.UtcNow;
        var token = new JwtSecurityToken(
            issuer: failure == "wrong-issuer" ? "https://invalid.test" : $"https://login.microsoftonline.com/{Tenant}/v2.0",
            audience: failure == "wrong-audience" ? "api://different-api" : Audience,
            claims:
            [
                new Claim("oid", failure == "wrong-identity" ? Guid.NewGuid().ToString() : Gateway),
                new Claim("tid", failure == "wrong-tenant" ? Guid.NewGuid().ToString() : Tenant)
            ],
            notBefore: now.AddMinutes(-10),
            expires: failure == "expired" ? now.AddMinutes(-5) : now.AddMinutes(5),
            signingCredentials: new SigningCredentials(TestKey, SecurityAlgorithms.HmacSha256));
        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["AZURE_CLIENT_ID"] = "11111111-1111-1111-1111-111111111111",
            ["AZURE_TENANT_ID"] = "22222222-2222-2222-2222-222222222222",
            ["GATEWAY_PRINCIPAL_ID"] = "33333333-3333-3333-3333-333333333333",
            ["BACKEND_AUDIENCE"] = "api://44444444-4444-4444-4444-444444444444",
            ["FOUNDRY_PROJECT_ENDPOINT"] = "https://test.services.ai.azure.com/api/projects/brokerage",
            ["FOUNDRY_AGENT_NAME"] = "brokerage-educator",
            ["FOUNDRY_AGENT_VERSION"] = "1",
            ["MODEL_DEPLOYMENT"] = "brokerage-model",
            ["FAQ_BLOB_URL"] = "https://test.blob.core.windows.net/knowledge/brokerage-faq.md",
            ["SIGNING_KEY_URL"] = "https://test.vault.azure.net/keys/receipt"
        }));
        builder.ConfigureServices(services =>
        {
            services.AddSingleton<IChatBackend>(new TestBackend { Fail = failBackend });
            services.PostConfigure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme, options =>
            {
                var metadata = new OpenIdConnectConfiguration
                {
                    Issuer = $"https://login.microsoftonline.com/{Tenant}/v2.0"
                };
                metadata.SigningKeys.Add(TestKey);
                options.ConfigurationManager = new StaticConfigurationManager<OpenIdConnectConfiguration>(metadata);
            });
        });
    }
}
