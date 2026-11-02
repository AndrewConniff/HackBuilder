"""Refresh the existing regional public retail estimate without changing its design."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

DIRECTORY = Path(__file__).resolve().parent
METERS = {
    "broker": "176d7148-0033-48c7-8b18-7af4a9d1dca7",
    "cpuActive": "18ba5751-fda4-558b-b9dc-9416e72b9a62",
    "cpuIdle": "5df0e75d-f25b-5da9-99d1-1060f84388f6",
    "memory": "ef6a0bec-4635-5e9c-8b2e-8b346b998acb",
    "cosmosAutoscale": "b905034e-d994-4b24-8dd7-f57e611f7987",
    "cosmosStorage": "56f07b6a-c7d9-490f-a196-a7ee08e28712",
    "inputTokens": "fa5f9dcf-3bf0-50ea-8c22-7daa13474f66",
    "outputTokens": "5d711bbe-b247-5277-891f-a99e24468d2d",
}


def main() -> None:
    meter_filter = " or ".join(f"meterId eq '{meter}'" for meter in METERS.values())
    query = urlencode({"$filter": f"armRegionName eq 'eastus2' and ({meter_filter})"})
    url = f"https://prices.azure.com/api/retail/prices?{query}"
    with urlopen(url, timeout=90) as response:
        raw = json.load(response)
    (DIRECTORY / "prices-refreshed-19f3d63e.json").write_text(
        json.dumps(raw, indent=2) + "\n", encoding="utf-8"
    )
    assert not raw.get("NextPageLink"), "Unexpected pagination; estimate not refreshed."
    rates = {}
    for name, meter in METERS.items():
        matches = [
            item for item in raw["Items"]
            if item["meterId"] == meter and item["type"] == "Consumption"
            and item["currencyCode"] == "USD" and item["tierMinimumUnits"] == 0
        ]
        assert matches, f"Missing current consumption rate for {name}."
        values = {item["retailPrice"] for item in matches}
        assert len(values) == 1, f"Ambiguous rate for {name}: {values}"
        rates[name] = {"rate": values.pop(), "unit": matches[0]["unitOfMeasure"], "meterId": meter}
    rate = {name: item["rate"] for name, item in rates.items()}
    seconds = 730 * 3600
    result = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": url,
        "currency": "USD",
        "region": "eastus2",
        "rates": rates,
        "monthlyExamples": {
            "hours": 730,
            "brokerOneMessagingUnit": round(730 * rate["broker"], 2),
            "nineReplicasIdle": round(seconds * (4.5 * rate["cpuIdle"] + 9 * rate["memory"]), 2),
            "nineReplicasActive": round(seconds * (4.5 * rate["cpuActive"] + 9 * rate["memory"]), 2),
            "cosmos400RU": round(730 * 4 * rate["cosmosAutoscale"], 2),
            "cosmos4000RU": round(730 * 40 * rate["cosmosAutoscale"], 2),
            "model24MInput7_2MOutput": round(24 * rate["inputTokens"] + 7.2 * rate["outputTokens"], 2),
        },
        "planningAllowances": {
            "sharedInfrastructureMonthly": [745, 1150],
            "fullReferenceMonthly": [900, 1650],
            "basis": "Retained rounded allowances; rates refreshed, confirmed SKUs and replica counts unchanged.",
        },
        "limitations": [
            "Not a quote, budget approval or spending cap.",
            "Ancillary services retain a $30-$120 allowance, not individually refreshed meter quotes.",
            "Free grants, negotiated discounts and taxes excluded; storage, backup, zones and telemetry can add costs.",
            "No charges incurred by a retail-price query; Cosmos zone access remains unavailable.",
        ],
    }
    (DIRECTORY / "cost-review-19f3d63e.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
