"""Generate reproducible ice-cream fixtures from the repository's exact synthetic identity catalogs."""

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(repository: Path) -> None:
    """Validate catalog records, then write ten recipe-based snapshots and strict per-store CSV packets."""
    with (repository / "fictitious_company_names.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        if next(reader) != ["Company Name", "Domain Name*"]:
            raise ValueError("Unexpected company catalog headers.")
        companies = list(reader)
    if companies[23] != ["Northwind Traders", "northwindtraders.com"]:
        raise ValueError("Selected company record changed; review provenance.")
    malformed = [index for index, row in enumerate(companies, 1) if len(row) != 2]
    print(f"Rejected malformed company records: {malformed}")
    with (repository / "fictitious_people_names.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        expected = ["FirstName", "LastName", "FullName", "FirstNameNative", "LastNameNative",
                    "FullNameNative", "Gender", "Language"]
        if next(reader) != expected:
            raise ValueError("Unexpected people catalog headers.")
        people = list(reader)[:12]
    if len(people) != 12 or any(len(row) != 8 or not all(row) for row in people):
        raise ValueError("Twelve valid people records required.")
    output = ROOT / "src" / "CoffeeShop.Web" / "SeedData"
    output.mkdir(parents=True, exist_ok=True)
    csv_dir = ROOT / "data"
    csv_dir.mkdir(exist_ok=True)
    snapshots = []
    for index in range(1, 11):
        store_id = f"{index:03}"
        opening = [
            {"Id": 1, "Sku": "vanilla", "Unit": "L", "OnHand": 20, "Target": 20, "UnitCost": 5},
            {"Id": 2, "Sku": "chocolate", "Unit": "L", "OnHand": 18, "Target": 20, "UnitCost": 6},
            {"Id": 3, "Sku": "cone", "Unit": "unit", "OnHand": 200, "Target": 200, "UnitCost": 0.2},
            {"Id": 4, "Sku": "cup", "Unit": "unit", "OnHand": 180, "Target": 200, "UnitCost": 0.1},
        ]
        recipes = [
            {"Product": "vanilla-cone", "Sku": "vanilla", "Unit": "L", "Quantity": 0.1},
            {"Product": "vanilla-cone", "Sku": "cone", "Unit": "unit", "Quantity": 1},
            {"Product": "chocolate-cup", "Sku": "chocolate", "Unit": "L", "Quantity": 0.1},
            {"Product": "chocolate-cup", "Sku": "cup", "Unit": "unit", "Quantity": 1},
        ]
        sales = [
            {"Product": "vanilla-cone", "Quantity": 80 + index, "UnitPrice": 4},
            {"Product": "chocolate-cup", "Quantity": 60 + index, "UnitPrice": 4.5},
        ]
        spoilage = [{"Sku": "vanilla", "Unit": "L", "Quantity": 0.5 + index / 10}]
        packet = {"Date": "2026-10-28", "Opening": opening, "Recipes": recipes, "Sales": sales,
                  "Spoilage": spoilage, "Labor": 140 + index * 2, "Occupancy": 45, "PlannedSales": 650}
        consumed = {row["Sku"]: Decimal(0) for row in opening}
        for sale in sales:
            for recipe in recipes:
                if recipe["Product"] == sale["Product"]:
                    consumed[recipe["Sku"]] += Decimal(str(recipe["Quantity"])) * sale["Quantity"]
        wasted = {row["Sku"]: Decimal(0) for row in opening}
        for row in spoilage:
            wasted[row["Sku"]] += Decimal(str(row["Quantity"]))
        closing = [{**row, "OnHand": float(Decimal(str(row["OnHand"])) - consumed[row["Sku"]]
                                         - wasted[row["Sku"]])} for row in opening]
        net_sales = sum(Decimal(str(row["UnitPrice"])) * row["Quantity"] for row in sales)
        cogs = sum(consumed[row["Sku"]] * Decimal(str(row["UnitCost"])) for row in opening)
        waste_cost = sum(wasted[row["Sku"]] * Decimal(str(row["UnitCost"])) for row in opening)
        snapshots.append({
            "Store": {"Id": index, "StoreId": store_id, "Name": f"Northwind Traders store {store_id}",
                      "Area": "north" if index <= 5 else "south", "Manager": people[index - 1][2]},
            "Version": f"seed-20261028-{store_id}", "Stock": closing,
            "Ledger": {"Id": index, "Date": packet["Date"], "NetSales": float(net_sales),
                       "Cogs": float(cogs), "Labor": packet["Labor"], "Occupancy": 45,
                       "Waste": float(waste_cost), "Complete": True, "PlannedSales": 650},
            "Input": packet,
        })
        with (csv_dir / f"day-{store_id}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["StoreId", "Date", "Kind", "Item", "Component", "Unit", "Quantity", "UnitCost", "Target"])
            prefix = [store_id, packet["Date"]]
            for row in opening:
                writer.writerow(prefix + ["stock", row["Sku"], "", row["Unit"],
                                          row["OnHand"], row["UnitCost"], row["Target"]])
            for row in recipes:
                writer.writerow(prefix + ["recipe", row["Product"], row["Sku"], row["Unit"], row["Quantity"], 0, 0])
            for row in sales:
                writer.writerow(prefix + ["sale", row["Product"], "", "unit", row["Quantity"], row["UnitPrice"], 0])
            for row in spoilage:
                writer.writerow(prefix + ["spoilage", row["Sku"], "", row["Unit"], row["Quantity"], 0, 0])
            for item, amount in [("labor", packet["Labor"]), ("occupancy", 45), ("planned-sales", 650)]:
                writer.writerow(prefix + ["cost", item, "", "USD", 1, amount, 0])
    (output / "stores.json").write_text(json.dumps(snapshots, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    provenance = {
        "company": {"catalog": "fictitious_company_names.csv", "record": 24, "companyName": companies[23][0],
                    "companyDomain": companies[23][1], "companySlug": "northwind-traders"},
        "people": [{"entity": f"store-{index:03}" if index <= 10 else ("area-north" if index == 11 else "area-south"),
                    "record": index, "FullName": row[2]} for index, row in enumerate(people, 1)],
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    print("Generated 10 snapshots, 10 CSV packets and catalog provenance.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    generate(parser.parse_args().repository)
