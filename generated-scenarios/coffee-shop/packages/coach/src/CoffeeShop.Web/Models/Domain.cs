namespace CoffeeShop.Web.Models;

public sealed record Store(int Id, string StoreId, string Name, string Area, string Manager);
public sealed record Stock(int Id, string Sku, string Unit, decimal OnHand, decimal Target, decimal UnitCost);
public sealed record DailyLedger(int Id, DateOnly Date, decimal NetSales, decimal Cogs,
    decimal Labor, decimal Occupancy, decimal Waste, bool Complete)
{
    public decimal Profit => NetSales - Cogs - Labor - Occupancy - Waste;
}
public sealed record StoreSnapshot(Store Store, string Version, Stock[] Stock, DailyLedger Ledger);
public sealed record OrderLine(string Sku, string Unit, decimal Quantity, decimal UnitCost)
{
    public decimal Total => Quantity * UnitCost;
}
public sealed record Order(int Id, string DraftId, string StoreId, string SnapshotVersion, string CreatedBy,
    DateTimeOffset ExpiresAt, OrderLine[] Lines, string Status, string? ApprovedBy = null,
    DateTimeOffset? ApprovedAt = null)
{
    public decimal Total => Lines.Sum(line => line.Total);
}
public sealed record StoredOrder(Order Value, string ETag);
public sealed record DraftRequest(string StoreId);
public sealed record ApprovalRequest(bool Confirm);
public sealed record CloseRequest(string[] StoreIds, string Question);
public sealed record AgentReceipt(string Agent, string Version, string ResponseId, string Text);
public sealed record CloseResult(string CorrelationId, string Status, StoreSnapshot[] Evidence,
    decimal NetSales, decimal Profit, AgentReceipt[] Agents);
