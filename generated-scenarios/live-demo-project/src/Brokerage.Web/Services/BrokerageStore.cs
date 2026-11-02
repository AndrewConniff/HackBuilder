using System.Security.Cryptography;
using System.Text.Json;
using System.Security.AccessControl;
using System.Security.Principal;
using Microsoft.AspNetCore.Identity;

namespace Brokerage.Web.Services;

internal sealed record KnowledgeEntry(int Id, string Title, string Version, string Question, string Answer, bool Approved);
internal sealed record Message(string Author, string Text, string? Source, string? Receipt);
internal sealed record Conversation(string Id, string CustomerId, string Status, string? Owner, int Revision,
    List<Message> Messages);
internal sealed record Account(string Id, string Name, string Role, string Hash, int Failures, DateTimeOffset? LockedUntil);
internal sealed record StoreState(List<Account> Accounts, List<KnowledgeEntry> Knowledge, List<Conversation> Conversations);
internal sealed record AnswerSelection(string SourceId, string Receipt);
internal sealed class StateConflictException(string message) : Exception(message);
internal sealed class InputException(string message) : Exception(message);
internal sealed class AccessException(string message) : Exception(message);

internal sealed class BrokerageStore(string directory)
{
    private readonly string statePath = Path.Combine(directory, "state.json");
    private readonly SemaphoreSlim mutex = new(1, 1);
    private readonly PasswordHasher<string> hasher = new();
    private readonly string unknownAccountHash = new PasswordHasher<string>().HashPassword("unknown", "invalid-account");
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    private async Task<T> TransactionAsync<T>(Func<StoreState, T> operation)
    {
        await mutex.WaitAsync();
        try
        {
            Directory.CreateDirectory(directory);
            await using var processLock = new FileStream(
                Path.Combine(directory, "state.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            if (!File.Exists(statePath))
            {
                throw new InvalidOperationException("Accounts and approved knowledge are not initialized.");
            }
            var state = JsonSerializer.Deserialize<StoreState>(await File.ReadAllTextAsync(statePath))
                ?? throw new InvalidDataException("Persistent brokerage state is invalid.");
            var result = operation(state);
            var temporary = statePath + ".tmp";
            await File.WriteAllTextAsync(temporary, JsonSerializer.Serialize(state, JsonOptions));
            File.Move(temporary, statePath, true);
            return result;
        }
        finally
        {
            mutex.Release();
        }
    }

    internal async Task InitializeAsync(string knowledgePath, string privateDirectory)
    {
        if (File.Exists(statePath))
        {
            throw new InvalidOperationException("Already initialized; refusing to replace accounts or business data.");
        }
        Directory.CreateDirectory(directory);
        Directory.CreateDirectory(privateDirectory);
        if (OperatingSystem.IsWindows())
        {
            var user = WindowsIdentity.GetCurrent().User
                ?? throw new InvalidOperationException("Current Windows user SID is unavailable.");
            foreach (var path in new[] { directory, privateDirectory })
            {
                var security = new DirectorySecurity();
                security.SetOwner(user);
                security.SetAccessRuleProtection(true, false);
                security.AddAccessRule(new FileSystemAccessRule(user, FileSystemRights.FullControl,
                    InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit,
                    PropagationFlags.None, AccessControlType.Allow));
                new DirectoryInfo(path).SetAccessControl(security);
            }
        }
        else
        {
            File.SetUnixFileMode(directory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            File.SetUnixFileMode(privateDirectory, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        }
        var knowledge = JsonSerializer.Deserialize<List<KnowledgeEntry>>(await File.ReadAllTextAsync(knowledgePath))
            ?? throw new InvalidDataException("Knowledge catalog is missing.");
        if (knowledge.Count == 0 || knowledge.Select(entry => entry.Id).Distinct().Count() != knowledge.Count)
        {
            throw new InvalidDataException("Knowledge catalog must have distinct entries.");
        }
        var accounts = new List<Account>();
        foreach (var account in new[]
        {
            (Id: "customer-001", Name: "Airi Ilves", Role: "Participant", File: "participant-access.json"),
            (Id: "representative-001", Name: "Hasan Ibrahimov", Role: "Coach", File: "coach-access.json")
        })
        {
            var password = Convert.ToBase64String(RandomNumberGenerator.GetBytes(24));
            accounts.Add(new(account.Id, account.Name, account.Role,
                hasher.HashPassword(account.Id, password), 0, null));
            var accessPath = Path.Combine(privateDirectory, account.File);
            await File.WriteAllTextAsync(accessPath, JsonSerializer.Serialize(new
            {
                username = account.Id, password, role = account.Role,
                loginPath = "/Login", deployment = "live-demo-project"
            }, JsonOptions));
            if (!OperatingSystem.IsWindows())
            {
                File.SetUnixFileMode(accessPath, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            }
        }
        await File.WriteAllTextAsync(statePath, JsonSerializer.Serialize(new StoreState(accounts, knowledge, []), JsonOptions));
    }

    internal Task<Account?> LoginAsync(string id, string password) => TransactionAsync(state =>
    {
        var index = state.Accounts.FindIndex(account => account.Id == id);
        if (index < 0)
        {
            // Equal-cost verification reduces username enumeration through response timing.
            hasher.VerifyHashedPassword(id, unknownAccountHash, password);
            return null;
        }
        var account = state.Accounts[index];
        if (account.LockedUntil > DateTimeOffset.UtcNow)
        {
            return null;
        }
        if (hasher.VerifyHashedPassword(id, account.Hash, password) == PasswordVerificationResult.Failed)
        {
            var failures = account.LockedUntil is not null ? 1 : account.Failures + 1;
            state.Accounts[index] = account with
            {
                Failures = failures,
                LockedUntil = failures >= 5 ? DateTimeOffset.UtcNow.AddMinutes(5) : null
            };
            return null;
        }
        state.Accounts[index] = account with { Failures = 0, LockedUntil = null };
        return account;
    });

    internal Task<List<KnowledgeEntry>> KnowledgeAsync() =>
        TransactionAsync(state => state.Knowledge.Where(entry => entry.Approved).ToList());

    internal Task<Conversation> CurrentAsync(string customer) => TransactionAsync(state =>
    {
        var current = state.Conversations.LastOrDefault(item => item.CustomerId == customer);
        if (current is not null)
        {
            return current;
        }
        var created = new Conversation(Guid.NewGuid().ToString("N"), customer, "automated", null, 0, []);
        state.Conversations.Add(created);
        return created;
    });

    internal Task<List<Conversation>> QueueAsync() =>
        TransactionAsync(state => state.Conversations.Where(item => item.Status != "automated").ToList());

    internal Task<Conversation> StartNewAsync(string customer, int revision) => TransactionAsync(state =>
    {
        var current = state.Conversations.LastOrDefault(item => item.CustomerId == customer);
        if (current is null || current.Status != "resolved" || current.Revision != revision)
        {
            throw new StateConflictException("Resolve the current case and refresh before starting another conversation.");
        }
        var created = new Conversation(Guid.NewGuid().ToString("N"), customer, "automated", null, 0, []);
        state.Conversations.Add(created);
        return created;
    });

    internal Task<Conversation> ApplyAsync(string id, string actor, bool coach, int revision,
        string action, string? text = null, AnswerSelection? selection = null) => TransactionAsync(state =>
    {
        var index = state.Conversations.FindIndex(item => item.Id == id);
        if (index < 0)
        {
            throw new InputException("Conversation not found.");
        }
        var current = state.Conversations[index];
        if (!coach && current.CustomerId != actor)
        {
            throw new AccessException("This conversation belongs to another customer.");
        }
        if (action == "escalate" && !coach && current.Status != "automated")
        {
            return current;
        }
        if (current.Revision != revision)
        {
            throw new StateConflictException("Conversation changed. Refresh before retrying.");
        }
        var messages = current.Messages.ToList();
        var updated = current;
        switch (action)
        {
            case "answer" when !coach && current.Status == "automated":
                RequireText(text);
                var source = state.Knowledge.SingleOrDefault(entry =>
                    entry.Approved && entry.Id.ToString(System.Globalization.CultureInfo.InvariantCulture) == selection?.SourceId);
                if (selection is null || string.IsNullOrWhiteSpace(selection.Receipt))
                {
                    throw new InputException("A verified agent receipt is required.");
                }
                if (source is null && selection.SourceId != "unsupported")
                {
                    throw new InputException("Agent selected an unknown or unapproved source.");
                }
                messages.Add(new("Customer", text!, null, null));
                messages.Add(source is null
                    ? new("Service notice", "No approved company answer was found. You can request a representative.",
                        null, selection.Receipt)
                    : new("Company knowledge", source.Answer, $"{source.Id}: {source.Title} / {source.Version}",
                        selection.Receipt));
                break;
            case "escalate" when !coach && current.Status == "automated":
                updated = current with { Status = "waiting" };
                break;
            case "claim" when coach && current.Status == "waiting":
                updated = current with { Status = "claimed", Owner = actor };
                break;
            case "reply" when coach && current.Status == "claimed" && current.Owner == actor:
                RequireText(text);
                messages.Add(new("Representative", text!, null, null));
                break;
            case "customer-reply" when !coach && current.Status is "waiting" or "claimed":
                RequireText(text);
                messages.Add(new("Customer", text!, null, null));
                break;
            case "resolve" when coach && current.Status == "claimed" && current.Owner == actor:
                updated = current with { Status = "resolved" };
                break;
            default:
                throw new AccessException("Action is not permitted for this role, owner or conversation state.");
        }
        updated = updated with { Revision = current.Revision + 1, Messages = messages };
        state.Conversations[index] = updated;
        return updated;
    });

    internal static void RequireText(string? text)
    {
        if (string.IsNullOrWhiteSpace(text) || text.Length > 2000)
        {
            throw new InputException("Enter between 1 and 2,000 characters.");
        }
    }
}
