namespace HospitalityFeedback.Web.Services;

public sealed class FeedbackOptions
{
    public string CompanyName { get; set; } = "Margie's Travel";
    public bool UseAzurite { get; set; }
    public bool LocalAnonymous { get; set; }
    public string BlobEndpoint { get; set; } = string.Empty;
    public string QueueEndpoint { get; set; } = string.Empty;
    public string QueueName { get; set; } = "feedback-ingest";
    public string PoisonQueueName { get; set; } = "feedback-poison";
    public string ProjectEndpoint { get; set; } = string.Empty;
    public string ModelDeployment { get; set; } = string.Empty;
    public string AgentName { get; set; } = "hotel-feedback-v1";
    public string TenantId { get; set; } = string.Empty;
    public string Audience { get; set; } = string.Empty;
    public string[] OperatorObjectIds { get; set; } = [];
    public int MaxEvidenceRecords { get; set; } = 100;
    public int MaxDeliveryAttempts { get; set; } = 5;
}
