using Azure.AI.Extensions.OpenAI;
using Azure.AI.Projects;
using Azure.Core;
using CoffeeShop.Web.Models;
using OpenAI.Responses;

namespace CoffeeShop.Web.Services;

public sealed class FoundryGateway(IConfiguration configuration, TokenCredential credential) : IAgentGateway
{
    public async Task<AgentReceipt> InvokeAsync(string agent, string evidence, CancellationToken ct)
    {
        var endpoint = configuration["Foundry:Endpoint"]
            ?? throw new InvalidOperationException("Foundry endpoint not installed.");
        var name = configuration[$"Foundry:{agent}:Name"]
            ?? throw new InvalidOperationException("Agent not installed.");
        var version = configuration[$"Foundry:{agent}:Version"]
            ?? throw new InvalidOperationException("Agent version not installed.");
        var client = new AIProjectClient(new Uri(endpoint), credential);
        var responses = client.ProjectOpenAIClient.GetProjectResponsesClientForAgentEndpoint(name);
        var options = new CreateResponseOptions
        {
            MaxOutputTokenCount = 800, StoredOutputEnabled = false
        };
        options.InputItems.Add(ResponseItem.CreateUserMessageItem(evidence));
        var response = (await responses.CreateResponseAsync(options, ct)).Value;
        if (response.Status != ResponseStatus.Completed || string.IsNullOrWhiteSpace(response.GetOutputText()))
            throw new InvalidOperationException("Agent did not produce a complete answer.");
        return new(name, version, response.Id, response.GetOutputText());
    }
}
