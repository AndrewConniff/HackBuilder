using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace HospitalityFeedback.Web.Models;

public sealed record FeedbackInput(
    string FeedbackId, string GuestId, string GuestName, string HotelId,
    string Language, string Category, string Text, DateTimeOffset ObservedAt);

public sealed record RawFeedback(FeedbackInput Feedback, string PayloadHash, string CorrelationId,
    DateTimeOffset ReceivedAt);
public sealed record Evidence(FeedbackInput Feedback, string CorrelationId, DateTimeOffset ProcessedAt);
public sealed record WorkItem(string FeedbackId, string CorrelationId);
public sealed record ProcessingStatus(string FeedbackId, string CorrelationId, string State,
    DateTimeOffset UpdatedAt, int Attempts, string? ErrorCode = null);
public sealed record IngestResult(string FeedbackId, string CorrelationId, string State, bool Duplicate);
public sealed record ChatRequest(string Question, string ResponseLanguage = "en",
    string? Category = null, string[]? Languages = null);
public sealed record Citation(string FeedbackId, string Quote);
public sealed record GroundedAnswer(string Answer, Citation[] Citations, bool InsufficientEvidence);
public sealed record ChatResult(GroundedAnswer Result, string AgentName, string ResponseId,
    string[] EvidenceScope, DateTimeOffset CheckedAtUtc);

public static partial class Rules
{
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    public static readonly string[] Languages = ["en", "es", "fr", "ja"];
    public static readonly string[] Categories = ["check-in", "housekeeping", "breakfast", "noise", "staff"];

    [GeneratedRegex("\\AHF-[0-9]{4,12}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex IdRegex();

    public static bool ValidId(string? id) => id is not null && IdRegex().IsMatch(id);

    public static void Validate(FeedbackInput input)
    {
        if (!ValidId(input.FeedbackId) || string.IsNullOrWhiteSpace(input.GuestId)
            || input.GuestId.Length > 64 || string.IsNullOrWhiteSpace(input.GuestName)
            || input.GuestName.Length > 150 || string.IsNullOrWhiteSpace(input.HotelId)
            || input.HotelId.Length > 64 || !Languages.Contains(input.Language)
            || !Categories.Contains(input.Category) || string.IsNullOrWhiteSpace(input.Text)
            || input.Text.Length > 4000 || input.ObservedAt == default
            || input.ObservedAt > DateTimeOffset.UtcNow.AddMinutes(5))
            throw new InputException("invalid_feedback", "Invalid ID, guest, language, category, timestamp or text.");
    }

    public static void Validate(ChatRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Question) || request.Question.Length > 2000
            || !Languages.Contains(request.ResponseLanguage)
            || (request.Category is not null && !Categories.Contains(request.Category))
            || (request.Languages is not null && request.Languages.Any(l => !Languages.Contains(l))))
            throw new InputException("invalid_chat", "Invalid question, language or category filter.");
    }

    public static string Hash(FeedbackInput input) =>
        Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(input, Json)));

    public static GroundedAnswer ValidateAnswer(string json, IReadOnlyList<Evidence> scope)
    {
        // Agent output is never trusted merely because the service returned HTTP 200.
        GroundedAnswer answer;
        try
        {
            answer = JsonSerializer.Deserialize<GroundedAnswer>(json, Json)
                ?? throw new JsonException();
        }
        catch (JsonException)
        {
            throw new GroundingException("Agent did not return the required JSON.");
        }
        if (string.IsNullOrWhiteSpace(answer.Answer) || answer.Answer.Length > 12000
            || answer.Citations is null || answer.Citations.Length > 30
            || (!answer.InsufficientEvidence && answer.Citations.Length == 0))
            throw new GroundingException("Missing answer or grounded citations.");
        foreach (var citation in answer.Citations)
        {
            var record = scope.SingleOrDefault(e => e.Feedback.FeedbackId == citation.FeedbackId);
            if (record is null || string.IsNullOrWhiteSpace(citation.Quote)
                || !record.Feedback.Text.Contains(citation.Quote, StringComparison.Ordinal))
                throw new GroundingException("Citation is not an exact excerpt from the supplied evidence.");
        }
        return answer;
    }
}

public sealed class InputException(string code, string message) : Exception(message)
{
    public string Code { get; } = code;
}
public sealed class ConflictException() : Exception("Feedback ID already exists with different content.");
public sealed class GroundingException(string message) : Exception(message);
public sealed class ConfigurationException(string message) : Exception(message);
