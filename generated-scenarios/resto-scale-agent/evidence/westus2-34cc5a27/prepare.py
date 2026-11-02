"""Collect exact-scope West US 2 read-only preparation without changing the reference or Azure defaults."""

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
sys.path.insert(0, str(Path.cwd() / "scripts"))

from azure_context import infrastructure_fingerprint

SPEC = importlib.util.spec_from_file_location("collector", RUN.parent / "validate-eastus-c99de84d.py")
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)
COLLECTOR.RUN = RUN
SUBSCRIPTION = COLLECTOR.SUBSCRIPTION
REGION = "westus2"
SCOPE = {
    "account": "petender@microsoft.com",
    "subscriptionId": SUBSCRIPTION,
    "tenantId": "16b3c013-d300-468d-ac64-7eda0820b6d3",
    "environment": "resto-scale-agent",
    "resourceGroup": "rg-resto-scale-agent",
    "region": REGION,
}


def write(name: str, value: object) -> None:
    (RUN / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def run(name: str, arguments: list[str]) -> dict:
    result = COLLECTOR.run(name, arguments)
    if result["exitCode"] and any(
        marker in (result["stdout"] + result["stderr"]).casefold()
        for marker in ("permission denied by", "permission request denied", "tool execution denied", "approval required")
    ):
        raise RuntimeError(f"Host/CLI denial retained in {name}.json; stop without alternative execution.")
    return result


def collect() -> None:
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
        "model-quota": ["cognitiveservices", "usage", "list", "--location", REGION,
                        "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-eligibility": ["cognitiveservices", "model", "list", "--location", REGION,
                              "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-capacity": [
            *COLLECTOR.rest(f"providers/Microsoft.CognitiveServices/locations/{REGION}/modelCapacities", "2024-10-01"),
            "--url-parameters", "modelFormat=OpenAI", "modelName=gpt-5.4-mini", "modelVersion=2026-03-17",
        ],
        "foundry-skus": ["cognitiveservices", "account", "list-skus", "--kind", "AIServices",
                         "--location", REGION, "--subscription", SUBSCRIPTION, "--output", "json"],
        "aca-usage": COLLECTOR.rest(f"providers/Microsoft.App/locations/{REGION}/usages", "2025-07-01"),
        "aca-profiles": COLLECTOR.rest(
            f"providers/Microsoft.App/locations/{REGION}/availableManagedEnvironmentsWorkloadProfileTypes", "2025-07-01"),
        "aca-environment-usage": [
            "containerapp", "env", "list-usages", "--name", "cae-resto-4tvlzr5zf2rxi",
            "--resource-group", SCOPE["resourceGroup"], "--subscription", SUBSCRIPTION, "--output", "json",
        ],
        "servicebus-skus": COLLECTOR.rest("providers/Microsoft.ServiceBus/sku", "2024-01-01"),
        "network-usage": ["network", "list-usages", "--location", REGION,
                          "--subscription", SUBSCRIPTION, "--output", "json"],
        "region-zones": [*COLLECTOR.rest("locations", "2022-12-01"), "--query", f"value[?name=='{REGION}']"],
        "policy": ["policy", "assignment", "list", "--subscription", SUBSCRIPTION,
                   "--disable-scope-strict-match", "--scope", f"/subscriptions/{SUBSCRIPTION}", "--output", "json"],
        "rbac": ["role", "assignment", "list", "--subscription", SUBSCRIPTION,
                 "--assignee-object-id", "214d672b-df87-4f3b-94fd-7863032546c1",
                 "--scope", f"/subscriptions/{SUBSCRIPTION}", "--include-inherited", "--output", "json"],
    }
    for name, arguments in jobs.items():
        result = run(name, arguments)
        if name == "group-exists":
            assert result["exitCode"] == 0 and result["result"] is False, (
                "Existing target requires ownership/conflict review before further preparation."
            )
    write("scope-and-fingerprint", {
        "scope": SCOPE, "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "infrastructureFingerprint": infrastructure_fingerprint(SCENARIO), "mutationsPerformed": False,
        "notApplicable": {
            "Microsoft.Compute/virtualMachines": "No VM or VMSS in either template; zero VM-family demand.",
            "Microsoft.Web/serverfarms": "No App Service/Functions plan; zero B2 worker demand.",
        },
    })


def preview() -> None:
    source = RUN.parent / "centralus-91633e9e"
    exclusions = json.loads((source / "preview-exclusions.json").read_text())
    for name in ("full", "registry", "cosmos", "broker", "vault", "foundry"):
        document = json.loads((source / f"preview-{name}.arm.json").read_text(encoding="utf-8-sig"))
        group, deployment = document["resources"]
        assert group["name"] == SCOPE["resourceGroup"] and group["location"] == "centralus"
        group["location"] = REGION
        deployment["name"] = f"preview-{name}-34cc5a27"
        values = deployment["properties"]["parameters"]
        assert values["location"]["value"] == "centralus"
        values["location"]["value"] = REGION
        if name == "full":
            assert read("main.arm") == deployment["properties"]["template"], "Current production template changed."
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
            "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", REGION,
            "--name", f"resto-{name}-34cc5a27", "--template-file", str(path),
            "--no-pretty-print", "--output", "json",
        ])
        if result["exitCode"] == 0:
            assert not any(
                change["changeType"] in ("Delete", "Modify") for change in result["result"].get("changes", [])
            ), "Unexpected existing target changes require scoped ownership review."
    exclusions["location"] = f"{REGION}; production required ${{AZURE_LOCATION}} unchanged."
    exclusions["scope"] = SCOPE
    write("preview-exclusions", exclusions)
    run("validate-full", [
        "deployment", "sub", "validate", "--subscription", SUBSCRIPTION, "--location", REGION,
        "--name", "resto-validate-34cc5a27", "--template-file", str(RUN / "preview-full.arm.json"),
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
        query = urlencode({"$filter": f"armRegionName eq '{REGION}' and {product_filter}"})
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
    {"collect": collect, "preview": preview, "prices": prices}[parser.parse_args().operation]()
