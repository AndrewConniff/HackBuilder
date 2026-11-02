using System.Net;
using System.Text;
using System.Text.Json;
using Azure.Core;
using BankSupport.Web.Models;
using BankSupport.Web.Services;
using Microsoft.Extensions.Configuration;

namespace BankSupport.Tests;

/// <summary>Validates the actual adapter's wire contract using local HTTP responses, not Azure.</summary>
public sealed class FoundryGatewayTests
{
    /// <summary>Project Responses calls pin the requested saved agent version and limit output.</summary>
    [Fact]
    public async Task SendsExactVersionedResponsesContract()
    {
        using var handler = new Handler(HttpStatusCode.OK,
            """{"id":"resp-test","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"{\"Route\":\"faq\"}"}]}]}""");
        var gateway = Gateway(handler);
        var result = await gateway.InvokeAsync<RouteDecision>("bank-triage", "7", new { Message = "Hours?" }, default);
        Assert.Equal("faq", result.Value.Route);
        Assert.Equal("resp-test", result.ResponseId);
        Assert.Equal("https://test.services.ai.azure.com/api/projects/banking/openai/v1/responses", handler.Uri);
        Assert.Equal("Bearer", handler.Scheme);
        using var body = JsonDocument.Parse(handler.Body!);
        Assert.Equal("7", body.RootElement.GetProperty("agent_reference").GetProperty("version").GetString());
        Assert.Equal(800, body.RootElement.GetProperty("max_output_tokens").GetInt32());
        Assert.False(body.RootElement.GetProperty("store").GetBoolean());
    }

    /// <summary>Service errors are explicit failures; bodies are not fabricated as answers.</summary>
    [Theory]
    [InlineData(HttpStatusCode.Forbidden)]
    [InlineData(HttpStatusCode.TooManyRequests)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task RejectsServiceErrors(HttpStatusCode status)
    {
        using var handler = new Handler(status, "{}");
        await Assert.ThrowsAsync<HttpRequestException>(() =>
            Gateway(handler).InvokeAsync<RouteDecision>("bank-triage", "7", new { Message = "Hours?" }, default));
    }

    /// <summary>Incomplete outputs are not accepted as complete agent execution.</summary>
    [Fact]
    public async Task RejectsIncompleteResponses()
    {
        using var handler = new Handler(HttpStatusCode.OK, """{"id":"resp-test","status":"incomplete","output":[]}""");
        await Assert.ThrowsAsync<InvalidDataException>(() =>
            Gateway(handler).InvokeAsync<RouteDecision>("bank-triage", "7", new { Message = "Hours?" }, default));
    }

    /// <summary>Missing/wrong-shaped provider fields are explicit invalid responses, not successful defaults.</summary>
    [Theory]
    [InlineData("{}")]
    [InlineData("""{"id":"resp-test","status":"completed","output":{}}""")]
    [InlineData("""{"id":"resp-test","status":"completed","output":[]}""")]
    public async Task RejectsMalformedProviderShapes(string json)
    {
        using var handler = new Handler(HttpStatusCode.OK, json);
        await Assert.ThrowsAsync<InvalidDataException>(() =>
            Gateway(handler).InvokeAsync<RouteDecision>("bank-triage", "7", new { Message = "Hours?" }, default));
    }

    private static FoundryGateway Gateway(Handler handler) => new(new HttpClient(handler), new Credential(),
        new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        { ["FOUNDRY_PROJECT_ENDPOINT"] = "https://test.services.ai.azure.com/api/projects/banking" }).Build());

    private sealed class Credential : TokenCredential
    {
        public override AccessToken GetToken(TokenRequestContext requestContext, CancellationToken cancellationToken) =>
            new("local-test-not-a-live-token", DateTimeOffset.UtcNow.AddMinutes(5));
        public override ValueTask<AccessToken> GetTokenAsync(TokenRequestContext requestContext,
            CancellationToken cancellationToken) => ValueTask.FromResult(GetToken(requestContext, cancellationToken));
    }

    private sealed class Handler(HttpStatusCode status, string json) : HttpMessageHandler
    {
        internal string? Uri { get; private set; }
        internal string? Scheme { get; private set; }
        internal string? Body { get; private set; }
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Uri = request.RequestUri!.ToString();
            Scheme = request.Headers.Authorization?.Scheme;
            Body = await request.Content!.ReadAsStringAsync(ct);
            return new HttpResponseMessage(status) { Content = new StringContent(json, Encoding.UTF8, "application/json") };
        }
    }
}
