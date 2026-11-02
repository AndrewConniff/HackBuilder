using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Azure.Cosmos;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>A guest-confirmed reservation request; names must reference the synthetic catalog mapping.</summary>
public sealed record ReservationRequest(string Slot, int Floor, int Seats, string GuestId, string RequestId,
    string? LegacyReferenceId = null);

/// <summary>A reservation receipt with the access code returned only at creation.</summary>
public sealed record ReservationResult(string VisitId, string AccessCode, string Status);

/// <summary>A typed capacity proposal without caller-controlled guest identity or idempotency key.</summary>
public sealed record ReservationProposal(string Slot, int Floor, int Seats);

/// <summary>An expiring caller-bound capacity preview; confirmation still rechecks authoritative slot version.</summary>
public sealed record ReservationPreview(string id, string aggregateKey, string Type, string Subject,
    ReservationRequest Request, int ExpectedSlotVersion, DateTimeOffset ExpiresAt);

/// <summary>Transactional business application independent of Foundry and Service Bus availability.</summary>
public sealed class RestaurantService(CosmosStore store, TimeProvider clock, IWebHostEnvironment environment)
{
    private static readonly Dictionary<string, string> Guests = new() { ["guest-001"] = "Airi Ilves" };

    /// <summary>Reserves authoritative capacity and a durable visit-creation outbox event atomically.</summary>
    public async Task<ReservationResult> Reserve(ReservationRequest request, CancellationToken token,
        int? expectedSlotVersion = null)
    {
        Rules.ValidateSlot(request.Slot);
        ValidateKey(request.RequestId);
        if (request.LegacyReferenceId is not null
            && (string.IsNullOrWhiteSpace(request.LegacyReferenceId) || request.LegacyReferenceId.Length > 128))
            throw new DomainException(400, "Legacy reference must contain 1-128 characters.");
        if (!Guests.TryGetValue(request.GuestId, out var name))
            throw new DomainException(400, "Use the catalog-backed synthetic guest guest-001.");
        var partition = $"slot:{request.Slot}";
        var id = Rules.Digest(new { request.Slot, request.RequestId })[..24].ToLowerInvariant();
        var existing = await CosmosStore.Read<Receipt>(store.Transactions, $"receipt:{request.RequestId}", partition, token);
        var digest = Rules.Digest(request);
        if (existing is not null)
        {
            if (existing.Value.Item.Digest != digest) throw new DomainException(409, "Idempotency key reused for a different request.");
            return new(existing.Value.Item.EntityId, string.Empty, "Reserved; use the originally issued access code.");
        }
        var code = Convert.ToHexString(RandomNumberGenerator.GetBytes(16));
        var slot = await CosmosStore.Read<Slot>(store.Transactions, "slot", partition, token);
        var before = slot?.Item ?? new Slot("slot", partition, "slot", 0, []);
        if (expectedSlotVersion is not null && before.Version != expectedSlotVersion)
            throw new DomainException(409, "Capacity changed; create a fresh reservation preview.");
        var after = Rules.Reserve(before, new(id, request.Floor, request.Seats, name, Rules.HashCode(code)));
        var batch = store.Transactions.CreateTransactionalBatch(new(partition));
        if (slot is null) batch.CreateItem(after);
        else batch.ReplaceItem("slot", after, new() { IfMatchEtag = slot.Value.ETag });
        var receipt = new Receipt($"receipt:{request.RequestId}", partition, "receipt", digest,
            "reserve", id, after.Version, 0, clock.GetUtcNow());
        batch.CreateItem(receipt).CreateItem(new Outbox($"event:{id}", partition, "outbox",
            "reservation", id, id, after.Version, "pending", clock.GetUtcNow(),
            LegacyReferenceId: request.LegacyReferenceId));
        await store.Commit(batch, token);
        return new(id, code, "Reserved; visit preparing");
    }

    /// <summary>Grounds a future synthetic reservation in current capacity without allocating any seats.</summary>
    public async Task<ReservationPreview> PreviewReservation(ReservationProposal proposal, Caller caller, CancellationToken token)
    {
        Rules.ValidateSlot(proposal.Slot);
        DemandReservation(caller, proposal.Floor);
        var partition = $"slot:{proposal.Slot}";
        var slot = (await CosmosStore.Read<Slot>(store.Transactions, "slot", partition, token))?.Item
            ?? new Slot("slot", partition, "slot", 0, []);
        _ = Rules.Reserve(slot, new("capacity-check", proposal.Floor, proposal.Seats, Guests["guest-001"], string.Empty));
        var preview = new ReservationPreview(Guid.NewGuid().ToString("N"), partition, "reservation-preview",
            caller.Subject, new(proposal.Slot, proposal.Floor, proposal.Seats, "guest-001", Guid.NewGuid().ToString("N")),
            slot.Version, clock.GetUtcNow().AddMinutes(2));
        await store.Transactions.CreateItemAsync(preview, new(partition), cancellationToken: token);
        return preview;
    }

    /// <summary>Allocates only the reviewed capacity proposal after explicit human confirmation.</summary>
    public async Task<ReservationResult> ConfirmReservation(string slot, string previewId, Caller caller, CancellationToken token)
    {
        Rules.ValidateSlot(slot);
        var preview = (await CosmosStore.Read<ReservationPreview>(store.Transactions, previewId, $"slot:{slot}", token))?.Item
            ?? throw new DomainException(404, "Reservation preview not found.");
        if (preview.Subject != caller.Subject) throw new DomainException(403, "Reservation preview belongs to another caller.");
        DemandReservation(caller, preview.Request.Floor);
        if (preview.ExpiresAt <= clock.GetUtcNow()) throw new DomainException(409, "Reservation preview expired.");
        return await Reserve(preview.Request, token, preview.ExpectedSlotVersion);
    }

    private static void DemandReservation(Caller caller, int floor)
    {
        if (caller.Role is not ("Guest" or "Host" or "Server" or "Manager")
            || caller.Role != "Guest" && !caller.Floors.Contains(floor))
            throw new DomainException(403, "Reservation is outside your role or floor scope.");
    }

    /// <summary>Authenticates only the requested reservation using its high-entropy code.</summary>
    public async Task<Visit> Login(string id, string code, CancellationToken token)
    {
        var visit = (await store.Visit(id, token)).Item;
        if (!Rules.VerifyCode(code, visit.AccessHash)) throw new DomainException(403, "Invalid reservation access code.");
        return visit;
    }

    /// <summary>Reads the caller's visit, removing financial fields for kitchen staff.</summary>
    public async Task<object> View(string id, Caller caller, CancellationToken token)
    {
        var visit = (await store.Visit(id, token)).Item;
        caller.Demand(visit);
        return caller.Role == "Kitchen"
            ? new { visit.id, visit.Floor, visit.Version, visit.Status,
                Tickets = visit.Tickets.Select(t => new { t.Id, t.Status, t.Dispatched, t.CreatedAt,
                    Lines = t.Lines.Select(l => new { l.Name, l.Quantity }) }) }
            : new { visit.id, visit.Floor, visit.Version, visit.Status, visit.AllocationReleased,
                visit.LegacyReferenceId, visit.Tickets, visit.TotalMinor,
                visit.Settled, visit.Survey, Currency = "USD", PaymentNotice = "Synthetic settlement - no money charged" };
    }

    /// <summary>Creates a durable caller-bound preview without applying the proposed write.</summary>
    public async Task<Preview> Preview(Command command, Caller caller, CancellationToken token)
    {
        var visit = (await store.Visit(command.VisitId, token)).Item;
        var menu = await store.Menu(token);
        var candidate = Rules.Apply(visit, command, caller, menu, clock.GetUtcNow());
        var preview = new Preview(Guid.NewGuid().ToString("N"), visit.aggregateKey, "preview",
            caller.Subject, command, Rules.Digest(command), clock.GetUtcNow().AddMinutes(2), candidate.TotalMinor);
        await store.Transactions.CreateItemAsync(preview, new(visit.aggregateKey), cancellationToken: token);
        return preview;
    }

    /// <summary>Confirms exactly the stored preview with ETag, authorization and idempotency revalidation.</summary>
    public async Task<Receipt> Confirm(string visitId, string previewId, string key, Caller caller, CancellationToken token)
    {
        ValidateKey(key);
        var partition = $"visit:{visitId}";
        var preview = (await CosmosStore.Read<Preview>(store.Transactions, previewId, partition, token))?.Item
            ?? throw new DomainException(404, "Preview not found.");
        if (preview.Subject != caller.Subject) throw new DomainException(403, "Preview belongs to another caller.");
        var (before, etag) = await store.Visit(visitId, token);
        caller.Demand(before, preview.Command.Kind is "settle" or "survey");
        var prior = await CosmosStore.Read<Receipt>(store.Transactions, $"receipt:{key}", partition, token);
        if (prior is not null)
        {
            if (prior.Value.Item.Digest != preview.Digest) throw new DomainException(409, "Idempotency key reused.");
            return prior.Value.Item;
        }
        if (preview.ExpiresAt <= clock.GetUtcNow()) throw new DomainException(409, "Preview expired; create a new preview.");
        if (preview.Command.Kind == "checkin")
        {
            var slot = await CosmosStore.Read<Slot>(store.Transactions, "slot", $"slot:{before.Slot}", token)
                ?? throw new DomainException(409, "Authoritative allocation is missing.");
            if (!slot.Item.Allocations.Any(allocation => allocation.VisitId == visitId))
                throw new DomainException(409, "Reservation allocation is no longer valid.");
        }
        var after = Rules.Apply(before, preview.Command, caller, await store.Menu(token), clock.GetUtcNow());
        var receipt = new Receipt($"receipt:{key}", partition, "receipt", preview.Digest,
            preview.Command.Kind, visitId, after.Version, after.TotalMinor, clock.GetUtcNow());
        var ticket = preview.Command.Kind == "transition"
            ? after.Tickets.Single(t => t.Id == preview.Command.TicketId) : after.Tickets.LastOrDefault();
        var ticketId = preview.Command.Kind is "order" or "transition" ? ticket!.Id : visitId;
        var batch = store.Transactions.CreateTransactionalBatch(new(partition))
            .ReplaceItem(visitId, after, new() { IfMatchEtag = etag })
            .CreateItem(receipt)
            .CreateItem(new { id = $"audit:{key}", aggregateKey = partition, Type = "audit",
                caller.Subject, Action = preview.Command.Kind, Version = after.Version, At = clock.GetUtcNow() })
            .CreateItem(new Outbox($"event:{visitId}:{after.Version}", partition, "outbox",
                preview.Command.Kind, visitId, ticketId, after.Version, "pending", clock.GetUtcNow(),
                preview.Command.Kind is "order" or "transition" ? ticket!.Sequence : 0));
        if (preview.Command.Kind == "settle")
            batch.CreateItem(new { id = "settlement", aggregateKey = partition, Type = "settlement",
                AmountMinor = after.TotalMinor, Currency = "USD", Synthetic = true, receipt.CommittedAt });
        await store.Commit(batch, token);
        return receipt;
    }

    /// <summary>Returns a bounded floor-scoped operational board, excluding financial and guest identity fields.</summary>
    public async Task<object[]> Board(Caller caller, string slot, int? floor, CancellationToken token)
    {
        if (caller.Role == "Guest") throw new DomainException(403, "Staff access required.");
        Rules.ValidateSlot(slot);
        if (floor is not null && !caller.Floors.Contains(floor.Value))
            throw new DomainException(403, "Floor is outside your authorized scope.");
        var floors = floor is null ? caller.Floors : [floor.Value];
        var visits = await store.Query<Visit>(store.Transactions, new QueryDefinition(
            "SELECT TOP 250 * FROM c WHERE c.Type = 'visit' AND c.Slot = @slot AND ARRAY_CONTAINS(@floors, c.Floor)")
            .WithParameter("@slot", slot).WithParameter("@floors", floors), 250, token);
        return visits.Select(v => (object)new { v.id, v.Floor, v.Version, v.Status,
            Tickets = v.Tickets.Select(t => new { t.Id, t.Status, t.Dispatched, t.CreatedAt,
                AgeSeconds = (int)(clock.GetUtcNow() - t.CreatedAt).TotalSeconds,
                Lines = t.Lines.Select(l => new { l.Name, l.Quantity }) }) }).ToArray();
    }

    /// <summary>Imports versioned synthetic source documents without overwriting existing state.</summary>
    public async Task Initialize(CancellationToken token)
    {
        var path = Path.Combine(environment.ContentRootPath, "SeedData", "catalog.json");
        using var seed = JsonDocument.Parse(await File.ReadAllTextAsync(path, token));
        foreach (var document in seed.RootElement.EnumerateArray())
        {
            var id = document.GetProperty("id").GetString()!;
            var partition = document.GetProperty("aggregateKey").GetString()!;
            var existing = await CosmosStore.Read<JsonElement>(store.Catalog, id, partition, token);
            if (existing is not null)
            {
                if (existing.Value.Item.GetProperty("Version").GetInt32() != document.GetProperty("Version").GetInt32())
                    throw new InvalidDataException($"Catalog {id} version differs; explicit migration is required.");
                continue;
            }
            await store.Catalog.CreateItemAsync(document, new(partition), cancellationToken: token);
        }
    }

    private static void ValidateKey(string key)
    {
        if (string.IsNullOrEmpty(key) || key.Length is < 8 or > 80
            || key.Any(c => !char.IsAsciiLetterOrDigit(c) && c != '-'))
            throw new DomainException(400, "Idempotency key must contain 8-80 ASCII letters, digits or hyphens.");
    }
}
