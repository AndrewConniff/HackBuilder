using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Restaurant.Web.Models;

/// <summary>Represents an explicitly rejected business operation.</summary>
public sealed class DomainException(int status, string message) : Exception(message)
{
    /// <summary>Gets the HTTP rejection status.</summary>
    public int Status { get; } = status;
}

/// <summary>Immutable authenticated business scope, never supplied by an agent.</summary>
public sealed record Caller(string Subject, string Role, string? VisitId, int[] Floors)
{
    /// <summary>Builds scope exclusively from verified claims.</summary>
    public static Caller From(ClaimsPrincipal principal)
    {
        var subject = principal.FindFirstValue("sub") ?? principal.FindFirstValue("oid")
            ?? throw new DomainException(403, "A stable subject claim is required.");
        if (principal.Identity?.AuthenticationType == "guest")
            return new(subject, "Guest", principal.FindFirstValue("visit"), []);
        var roles = principal.FindAll("roles").Select(c => c.Value).ToArray();
        var role = new[] { "Manager", "Kitchen", "Server", "Host" }.FirstOrDefault(roles.Contains)
            ?? throw new DomainException(403, "A restaurant staff app role is required.");
        var floors = principal.FindAll("floors").SelectMany(c => c.Value.Split(','))
            .Select(value => int.TryParse(value, out var floor) ? floor : 0)
            .Where(floor => floor is >= 1 and <= 5)
            .Concat(Enumerable.Range(1, 5).Where(floor => roles.Contains($"Floor.{floor}")))
            .Distinct().ToArray();
        if (role != "Manager" && floors.Length == 0)
            throw new DomainException(403, "Staff floor assignments are required.");
        return new(subject, role, null, role == "Manager" ? [1, 2, 3, 4, 5] : floors);
    }

    /// <summary>Rejects cross-visit and cross-floor access.</summary>
    public void Demand(Visit visit, bool financial = false)
    {
        if (Role == "Guest" ? VisitId != visit.id : !Floors.Contains(visit.Floor))
            throw new DomainException(403, "This visit is outside your authorized scope.");
        if (financial && Role == "Kitchen")
            throw new DomainException(403, "Kitchen staff cannot access bills.");
    }
}

/// <summary>A versioned menu item with an authoritative integer minor-unit price.</summary>
public sealed record MenuItem(int Id, string Name, int PriceMinor, bool Available, bool Vegetarian, int Version);

/// <summary>A priced immutable order line captured at confirmation.</summary>
public sealed record OrderLine(int Id, string Name, int Quantity, int PriceMinor, int MenuVersion);

/// <summary>A kitchen ticket whose dispatch and preparation statuses are distinct.</summary>
public sealed record Ticket(string Id, OrderLine[] Lines, string Status, bool Dispatched,
    DateTimeOffset CreatedAt, int Sequence = 1);

/// <summary>Authoritative visit state; all dependent writes share its Cosmos partition.</summary>
public sealed record Visit(
    string id, string aggregateKey, string Type, int Version, string ReservationId,
    string Slot, int Floor, int Seats, string GuestName, string AccessHash,
    string Status, Ticket[] Tickets, bool Settled, int? Survey, string LegacyReferenceId,
    bool AllocationReleased = false)
{
    /// <summary>Gets the server-priced total in USD cents.</summary>
    public int TotalMinor => checked(Tickets.Sum(ticket => ticket.Lines.Sum(line => line.PriceMinor * line.Quantity)));
}

/// <summary>A versioned reservation allocation in the authoritative service-slot partition.</summary>
public sealed record Allocation(string VisitId, int Floor, int Seats, string GuestName, string AccessHash);

/// <summary>A capacity-controlled meal slot with a fixed five-floor venue.</summary>
public sealed record Slot(string id, string aggregateKey, string Type, int Version, Allocation[] Allocations);

/// <summary>A typed action submitted for preview and explicit confirmation.</summary>
public sealed record Command(string Kind, string VisitId, int ExpectedVersion,
    Dictionary<int, int>? Items = null, string? TicketId = null, string? TargetStatus = null, int? Rating = null);

/// <summary>A caller-bound, expiring, durable action preview.</summary>
public sealed record Preview(string id, string aggregateKey, string Type, string Subject,
    Command Command, string Digest, DateTimeOffset ExpiresAt, int TotalMinor);

/// <summary>A stable idempotency receipt; no transport response implies success without this record.</summary>
public sealed record Receipt(string id, string aggregateKey, string Type, string Digest,
    string Action, string EntityId, int Version, int TotalMinor, DateTimeOffset CommittedAt);

/// <summary>A durable event committed atomically with business state.</summary>
public sealed record Outbox(string id, string aggregateKey, string Type, string Kind,
    string EntityId, string SessionId, int Version, string Status, DateTimeOffset CreatedAt, int Sequence = 0,
    string? LegacyReferenceId = null);

/// <summary>The deterministic rules shared by the transaction API and tests.</summary>
public static class Rules
{
    /// <summary>Hashes canonical request content for idempotency and preview binding.</summary>
    public static string Digest<T>(T value) =>
        Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(value)));

    /// <summary>Hashes a high-entropy reservation code before durable storage.</summary>
    public static string HashCode(string code) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(code)));

    /// <summary>Compares stored code hashes without timing-dependent string comparison.</summary>
    public static bool VerifyCode(string code, string expected) =>
        CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(HashCode(code)), Encoding.ASCII.GetBytes(expected));

    /// <summary>Checks bounded service slot syntax without deriving cloud configuration.</summary>
    public static void ValidateSlot(string slot)
    {
        if (string.IsNullOrWhiteSpace(slot)) throw new DomainException(400, "A service slot is required.");
        var parts = slot.Split(':');
        if (parts.Length != 2 || !DateOnly.TryParseExact(parts[0], "yyyy-MM-dd", out _)
            || !int.TryParse(parts[1], out var turn) || turn is < 1 or > 5)
            throw new DomainException(400, "Use a service slot yyyy-MM-dd:1 through :5.");
    }

    /// <summary>Allocates capacity without exceeding fifty seats on any floor.</summary>
    public static Slot Reserve(Slot slot, Allocation allocation)
    {
        if (allocation.Floor is < 1 or > 5 || allocation.Seats is < 1 or > 12
            || slot.Allocations.Where(a => a.Floor == allocation.Floor).Sum(a => a.Seats) + allocation.Seats > 50)
            throw new DomainException(409, "The requested floor has insufficient capacity.");
        return slot with { Version = slot.Version + 1, Allocations = [.. slot.Allocations, allocation] };
    }

    /// <summary>Applies an authorized action to one aggregate, rejecting stale or unsafe writes.</summary>
    public static Visit Apply(Visit visit, Command command, Caller caller, MenuItem[] menu, DateTimeOffset now)
    {
        caller.Demand(visit, command.Kind is "settle" or "survey");
        if (command.VisitId != visit.id || command.ExpectedVersion != visit.Version)
            throw new DomainException(409, "Visit changed. Refresh and create a new preview.");
        var result = command.Kind switch
        {
            "checkin" when caller.Role is "Guest" or "Host" or "Server" or "Manager"
                && visit.Status == "Reserved" => visit with { Status = "Active" },
            "cancel" when caller.Role is "Guest" or "Host" or "Server" or "Manager"
                && visit.Status == "Reserved" => visit with { Status = "Cancelled" },
            "order" when caller.Role is "Guest" or "Server" or "Manager"
                && visit.Status == "Active" && !visit.Settled => AddOrder(visit, command, menu, now),
            "transition" when caller.Role is "Kitchen" or "Server" or "Manager" => Transition(visit, command, caller),
            "settle" when caller.Role is "Guest" or "Server" or "Manager"
                && !visit.Settled && visit.Tickets.Length > 0 && visit.Tickets.All(t => t.Status == "served")
                => visit with { Settled = true, Status = "Settled" },
            "survey" when caller.Role is "Guest" or "Manager"
                && visit.Settled && visit.Survey is null && command.Rating is >= 1 and <= 5
                => visit with { Survey = command.Rating },
            _ => throw new DomainException(409, "Action is not permitted for this role or current visit state.")
        };
        return result with { Version = visit.Version + 1 };
    }

    private static Visit AddOrder(Visit visit, Command command, MenuItem[] menu, DateTimeOffset now)
    {
        if (command.Items is null || command.Items.Count is < 1 or > 12 || visit.Tickets.Length >= 50)
            throw new DomainException(400, "Select 1-12 menu items; at most 50 orders per visit.");
        var lines = command.Items.OrderBy(pair => pair.Key).Select(pair =>
        {
            var item = menu.SingleOrDefault(item => item.Id == pair.Key && item.Available)
                ?? throw new DomainException(409, "A menu item is unavailable.");
            if (pair.Value is < 1 or > 12) throw new DomainException(400, "Quantity must be 1-12.");
            return new OrderLine(item.Id, item.Name, pair.Value, item.PriceMinor, item.Version);
        }).ToArray();
        // Deriving the ticket ID from the version makes a retried preview produce the same event identity.
        return visit with { Tickets = [.. visit.Tickets,
            new($"{visit.id}-{visit.Version + 1}", lines, "submitted", false, now)] };
    }

    private static Visit Transition(Visit visit, Command command, Caller caller)
    {
        var ticket = visit.Tickets.SingleOrDefault(t => t.Id == command.TicketId)
            ?? throw new DomainException(404, "Ticket not found.");
        var next = ticket.Status switch
        {
            "submitted" => "accepted", "accepted" => "preparing", "preparing" => "ready", "ready" => "served", _ => null
        };
        if (!ticket.Dispatched || next is null || next != command.TargetStatus
            || next == "served" && caller.Role == "Kitchen"
            || next != "served" && caller.Role == "Server")
            throw new DomainException(409, "Invalid kitchen transition, role or pending dispatch.");
        return visit with { Tickets = visit.Tickets.Select(t => t.Id == ticket.Id
            ? t with { Status = next, Sequence = t.Sequence + 1 } : t).ToArray() };
    }
}
