"""Refresh only the authorized Central US reference preparation, preserving prior observations."""

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))

from azure_context import infrastructure_fingerprint

SPEC = importlib.util.spec_from_file_location("prior_collector", RUN.parent / "validate-eastus-c99de84d.py")
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)
COLLECTOR.RUN = RUN
SUBSCRIPTION = COLLECTOR.SUBSCRIPTION
BASE = COLLECTOR.BASE
SCOPE = {
    "account": "petender@microsoft.com",
    "subscriptionId": SUBSCRIPTION,
    "tenantId": "16b3c013-d300-468d-ac64-7eda0820b6d3",
    "environment": "resto-scale-agent",
    "resourceGroup": "rg-resto-scale-agent",
    "region": "centralus",
}


def write(name: str, value: object) -> None:
    (RUN / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def run(name: str, arguments: list[str]) -> dict:
    result = COLLECTOR.run(name, arguments)
    if result["exitCode"] and any(
        text in (result["stderr"] + result["stdout"]).casefold()
        for text in ("permission denied by", "permission request denied", "tool execution denied", "approval required")
    ):
        raise RuntimeError(f"Host/CLI approval failure retained in {name}.json; stop without alternate execution.")
    return result


def collect(start_at: str | None = None) -> None:
    identity = run("identity", [
        "account", "show", "--subscription", SUBSCRIPTION, "--query",
        "{account:user.name,subscriptionId:id,tenantId:tenantId,state:state,name:name}", "--output", "json",
    ])
    assert identity["exitCode"] == 0
    assert all(identity["result"][key] == SCOPE[key] for key in ("account", "subscriptionId", "tenantId"))
    assert identity["result"]["state"] == "Enabled"
    jobs = {
        "group-exists": ["group", "exists", "--subscription", SUBSCRIPTION,
                         "--name", SCOPE["resourceGroup"], "--output", "json"],
        "providers": ["provider", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "features": ["feature", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "cosmos-locations": ["cosmosdb", "locations", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-quota": ["cognitiveservices", "usage", "list", "--location", "centralus",
                        "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-eligibility": ["cognitiveservices", "model", "list", "--location", "centralus",
                              "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-capacity": [
            *COLLECTOR.rest("providers/Microsoft.CognitiveServices/locations/centralus/modelCapacities", "2024-10-01"),
            "--url-parameters", "modelFormat=OpenAI", "modelName=gpt-5.4-mini", "modelVersion=2026-03-17",
        ],
        "foundry-skus": ["cognitiveservices", "account", "list-skus", "--kind", "AIServices",
                         "--location", "centralus", "--subscription", SUBSCRIPTION, "--output", "json"],
        "aca-usage": COLLECTOR.rest("providers/Microsoft.App/locations/centralus/usages", "2025-07-01"),
        "aca-profiles": COLLECTOR.rest(
            "providers/Microsoft.App/locations/centralus/availableManagedEnvironmentsWorkloadProfileTypes", "2025-07-01"),
        "servicebus-skus": COLLECTOR.rest("providers/Microsoft.ServiceBus/sku", "2024-01-01"),
        "network-usage": ["network", "list-usages", "--location", "centralus",
                          "--subscription", SUBSCRIPTION, "--output", "json"],
        "region-zones": [
            *COLLECTOR.rest("locations", "2022-12-01"), "--query", "value[?name=='centralus']",
        ],
        "policy": ["policy", "assignment", "list", "--subscription", SUBSCRIPTION,
                   "--disable-scope-strict-match", "--scope", f"/subscriptions/{SUBSCRIPTION}", "--output", "json"],
        "rbac": ["role", "assignment", "list", "--subscription", SUBSCRIPTION,
                 "--assignee-object-id", "214d672b-df87-4f3b-94fd-7863032546c1",
                 "--scope", f"/subscriptions/{SUBSCRIPTION}", "--include-inherited", "--output", "json"],
    }
    active = start_at is None
    for name, arguments in jobs.items():
        active = active or name == start_at
        if active:
            run(name, arguments)
    write("scope-and-fingerprint", {
        "scope": SCOPE, "infrastructureFingerprint": infrastructure_fingerprint(SCENARIO),
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "productionLocation": "${AZURE_LOCATION}",
        "noMutations": True,
        "notApplicable": {
            "Microsoft.Compute/virtualMachines": "No VM or VMSS planned; no VM-family quota demand.",
            "Microsoft.Web/serverfarms": "No App Service/Functions plan planned; no B2 worker demand.",
        },
    })


def preview() -> None:
    source = RUN.parent / "eastus-c99de84d"
    exclusions = json.loads((source / "preview-exclusions.json").read_text())
    for name in ("full", "registry", "cosmos", "broker", "vault", "foundry"):
        document = json.loads((source / f"preview-{name}.arm.json").read_text(encoding="utf-8-sig"))
        group, deployment = document["resources"]
        assert group["name"] == SCOPE["resourceGroup"] and group["location"] == "eastus"
        group["location"] = "centralus"
        deployment["name"] = f"preview-{name}-91633e9e"
        values = deployment["properties"]["parameters"]
        assert values["location"]["value"] == "eastus"
        values["location"]["value"] = "centralus"
        if name == "full":
            current = json.loads((RUN / "main.arm.json").read_text(encoding="utf-8-sig"))
            assert current == deployment["properties"]["template"], "Production infrastructure changed; rebuild preview."
            values["guestSigningKeyExpiration"]["value"] = (
                datetime.now(timezone.utc) + timedelta(days=180)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        if name == "vault":
            values["keys"]["value"][0]["attributes"]["exp"] = (
                int((datetime.now(timezone.utc) + timedelta(days=180)).timestamp())
            )
        path = RUN / f"preview-{name}.arm.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        result = run(f"what-if-{name}", [
            "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", "centralus",
            "--name", f"resto-{name}-91633e9e", "--template-file", str(path),
            "--no-pretty-print", "--output", "json",
        ])
        if result["exitCode"] == 0:
            changes = result.get("result", {}).get("changes", [])
            assert not any(item.get("changeType") in ("Delete", "Modify") for item in changes), (
                "Unexpected existing resource changes; stop for target ownership review."
            )
    exclusions["location"] = "centralus; required production ${AZURE_LOCATION} remains unchanged."
    exclusions["scope"] = SCOPE
    write("preview-exclusions", exclusions)
    run("validate-full", [
        "deployment", "sub", "validate", "--subscription", SUBSCRIPTION, "--location", "centralus",
        "--name", "resto-validate-91633e9e", "--template-file", str(RUN / "preview-full.arm.json"),
        "--output", "json",
    ])
    run("group-exists-final", [
        "group", "exists", "--subscription", SUBSCRIPTION, "--name", SCOPE["resourceGroup"], "--output", "json",
    ])


def prices() -> None:
    for name, product_filter in {
        "aca": "serviceName eq 'Azure Container Apps'",
        "cosmos": "serviceName eq 'Azure Cosmos DB'",
        "broker": "serviceName eq 'Service Bus'",
        "model": "serviceName eq 'Foundry Models' and productName eq 'Azure OpenAI GPT5'",
    }.items():
        query = urlencode({"$filter": f"armRegionName eq 'centralus' and {product_filter}"})
        url = f"https://prices.azure.com/api/retail/prices?{query}"
        pages = []
        while url:
            with urlopen(url, timeout=90) as response:
                data = json.load(response)
            pages.append({"source": url, "response": data})
            url = data.get("NextPageLink")
        write(f"prices-{name}", {"checkedAtUtc": datetime.now(timezone.utc).isoformat(), "pages": pages})
        print(f"prices-{name}: {sum(len(page['response']['Items']) for page in pages)} items", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("collect", "preview", "prices"))
    parser.add_argument("--start-at", help="Resume an incomplete collection without repeating successful queries.")
    arguments = parser.parse_args()
    if arguments.operation == "collect":
        collect(arguments.start_at)
    else:
        {"preview": preview, "prices": prices}[arguments.operation]()
