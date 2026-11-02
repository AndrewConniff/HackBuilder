"""Local/public-only review evidence. Never queries subscription resources or Microsoft Graph."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

from check_management_readiness import MANAGEMENT_VM_SIZE

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "local-evidence" / "management-repair-20261024"


def prices(service: str, extra: str = "") -> list[dict]:
    query = f"armRegionName eq 'centralus' and serviceName eq '{service}' and priceType eq 'Consumption'"
    if extra:
        query += " and " + extra
    url = "https://prices.azure.com/api/retail/prices?" + urllib.parse.urlencode({"$filter": query})
    items = []
    while url:
        with urllib.request.urlopen(url, timeout=90) as response:
            result = json.load(response)
        items += result["Items"]
        url = result.get("NextPageLink")
    return items


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    checks = []
    commands = [
        ["az", "bicep", "build", "--file", str(ROOT / "infra" / "main.bicep"), "--stdout"],
        ["az", "bicep", "lint", "--file", str(ROOT / "infra" / "main.bicep")],
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_*.py", "-v"],
    ]
    for args in commands:
        executable = shutil.which(args[0])
        start = datetime.now(timezone.utc).isoformat()
        result = subprocess.run([executable, *args[1:]], capture_output=True, text=True, timeout=240, check=False)
        checks.append({"command": args, "startedAtUtc": start, "exitCode": result.returncode,
                       "stdout": "Compiled template omitted" if "--stdout" in args and result.returncode == 0
                       else result.stdout, "stderr": result.stderr})
    rate_sets = {
        "vm": prices("Virtual Machines", f"armSkuName eq '{MANAGEMENT_VM_SIZE}'"),
        "nat": prices("Virtual Network", "contains(productName, 'NAT')"),
        "ip": prices("Virtual Network", "contains(productName, 'IP Addresses')"),
        "disk": prices("Storage", "contains(productName, 'Standard SSD')"),
    }
    (EVIDENCE / "public-retail-prices.json").write_text(
        json.dumps({"retrievedAtUtc": datetime.now(timezone.utc).isoformat(), "currency": "USD",
                    "source": "https://prices.azure.com/api/retail/prices", "items": rate_sets}, indent=2) + "\n")
    (EVIDENCE / "local-checks.json").write_text(
        json.dumps({"recordedAtUtc": datetime.now(timezone.utc).isoformat(),
                    "cloudResourceOrDirectoryOperations": False, "checks": checks}, indent=2) + "\n")
    for name, items in rate_sets.items():
        selected = [item for item in items if
                    ("Spot" not in item["skuName"] and "Low Priority" not in item["skuName"])
                    and (name != "vm" or "Windows" not in item["productName"])
                    and (name != "disk" or item["meterName"] in {"E4 LRS Disk", "E4 LRS Disk Operations"})
                    and (name != "ip" or "Standard IPv4" in item["meterName"])]
        print(name, [(i["productName"], i["meterName"], i["retailPrice"], i["unitOfMeasure"]) for i in selected])
    print("Local command exits:", [check["exitCode"] for check in checks])
    return int(any(check["exitCode"] for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())
