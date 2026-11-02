namespace CoffeeShop.Web.Models;

/// <summary>A synthetic store with a stable operations owner and area.</summary>
public sealed record Store(int Id, string StoreId, string Name, string Area, string Manager);
/// <summary>Closing stock in the authoritative base unit.</summary>
public sealed record Stock(int Id, string Sku, string Unit, decimal OnHand, decimal Target, decimal UnitCost);
/// <summary>Deterministic managerial figures; waste is excluded from sold-product COGS.</summary>
public sealed record DailyLedger(int Id, DateOnly Date, decimal NetSales, decimal Cogs,
    decimal Labor, decimal Occupancy, decimal Waste, bool Complete, decimal PlannedSales = 0)
{
    /// <summary>Operating profit, not statutory or tax accounting.</summary>
    public decimal Profit => NetSales - Cogs - Labor - Occupancy - Waste;
    /// <summary>Sales variance versus the imported plan.</summary>
    public decimal SalesVariance => NetSales - PlannedSales;
}
/// <summary>A versioned business-day snapshot and its raw recipe evidence.</summary>
public sealed record StoreSnapshot(Store Store, string Version, Stock[] Stock, DailyLedger Ledger,
    DayInput? Input = null);
/// <summary>Component usage per sold product in the component's base unit.</summary>
public sealed record Recipe(string Product, string Sku, string Unit, decimal Quantity);
/// <summary>A sold product quantity and net selling price.</summary>
public sealed record Sale(string Product, decimal Quantity, decimal UnitPrice);
/// <summary>Explicit spoilage, separate from normal sold-product consumption.</summary>
public sealed record Spoilage(string Sku, string Unit, decimal Quantity);
/// <summary>One complete daily import packet; quantities and prices use decimal arithmetic.</summary>
public sealed record DayInput(DateOnly Date, Stock[] Opening, Recipe[] Recipes, Sale[] Sales,
    Spoilage[] Spoilage, decimal Labor, decimal Occupancy, decimal PlannedSales);
/// <summary>A bounded CSV payload with optimistic concurrency.</summary>
public sealed record ImportRequest(string ExpectedVersion, string Csv);
/// <summary>A replenishment item in a deterministic internal order.</summary>
public sealed record OrderLine(string Sku, string Unit, decimal Quantity, decimal UnitCost)
{
    /// <summary>Authoritative line amount.</summary>
    public decimal Total => Quantity * UnitCost;
}
/// <summary>A human-reviewed internal order with no supplier side effect.</summary>
public sealed record Order(int Id, string DraftId, string StoreId, string SnapshotVersion, string CreatedBy,
    DateTimeOffset ExpiresAt, OrderLine[] Lines, string Status, string? ApprovedBy = null,
    DateTimeOffset? ApprovedAt = null)
{
    /// <summary>Authoritative order amount.</summary>
    public decimal Total => Lines.Sum(line => line.Total);
}
/// <summary>An internal order and its persistence concurrency token.</summary>
public sealed record StoredOrder(Order Value, string ETag);
/// <summary>Requests a draft for one authorized store.</summary>
public sealed record DraftRequest(string StoreId);
/// <summary>Explicit human confirmation, never supplied by an agent.</summary>
public sealed record ApprovalRequest(bool Confirm);
/// <summary>A bounded selection of stores and an advisory question.</summary>
public sealed record CloseRequest(string[] StoreIds, string Question);
/// <summary>Real Foundry invocation metadata and advisory output.</summary>
public sealed record AgentReceipt(string Agent, string Version, string ResponseId, string Text);
/// <summary>One uniquely owned store/domain assignment and its real invocation receipt.</summary>
public sealed record WorkReceipt(string AssignmentId, string StoreId, string Domain, string SnapshotVersion,
    AgentReceipt Agent);
/// <summary>A generated daily report that must be explicitly reviewed before finalization.</summary>
public sealed record CloseResult(string CorrelationId, string Status, StoreSnapshot[] Evidence,
    decimal NetSales, decimal Profit, AgentReceipt[] Agents, WorkReceipt[] Assignments,
    DateTimeOffset CreatedAt, string? ReviewedBy = null, DateTimeOffset? ReviewedAt = null);
/// <summary>A daily report and its concurrency token.</summary>
public sealed record StoredClose(CloseResult Value, string ETag);
