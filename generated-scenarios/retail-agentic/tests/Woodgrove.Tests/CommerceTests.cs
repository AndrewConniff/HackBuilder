using System.Text.Json;
using Azure.Data.Tables;
using Woodgrove.Web.Models;
using Woodgrove.Web.Services;

namespace Woodgrove.Tests;

/// <summary>Local policy and real SDK transaction-shape tests; these do not claim Azure or model acceptance.</summary>
public sealed class CommerceTests
{
    private static readonly DateTimeOffset Now = DateTimeOffset.Parse("2026-10-28T01:00:00Z");
    private static Product[] Products =>
    [
        new(1, "Oat beverage, 1 litre", 320, 10, ["oats"]),
        new(2, "Rice beverage, 1 litre", 350, 10, []),
        new(3, "Unknown snack", 250, 10, null),
        new(4, "Dairy beverage", 300, 10, ["milk"])
    ];
    private static GroceryOrder Order => new(
        "aaaaaaaaaaaaaaaaaaaaaaaa", "customer-001", [new(1, 2)], "09:00-11:00", 640, ["milk"],
        "Confirmed", 1, 5, null, [], Now);

    /// <summary>Tests the exact accepted line-count, quantity and cent-total limits.</summary>
    [Fact]
    public void CartLimitsAreExact()
    {
        Assert.Equal(640, CommercePolicy.Price([new(1, 2)], Products));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([], Products));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([new(1, 0)], Products));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([new(1, 11)], Products));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([new(1, 1), new(1, 1)], Products));
        var products = Enumerable.Range(1, 21).Select(x => new Product(x, "Synthetic product", 100, 10, [])).ToArray();
        Assert.Equal(20_000, CommercePolicy.Price(products.Take(20).Select(x => new CartLine(x.Id, 10)).ToArray(), products));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price(products.Select(x => new CartLine(x.Id, 1)).ToArray(), products));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([new(1, 10)], [products[0] with { PriceCents = 2001 }]));
    }

    /// <summary>Rejects missing allergen data, excluded allergens and insufficient stock.</summary>
    [Theory]
    [InlineData(3, 1)]
    [InlineData(4, 1)]
    [InlineData(1, 10)]
    public void UnsafeOrUnavailableSubstitutionIsRejected(int product, int quantity)
    {
        var products = Products.Select(p => p.Id == 1 ? p with { Stock = 1 } : p).ToArray();
        Assert.Throws<PolicyException>(() => CommercePolicy.Propose(Order, [new(product, quantity)], Order.Slot, products, Now));
    }

    /// <summary>Accepts the exact reviewed proposal without silently altering the original commitment first.</summary>
    [Fact]
    public void ExactProposalRequiresActualCustomerDecision()
    {
        var original = Order;
        var proposal = CommercePolicy.Propose(original, [new(2, 2)], original.Slot, Products, Now);
        Assert.Equal(640, original.TotalCents);
        var pending = original with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        var accepted = CommercePolicy.Accept(pending, "customer-001", proposal.Fingerprint, Products, Now.AddMinutes(1));
        Assert.Equal(700, accepted.TotalCents);
        Assert.Equal(2, accepted.Lines.Single().ProductId);
        Assert.Equal("Confirmed", accepted.Status);
        Assert.Null(accepted.Proposal);
    }

    /// <summary>Rejects the wrong owner, stale version, exact expiry and altered fingerprint.</summary>
    [Fact]
    public void StaleExpiredCrossCustomerAndAlteredApprovalsFail()
    {
        var proposal = CommercePolicy.Propose(Order, [new(2, 2)], Order.Slot, Products, Now);
        var pending = Order with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        Assert.Throws<PolicyException>(() => CommercePolicy.Accept(pending, "customer-002", proposal.Fingerprint, Products, Now));
        Assert.Throws<PolicyException>(() => CommercePolicy.Accept(pending, "customer-001", proposal.Fingerprint, Products, proposal.ExpiresAt));
        Assert.Throws<PolicyException>(() => CommercePolicy.Accept(pending with { Version = pending.Version + 1 },
            "customer-001", proposal.Fingerprint, Products, Now));
        Assert.Throws<PolicyException>(() => CommercePolicy.Accept(pending, "customer-001", "altered", Products, Now));
        Assert.Throws<PolicyException>(() => CommercePolicy.Accept(
            pending with { Proposal = proposal with { Slot = "17:00-19:00" } },
            "customer-001", proposal.Fingerprint, Products, Now));
    }

    /// <summary>Rejects changed catalog prices after a proposal was reviewed.</summary>
    [Fact]
    public void IncreasedCatalogChargeNeedsNewApproval()
    {
        var proposal = CommercePolicy.Propose(Order, [new(2, 2)], Order.Slot, Products, Now);
        var pending = Order with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        var changed = Products.Select(x => x.Id == 2 ? x with { PriceCents = 351 } : x).ToArray();
        Assert.Throws<PolicyException>(() => CommercePolicy.Accept(pending, "customer-001", proposal.Fingerprint, changed, Now));
    }

    /// <summary>Delivery changes cannot replace reserved goods or require the same stock to be available twice.</summary>
    [Fact]
    public void DeliveryApprovalPreservesReservedGoods()
    {
        var reserved = Order with { Stage = 2, Status = "ReadyForDispatch" };
        var emptyStock = Products.Select(x => x with { Stock = 0 }).ToArray();
        Assert.Throws<PolicyException>(() => CommercePolicy.Propose(reserved, [new(2, 2)], "12:00-14:00", Products, Now));
        var proposal = CommercePolicy.Propose(reserved, reserved.Lines, "12:00-14:00", emptyStock, Now);
        var pending = reserved with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        Assert.Equal("12:00-14:00", CommercePolicy.Accept(pending, "customer-001", proposal.Fingerprint, emptyStock, Now).Slot);
    }

    /// <summary>A disrupted slot cannot be proposed again, and approval alone clears that synthetic delay.</summary>
    [Fact]
    public void DelayRequiresAnActuallyChangedApprovedWindow()
    {
        var delayed = Order with { Stage = 2, Status = "ReadyForDispatch", Disruption = "delay" };
        Assert.Throws<PolicyException>(() =>
            CommercePolicy.Propose(delayed, delayed.Lines, delayed.Slot, Products, Now));
        var proposal = CommercePolicy.Propose(delayed, delayed.Lines, "17:00-19:00", Products, Now);
        var pending = delayed with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        var accepted = CommercePolicy.Accept(pending, delayed.CustomerId, proposal.Fingerprint, Products, Now);
        Assert.Equal("none", accepted.Disruption);
        Assert.Equal("17:00-19:00", accepted.Slot);
    }

    /// <summary>Rejects free/negative catalog prices and proposals that change no accepted commitment.</summary>
    [Fact]
    public void InvalidPricesAndNoOpProposalsFail()
    {
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([new(1, 1)], [Products[0] with { PriceCents = 0 }]));
        Assert.Throws<PolicyException>(() => CommercePolicy.Price([new(1, 1)], [Products[0] with { PriceCents = -1 }]));
        Assert.Throws<PolicyException>(() => CommercePolicy.Propose(Order, Order.Lines, Order.Slot, Products, Now));
    }

    /// <summary>Tests the exact persisted active-time threshold used for all resumed stage attempts.</summary>
    [Fact]
    public void ActiveTimeBudgetDoesNotReset()
    {
        Assert.Equal(TimeSpan.FromSeconds(60), CommercePolicy.RemainingStageTime(0));
        Assert.Equal(TimeSpan.FromMilliseconds(1), CommercePolicy.RemainingStageTime(59_999));
        Assert.Throws<PolicyException>(() => CommercePolicy.RemainingStageTime(60_000));
        Assert.Throws<PolicyException>(() => CommercePolicy.RemainingStageTime(-1));
    }

    /// <summary>Concurrent new carts cannot exceed the exact 50-order daily limit.</summary>
    [Fact]
    public async Task ConcurrentCreatesRespectDailyThresholdAndPayload()
    {
        var (store, memory) = Fixture(Order);
        var day = "count-" + DateTimeOffset.UtcNow.ToString("yyyyMMdd");
        memory.Put(new TableEntity("store-001", day) { ["Count"] = 49 });
        async Task<bool> Create(string request)
        {
            try
            {
                await store.CreateAsync("customer-001", [new(1, 1)], "09:00-11:00", [], request);
                return true;
            }
            catch (PolicyException) { return false; }
        }
        Assert.Single(await Task.WhenAll(Create("cart-a"), Create("cart-b")), x => x);
        Assert.Equal(50, memory.Rows[day].GetInt32("Count"));
        await Assert.ThrowsAsync<PolicyException>(() =>
            store.CreateAsync("customer-001", [new(1, 1)], "09:00-11:00", [], "cart-c"));
    }

    /// <summary>Stage commits reserve/capture once, and dispatch does not reprice already reserved groceries.</summary>
    [Fact]
    public async Task SyntheticPaymentAndReservationCommitOnce()
    {
        var initial = Order with { Stage = 0, AuthorizedCents = 0, CapturedCents = 0 };
        var (store, memory) = Fixture(initial);
        async Task<GroceryOrder> Complete(int stage) =>
            await store.ChangeAsync(initial.Id, null, $"stage-{stage}-complete", $"stage-{stage}",
                (order, products) => CommercePolicy.CompleteStage(order, products, stage, "test-response", Now));
        var authorized = await Complete(0);
        Assert.Equal(640, authorized.AuthorizedCents);
        Assert.Equal(0, authorized.CapturedCents);
        var reserved = await Complete(1);
        Assert.Equal(640, reserved.CapturedCents);
        Assert.Equal("ReadyForDispatch", reserved.Status);
        await Complete(1);
        Assert.Equal(2, memory.BatchSizes.Count);
        Assert.Equal(8, JsonSerializer.Deserialize<Product>(memory.Rows["product-001"].GetString("Json")!)!.Stock);
        var changed = Products.Select(x => x with { PriceCents = 9999 }).ToArray();
        var delayed = reserved with { Disruption = "delay" };
        var proposal = CommercePolicy.Propose(delayed, delayed.Lines, "17:00-19:00", changed, Now);
        Assert.Equal(640, proposal.TotalCents);
        var pending = delayed with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        var accepted = CommercePolicy.Accept(pending, delayed.CustomerId, proposal.Fingerprint, changed, Now);
        var dispatched = CommercePolicy.CompleteStage(accepted, changed, 2, "test-dispatch", Now).Order;
        Assert.Equal(640, dispatched.CapturedCents);
        Assert.Equal("Dispatched", dispatched.Status);
        var cancelled = await new OrderWorkflow(store).CancelAsync(
            initial.Id, initial.CustomerId, "cancel", CancellationToken.None);
        Assert.Equal(640, cancelled.RefundedCents);
        await new OrderWorkflow(store).CancelAsync(initial.Id, initial.CustomerId, "cancel", CancellationToken.None);
        Assert.Equal(10, JsonSerializer.Deserialize<Product>(memory.Rows["product-001"].GetString("Json")!)!.Stock);
    }

    /// <summary>Even a model-selected completion cannot bypass synthetic tool failure, delay or payment guards.</summary>
    [Fact]
    public void SyntheticExceptionsNeverFabricateCompletion()
    {
        Assert.Throws<PolicyException>(() =>
            CommercePolicy.CompleteStage(Order with { Disruption = "tool-timeout" }, Products, 1, "test", Now));
        Assert.Throws<PolicyException>(() => CommercePolicy.CompleteStage(Order, Products, 1, "test", Now));
        Assert.Throws<PolicyException>(() => CommercePolicy.CompleteStage(
            Order with { Stage = 2, Status = "ReadyForDispatch", Disruption = "delay" }, Products, 2, "test", Now));
    }

    /// <summary>Expiry at the exact boundary holds the order without applying its proposed replacement or charge.</summary>
    [Fact]
    public void ExpiredProposalBecomesAHoldWithoutApproval()
    {
        var proposal = CommercePolicy.Propose(Order, [new(2, 2)], Order.Slot, Products, Now);
        var pending = Order with { Proposal = proposal, Status = "AwaitingCustomer", Version = proposal.OrderVersion };
        Assert.Throws<PolicyException>(() => CommercePolicy.Expire(pending, proposal.Fingerprint, Now));
        var held = CommercePolicy.Expire(pending, proposal.Fingerprint, proposal.ExpiresAt);
        Assert.Equal("Held", held.Status);
        Assert.Equal(640, held.TotalCents);
        Assert.Equal(pending.Lines, held.Lines);
        Assert.Null(held.Proposal);
    }

    /// <summary>Replayed identical actions commit once, while changed payloads cannot reuse the same receipt.</summary>
    [Fact]
    public async Task TransactionReceiptBindsPayloadAndDeduplicates()
    {
        var (store, memory) = Fixture(Order);
        var calls = 0;
        (GroceryOrder, Product[]) Change(GroceryOrder order, Product[] products)
        {
            calls++;
            return (order with { Version = order.Version + 1 }, [products[0] with { Stock = 8 }]);
        }
        await store.ChangeAsync(Order.Id, "customer-001", "reserve", "two-units", Change);
        await store.ChangeAsync(Order.Id, "customer-001", "reserve", "two-units", Change);
        Assert.Equal(1, calls);
        Assert.Equal(3, Assert.Single(memory.BatchSizes));
        await Assert.ThrowsAsync<PolicyException>(() =>
            store.ChangeAsync(Order.Id, "customer-001", "reserve", "three-units", Change));
        await Assert.ThrowsAsync<PolicyException>(() =>
            store.ChangeAsync(Order.Id, "customer-002", "reserve", "two-units", Change));
    }

    /// <summary>An ambiguous committed response is reconciled from its atomic receipt without repeating stock changes.</summary>
    [Fact]
    public async Task AmbiguousWriteReconcilesCommittedReceipt()
    {
        var (store, memory) = Fixture(Order);
        memory.FailAfterCommit = true;
        var result = await store.ChangeAsync(Order.Id, "customer-001", "reserve", "two", (order, products) =>
            (order with { Version = order.Version + 1 }, [products[0] with { Stock = products[0].Stock - 2 }]));
        Assert.Equal(6, result.Version);
        Assert.Single(memory.BatchSizes);
        var stock = JsonSerializer.Deserialize<Product>(memory.Rows["product-001"].GetString("Json")!)!;
        Assert.Equal(8, stock.Stock);
    }

    /// <summary>Concurrent reservations cannot both spend the same stock snapshot.</summary>
    [Fact]
    public async Task ConcurrentStateUsesExactETags()
    {
        var (store, memory) = Fixture(Order);
        async Task<bool> Reserve(string key)
        {
            try
            {
                await store.ChangeAsync(Order.Id, "customer-001", key, key, (order, products) =>
                {
                    if (order.Status != "Confirmed") throw new PolicyException("Already reserved.");
                    return (order with { Status = "ReadyForDispatch", Version = order.Version + 1 },
                        [products[0] with { Stock = products[0].Stock - 2 }]);
                });
                return true;
            }
            catch (PolicyException) { return false; }
        }
        var results = await Task.WhenAll(Reserve("a"), Reserve("b"));
        Assert.Single(results, x => x);
        Assert.Single(memory.BatchSizes);
    }

    /// <summary>Customer cancellation returns reserved stock once and cannot cancel a dispatched order.</summary>
    [Fact]
    public async Task CancellationIsAtomicAndDispatchIsFinal()
    {
        var reserved = Order with { Stage = 2, Status = "ReadyForDispatch" };
        var (store, memory) = Fixture(reserved);
        var workflow = new OrderWorkflow(store);
        await workflow.CancelAsync(Order.Id, "customer-001", "cancel", CancellationToken.None);
        await workflow.CancelAsync(Order.Id, "customer-001", "cancel", CancellationToken.None);
        Assert.Equal(12, JsonSerializer.Deserialize<Product>(memory.Rows["product-001"].GetString("Json")!)!.Stock);
        var (dispatchedStore, _) = Fixture(reserved with { Stage = 3, Status = "Dispatched" });
        await Assert.ThrowsAsync<PolicyException>(() =>
            new OrderWorkflow(dispatchedStore).CancelAsync(Order.Id, "customer-001", "cancel", CancellationToken.None));
    }

    /// <summary>A failed-stage retry retains the durable request budget and stage checkpoint.</summary>
    [Fact]
    public async Task RetryDoesNotResetBudgets()
    {
        var failed = Order with { Status = "Failed", Requests = 17, Tools = 23, StageRequests = [0, 5, 0] };
        var (store, _) = Fixture(failed);
        var result = await new OrderWorkflow(store).RetryAsync(
            failed.Id, failed.CustomerId, "retry", CancellationToken.None);
        Assert.Equal(17, result.Requests);
        Assert.Equal(23, result.Tools);
        Assert.Equal(5, result.StageRequests![1]);
        Assert.Equal(1, result.Stage);
    }

    private static (TableStorageDataService, MemoryTable) Fixture(GroceryOrder order)
    {
        var memory = new MemoryTable();
        memory.Put(new TableEntity("store-001", "order-" + order.Id)
        { ["Json"] = JsonSerializer.Serialize(order), ["CustomerId"] = order.CustomerId });
        foreach (var product in Products)
            memory.Put(new TableEntity("store-001", "product-" + product.Id.ToString("D3"))
            { ["Json"] = JsonSerializer.Serialize(product) });
        return (new(new MemoryTableService(memory)), memory);
    }
}
