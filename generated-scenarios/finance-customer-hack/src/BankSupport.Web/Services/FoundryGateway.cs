using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Azure.Core;
using BankSupport.Web.Models;

namespace BankSupport.Web.Services;

/// <summary>Real saved-agent inference boundary, replaceable only by explicitly injected test doubles.</summary>
public interface IFoundryGateway
{
    /// <summary>Invokes a named, installed version and returns its response ID and typed output.</summary>
    Task<(T Value, string ResponseId)> InvokeAsync<T>(string name, string version, object input, CancellationToken ct);
}

/// <summary>Current project Responses REST adapter authenticated by managed identity at runtime.</summary>
public sealed class FoundryGateway(HttpClient http, TokenCredential credential, IConfiguration configuration) : IFoundryGateway
{
    /// <inheritdoc />
    public async Task<(T Value, string ResponseId)> InvokeAsync<T>(
        string name, string version, object input, CancellationToken ct)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(45));
        var endpoint = configuration["FOUNDRY_PROJECT_ENDPOINT"]
            ?? throw new InvalidOperationException("FOUNDRY_PROJECT_ENDPOINT is required.");
        using var request = new HttpRequestMessage(HttpMethod.Post, endpoint.TrimEnd('/') + "/openai/v1/responses");
        var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), timeout.Token);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
        request.Content = JsonContent.Create(new
        {
            agent_reference = new { type = "agent_reference", name, version },
            input = JsonSerializer.Serialize(input), max_output_tokens = 800, store = false
        });
        using var response = await http.SendAsync(request, timeout.Token);
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"Foundry agent call failed with HTTP {(int)response.StatusCode}.",
                null, response.StatusCode);
        using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(timeout.Token));
        var root = doc.RootElement;
        if (RequiredString(root, "status") != "completed")
            throw new InvalidDataException("Foundry response did not complete.");
        var id = RequiredString(root, "id");
        var text = string.Concat(RequiredArray(root, "output").EnumerateArray()
            .Where(item => RequiredString(item, "type") == "message")
            .SelectMany(item => RequiredArray(item, "content").EnumerateArray())
            .Where(item => RequiredString(item, "type") == "output_text")
            .Select(item => RequiredString(item, "text")));
        if (string.IsNullOrWhiteSpace(text))
            throw new InvalidDataException("Foundry returned no response ID or output text.");
        var value = JsonSerializer.Deserialize<T>(text, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            RespectRequiredConstructorParameters = true
        }) ?? throw new InvalidDataException("Foundry returned invalid typed output.");
        return (value, id);
    }

    private static string RequiredString(JsonElement element, string property)
    {
        if (element.ValueKind != JsonValueKind.Object || !element.TryGetProperty(property, out var value)
            || value.ValueKind != JsonValueKind.String || string.IsNullOrWhiteSpace(value.GetString()))
            throw new InvalidDataException($"Foundry response is missing a valid {property} string.");
        return value.GetString()!;
    }

    private static JsonElement RequiredArray(JsonElement element, string property)
    {
        if (element.ValueKind != JsonValueKind.Object || !element.TryGetProperty(property, out var value)
            || value.ValueKind != JsonValueKind.Array)
            throw new InvalidDataException($"Foundry response is missing a valid {property} array.");
        return value;
    }
}
