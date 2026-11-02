using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Azure.Core;

namespace FeedbackCampaign.Web;

public interface IFoundryAgent
{
    Task<(Analysis Analysis, string ResponseId)> Analyze(Post post, Rules rules, CancellationToken cancellation);
    Task<(string Text, string ResponseId)> Chat(string prompt, CancellationToken cancellation);
}

/// <summary>Real project Responses invocation; runtime credential is managed identity only.</summary>
public sealed class FoundryAgent(IConfiguration config, TokenCredential credential, IHttpClientFactory factory) : IFoundryAgent
{
    public const string Name = "campaign-listener";
    private string Endpoint => config["FOUNDRY_PROJECT_ENDPOINT"]
        ?? throw new InvalidOperationException("Foundry project endpoint is not configured.");
    private string Policy => File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Policy", "campaign-policy.md"));

    public async Task<(Analysis Analysis, string ResponseId)> Analyze(Post post, Rules rules, CancellationToken cancellation)
    {
        // Do not transmit poster identity/contact to the model; the original packet stays in the case.
        var input = JsonSerializer.Serialize(new { task = "analyze", post.Campaign, post.Subject, post.Body, rules, policy = Policy });
        var result = await Invoke(input, cancellation);
        var analysis = JsonSerializer.Deserialize<Analysis>(result.Text, TableStateStore.Json)
            ?? throw new InvalidOperationException("Empty agent analysis.");
        analysis.Validate();
        return (analysis, result.ResponseId);
    }

    public Task<(string Text, string ResponseId)> Chat(string prompt, CancellationToken cancellation) =>
        Invoke(JsonSerializer.Serialize(new { task = "chat", question = prompt, policy = Policy }), cancellation);

    private async Task<(string Text, string ResponseId)> Invoke(string input, CancellationToken cancellation)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellation);
        timeout.CancelAfter(TimeSpan.FromSeconds(60));
        var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), timeout.Token);
        using var request = new HttpRequestMessage(HttpMethod.Post, $"{Endpoint.TrimEnd('/')}/openai/v1/responses");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
        request.Content = JsonContent.Create(new
        {
            agent_reference = new { name = Name, type = "agent_reference",
                version = config["FOUNDRY_AGENT_VERSION"] ?? throw new InvalidOperationException("Agent version is not initialized.") },
            input,
            max_output_tokens = 1500,
            store = false
        });
        using var response = await factory.CreateClient("foundry").SendAsync(request, timeout.Token);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Foundry invocation failed with HTTP {(int)response.StatusCode}.");
        using var document = JsonDocument.Parse(await response.Content.ReadAsStringAsync(timeout.Token));
        var root = document.RootElement;
        if (root.TryGetProperty("status", out var status) && status.GetString() != "completed")
            throw new InvalidOperationException("Foundry response did not complete.");
        var text = string.Concat(root.GetProperty("output").EnumerateArray()
            .Where(item => item.TryGetProperty("content", out _))
            .SelectMany(item => item.GetProperty("content").EnumerateArray())
            .Where(item => item.GetProperty("type").GetString() == "output_text")
            .Select(item => item.GetProperty("text").GetString()));
        if (string.IsNullOrWhiteSpace(text)) throw new InvalidOperationException("Foundry returned no text.");
        return (text, root.GetProperty("id").GetString()!);
    }
}
