using System.Net;
using System.Text.Json;
using Azure.Core;
using HospitalityFeedback.Web.Models;
using HospitalityFeedback.Web.Services;
using Xunit;

namespace HospitalityFeedback.Tests;

// These are isolated wire-contract tests with synthetic HTTP responses, NOT live agent acceptance.
public sealed class AgentContractTests
{
    [Fact]
    public async Task MissingConfigurationNeverInvokesHttpOrCreatesMockSuccess()
    {
        var handler = new ContractHandler();
        var client = new FoundryAgent(new HttpClient(handler), new LocalTestCredential(), new());
        await Assert.ThrowsAsync<ConfigurationException>(() =>
            client.ChatAsync(new("Summarize"), [], CancellationToken.None));
        Assert.Empty(handler.Paths);
    }

    [Fact]
    public async Task UsesCurrentPersistedAgentScopedResponsesProtocolAndValidatesCitations()
    {
        var handler = new ContractHandler();
        var client = new FoundryAgent(new HttpClient(handler), new LocalTestCredential(),
            new FeedbackOptions
            {
                ProjectEndpoint = "https://unit-test.invalid/api/projects/local-contract",
                ModelDeployment = "unit-test-model",
                AgentName = "unit-contract-agent"
            });
        var result = await client.ChatAsync(new("Summarize"), [], CancellationToken.None);
        Assert.True(result.Result.InsufficientEvidence);
        Assert.EndsWith("/agents/unit-contract-agent?api-version=v1", handler.Paths[0], StringComparison.Ordinal);
        Assert.EndsWith("/agents?api-version=v1", handler.Paths[1], StringComparison.Ordinal);
        Assert.EndsWith(
            "/agents/unit-contract-agent/endpoint/protocols/openai/responses?api-version=v1",
            handler.Paths[2], StringComparison.Ordinal);
        using var body = JsonDocument.Parse(handler.Bodies[1]!);
        Assert.Equal("prompt", body.RootElement.GetProperty("definition").GetProperty("kind").GetString());
        Assert.Equal("unit-test-model", body.RootElement.GetProperty("definition").GetProperty("model").GetString());
    }

    private sealed class LocalTestCredential : TokenCredential
    {
        public override AccessToken GetToken(TokenRequestContext requestContext, CancellationToken cancellationToken)
        {
            Assert.Equal("https://ai.azure.com/.default", Assert.Single(requestContext.Scopes));
            return new AccessToken("synthetic-unit-test-token", DateTimeOffset.UtcNow.AddMinutes(1));
        }
        public override ValueTask<AccessToken> GetTokenAsync(TokenRequestContext requestContext,
            CancellationToken cancellationToken) => ValueTask.FromResult(GetToken(requestContext, cancellationToken));
    }

    private sealed class ContractHandler : HttpMessageHandler
    {
        public List<string> Paths { get; } = [];
        public List<string?> Bodies { get; } = [];
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Paths.Add(request.RequestUri!.PathAndQuery);
            Bodies.Add(request.Content is null ? null : await request.Content.ReadAsStringAsync(ct));
            Assert.Equal("Bearer", request.Headers.Authorization?.Scheme);
            if (request.Method == HttpMethod.Get) return new(HttpStatusCode.NotFound);
            if (Paths.Count == 2) return new(HttpStatusCode.OK) { Content = new StringContent("{}") };
            var answer = JsonSerializer.Serialize(new GroundedAnswer("No evidence.", [], true), Rules.Json);
            var response = new
            {
                id = "unit-test-response-not-live", status = "completed",
                output = new[] { new { type = "message",
                    content = new[] { new { type = "output_text", text = answer } } } }
            };
            return new(HttpStatusCode.OK) { Content = new StringContent(JsonSerializer.Serialize(response)) };
        }
    }
}
