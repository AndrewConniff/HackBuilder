using System.Net;
using System.Text.Json;
using Azure.Core;
using FeedbackCampaign.Web;
using Microsoft.Extensions.Configuration;
using Xunit;

namespace FeedbackCampaign.Tests;

public sealed class FoundryWireTests
{
    [Fact]
    public async Task CallsVersionPinnedProjectAgentAndMinimizesPersonalData()
    {
        var handler = new Wire();
        var client = Make(handler);
        var answer = await client.Analyze(new Post("source", "Airi Ilves", "subscriber1@example.test",
            "Streaming launch", "Great launch", "The captions are excellent."), Rules.Initial, default);
        Assert.Equal("test-wire-response", answer.ResponseId);
        Assert.Equal("/api/projects/campaign/openai/v1/responses", handler.Path);
        Assert.DoesNotContain("Airi", handler.Body); Assert.DoesNotContain("subscriber1", handler.Body);
        using var request = JsonDocument.Parse(handler.Body);
        var agent = request.RootElement.GetProperty("agent_reference");
        Assert.Equal("campaign-listener", agent.GetProperty("name").GetString());
        Assert.Equal("7", agent.GetProperty("version").GetString());
        Assert.Equal("agent_reference", agent.GetProperty("type").GetString());
        Assert.False(request.RootElement.GetProperty("store").GetBoolean());
        Assert.Contains("campaign-policy-v1", handler.Body);
    }

    [Fact]
    public async Task ProviderFailureHasNoCannedSuccess() =>
        await Assert.ThrowsAsync<InvalidOperationException>(() => Make(new Wire { Code = HttpStatusCode.Forbidden })
            .Chat("What may Sales promise?", default));

    [Fact]
    public async Task InvalidAgentOutputIsRejected() =>
        await Assert.ThrowsAsync<JsonException>(() => Make(new Wire { Text = "Not structured analysis" })
            .Analyze(new Post("source", "Airi Ilves", "subscriber1@example.test", "Launch", "Topic", "Body"), Rules.Initial, default));

    private static FoundryAgent Make(Wire handler)
    {
        // Policy content comes from the real project publish output, not fabricated retrieval.
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["FOUNDRY_PROJECT_ENDPOINT"] = "https://local-wire-test.invalid/api/projects/campaign",
            ["FOUNDRY_AGENT_VERSION"] = "7",
        }).Build();
        return new FoundryAgent(config, new TestCredential(), new Factory(handler));
    }
    private sealed class TestCredential : TokenCredential
    {
        public override AccessToken GetToken(TokenRequestContext requestContext, CancellationToken cancellationToken) =>
            new("test-only-token", DateTimeOffset.UtcNow.AddMinutes(5));
        public override ValueTask<AccessToken> GetTokenAsync(TokenRequestContext requestContext, CancellationToken cancellationToken) =>
            ValueTask.FromResult(GetToken(requestContext, cancellationToken));
    }
    private sealed class Factory(Wire handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new(handler, false);
    }
    private sealed class Wire : HttpMessageHandler
    {
        public HttpStatusCode Code { get; init; } = HttpStatusCode.OK;
        public string? Text { get; init; }
        public string Body { get; private set; } = "";
        public string Path { get; private set; } = "";
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Path = request.RequestUri!.AbsolutePath;
            Body = await request.Content!.ReadAsStringAsync(ct);
            Assert.Equal("Bearer", request.Headers.Authorization!.Scheme);
            var text = Text ?? JsonSerializer.Serialize(new Analysis(new(.9, .05, .05), new(.9, .05, .05),
                new(.9, .05, .05), "Test assessment", "Test investigation", "Test recommendation", "Test draft", "campaign-policy-v1"),
                TableStateStore.Json);
            return new HttpResponseMessage(Code) { Content = new StringContent(JsonSerializer.Serialize(new
            {
                id = "test-wire-response", status = "completed",
                output = new[] { new { type = "message", content = new[] { new { type = "output_text", text } } } }
            })) };
        }
    }
}
