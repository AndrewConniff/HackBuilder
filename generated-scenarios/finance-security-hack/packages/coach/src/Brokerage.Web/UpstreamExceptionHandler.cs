using Azure;
using Azure.Identity;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using System.ClientModel;

namespace Brokerage.Web;

/// <summary>Reports real upstream failures without exposing SDK responses, prompts or tokens.</summary>
public sealed class UpstreamExceptionHandler(ILogger<UpstreamExceptionHandler> logger) : IExceptionHandler
{
    /// <inheritdoc />
    public async ValueTask<bool> TryHandleAsync(
        HttpContext context, Exception exception, CancellationToken cancellationToken)
    {
        var status = exception switch
        {
            RequestFailedException { Status: 429 } or ClientResultException { Status: 429 } => 429,
            RequestFailedException or ClientResultException or AuthenticationFailedException => 502,
            InvalidDataException => 502,
            OperationCanceledException when !context.RequestAborted.IsCancellationRequested => 504,
            _ => 500
        };
        logger.LogError("Chat failed. Correlation={CorrelationId} ErrorType={ErrorType} Status={Status}",
            context.TraceIdentifier, exception.GetType().Name, status);
        context.Response.StatusCode = status;
        await context.Response.WriteAsJsonAsync(new ProblemDetails
        {
            Status = status,
            Title = "The request could not be completed.",
            Extensions = { ["correlationId"] = context.TraceIdentifier }
        }, cancellationToken);
        return true;
    }
}
