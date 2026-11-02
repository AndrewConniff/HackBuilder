using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Woodgrove.Web.Models;

/// <summary>A catalog product with integer-cent pricing and explicit safety metadata.</summary>
public sealed record Product(int Id, string Name, int PriceCents, int Stock, string[]? Allergens);

/// <summary>A bounded cart line referencing one catalog product.</summary>
public sealed record CartLine(int ProductId, int Quantity);

/// <summary>A customer-bound, expiring proposal for an exact new order commitment.</summary>
public sealed record Proposal(
    string Fingerprint, int OrderVersion, DateTimeOffset ExpiresAt, CartLine[] Lines, string Slot, int TotalCents);

/// <summary>An inspectable event, never hidden model reasoning.</summary>
public sealed record TimelineEvent(DateTimeOffset At, string Kind, string Message, string? ResponseId = null);

/// <summary>The durable business order and bounded workflow checkpoint.</summary>
public sealed record GroceryOrder(
    string Id, string CustomerId, CartLine[] Lines, string Slot, int TotalCents, string[] ExcludedAllergens,
    string Status, int Stage, int Version, Proposal? Proposal, TimelineEvent[] Timeline,
    DateTimeOffset CreatedAt, DateTimeOffset? DeliveryDueAt = null, int Requests = 0, int Tools = 0,
    int[]? StageRequests = null, int[]? StageTools = null, int[]? InputTokens = null, int[]? OutputTokens = null,
    string Disruption = "none", int AuthorizedCents = 0, int CapturedCents = 0, int RefundedCents = 0);

/// <summary>A non-success business outcome that can be shown safely to the customer.</summary>
public sealed class PolicyException(string message) : Exception(message);

/// <summary>Server-owned validation and approval rules shared by UI, agents and tests.</summary>
public static class CommercePolicy
{
    /// <summary>Checks and prices the complete cart without trusting model-provided prices.</summary>
    public static int Price(CartLine[] lines, IReadOnlyList<Product> products)
    {
        if (lines.Length is < 1 or > 20 || lines.Select(x => x.ProductId).Distinct().Count() != lines.Length)
            throw new PolicyException("Use 1-20 distinct catalog products.");
        var total = 0;
        foreach (var line in lines)
        {
            if (line.Quantity is < 1 or > 10)
                throw new PolicyException("Each product quantity must be between 1 and 10.");
            var product = products.SingleOrDefault(x => x.Id == line.ProductId)
                ?? throw new PolicyException("Unknown catalog product.");
            if (product.PriceCents <= 0)
                throw new PolicyException("Catalog prices must be positive integer cents.");
            total = checked(total + product.PriceCents * line.Quantity);
        }
        if (total > 20_000)
            throw new PolicyException("The synthetic order limit is USD 200.");
        return total;
    }

    /// <summary>Requires server-derived customer ownership, including before receipt reads.</summary>
    public static void Owns(GroceryOrder order, string customerId)
    {
        if (!string.Equals(order.CustomerId, customerId, StringComparison.Ordinal))
            throw new PolicyException("This order is not available to the signed-in customer.");
    }

    /// <summary>Rejects missing, conflicting or disallowed safety metadata and insufficient inventory.</summary>
    public static void Available(
        CartLine[] lines, IReadOnlyList<Product> products, string[] excludedAllergens, bool requireStock = true)
    {
        Price(lines, products);
        foreach (var line in lines)
        {
            var product = products.Single(x => x.Id == line.ProductId);
            if (product.Allergens is null ||
                product.Allergens.Any(x => excludedAllergens.Contains(x, StringComparer.OrdinalIgnoreCase)))
                throw new PolicyException("Safety metadata is missing or conflicts with the customer's exclusions.");
            if (requireStock && product.Stock < line.Quantity)
                throw new PolicyException($"Insufficient synthetic stock for {product.Name}.");
        }
    }

    /// <summary>Creates a canonical proposal bound to customer, order, version, lines, price, slot and expiry.</summary>
    public static Proposal Propose(
        GroceryOrder order, CartLine[] lines, string slot, IReadOnlyList<Product> products, DateTimeOffset now)
    {
        if (order.Stage is not (1 or 2) ||
            order.Status != (order.Stage == 2 ? "ReadyForDispatch" : "Confirmed"))
            throw new PolicyException("This stage cannot change the customer commitment.");
        ValidSlot(slot);
        Available(lines, products, order.ExcludedAllergens, order.Stage == 1);
        if (order.Stage == 2 && !lines.OrderBy(x => x.ProductId).SequenceEqual(order.Lines.OrderBy(x => x.ProductId)))
            throw new PolicyException("The delivery stage cannot replace reserved products.");
        if (order.Stage == 2 && order.Disruption == "delay" && slot == order.Slot)
            throw new PolicyException("The disrupted delivery window is unavailable; propose another offered window.");
        if (order.Stage == 1 && slot != order.Slot)
            throw new PolicyException("Only delivery coordination can propose a changed slot.");
        var price = order.Stage == 2 ? order.TotalCents : Price(lines, products);
        if (lines.OrderBy(x => x.ProductId).SequenceEqual(order.Lines.OrderBy(x => x.ProductId)) &&
            slot == order.Slot && price == order.TotalCents)
            throw new PolicyException("There is no changed commitment to propose.");
        var canonicalLines = lines.OrderBy(x => x.ProductId).ToArray();
        var expiry = now.AddMinutes(10);
        var version = order.Version + 1;
        var fingerprint = Fingerprint(order, version, canonicalLines, slot, price, expiry);
        return new(fingerprint, version, expiry, canonicalLines, slot, price);
    }

    /// <summary>Applies only an unexpired, unaltered proposal presented to the owning customer.</summary>
    public static GroceryOrder Accept(
        GroceryOrder order, string customerId, string fingerprint, IReadOnlyList<Product> products,
        DateTimeOffset now)
    {
        Owns(order, customerId);
        var proposal = order.Proposal ?? throw new PolicyException("There is no pending proposal.");
        if (order.Status != "AwaitingCustomer" || proposal.OrderVersion != order.Version ||
            proposal.ExpiresAt <= now || !string.Equals(proposal.Fingerprint, fingerprint, StringComparison.Ordinal) ||
            Fingerprint(order, proposal.OrderVersion, proposal.Lines, proposal.Slot,
                proposal.TotalCents, proposal.ExpiresAt) != proposal.Fingerprint)
            throw new PolicyException("This proposal is expired, stale or not the exact proposal you reviewed.");
        if ((order.Stage == 2 ? order.TotalCents : Price(proposal.Lines, products)) != proposal.TotalCents)
            throw new PolicyException("Catalog prices changed. Review a new proposal.");
        Available(proposal.Lines, products, order.ExcludedAllergens, order.Stage == 1);
        return order with
        {
            Lines = proposal.Lines, Slot = proposal.Slot, TotalCents = proposal.TotalCents,
            Status = order.Stage == 2 ? "ReadyForDispatch" : "Confirmed",
            Disruption = order.Stage == 2 ? "none" : order.Disruption,
            AuthorizedCents = order.Stage == 1 ? proposal.TotalCents : order.AuthorizedCents,
            Proposal = null, Version = order.Version + 1,
            Timeline = [.. order.Timeline, new(now, "CustomerDecision", "Exact proposal accepted.")]
        };
    }

    /// <summary>Validates supported synthetic delivery windows.</summary>
    public static void ValidSlot(string slot)
    {
        if (slot is not ("09:00-11:00" or "12:00-14:00" or "17:00-19:00"))
            throw new PolicyException("Select an offered synthetic delivery window.");
    }

    /// <summary>Enforces a persisted 60-second stage total, including previous failed or resumed attempts.</summary>
    public static TimeSpan RemainingStageTime(int spentMilliseconds)
    {
        if (spentMilliseconds is < 0 or >= 60_000)
            throw new PolicyException("The durable stage active-time budget is exhausted or invalid.");
        return TimeSpan.FromMilliseconds(60_000 - spentMilliseconds);
    }

    /// <summary>Moves an actually expired exact proposal to a recoverable hold without changing its commitment.</summary>
    public static GroceryOrder Expire(GroceryOrder order, string fingerprint, DateTimeOffset now)
    {
        if (order.Status != "AwaitingCustomer" || order.Proposal is not { } proposal ||
            proposal.Fingerprint != fingerprint || proposal.ExpiresAt > now)
            throw new PolicyException("There is no matching expired proposal.");
        return order with
        {
            Status = "Held", Proposal = null, Version = order.Version + 1,
            Timeline = [.. order.Timeline, new(now, "ProposalExpired",
                "The exact proposal expired; no changed items, charge or window were executed. Cancel to recover.")]
        };
    }

    /// <summary>Commits only the accepted synthetic payment, reservation or dispatch for the current agent stage.</summary>
    public static (GroceryOrder Order, Product[] Stock) CompleteStage(
        GroceryOrder order, Product[] products, int stage, string responseId, DateTimeOffset now)
    {
        if (stage is < 0 or > 2 || order.Stage != stage ||
            order.Status != (stage == 2 ? "ReadyForDispatch" : "Confirmed"))
            throw new PolicyException("The stage is stale, paused or not authorized to run.");
        if (stage < 2 && Price(order.Lines, products) != order.TotalCents)
            throw new PolicyException("Catalog prices changed; an exact new customer proposal is required.");
        if (order.Disruption == "tool-timeout")
            throw new PolicyException("The injected synthetic adapter failure must be cleared before completion.");
        if (stage == 2 && order.Disruption == "delay")
            throw new PolicyException("The accepted window is disrupted; approval of a new window is required.");
        if (stage >= 1)
            Available(order.Lines, products, order.ExcludedAllergens, requireStock: stage == 1);
        if (stage == 1 && (order.AuthorizedCents != order.TotalCents || order.CapturedCents != 0))
            throw new PolicyException("An exact authorization and an uncaptured synthetic payment are required.");
        if (stage == 2 && (order.CapturedCents != order.TotalCents || order.RefundedCents != 0))
            throw new PolicyException("Dispatch requires the accepted, unrefunded synthetic payment.");
        var stock = stage == 1 ? order.Lines.Select(line =>
        {
            var product = products.Single(x => x.Id == line.ProductId);
            return product with { Stock = product.Stock - line.Quantity };
        }).ToArray() : [];
        var status = stage == 1 ? "ReadyForDispatch" : stage == 2 ? "Dispatched" : "Confirmed";
        string[] events = stage switch
        {
            0 => ["SyntheticPaymentAuthorized"],
            1 => ["Reserved", "SyntheticPaymentCaptured", "Picking", "ReadyForDispatch"],
            _ => ["Dispatched"]
        };
        return (order with
        {
            Stage = stage + 1, Status = status, Version = order.Version + 1,
            AuthorizedCents = stage == 0 ? order.TotalCents : order.AuthorizedCents,
            CapturedCents = stage == 1 ? order.TotalCents : order.CapturedCents,
            DeliveryDueAt = stage == 2 ? now.AddSeconds(45) : null,
            Timeline = [.. order.Timeline, .. events.Select(e => new TimelineEvent(
                now, e, $"Verified stage action: {e}; commerce, charges and delivery are synthetic.", responseId))]
        }, stock);
    }

    /// <summary>Computes a stable action/proposal digest without exposing the original content.</summary>
    public static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static string Fingerprint(
        GroceryOrder order, int version, CartLine[] lines, string slot, int price, DateTimeOffset expires) =>
        Hash(JsonSerializer.Serialize(new
        {
            order.Id, order.CustomerId, Version = version, Lines = lines.OrderBy(x => x.ProductId).ToArray(),
            Slot = slot, TotalCents = price, ExpiresAt = expires
        }));
}
