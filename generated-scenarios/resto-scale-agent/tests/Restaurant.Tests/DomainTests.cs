using Restaurant.Web.Models;
using Restaurant.Web.Services;
using Azure.Core;
using Microsoft.Extensions.Configuration;
using System.Security.Claims;
using Xunit;

namespace Restaurant.Tests;

/// <summary>Local deterministic correctness evidence, not live database concurrency or agent acceptance.</summary>
public sealed class DomainTests
{
    /// <summary>Verifies installer-produced signed floor roles preserve the existing floor boundary.</summary>
    [Fact]
    public void InstalledStaffRolesRequireBothBusinessRoleAndFloorAssignment()
    {
        var principal = new ClaimsPrincipal(new ClaimsIdentity([
            new Claim("sub", "synthetic-staff"),
            new Claim("roles", "Server"),
            new Claim("roles", "Floor.3"),
            new Claim("roles", "Floor.6")
        ], "staff"));
        var caller = Caller.From(principal);
        Assert.Equal("Server", caller.Role);
        Assert.Equal([3], caller.Floors);
        caller.Demand(Reserved());
        Assert.Throws<DomainException>(() => caller.Demand(Reserved() with { Floor = 2 }));
        principal = new(new ClaimsIdentity([
            new Claim("sub", "synthetic-staff"), new Claim("roles", "Floor.3")
        ], "staff"));
        Assert.Throws<DomainException>(() => Caller.From(principal));
        principal = new(new ClaimsIdentity([
            new Claim("sub", "synthetic-staff"), new Claim("roles", "Server")
        ], "staff"));
        Assert.Throws<DomainException>(() => Caller.From(principal));
    }

    private static readonly DateTimeOffset Now = DateTimeOffset.Parse("2026-10-23T07:00:00Z");
    private static readonly MenuItem[] Menu = [new(1, "Roasted vegetable bowl", 1600, true, true, 1)];
    private static Visit Reserved() => new("visit1", "visit:visit1", "visit", 1, "reservation1",
        "2026-10-23:1", 3, 2, "Airi Ilves", Rules.HashCode("synthetic-code"),
        "Reserved", [], false, null, "legacy-001");
    private static readonly Caller Guest = new("guest:visit1", "Guest", "visit1", []);
    private static readonly Caller Kitchen = new("kitchen-001", "Kitchen", null, [3]);
    private static readonly Caller Server = new("host-001", "Server", null, [3]);

    /// <summary>Validates all five turns without confusing daily covers with concurrent seating.</summary>
    [Fact]
    public void FiveTurnsProvide1250CoversWithoutExceedingCapacity()
    {
        var covers = 0;
        for (var turn = 1; turn <= 5; turn++)
        {
            var slot = new Slot("slot", $"slot:2026-10-23:{turn}", "slot", 0, []);
            for (var floor = 1; floor <= 5; floor++)
            {
                for (var seat = 0; seat < 50; seat++)
                {
                    slot = Rules.Reserve(slot, new($"{turn}-{floor}-{seat}", floor, 1, "Airi Ilves", "hash"));
                    covers++;
                }
                Assert.Throws<DomainException>(() => Rules.Reserve(slot, new("overflow", floor, 1, "Airi Ilves", "hash")));
            }
            Assert.Equal(250, slot.Allocations.Sum(item => item.Seats));
        }
        Assert.Equal(1250, covers);
    }

    /// <summary>Exercises the guest-to-kitchen-to-settlement-to-survey state machine and captured prices.</summary>
    [Fact]
    public void CompleteGuestJourneyRequiresDispatchAndHumanTransitions()
    {
        var visit = Reserved();
        visit = Rules.Apply(visit, new("checkin", visit.id, visit.Version), Guest, Menu, Now);
        visit = Rules.Apply(visit, new("order", visit.id, visit.Version, new() { [1] = 2 }), Guest, Menu, Now);
        Assert.Equal(3200, visit.TotalMinor);
        var ticket = Assert.Single(visit.Tickets);
        Assert.Equal(1, ticket.Sequence);
        Assert.False(ticket.Dispatched);
        Assert.Throws<DomainException>(() => Rules.Apply(visit,
            new("transition", visit.id, visit.Version, TicketId: ticket.Id, TargetStatus: "accepted"), Kitchen, Menu, Now));
        Assert.Throws<DomainException>(() => Rules.Apply(visit, new("settle", visit.id, visit.Version), Guest, Menu, Now));
        visit = visit with { Tickets = [ticket with { Dispatched = true }] };
        foreach (var status in new[] { "accepted", "preparing", "ready", "served" })
            visit = Rules.Apply(visit, new("transition", visit.id, visit.Version,
                TicketId: ticket.Id, TargetStatus: status), status == "served" ? Server : Kitchen, Menu, Now);
        Assert.Equal(5, visit.Tickets.Single().Sequence);
        visit = Rules.Apply(visit, new("settle", visit.id, visit.Version), Guest, Menu, Now);
        Assert.True(visit.Settled);
        Assert.Throws<DomainException>(() => Rules.Apply(visit, new("settle", visit.id, visit.Version), Guest, Menu, Now));
        visit = Rules.Apply(visit, new("survey", visit.id, visit.Version, Rating: 5), Guest, Menu, Now);
        Assert.Equal(5, visit.Survey);
        Assert.Throws<DomainException>(() => Rules.Apply(visit, new("survey", visit.id, visit.Version, Rating: 4), Guest, Menu, Now));
    }

    /// <summary>Proves callers cannot choose another visit, floor or kitchen financial authority.</summary>
    [Fact]
    public void ScopeVersionAndFinancialBoundariesRejectInvalidRequests()
    {
        var visit = Reserved();
        Assert.Throws<DomainException>(() => (Guest with { VisitId = "other" }).Demand(visit));
        Assert.Throws<DomainException>(() => (Server with { Floors = [2] }).Demand(visit));
        Assert.Throws<DomainException>(() => Kitchen.Demand(visit, financial: true));
        Assert.Throws<DomainException>(() => Rules.Apply(visit, new("checkin", visit.id, 0), Guest, Menu, Now));
        Assert.Throws<DomainException>(() => Rules.Apply(visit, new("order", visit.id, 1, new() { [1] = 1 }), Guest, Menu, Now));
    }

    /// <summary>Checks unavailable menu items, quantity limits and server-owned pricing.</summary>
    [Theory]
    [InlineData(1, 0)]
    [InlineData(1, 13)]
    [InlineData(99, 1)]
    public void InvalidOrdersAreExplicitlyRejected(int item, int quantity)
    {
        var visit = Reserved() with { Status = "Active" };
        Assert.Throws<DomainException>(() => Rules.Apply(visit,
            new("order", visit.id, visit.Version, new() { [item] = quantity }), Guest, Menu, Now));
    }

    /// <summary>Checks high-entropy access-code hashing and digest sensitivity.</summary>
    [Fact]
    public void HashesDoNotAcceptAnotherCodeOrChangedRequest()
    {
        Assert.True(Rules.VerifyCode("correct", Rules.HashCode("correct")));
        Assert.False(Rules.VerifyCode("incorrect", Rules.HashCode("correct")));
        Assert.NotEqual(Rules.Digest(new { Seats = 2 }), Rules.Digest(new { Seats = 3 }));
    }

    /// <summary>Rejects unknown venue slot shapes.</summary>
    [Theory]
    [InlineData("today:1")]
    [InlineData("2026-10-23:0")]
    [InlineData("2026-10-23:6")]
    public void InvalidServiceSlotsAreRejected(string slot) =>
        Assert.Throws<DomainException>(() => Rules.ValidateSlot(slot));

    /// <summary>Cancellation stops further actions while durable compensation releases the separate slot partition.</summary>
    [Fact]
    public void CancelledReservationCannotCheckInOrderOrCancelTwice()
    {
        var visit = Reserved();
        visit = Rules.Apply(visit, new("cancel", visit.id, visit.Version), Guest, Menu, Now);
        Assert.Equal("Cancelled", visit.Status);
        Assert.False(visit.AllocationReleased);
        foreach (var kind in new[] { "checkin", "order", "cancel" })
            Assert.Throws<DomainException>(() => Rules.Apply(visit,
                new(kind, visit.id, visit.Version, new() { [1] = 1 }), Guest, Menu, Now));
    }

    /// <summary>Only pre-service reservations may release capacity through cancellation.</summary>
    [Fact]
    public void ActiveVisitAndKitchenRoleCannotCancelReservation()
    {
        var reserved = Reserved();
        Assert.Throws<DomainException>(() => Rules.Apply(reserved,
            new("cancel", reserved.id, reserved.Version), Kitchen, Menu, Now));
        var active = Rules.Apply(reserved, new("checkin", reserved.id, reserved.Version), Guest, Menu, Now);
        Assert.Throws<DomainException>(() => Rules.Apply(active,
            new("cancel", active.id, active.Version), Guest, Menu, Now));
    }

    /// <summary>Versioned imports reject malformed identities and scope before any database writes.</summary>
    [Fact]
    public void LegacyImportRequiresVersionedSyntheticCatalogBackedRecords()
    {
        var record = new LegacyReservation("legacy-001", "2026-10-23:1", 3, 2, "guest-001");
        var document = new LegacyDocument(1, true, "synthetic-legacy", [record]);
        LegacyImport.Validate(document);
        foreach (var invalid in new[]
        {
            document with { Synthetic = false }, document with { SchemaVersion = 2 },
            document with { Records = [record, record] },
            document with { Records = [record with { GuestId = "unknown" }] },
            document with { Records = [record with { Floor = 6 }] },
            document with { Records = [record with { Slot = "invalid" }] }
        })
            Assert.Throws<DomainException>(() => LegacyImport.Validate(invalid));
    }

    /// <summary>Public shells may construct the credential, but absent identity cannot fall back to developer login.</summary>
    [Fact]
    public void MissingRuntimeIdentityIsRejectedAtTheFirstTokenRequest()
    {
        var credential = new RuntimeIdentityCredential(new ConfigurationBuilder().Build());
        var failure = Assert.Throws<InvalidOperationException>(() =>
            credential.GetToken(new TokenRequestContext(["https://management.azure.com/.default"]), CancellationToken.None));
        Assert.Contains("AZURE_CLIENT_ID", failure.Message);
    }
}
