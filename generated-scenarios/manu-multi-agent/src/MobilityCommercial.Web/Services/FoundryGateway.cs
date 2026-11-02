using System.ClientModel.Primitives;
using Azure.AI.Extensions.OpenAI;
using Azure.Core;
using MobilityCommercial.Web.Models;
using OpenAI.Responses;

namespace MobilityCommercial.Web.Services;

internal interface IAgentGateway
{
    Task<AgentTurn> RespondAsync(AgentInput input, string? previousResponseId,
        IReadOnlyList<(string CallId, string Output)> toolOutputs, CancellationToken cancellationToken);
}

internal sealed class FoundryGateway(AppSettings settings, TokenCredential credential) : IAgentGateway
{
    public async Task<AgentTurn> RespondAsync(AgentInput input, string? previousResponseId,
        IReadOnlyList<(string CallId, string Output)> toolOutputs, CancellationToken cancellationToken)
    {
        // Disable SDK retries: every inference attempt must remain inside the application call budget.
        var client = new ProjectResponsesClient(settings.ProjectEndpoint, credential,
            new AgentReference(input.Pin.Name, input.Pin.Version), null,
            new ProjectResponsesClientOptions { RetryPolicy = new ClientRetryPolicy(0) });
        CreateResponseOptions options = new()
        {
            MaxOutputTokenCount = 800,
            PreviousResponseId = previousResponseId
        };
        if (previousResponseId is null) options.InputItems.Add(ResponseItem.CreateUserMessageItem(input.Prompt));
        foreach (var output in toolOutputs)
            options.InputItems.Add(ResponseItem.CreateFunctionCallOutputItem(output.CallId, output.Output));
        ResponseResult response = await client.CreateResponseAsync(options, cancellationToken);
        if (response.Status != ResponseStatus.Completed || response.Usage is null
            || string.IsNullOrWhiteSpace(response.Id))
            throw new WorkflowException(502, "incomplete_agent_response");
        return new(string.Empty, response.Id, response.GetOutputText(),
            response.OutputItems.OfType<FunctionCallResponseItem>()
                .Select(c => new ToolCall(c.CallId, c.FunctionName, c.FunctionArguments.ToString())).ToArray(),
            response.Usage.InputTokenCount, response.Usage.OutputTokenCount);
    }
}
