"""Collect only authorized read-only Central US preparation using the existing scenario collector."""

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid5

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
SPEC = importlib.util.spec_from_file_location("centralus_prior", RUN.parent / "centralus-91633e9e" / "prepare.py")
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)
PRIOR.RUN = RUN
PRIOR.COLLECTOR.RUN = RUN
SCOPE = PRIOR.SCOPE
SUBSCRIPTION = SCOPE["subscriptionId"]
BASE = PRIOR.BASE
read = PRIOR.read
write = PRIOR.write
FOUNDRY_NAME = "ai-resto-" + uuid5(
    UUID("11fb06fb-712d-4ddd-98c7-e71bbd588830"),
    "-".join((SUBSCRIPTION, SCOPE["environment"], "resto-scale-agent", "foundry-v2")),
).hex


def run(name: str, arguments: list[str]) -> dict:
    return PRIOR.run(name, arguments)


def discover() -> None:
    identity = run("identity", [
        "account", "show", "--subscription", SUBSCRIPTION, "--query",
        "{account:user.name,subscriptionId:id,tenantId:tenantId,state:state,name:name}", "--output", "json",
    ])["result"]
    if any(identity[key] != SCOPE[key] for key in ("account", "subscriptionId", "tenantId")):
        raise RuntimeError("Current identity differs from authorized scope.")
    if identity["state"] != "Enabled":
        raise RuntimeError("Subscription is not Enabled.")
    for name, arguments in {
        "group-exists": [
            "group", "exists", "--name", SCOPE["resourceGroup"], "--subscription", SUBSCRIPTION, "--output", "json",
        ],
        "owned-accounts": [
            "resource", "list", "--resource-group", SCOPE["resourceGroup"], "--subscription", SUBSCRIPTION,
            "--resource-type", "Microsoft.CognitiveServices/accounts", "--output", "json",
        ],
        "aca-usage": PRIOR.COLLECTOR.rest("providers/Microsoft.App/locations/centralus/usages", "2025-07-01"),
        "aca-quota": PRIOR.COLLECTOR.rest(
            "providers/Microsoft.App/locations/centralus/providers/Microsoft.Quota/quotas", "2025-09-01"),
        "aca-quota-usage": PRIOR.COLLECTOR.rest(
            "providers/Microsoft.App/locations/centralus/providers/Microsoft.Quota/usages", "2025-09-01"),
    }.items():
        run(name, arguments)


def name_check() -> None:
    path = RUN / "foundry-domain-request.json"
    path.write_text(json.dumps({
        "subdomainName": FOUNDRY_NAME, "type": "Microsoft.CognitiveServices/accounts", "kind": "AIServices",
    }), encoding="utf-8")
    result = run("foundry-domain-availability", [
        "rest", "--method", "post", "--subscription", SUBSCRIPTION,
        "--url", f"{BASE}/providers/Microsoft.CognitiveServices/checkDomainAvailability?api-version=2024-10-01",
        "--body", f"@{path}", "--headers", "Content-Type=application/json", "--output", "json",
    ])
    if result["exitCode"] != 0 or result["result"].get("isSubdomainAvailable") is not True:
        raise RuntimeError("Replacement domain availability not verified; no new what-if may run.")


def quota_metadata() -> None:
    run("aca-usage-latest", PRIOR.COLLECTOR.rest("providers/Microsoft.App/locations/centralus/usages", "2026-07-01"))
    run("quota-provider", [
        "provider", "show", "--namespace", "Microsoft.Quota", "--subscription", SUBSCRIPTION,
        "--query", "{namespace:namespace,registrationState:registrationState}", "--output", "json",
    ])
    run("app-usage-api-types", [
        "provider", "show", "--namespace", "Microsoft.App", "--subscription", SUBSCRIPTION,
        "--query",
        "resourceTypes[?contains(resourceType, 'usage') || contains(resourceType, 'quota')]."
        "{resourceType:resourceType,apiVersions:apiVersions}", "--output", "json",
    ])


def preview() -> None:
    availability = PRIOR.read("foundry-domain-availability")
    if availability["result"].get("isSubdomainAvailable") is not True:
        raise RuntimeError("Check the replacement domain before previews.")
    compiled = json.loads((RUN / "main.arm.json").read_text(encoding="utf-8-sig"))
    modules = compiled["resources"]
    named = {item["name"]: item for item in modules.values() if isinstance(item.get("name"), str)}
    exclusions = PRIOR.read("scope-and-fingerprint")
    exclusions["exclusions"] = {}
    for name in ("full", "registry", "cosmos", "broker", "vault", "foundry"):
        document = json.loads((RUN.parent / "centralus-91633e9e" / f"preview-{name}.arm.json").read_text())
        deployment = document["resources"][1]
        deployment["name"] = f"preview-{name}-189819a8"
        values = deployment["properties"]["parameters"]
        if name == "full":
            deployment["properties"]["template"] = compiled
            values["guestSigningKeyExpiration"]["value"] = (
                datetime.now(timezone.utc) + timedelta(days=180)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            deployment["properties"]["template"] = named[name]["properties"]["template"]
        if name == "foundry":
            values["name"]["value"] = FOUNDRY_NAME
            values["customSubDomainName"]["value"] = FOUNDRY_NAME
        if name == "vault":
            values["keys"]["value"][0]["attributes"]["exp"] = int(
                (datetime.now(timezone.utc) + timedelta(days=180)).timestamp()
            )
        path = RUN / f"preview-{name}.arm.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        result = run(f"what-if-{name}", [
            "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", "centralus",
            "--name", f"resto-{name}-189819a8", "--template-file", str(path),
            "--no-pretty-print", "--output", "json",
        ])
        if result["exitCode"] == 0 and any(
            item.get("changeType") in ("Delete", "Modify") for item in result["result"].get("changes", [])
        ):
            raise RuntimeError("Unexpected existing target changes require scoped ownership review.")
    run("validate-full", [
        "deployment", "sub", "validate", "--subscription", SUBSCRIPTION, "--location", "centralus",
        "--name", "resto-validate-189819a8", "--template-file", str(RUN / "preview-full.arm.json"), "--output", "json",
    ])
    previous = json.loads((RUN.parent / "centralus-91633e9e" / "preview-exclusions.json").read_text())
    previous.update({"scope": SCOPE, "foundryName": FOUNDRY_NAME,
                     "names": "Only Foundry uses repaired v2 expression; all other exact names unchanged."})
    PRIOR.write("preview-exclusions", previous)
    run("group-exists-final", [
        "group", "exists", "--subscription", SUBSCRIPTION, "--name", SCOPE["resourceGroup"], "--output", "json",
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("discover", "collect", "prices", "name", "preview", "quota"))
    args = parser.parse_args()
    if args.operation == "discover":
        discover()
    elif args.operation == "collect":
        PRIOR.collect()
    elif args.operation == "prices":
        PRIOR.prices()
    elif args.operation == "name":
        name_check()
    elif args.operation == "quota":
        quota_metadata()
    else:
        preview()
