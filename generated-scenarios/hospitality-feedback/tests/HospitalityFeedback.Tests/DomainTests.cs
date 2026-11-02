using System.Text.Json;
using HospitalityFeedback.Web.Models;
using HospitalityFeedback.Web.Services;
using Xunit;

namespace HospitalityFeedback.Tests;

public sealed class DomainTests
{
    internal static FeedbackInput Sample(string id = "HF-9001") =>
        new(id, "G-001", "Airi Ilves", "HOTEL-01", "ja", "check-in",
            "チェックインに四十分かかりました。", DateTimeOffset.Parse("2026-10-10T12:00:00Z"));

    [Theory]
    [InlineData("HF-0001", true)]
    [InlineData("HF-000000000001", true)]
    [InlineData("../../raw", false)]
    [InlineData("HF-1", false)]
    [InlineData("HF-0001\n", false)]
    public void IdRulesRejectUnsafePaths(string id, bool expected) => Assert.Equal(expected, Rules.ValidId(id));

    [Theory]
    [InlineData("en")]
    [InlineData("es")]
    [InlineData("fr")]
    [InlineData("ja")]
    public void SupportedLanguagesValidate(string language) => Rules.Validate(Sample() with { Language = language });

    [Fact]
    public void RejectsUnsupportedLanguage() =>
        Assert.Throws<InputException>(() => Rules.Validate(Sample() with { Language = "xx" }));

    [Fact]
    public void RejectsEmptyText() =>
        Assert.Throws<InputException>(() => Rules.Validate(Sample() with { Text = " " }));

    [Fact]
    public void HashDetectsPayloadCollision()
    {
        Assert.Equal(Rules.Hash(Sample()), Rules.Hash(Sample()));
        Assert.NotEqual(Rules.Hash(Sample()), Rules.Hash(Sample() with { Text = "Changed" }));
    }

    [Fact]
    public void ExactJapaneseQuoteIsValid()
    {
        var answer = new GroundedAnswer("遅れがありました。", [new("HF-9001", "四十分")], false);
        var result = Rules.ValidateAnswer(JsonSerializer.Serialize(answer, Rules.Json),
            [new Evidence(Sample(), "correlation", DateTimeOffset.UtcNow)]);
        Assert.Equal("四十分", result.Citations[0].Quote);
    }

    [Fact]
    public void InventedSourceIsRejected() => Assert.Throws<GroundingException>(() =>
        Rules.ValidateAnswer("""{"answer":"A claim","citations":[{"feedbackId":"HF-9999","quote":"x"}]}""",
            [new Evidence(Sample(), "correlation", DateTimeOffset.UtcNow)]));

    [Fact]
    public void TranslatedQuoteIsNotOriginalEvidence() => Assert.Throws<GroundingException>(() =>
        Rules.ValidateAnswer("""{"answer":"Delay","citations":[{"feedbackId":"HF-9001","quote":"forty minutes"}]}""",
            [new Evidence(Sample(), "correlation", DateTimeOffset.UtcNow)]));

    [Fact]
    public void UngroundedSuccessIsRejected() => Assert.Throws<GroundingException>(() =>
        Rules.ValidateAnswer("""{"answer":"All guests are happy","citations":[],"insufficientEvidence":false}""", []));

    [Fact]
    public void InsufficientEvidenceIsRepresentable() =>
        Assert.True(Rules.ValidateAnswer(
            """{"answer":"Revenue is not in the feedback.","citations":[],"insufficientEvidence":true}""", [])
            .InsufficientEvidence);

    [Fact]
    public void BadJsonIsNotSuccess() =>
        Assert.Throws<GroundingException>(() => Rules.ValidateAnswer("Not JSON", []));

    [Fact]
    public void ResponseParserUsesOnlyOutputText()
    {
        using var doc = JsonDocument.Parse(
            """{"output":[{"type":"reasoning"},{"type":"message","content":[{"type":"output_text","text":"A"}]}]}""");
        Assert.Equal("A", FoundryAgent.ExtractText(doc.RootElement));
    }

    [Fact]
    public void InstructionsAreCompanySpecificAndTreatFeedbackAsUntrusted()
    {
        Assert.Contains("Margie's Travel", FoundryAgent.Instructions);
        Assert.Contains("untrusted", FoundryAgent.Instructions);
    }
}
