using Azure.AI.Extensions.OpenAI;
using Azure.AI.Projects;
using Azure.Core;
using CoffeeShop.Web.Models;
using OpenAI.Responses;

namespace CoffeeShop.Web.Services;

/// <summary>Invokes installed version-selected Foundry endpoints with bounded payloads and shared call capacity.</summary>
public sealed class FoundryGateway(IConfiguration configuration, TokenCredential credential) : IAgentGateway
{
    private readonly SemaphoreSlim calls = new(40, 40);
    private readonly Lazy<AIProjectClient> project = new(() => new AIProjectClient(
        new Uri(configuration["Foundry:Endpoint"]
            ?? throw new InvalidOperationException("Foundry endpoint not installed.")), credential));

    /// <inheritdoc />
    public async Task<AgentReceipt> InvokeAsync(string agent, string evidence, CancellationToken ct)
    {
        if (evidence.Length > 24000) throw new ArgumentException("Agent input budget exceeded.");
        var name = configuration[$"Foundry:{agent}:Name"]
            ?? throw new InvalidOperationException("Agent not installed.");
        var version = configuration[$"Foundry:{agent}:Version"]
            ?? throw new InvalidOperationException("Agent version not installed.");
        await calls.WaitAsync(ct);
        try
        {
            var responses = project.Value.ProjectOpenAIClient.GetProjectResponsesClientForAgentEndpoint(name);
            var options = new CreateResponseOptions
            {
                MaxOutputTokenCount = 400, StoredOutputEnabled = false
            };
            options.InputItems.Add(ResponseItem.CreateUserMessageItem(evidence));
            var response = (await responses.CreateResponseAsync(options, ct)).Value;
            if (response.Status != ResponseStatus.Completed || string.IsNullOrWhiteSpace(response.GetOutputText()))
                throw new InvalidOperationException("Agent did not produce a complete answer.");
            return new(name, version, response.Id, response.GetOutputText());
        }
        finally { calls.Release(); }
    }
}
