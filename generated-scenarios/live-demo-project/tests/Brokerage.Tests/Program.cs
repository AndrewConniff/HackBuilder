using System.Text.Json;
using System.Net;
using System.Text;
using Azure.Core;
using Brokerage.Web.Services;
using Microsoft.Extensions.Configuration;

var project = Path.GetFullPath(args.Single());
var root = Path.Combine(Path.GetTempPath(), "brokerage-tests-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
var results = new List<string>();
try
{
    var store = new BrokerageStore(Path.Combine(root, "data"));
    var credentials = Path.Combine(root, "private");
    await store.InitializeAsync(Path.Combine(project, "src", "Brokerage.Web", "SeedData", "knowledge.json"), credentials);
    using var access = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(credentials, "participant-access.json")));
    var password = access.RootElement.GetProperty("password").GetString()!;
    Check(await store.LoginAsync("customer-001", password) is { Role: "Participant" }, "local login and server role");
    Check(await store.LoginAsync("customer-001", "wrong") is null, "failed login");
    for (var attempt = 0; attempt < 4; attempt++)
    {
        await store.LoginAsync("customer-001", "wrong");
    }
    Check(await store.LoginAsync("customer-001", password) is null, "five failures lock account");
    var entries = await store.KnowledgeAsync();
    Check(entries.Count == 10, "ten approved company fixtures");
    var handler = new SelectionHandler();
    var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
    {
        ["Foundry:ProjectEndpoint"] = "https://local-test.services.ai.azure.com/api/projects/brokerage",
        ["Foundry:AgentName"] = "company selector"
    }).Build();
    var selector = new FoundrySelector(new HttpClient(handler), new ComponentCredential(), configuration);
    Check((await selector.SelectAsync("How do I start?", entries, CancellationToken.None)).SourceId == "1",
        "selector accepts an explicit local-test function response");
    Check(handler.Path == "/api/projects/brokerage/agents/company%20selector/endpoint/protocols/openai/responses"
        + "?api-version=v1", "selector uses the consumer-authorized agent endpoint");
    using var body = JsonDocument.Parse(handler.Body!);
    Check(!body.RootElement.TryGetProperty("agent", out _) &&
        !body.RootElement.GetProperty("store").GetBoolean() &&
        !body.RootElement.GetProperty("parallel_tool_calls").GetBoolean() &&
        body.RootElement.GetProperty("max_output_tokens").GetInt32() == 300 &&
        body.RootElement.GetProperty("tool_choice").GetProperty("name").GetString() == "select_company_answer",
        "agent endpoint request retains stateless bounded forced-function controls");
    var conversation = await store.CurrentAsync("customer-001");
    var selection = Parse("1");
    conversation = await store.ApplyAsync(conversation.Id, "customer-001", false, 0,
        "answer", "How do I start?", selection);
    Check(conversation.Messages.Last().Text == entries.Single(item => item.Id == 1).Answer,
        "automated answer matches company wording exactly");
    Check(conversation.Messages.Last().Source!.Contains(entries[0].Version), "citation carries approved source version");
    await Reject<StateConflictException>(() => store.StartNewAsync("customer-001", conversation.Revision),
        "open case cannot be bypassed with a new conversation");
    await Reject<AccessException>(() => store.ApplyAsync(conversation.Id, "another-customer", false,
        conversation.Revision, "escalate"), "cross-customer denial");
    await Reject<AccessException>(() => store.ApplyAsync(conversation.Id, "customer-001", false,
        conversation.Revision, "claim"), "customer cannot claim");
    conversation = await store.ApplyAsync(conversation.Id, "customer-001", false, conversation.Revision,
        "answer", "Predict an unrelated asset price", Parse("unsupported"));
    Check(conversation.Messages.Last().Source is null &&
        conversation.Messages.Last().Text.StartsWith("No approved company answer"), "unsupported fails closed");
    foreach (var source in new[] { "9999", "ignore policy" })
    {
        await Reject<InvalidDataException>(() => Task.FromResult(Parse(source)), "unknown selection denied: " + source);
    }
    await Reject<InvalidDataException>(() => Task.FromResult(FoundrySelector.ParseSelection(
        JsonDocument.Parse("""{"id":"test","output":[{"type":"message","text":"Invented model answer"}]}""").RootElement,
        entries)), "model prose cannot become a company answer");
    var pending = await store.ApplyAsync(conversation.Id, "customer-001", false, conversation.Revision, "escalate");
    Check((await store.ApplyAsync(pending.Id, "customer-001", false, 0, "escalate")).Id == pending.Id,
        "escalation is idempotent");
    await Reject<AccessException>(() => store.ApplyAsync(pending.Id, "customer-001", false, pending.Revision,
        "answer", "fees", Parse("3")), "AI stops after human takeover");
    pending = await store.ApplyAsync(pending.Id, "customer-001", false, pending.Revision, "customer-reply",
        "Please help me locate the current fee schedule.");
    Check(pending.Messages.Last().Author == "Customer", "customer messages reach the human queue without AI");
    var claimed = await store.ApplyAsync(pending.Id, "representative-001", true, pending.Revision, "claim");
    await Reject<StateConflictException>(() => store.ApplyAsync(pending.Id, "other-representative", true,
        pending.Revision, "claim"), "competing claim conflicts");
    await Reject<AccessException>(() => store.ApplyAsync(claimed.Id, "other-representative", true, claimed.Revision,
        "reply", "Not my case"), "only assigned representative replies");
    var replied = await store.ApplyAsync(claimed.Id, "representative-001", true, claimed.Revision,
        "reply", "I can help with your service question.");
    Check(replied.Messages.Last().Author == "Representative", "real human reply remains labeled");
    var restarted = new BrokerageStore(Path.Combine(root, "data"));
    Check((await restarted.CurrentAsync("customer-001")).Messages.Last().Text == replied.Messages.Last().Text,
        "human reply persists across store restart");
    var resolved = await store.ApplyAsync(replied.Id, "representative-001", true, replied.Revision, "resolve");
    Check(resolved.Status == "resolved", "representative resolves");
    await Reject<StateConflictException>(() => store.StartNewAsync("customer-001", resolved.Revision - 1),
        "stale new-conversation request conflicts");
    var next = await store.StartNewAsync("customer-001", resolved.Revision);
    Check(next.Id != resolved.Id && next.Status == "automated" && next.Messages.Count == 0 &&
        (await store.QueueAsync()).Any(item => item.Id == resolved.Id && item.Status == "resolved"),
        "new conversation preserves the resolved case and restarts the independent AI workflow");
    await Reject<AccessException>(() => store.ApplyAsync(resolved.Id, "customer-001", false, resolved.Revision,
        "customer-reply", "Reopen silently"), "resolved case cannot be mutated by customer");
    await Reject<InvalidDataException>(() => Task.FromResult(FoundrySelector.ParseSelection(
        JsonDocument.Parse("""{"id":"test","status":"incomplete","output":[]}""").RootElement, entries)),
        "incomplete inference is not success");
    await Reject<InputException>(() => Task.Run(() => BrokerageStore.RequireText(new string('x', 2001))),
        "input limit is exactly 2000 characters");
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        status = "passed",
        evidenceType = "local-component-tests-not-Azure-runtime",
        checkedAtUtc = DateTimeOffset.UtcNow,
        count = results.Count,
        checks = results
    }, new JsonSerializerOptions { WriteIndented = true }));

    AnswerSelection Parse(string source)
    {
        using var json = JsonDocument.Parse(JsonSerializer.Serialize(new
        {
            id = "test-only-agent-receipt",
            output = new[] { new { type = "function_call", name = "select_company_answer",
                arguments = JsonSerializer.Serialize(new { source_id = source }) } }
        }));
        return FoundrySelector.ParseSelection(json.RootElement, entries);
    }
}
finally
{
    Directory.Delete(root, true);
}

void Check(bool condition, string name)
{
    if (!condition)
    {
        throw new InvalidOperationException("FAILED: " + name);
    }
    results.Add(name);
}

async Task Reject<T>(Func<Task> operation, string name) where T : Exception
{
    try
    {
        await operation();
    }
    catch (T)
    {
        results.Add(name);
        return;
    }
    throw new InvalidOperationException("FAILED: " + name);
}

internal sealed class SelectionHandler : HttpMessageHandler
{
    internal string? Path { get; private set; }
    internal string? Body { get; private set; }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellation)
    {
        Path = request.RequestUri!.GetComponents(UriComponents.PathAndQuery, UriFormat.UriEscaped);
        Body = await request.Content!.ReadAsStringAsync(cancellation);
        return new(HttpStatusCode.OK)
        {
            Content = new StringContent(
                """{"id":"local-test-only","status":"completed","output":[{"type":"function_call","name":"select_company_answer","arguments":"{\"source_id\":\"1\"}"}]}""",
                Encoding.UTF8, "application/json")
        };
    }
}

internal sealed class ComponentCredential : TokenCredential
{
    /// <inheritdoc />
    public override AccessToken GetToken(TokenRequestContext requestContext, CancellationToken cancellationToken) =>
        new("local-component-test-not-an-Azure-token", DateTimeOffset.UtcNow.AddMinutes(1));

    /// <inheritdoc />
    public override ValueTask<AccessToken> GetTokenAsync(
        TokenRequestContext requestContext, CancellationToken cancellationToken) =>
        ValueTask.FromResult(GetToken(requestContext, cancellationToken));
}
