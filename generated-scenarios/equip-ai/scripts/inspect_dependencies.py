"""Inventory scenario packages using only the approved feed's advertised resources."""

import json
import urllib.request
from pathlib import Path

PACKAGES = {
    "Azure.Identity": "1.21.0",
    "Azure.AI.Projects": "2.0.1",
    "Azure.AI.Projects.Agents": "2.0.0",
    "Azure.AI.Extensions.OpenAI": "2.0.0",
    "Azure.Storage.Blobs": "12.30.1",
    "Microsoft.AspNetCore.Authentication.JwtBearer": "10.0.13",
    "Microsoft.Azure.Devices.Client": None,
    "Microsoft.Playwright": None,
}
FEED = "https://packagefeedproxy.microsoft.io/nuget/v3/index.json"


def read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def main() -> None:
    index = read_json(FEED)
    base = next(item["@id"] for item in index["resources"] if item["@type"] == "PackageBaseAddress/3.0.0")
    records = []
    for package, selected in PACKAGES.items():
        metadata = read_json(f"{base}{package.lower()}/index.json")
        versions = metadata["versions"]
        stable = [version for version in versions if "-" not in version]
        if selected is None:
            selected = max(stable, key=lambda value: tuple(int(part) for part in value.split(".")))
        if selected not in versions:
            raise ValueError(f"{package} {selected} is not available from the approved feed")
        record = {"package": package, "version": selected, "metadataVerified": True}
        records.append(record)
        print(json.dumps(record))
    target = Path(__file__).resolve().parents[1] / "dependency-inventory.json"
    target.write_text(json.dumps({"feed": FEED, "packages": records}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
