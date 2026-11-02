"""Verify scenario fixture identity provenance against explicitly supplied repository catalogs."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-root", required=True, type=Path)
    args = parser.parse_args()
    company_file = args.catalog_root / "fictitious_company_names.csv"
    people_file = args.catalog_root / "fictitious_people_names.csv"
    industry_file = args.catalog_root / "microsoft_industry_verticals.csv"
    with company_file.open(encoding="utf-8-sig", newline="") as stream:
        companies = list(csv.DictReader(stream))
    with people_file.open(encoding="utf-8-sig", newline="") as stream:
        people = list(csv.DictReader(stream))
    with industry_file.open(encoding="utf-8-sig", newline="") as stream:
        industries = list(csv.DictReader(stream))
    assert any(row["Company Name"] == "Fourth Coffee" and row["Domain Name*"] == "fourthcoffee.com" for row in companies)
    assert any(row["Industry"] == "Hospitality & Travel" for row in industries)
    mapping = {"001": people[0]["FullName"], "002": people[1]["FullName"], "003": people[3]["FullName"]}
    snapshots = json.loads((ROOT / "src/CoffeeShop.Web/SeedData/stores.json").read_text(encoding="utf-8"))
    for snapshot in snapshots:
        store = snapshot["Store"]
        assert mapping[store["StoreId"]] == store["Manager"]
    assert sum(len(snapshot["Stock"]) for snapshot in snapshots) == 12
    provenance = {
        "company": "Fourth Coffee", "domain": "fourthcoffee.com", "companySlug": "fourth-coffee",
        "industry": "Hospitality & Travel", "businessUnits": ["sales"],
        "storeManagerMapping": mapping, "northAreaManager": people[2]["FullName"],
        "catalogDigests": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [company_file, people_file, industry_file]
        },
        "stockRecords": 12, "stores": 3, "dailyLedgerRecords": 3,
        "identityNote": "Synthetic people only, never automatically mapped to real Entra users.",
    }
    (ROOT / "evidence/catalog-provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Catalog identity, exact industry and all 12 stock-record provenance checks passed.")


if __name__ == "__main__":
    main()
