using System.Globalization;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using CoffeeShop.Web.Models;
using Microsoft.VisualBasic.FileIO;

namespace CoffeeShop.Web.Services;

/// <summary>Converts a complete validated CSV day packet into recipe-based stock and managerial P&amp;L.</summary>
public sealed class DailyOperations(StoreAccess access, IRepository repository)
{
    /// <summary>Imports one store atomically; an import hash can be committed only once.</summary>
    public async Task<StoreSnapshot> ImportAsync(ClaimsPrincipal user, string storeId, ImportRequest request,
        CancellationToken ct)
    {
        access.Demand(user, storeId);
        if (string.IsNullOrWhiteSpace(request.ExpectedVersion))
            throw new ArgumentException("Expected version is required.");
        var current = await repository.ReadAsync(storeId, ct);
        var input = Parse(storeId, request.Csv);
        if (input.Date < current.Ledger.Date) throw new InvalidOperationException("Cannot replace a newer business day.");
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(request.Csv))).ToLowerInvariant();
        var snapshot = Calculate(current.Store, hash, input);
        return await repository.ImportAsync(snapshot, request.ExpectedVersion, hash, ct);
    }

    /// <summary>Validates strict bounded rows; quantities use L or unit, dates use ISO and amounts use invariant decimals.</summary>
    public static DayInput Parse(string storeId, string csv)
    {
        if (string.IsNullOrWhiteSpace(csv) || csv.Length > 24000)
            throw new ArgumentException("CSV must contain 1-24000 characters.");
        using var parser = new TextFieldParser(new StringReader(csv));
        parser.SetDelimiters(",");
        parser.HasFieldsEnclosedInQuotes = true;
        string[]? header;
        try { header = parser.ReadFields(); }
        catch (MalformedLineException error) { throw new ArgumentException("Malformed CSV header.", error); }
        string[] columns = ["StoreId", "Date", "Kind", "Item", "Component", "Unit", "Quantity", "UnitCost", "Target"];
        if (header is null || !header.SequenceEqual(columns)) throw new ArgumentException("CSV header does not match.");
        List<Stock> opening = [];
        List<Recipe> recipes = [];
        List<Sale> sales = [];
        List<Spoilage> waste = [];
        Dictionary<string, decimal> costs = [];
        HashSet<string> rows = [];
        DateOnly? date = null;
        var count = 0;
        try
        {
            while (!parser.EndOfData)
            {
                var row = parser.ReadFields() ?? throw new ArgumentException("Empty CSV row.");
                if (++count > 100 || row.Length != columns.Length || row.Any(value => value.Length > 80)
                    || row[0] != storeId
                    || !DateOnly.TryParseExact(row[1], "yyyy-MM-dd", CultureInfo.InvariantCulture,
                        DateTimeStyles.None, out var day))
                    throw new ArgumentException("Invalid row, store, date or row budget.");
                if (date is not null && date != day) throw new ArgumentException("Mixed business dates.");
                date = day;
                var kind = row[2];
                var item = row[3];
                if (string.IsNullOrWhiteSpace(item) || !rows.Add($"{kind}|{item}|{row[4]}"))
                    throw new ArgumentException("Empty item or duplicate row.");
                var quantity = Number(row[6]);
                var price = Number(row[7]);
                var target = Number(row[8]);
                if (kind == "stock" && row[4] == "" && row[5] is "L" or "unit")
                    opening.Add(new(opening.Count + 1, item, row[5], quantity, target, price));
                else if (kind == "recipe" && row[5] is "L" or "unit" && price == 0 && target == 0)
                    recipes.Add(new(item, row[4], row[5], quantity));
                else if (kind == "sale" && row[4] == "" && row[5] == "unit" && target == 0)
                    sales.Add(new(item, quantity, price));
                else if (kind == "spoilage" && row[4] == "" && row[5] is "L" or "unit" && price == 0 && target == 0)
                    waste.Add(new(item, row[5], quantity));
                else if (kind == "cost" && item is "labor" or "occupancy" or "planned-sales"
                    && row[4] == "" && row[5] == "USD" && quantity == 1 && target == 0)
                    costs.Add(item, price);
                else throw new ArgumentException("Unsupported row kind, units or nonzero unused fields.");
            }
        }
        catch (MalformedLineException error) { throw new ArgumentException("Malformed CSV quoting.", error); }
        if (date is null || costs.Count != 3 || opening.Count == 0 || recipes.Count == 0 || sales.Count == 0)
            throw new ArgumentException("Incomplete day packet; stock, recipes, sales and three cost rows required.");
        return new(date.Value, [.. opening], [.. recipes], [.. sales], [.. waste],
            costs["labor"], costs["occupancy"], costs["planned-sales"]);
    }

    /// <summary>Computes closing units and money without model arithmetic or double-counting spoilage.</summary>
    public static StoreSnapshot Calculate(Store store, string version, DayInput input)
    {
        if (input.Opening.Length is < 1 or > 20 || input.Recipes.Length is < 1 or > 40
            || input.Sales.Length is < 1 or > 20 || input.Spoilage.Length > 20
            || input.Opening.Select(row => row.Sku).Distinct().Count() != input.Opening.Length
            || input.Sales.Select(row => row.Product).Distinct().Count() != input.Sales.Length
            || input.Spoilage.Select(row => row.Sku).Distinct().Count() != input.Spoilage.Length
            || input.Recipes.Select(row => (row.Product, row.Sku)).Distinct().Count() != input.Recipes.Length)
            throw new ArgumentException("Invalid or duplicate stock, recipe, sale or spoilage records.");
        foreach (var value in new[] { input.Labor, input.Occupancy, input.PlannedSales })
            DemandNumber(value);
        var stock = input.Opening.ToDictionary(row => row.Sku, StringComparer.Ordinal);
        var consumed = stock.Keys.ToDictionary(key => key, _ => 0m);
        var spoiled = stock.Keys.ToDictionary(key => key, _ => 0m);
        foreach (var row in input.Opening)
        {
            if (string.IsNullOrWhiteSpace(row.Sku) || row.Unit is not ("L" or "unit"))
                throw new ArgumentException("Invalid stock identity or base unit.");
            DemandNumber(row.OnHand); DemandNumber(row.Target); DemandNumber(row.UnitCost);
        }
        foreach (var recipe in input.Recipes)
        {
            if (!stock.TryGetValue(recipe.Sku, out var component) || recipe.Unit != component.Unit
                || string.IsNullOrWhiteSpace(recipe.Product) || recipe.Quantity <= 0)
                throw new ArgumentException("Invalid recipe component or unit.");
            DemandNumber(recipe.Quantity);
        }
        decimal netSales = 0;
        foreach (var sale in input.Sales)
        {
            DemandNumber(sale.Quantity); DemandNumber(sale.UnitPrice);
            var recipe = input.Recipes.Where(row => row.Product == sale.Product).ToArray();
            if (recipe.Length == 0) throw new ArgumentException("Sale has no recipe.");
            netSales += sale.Quantity * sale.UnitPrice;
            foreach (var row in recipe) consumed[row.Sku] += sale.Quantity * row.Quantity;
        }
        foreach (var waste in input.Spoilage)
        {
            if (!stock.TryGetValue(waste.Sku, out var row) || row.Unit != waste.Unit)
                throw new ArgumentException("Invalid spoilage component or unit.");
            DemandNumber(waste.Quantity);
            spoiled[waste.Sku] += waste.Quantity;
        }
        var closing = input.Opening.Select(row => row with
        {
            OnHand = row.OnHand - consumed[row.Sku] - spoiled[row.Sku]
        }).ToArray();
        if (closing.Any(row => row.OnHand < 0))
            throw new ArgumentException("Sales and spoilage exceed opening stock.");
        decimal Money(decimal value) => decimal.Round(value, 2, MidpointRounding.AwayFromZero);
        var cogs = Money(stock.Sum(row => consumed[row.Key] * row.Value.UnitCost));
        var wasteCost = Money(stock.Sum(row => spoiled[row.Key] * row.Value.UnitCost));
        return new(store, version, closing, new(store.Id, input.Date, Money(netSales), cogs,
            input.Labor, input.Occupancy, wasteCost, true, input.PlannedSales), input);
    }

    private static decimal Number(string value)
    {
        if (!decimal.TryParse(value, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var number))
            throw new ArgumentException("Invalid invariant decimal.");
        DemandNumber(number);
        return number;
    }

    private static void DemandNumber(decimal value)
    {
        if (value is < 0 or > 1000000 || decimal.Round(value, 4) != value)
            throw new ArgumentException("Amounts must be nonnegative, at most 1000000 and have at most four decimals.");
    }
}
