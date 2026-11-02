"""Retain read-only repair previews using the existing scenario Azure command collector."""

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid5

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
sys.path.insert(0, str(Path.cwd() / "scripts"))

from azure_context import infrastructure_fingerprint

SPEC = importlib.util.spec_from_file_location("resto_collector", RUN.parent / "centralus-91633e9e" / "prepare.py")
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)
COLLECTOR.COLLECTOR.RUN = RUN
SCOPE = COLLECTOR.SCOPE
SUBSCRIPTION = SCOPE["subscriptionId"]
GROUP = SCOPE["resourceGroup"]
PREFIX = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{GROUP}/providers/"
VAULT_NAME = "kv-resto-" + uuid5(
    UUID("11fb06fb-712d-4ddd-98c7-e71bbd588830"),
    "-".join((SUBSCRIPTION, SCOPE["environment"], "resto-scale-agent", "vault-v2")),
).hex[:15]


def write(name: str, value: object) -> None:
    (RUN / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def run(name: str, arguments: list[str]) -> dict:
    if (RUN / f"{name}.json").exists():
        raise FileExistsError(f"Keep prior observations intact: {name}")
    return COLLECTOR.run(name, arguments)


def required(name: str, arguments: list[str]) -> dict | list:
    record = run(name, arguments)
    if record["exitCode"] != 0 or "result" not in record:
        raise RuntimeError(f"Read-only check failed; inspect {name}.json.")
    return record["result"]


def observe() -> None:
    identity = required("identity", [
        "account", "show", "--subscription", SUBSCRIPTION, "--query",
        "{account:user.name,subscriptionId:id,tenantId:tenantId,state:state}", "--output", "json",
    ])
    if any(identity[key] != SCOPE[key] for key in ("account", "subscriptionId", "tenantId")):
        raise RuntimeError("Identity does not match authorized preparation scope.")
    if identity["state"] != "Enabled":
        raise RuntimeError("Target subscription is not enabled.")
    resources = required("resources-before", [
        "resource", "list", "--subscription", SUBSCRIPTION, "--resource-group", GROUP, "--output", "json",
    ])
    prior = json.loads((RUN.parent / "foundation-47a34228" / "resources-final.json").read_text())["result"]
    if {item["id"].casefold() for item in resources} != {item["id"].casefold() for item in prior}:
        raise RuntimeError("Resource inventory changed; review ownership before preview.")
    for item in resources:
        if item["location"] != "centralus" or any(
            item["tags"].get(key) != value
            for key, value in {"Project": "resto-scale-agent", "Environment": SCOPE["environment"]}.items()
        ):
            raise RuntimeError(f"Unverified resource ownership: {item['id']}")
    required("deployments", [
        "deployment", "group", "list", "--subscription", SUBSCRIPTION, "--resource-group", GROUP,
        "--query", "[].{name:name,state:properties.provisioningState,outputs:properties.outputs}", "--output", "json",
    ])
    for role in ("web", "chat", "worker", "scaler"):
        required(f"identity-{role}", [
            "identity", "show", "--subscription", SUBSCRIPTION, "--resource-group", GROUP,
            "--name", f"id-resto-{role}-4tvlzr5zf2rxi", "--output", "json",
        ])
    required("cosmos-grants-before", [
        "cosmosdb", "sql", "role", "assignment", "list", "--subscription", SUBSCRIPTION,
        "--resource-group", GROUP, "--account-name", "cosmos-resto-4tvlzr5zf2rxi", "--output", "json",
    ])
    required("aca-environment-usage", [
        "containerapp", "env", "list-usages", "--subscription", SUBSCRIPTION, "--resource-group", GROUP,
        "--name", "cae-resto-4tvlzr5zf2rxi", "--output", "json",
    ])
    write("vault-name-request", {"name": VAULT_NAME, "type": "Microsoft.KeyVault/vaults"})
    available = required("vault-name-availability", [
        "rest", "--method", "post", "--subscription", SUBSCRIPTION,
        "--url", f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
        "Microsoft.KeyVault/checkNameAvailability?api-version=2024-11-01",
        "--body", f"@{RUN / 'vault-name-request.json'}", "--headers", "Content-Type=application/json",
        "--output", "json",
    ])
    if available.get("nameAvailable") is not True:
        raise RuntimeError("Replacement vault name is unavailable; do not preview or adopt a conflicting vault.")
    write("ownership-review", {
        "scope": SCOPE, "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "retainedResourceCount": len(resources), "unchangedInventory": True,
        "replacementVaultName": VAULT_NAME, "replacementVaultExists": False,
        "basis": "Exact prior resource IDs, scenario/environment tags and retained deployment receipts.",
        "infrastructureFingerprint": infrastructure_fingerprint(SCENARIO),
        "directoryReadsOrWrites": False, "cloudMutations": False,
    })


def reconcile() -> None:
    identity = read("identity")["result"]
    if any(identity[key] != SCOPE[key] for key in ("account", "subscriptionId", "tenantId")):
        raise RuntimeError("Saved identity does not match exact preparation scope.")
    exists = required("group-exists-reconciled", [
        "group", "exists", "--subscription", SUBSCRIPTION, "--name", GROUP, "--output", "json",
    ])
    if exists is not False:
        raise RuntimeError("Group absence not confirmed; inspect ownership before proceeding.")
    for name, arguments in {
        "cosmos-locations": ["cosmosdb", "locations", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-quota": ["cognitiveservices", "usage", "list", "--subscription", SUBSCRIPTION,
                        "--location", "centralus", "--output", "json"],
        "model-capacity": [
            *COLLECTOR.COLLECTOR.rest("providers/Microsoft.CognitiveServices/locations/centralus/modelCapacities",
                                      "2024-10-01"),
            "--url-parameters", "modelFormat=OpenAI", "modelName=gpt-5.4-mini", "modelVersion=2026-03-17",
        ],
        "providers": ["provider", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
    }.items():
        required(name, arguments)
    write("vault-name-request", {"name": VAULT_NAME, "type": "Microsoft.KeyVault/vaults"})
    required("vault-name-availability", [
        "rest", "--method", "post", "--subscription", SUBSCRIPTION,
        "--url", f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
        "Microsoft.KeyVault/checkNameAvailability?api-version=2024-11-01",
        "--body", f"@{RUN / 'vault-name-request.json'}", "--headers", "Content-Type=application/json",
        "--output", "json",
    ])
    write("foundry-name-request", {
        "subdomainName": "ai-resto-6f6767a4ef6b5c6bb82c4a11edebfdec",
        "type": "Microsoft.CognitiveServices/accounts", "kind": "AIServices",
    })
    required("foundry-name-availability", [
        "rest", "--method", "post", "--subscription", SUBSCRIPTION,
        "--url", f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
        "Microsoft.CognitiveServices/checkDomainAvailability?api-version=2024-10-01",
        "--body", f"@{RUN / 'foundry-name-request.json'}", "--headers", "Content-Type=application/json",
        "--output", "json",
    ])
    write("ownership-review", {
        "scope": SCOPE, "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "currentGroupExists": False, "currentResourcesVerified": False,
        "priorListedResources": 13, "removedBy": None, "removedAtUtc": None,
        "historicalConsumptionQuota": "0/500 on the former environment, not current allocation evidence",
        "currentConsumptionQuota": None, "replacementVaultName": VAULT_NAME,
        "infrastructureFingerprint": infrastructure_fingerprint(SCENARIO),
        "cloudMutations": False, "directoryReadsOrWrites": False,
    })


def preview() -> None:
    if read("vault-name-availability")["result"].get("nameAvailable") is not True:
        raise RuntimeError("Replacement name availability must be verified before preview.")
    if read("foundry-name-availability")["result"].get("isSubdomainAvailable") is not True:
        raise RuntimeError("Foundry domain availability must be verified before preview.")
    parameters = json.loads(
        (RUN.parent / "centralus-189819a8" / "preview-full.arm.json").read_text()
    )["resources"][1]["properties"]["parameters"]
    parameters["guestSigningKeyExpiration"]["value"] = (
        datetime.now(timezone.utc) + timedelta(days=180)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    write("main.parameters", {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
        "contentVersion": "1.0.0.0", "parameters": parameters,
    })
    document = json.loads((RUN.parent / "centralus-189819a8" / "preview-full.arm.json").read_text())
    deployment = document["resources"][1]
    deployment["name"] = "resto-repair-6f748869"
    deployment["properties"]["template"] = read("main.arm")
    deployment["properties"]["parameters"] = parameters
    write("preview-full.arm", document)
    required("what-if-full", [
        "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", "centralus",
        "--name", "resto-repair-6f748869", "--template-file", str(RUN / "preview-full.arm.json"),
        "--no-pretty-print", "--output", "json",
    ])
    required("validate-full", [
        "deployment", "sub", "validate", "--subscription", SUBSCRIPTION, "--location", "centralus",
        "--name", "resto-repair-validation-6f748869", "--template-file", str(RUN / "preview-full.arm.json"),
        "--output", "json",
    ])


def independent() -> None:
    if read("vault-name-availability")["result"].get("nameAvailable") is not True:
        raise RuntimeError("Replacement vault availability must be verified before preview.")
    compiled = read("main.arm")
    for name in ("vault", "cosmos"):
        document = json.loads((RUN.parent / "centralus-189819a8" / f"preview-{name}.arm.json").read_text())
        deployment = document["resources"][1]
        deployment["name"] = f"resto-{name}-repair-6f748869"
        deployment["properties"]["template"] = compiled["resources"][name]["properties"]["template"]
        values = deployment["properties"]["parameters"]
        if name == "vault":
            values["name"]["value"] = VAULT_NAME
            values["keys"]["value"][0]["attributes"]["exp"] = int(
                (datetime.now(timezone.utc) + timedelta(days=180)).timestamp()
            )
        else:
            values["sqlRoleAssignments"] = {"value": [{
                "principalId": read("main.parameters")["parameters"]["principalId"]["value"],
                "roleDefinitionId": "00000000-0000-0000-0000-000000000002",
                "scope": f"{PREFIX}Microsoft.DocumentDB/databaseAccounts/cosmos-resto-4tvlzr5zf2rxi/dbs/restaurant",
            }]}
        write(f"preview-{name}.arm", document)
        required(f"what-if-{name}", [
            "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", "centralus",
            "--name", f"resto-{name}-repair-6f748869", "--template-file", str(RUN / f"preview-{name}.arm.json"),
            "--no-pretty-print", "--output", "json",
        ])
    write("preview-limitations", {
        "scope": SCOPE,
        "vault": "Exact replacement name and security/key parameters; excludes future web MI and deployer grants/diagnostics.",
        "cosmos": "Exact database controls and one real deployer grant with fully qualified database scope; "
        "excludes two uncreated managed identities and diagnostics. Not installed access or end-to-end acceptance.",
        "runtime": "No exact preview: actual infrastructure outputs, staff receipt, image digest and agent versions "
        "do not exist. Capture outputs and run dependent preview during any future authorized coherent installation.",
        "historicalConsumptionQuota": "0/500 applies to the former environment only; require actual new quota >=28 vCPU.",
        "cloudMutations": False,
    })


def checks() -> None:
    for name, arguments in {
        "aca-usage": COLLECTOR.COLLECTOR.rest("providers/Microsoft.App/locations/centralus/usages", "2025-07-01"),
        "network-usage": ["network", "list-usages", "--location", "centralus",
                          "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-eligibility": ["cognitiveservices", "model", "list", "--location", "centralus",
                              "--subscription", SUBSCRIPTION, "--output", "json"],
        "policy": ["policy", "assignment", "list", "--subscription", SUBSCRIPTION,
                   "--disable-scope-strict-match", "--scope", f"/subscriptions/{SUBSCRIPTION}", "--output", "json"],
        "rbac": ["role", "assignment", "list", "--subscription", SUBSCRIPTION,
                 "--assignee-object-id", read("main.parameters")["parameters"]["principalId"]["value"],
                 "--scope", f"/subscriptions/{SUBSCRIPTION}", "--include-inherited", "--output", "json"],
    }.items():
        required(name, arguments)
    required("group-exists-final", [
        "group", "exists", "--subscription", SUBSCRIPTION, "--name", GROUP, "--output", "json",
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("observe", "reconcile", "preview", "independent", "checks")
    )
    args = parser.parse_args()
    {
        "observe": observe, "reconcile": reconcile, "preview": preview,
        "independent": independent, "checks": checks,
    }[args.operation]()
