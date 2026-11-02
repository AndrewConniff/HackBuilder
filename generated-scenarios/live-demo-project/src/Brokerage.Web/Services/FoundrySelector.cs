using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Azure.Core;

namespace Brokerage.Web.Services;

internal interface IAnswerSelector
{
    Task<AnswerSelection> SelectAsync(string question, IReadOnlyList<KnowledgeEntry> entries, CancellationToken cancellation);
}

internal sealed class FoundrySelector(HttpClient client, TokenCredential credential, IConfiguration configuration)
    : IAnswerSelector
{
    public async Task<AnswerSelection> SelectAsync(
        string question, IReadOnlyList<KnowledgeEntry> entries, CancellationToken cancellation)
    {
        BrokerageStore.RequireText(question);
        var endpoint = configuration["Foundry:ProjectEndpoint"]
            ?? throw new InvalidOperationException("Foundry project endpoint is not configured.");
        var name = configuration["Foundry:AgentName"]
            ?? throw new InvalidOperationException("Foundry prompt agent is not configured.");
        var uri = new Uri(endpoint.TrimEnd('/') + "/agents/" + Uri.EscapeDataString(name)
            + "/endpoint/protocols/openai/responses?api-version=v1");
        if (uri.Scheme != Uri.UriSchemeHttps || !uri.Host.EndsWith(".ai.azure.com", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("Foundry endpoint must be an Azure Foundry HTTPS endpoint.");
        }
        var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), cancellation);
        using var request = new HttpRequestMessage(HttpMethod.Post, uri);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
        request.Content = JsonContent.Create(new
        {
            input = JsonSerializer.Serialize(new
            {
                question,
                approvedCatalog = entries.Select(entry => new { entry.Id, entry.Question, entry.Answer })
            }),
            store = false,
            tool_choice = new { type = "function", name = "select_company_answer" },
            parallel_tool_calls = false,
            max_output_tokens = 300
        });
        using var response = await client.SendAsync(request, cancellation);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Foundry returned HTTP {(int)response.StatusCode}.",
                null, response.StatusCode);
        }
        using var payload = JsonDocument.Parse(await response.Content.ReadAsStringAsync(cancellation));
        return ParseSelection(payload.RootElement, entries);
    }

    internal static AnswerSelection ParseSelection(JsonElement payload, IReadOnlyList<KnowledgeEntry> entries)
    {
        if (payload.TryGetProperty("status", out var status) && status.GetString() != "completed")
        {
            throw new InvalidDataException("Foundry invocation did not complete successfully.");
        }
        if (!payload.TryGetProperty("id", out var receipt) || string.IsNullOrWhiteSpace(receipt.GetString()))
        {
            throw new InvalidDataException("Foundry response is missing an invocation receipt.");
        }
        var calls = payload.GetProperty("output").EnumerateArray()
            .Where(item => item.GetProperty("type").GetString() == "function_call").ToArray();
        if (calls.Length != 1 || calls[0].GetProperty("name").GetString() != "select_company_answer")
        {
            throw new InvalidDataException("Foundry must return exactly one approved selection function call.");
        }
        using var arguments = JsonDocument.Parse(calls[0].GetProperty("arguments").GetString()
            ?? throw new InvalidDataException("Function arguments missing."));
        var source = arguments.RootElement.GetProperty("source_id").GetString();
        if (source != "unsupported" && !entries.Any(entry => entry.Approved &&
            entry.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) == source))
        {
            throw new InvalidDataException("Foundry selected an unknown or unapproved company source.");
        }
        return new(source!, receipt.GetString()!);
    }
}
