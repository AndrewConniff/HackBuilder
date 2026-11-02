using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Security.Claims;
using Brokerage.Web.Services;

namespace Brokerage.Web.Pages;

/// <summary>Shows company-only answers and the customer's human support conversation.</summary>
public class IndexModel(IServiceProvider services, ILogger<IndexModel> logger) : PageModel
{
    private readonly BrokerageStore store = services.GetRequiredService<BrokerageStore>();
    internal Conversation? Conversation { get; private set; }
    internal string? Error { get; private set; }

    /// <summary>Loads the signed-in customer's conversation.</summary>
    public async Task<IActionResult> OnGetAsync()
    {
        if (User.IsInRole("Coach"))
        {
            return RedirectToPage("/Desk");
        }
        Conversation = await store.CurrentAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
        return Page();
    }

    /// <summary>Asks the real Foundry agent to select an approved company source.</summary>
    public async Task<IActionResult> OnPostAskAsync(string question, int revision)
    {
        try
        {
            if (!User.IsInRole("Participant"))
            {
                return Forbid();
            }
            BrokerageStore.RequireText(question);
            var actor = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
            var conversation = await store.CurrentAsync(actor);
            if (conversation.Status != "automated")
            {
                throw new StateConflictException("A representative owns this conversation. AI answers are paused.");
            }
            var selection = await services.GetRequiredService<IAnswerSelector>()
                .SelectAsync(question, await store.KnowledgeAsync(), HttpContext.RequestAborted);
            await store.ApplyAsync(conversation.Id, actor, false, revision, "answer", question, selection);
            return RedirectToPage();
        }
        catch (Exception exception) when (exception is InputException or StateConflictException
            or InvalidOperationException or HttpRequestException or InvalidDataException
            or System.Text.Json.JsonException or OperationCanceledException or Azure.Identity.CredentialUnavailableException
            or Azure.Identity.AuthenticationFailedException)
        {
            logger.LogWarning(exception, "Question failed. Correlation {Correlation}", HttpContext.TraceIdentifier);
            Error = $"The answer could not be completed. {exception.Message} Reference: {HttpContext.TraceIdentifier}";
            Response.StatusCode = exception is InputException ? 400 : exception is StateConflictException ? 409 : 503;
            Conversation = await store.CurrentAsync(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
            return Page();
        }
    }

    /// <summary>Transfers ownership into the durable human queue.</summary>
    public async Task<IActionResult> OnPostEscalateAsync(int revision)
    {
        if (!User.IsInRole("Participant"))
        {
            return Forbid();
        }
        var actor = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var conversation = await store.CurrentAsync(actor);
        try
        {
            await store.ApplyAsync(conversation.Id, actor, false, revision, "escalate");
        }
        catch (StateConflictException exception)
        {
            logger.LogWarning(exception, "Escalation conflict for {Conversation}", conversation.Id);
            Error = exception.Message;
            Response.StatusCode = 409;
            Conversation = await store.CurrentAsync(actor);
            return Page();
        }
        return RedirectToPage();
    }

    /// <summary>Adds a customer message to an open human-owned case without invoking AI.</summary>
    public async Task<IActionResult> OnPostReplyAsync(string text, int revision)
    {
        if (!User.IsInRole("Participant"))
        {
            return Forbid();
        }
        var actor = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var conversation = await store.CurrentAsync(actor);
        try
        {
            await store.ApplyAsync(conversation.Id, actor, false, revision, "customer-reply", text);
            return RedirectToPage();
        }

        /// <summary>Starts a separate conversation after resolution without changing the prior case.</summary>
        public async Task<IActionResult> OnPostStartNewAsync(int revision)
        {
            if (!User.IsInRole("Participant"))
            {
                return Forbid();
            }
            var actor = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
            try
            {
                await store.StartNewAsync(actor, revision);
            }
            catch (StateConflictException exception)
            {
                logger.LogWarning(exception, "New conversation rejected for {Customer}", actor);
                Error = exception.Message;
                Response.StatusCode = 409;
                Conversation = await store.CurrentAsync(actor);
                return Page();
            }
            return RedirectToPage();
        }
        catch (Exception exception) when (exception is AccessException or InputException or StateConflictException)
        {
            logger.LogWarning(exception, "Customer reply rejected for {Case}", conversation.Id);
            Error = exception.Message;
            Response.StatusCode = exception is AccessException ? 403 : exception is StateConflictException ? 409 : 400;
            Conversation = await store.CurrentAsync(actor);
            return Page();
        }
    }
}
