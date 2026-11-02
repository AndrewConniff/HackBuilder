using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

namespace Brokerage.Web;

/// <summary>A single independent customer question; no cross-customer conversation identifiers are accepted.</summary>
public sealed record ChatRequest(string Message);

/// <summary>Answer with verifiable source identifiers and a signed digest receipt, not a correctness guarantee.</summary>
public sealed record ChatReply(
    string Answer, string[] Sources, string CorrelationId, string AgentResponseId,
    string Digest, string Signature, string KeyId);

/// <summary>Result of a real agent invocation.</summary>
public sealed record AgentAnswer(string Text, string ResponseId);

/// <summary>Key Vault signing result containing the versioned verification key identifier.</summary>
public sealed record ReceiptSignature(string Signature, string KeyId);

/// <summary>External data-plane operations, replaceable only by the test host.</summary>
public interface IChatBackend
{
    /// <summary>Loads the installed, private synthetic brokerage source.</summary>
    Task<string> ReadFaqAsync(CancellationToken cancellationToken);
    /// <summary>Invokes the configured Foundry agent version with bounded source context.</summary>
    Task<AgentAnswer> InvokeAsync(string message, string source, CancellationToken cancellationToken);
    /// <summary>Signs a SHA-256 digest with a nonexportable Key Vault key.</summary>
    Task<ReceiptSignature> SignAsync(byte[] digest, CancellationToken cancellationToken);
}

/// <summary>Coordinates source loading, actual inference and signed response evidence.</summary>
public sealed partial class ChatService(IChatBackend backend, ILogger<ChatService> logger)
{
    /// <summary>Returns only an agent-produced answer with validated source identifiers and a signed receipt.</summary>
    public async Task<ChatReply> SendAsync(string message, string correlationId, CancellationToken cancellationToken)
    {
        var source = await backend.ReadFaqAsync(cancellationToken);
        var result = await backend.InvokeAsync(message, source, cancellationToken);
        if (string.IsNullOrWhiteSpace(result.Text) || string.IsNullOrWhiteSpace(result.ResponseId))
            throw new InvalidDataException("Foundry returned no usable answer or response identifier.");
        var validIds = SourceId().Matches(source).Select(m => m.Value).ToHashSet(StringComparer.Ordinal);
        var citations = SourceId().Matches(result.Text).Select(m => m.Value).Distinct().ToArray();
        if (citations.Any(id => !validIds.Contains(id)))
            throw new InvalidDataException("Foundry returned an unknown source identifier.");
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(result.Text));
        var receipt = await backend.SignAsync(digest, cancellationToken);
        logger.LogInformation("Chat completed. Correlation={CorrelationId} AgentResponse={AgentResponseId} Sources={Count}",
            correlationId, result.ResponseId, citations.Length);
        return new(result.Text, citations, correlationId, result.ResponseId,
            Convert.ToHexStringLower(digest), receipt.Signature, receipt.KeyId);
    }

    [GeneratedRegex(@"FAQ-\d{2}", RegexOptions.CultureInvariant)]
    private static partial Regex SourceId();
}
