"""Collect authorized read-only East US reference preparation evidence without changing Azure defaults."""

import argparse
import copy
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

DIRECTORY = Path(__file__).resolve().parent
RUN = DIRECTORY / "eastus-c99de84d"
SUBSCRIPTION = "efd64343-6ef4-4926-951f-d3229f38bd76"
BASE = f"https://management.azure.com/subscriptions/{SUBSCRIPTION}"
AZ = shutil.which("az")


def run(name: str, arguments: list[str]) -> dict:
    if AZ is None:
        raise RuntimeError("Azure CLI is unavailable; do not install shared tools from this worker.")
    RUN.mkdir(exist_ok=True)
    command = [AZ, *arguments]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=240, check=False)
    (RUN / f"{name}.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (RUN / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    record = {
        "command": subprocess.list2cmdline(["az", *arguments]),
        "startedAtUtc": started,
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "exitCode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode == 0 and result.stdout.strip():
        try:
            record["result"] = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            record["parseError"] = str(error)
    (RUN / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"name": name, "exitCode": result.returncode, "stderr": result.stderr[:500]}), flush=True)
    return record


def rest(path: str, version: str) -> list[str]:
    return [
        "rest", "--method", "get", "--subscription", SUBSCRIPTION,
        "--url", f"{BASE}/{path}?api-version={version}", "--output", "json",
    ]


def collect() -> None:
    jobs = {
        "identity": [
            "account", "show", "--subscription", SUBSCRIPTION, "--query",
            "{account:user.name,subscriptionId:id,tenantId:tenantId,state:state,name:name}", "--output", "json",
        ],
        "group-exists": [
            "group", "exists", "--subscription", SUBSCRIPTION, "--name", "rg-resto-scale-agent", "--output", "json",
        ],
        "providers": ["provider", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "features": ["feature", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "cosmos-locations": ["cosmosdb", "locations", "list", "--subscription", SUBSCRIPTION, "--output", "json"],
        "model-quota": [
            "cognitiveservices", "usage", "list", "--location", "eastus",
            "--subscription", SUBSCRIPTION, "--output", "json",
        ],
        "model-eligibility": [
            "cognitiveservices", "model", "list", "--location", "eastus",
            "--subscription", SUBSCRIPTION, "--output", "json",
        ],
        "model-capacity-regional-corrected": [
            *rest("providers/Microsoft.CognitiveServices/locations/eastus/modelCapacities", "2024-10-01"),
            "--url-parameters", "modelFormat=OpenAI", "modelName=gpt-5.4-mini", "modelVersion=2026-03-17",
        ],
        "aca-usage": rest("providers/Microsoft.App/locations/eastus/usages", "2025-07-01"),
        "aca-profiles": rest("providers/Microsoft.App/locations/eastus/availableManagedEnvironmentsWorkloadProfileTypes",
                             "2025-07-01"),
        "servicebus-skus": rest("providers/Microsoft.ServiceBus/sku", "2024-01-01"),
        "web-usage": rest("providers/Microsoft.Web/locations/eastus/usages", "2024-11-01"),
        "web-skus": rest("providers/Microsoft.Web/skus", "2024-11-01"),
        "policy": ["policy", "assignment", "list", "--subscription", SUBSCRIPTION,
                   "--disable-scope-strict-match", "--scope", f"/subscriptions/{SUBSCRIPTION}", "--output", "json"],
        "rbac": ["role", "assignment", "list", "--subscription", SUBSCRIPTION,
                 "--assignee-object-id", "214d672b-df87-4f3b-94fd-7863032546c1",
                 "--scope", f"/subscriptions/{SUBSCRIPTION}", "--include-inherited", "--output", "json"],
    }
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda item: run(*item), jobs.items()))


def preview() -> None:
    template = json.loads((DIRECTORY / "main-c99de84d.arm.json").read_text(encoding="utf-8-sig"))
    assert "defaultValue" not in template["parameters"]["location"]
    parameters = json.loads((DIRECTORY / "main-preflight.parameters.json").read_text(encoding="utf-8-sig"))
    parameters["parameters"]["location"]["value"] = "eastus"
    parameters["parameters"]["guestSigningKeyExpiration"]["value"] = (
        datetime.now(timezone.utc) + timedelta(days=180)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    (RUN / "main.parameters.json").write_text(json.dumps(parameters, indent=2) + "\n", encoding="utf-8")
    modules = template["resources"]
    modules = list(modules.values()) if isinstance(modules, dict) else modules
    named = {item["name"]: item for item in modules if isinstance(item.get("name"), str)}
    for name in ("cosmos", "environment", "broker"):
        assert named[name]["properties"]["parameters"]["zoneRedundant"]["value"] is True
    assert named["registry"]["properties"]["parameters"]["acrSku"]["value"] == "Basic"
    assert named["registry"]["properties"]["parameters"]["networkRuleSetDefaultAction"]["value"] == "Allow"
    tags = {
        "Environment": "resto-scale-agent", "ManagedBy": "Bicep",
        "Project": "resto-scale-agent", "SecurityControl": "Ignore",
    }

    def wrapper(inner: dict, values: dict, name: str) -> Path:
        document = {
            "$schema": "https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "variables": {"tags": tags},
            "resources": [
                {
                    "type": "Microsoft.Resources/resourceGroups", "apiVersion": "2024-03-01",
                    "name": "rg-resto-scale-agent", "location": "eastus", "tags": tags,
                },
                {
                    "type": "Microsoft.Resources/deployments", "apiVersion": "2022-09-01",
                    "name": f"preview-{name}-c99de84d", "resourceGroup": "rg-resto-scale-agent",
                    "dependsOn": [
                        "[subscriptionResourceId('Microsoft.Resources/resourceGroups', 'rg-resto-scale-agent')]"
                    ],
                    "properties": {
                        "mode": "Incremental", "expressionEvaluationOptions": {"scope": "inner"},
                        "parameters": values, "template": inner,
                    },
                },
            ],
        }
        path = RUN / f"preview-{name}.arm.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return path

    paths = {"full": wrapper(template, parameters["parameters"], "full")}
    excluded = {}
    for name, resource_name in {
        "registry": "acrresto4tvlzr5zf2rxi",
        "cosmos": "cosmos-resto-4tvlzr5zf2rxi",
        "broker": "sb-resto-4tvlzr5zf2rxi",
        "vault": "kv-resto-4tvlzr5zf2rxi",
        "foundry": "ai-resto-4tvlzr5zf2rxi",
    }.items():
        module = named[name]["properties"]
        values = copy.deepcopy(module["parameters"])
        values.update({"name": {"value": resource_name}, "location": {"value": "eastus"}, "tags": {"value": tags}})
        excluded[name] = []
        for key in ("roleAssignments", "sqlRoleAssignments", "diagnosticSettings"):
            if key in values:
                values[key] = {"value": []}
                excluded[name].append(key)
        if name == "broker":
            values["queues"]["value"][0]["roleAssignments"] = []
            excluded[name].append("queue.roleAssignments")
        if name == "vault":
            values["keys"]["value"][0]["roleAssignments"] = []
            values["keys"]["value"][0]["attributes"]["exp"] = (
                int((datetime.now(timezone.utc) + timedelta(days=180)).timestamp())
            )
            excluded[name].append("key.roleAssignments")
        if name == "foundry":
            values["customSubDomainName"] = {"value": resource_name}
            deployment = values["deployments"]["value"][0]
            deployment["model"] = {"format": "OpenAI", "name": "gpt-5.4-mini", "version": "2026-03-17"}
            deployment["sku"] = {"name": "GlobalStandard", "capacity": 100}
        paths[name] = wrapper(module["template"], values, name)
    (RUN / "preview-exclusions.json").write_text(
        json.dumps({
            "purpose": "Independent partial provider previews only; unchanged full production template preview retained.",
            "exclusions": excluded,
            "identity": "No fabricated identity IDs; all dependent grants excluded, never claimed validated.",
            "names": "Exact proposed names retained from prior same-group preview; no resources created.",
            "location": "eastus; production location remains required and supplied through AZURE_LOCATION.",
        }, indent=2) + "\n", encoding="utf-8"
    )
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(
            lambda item: run(f"what-if-{item[0]}", [
                "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", "eastus",
                "--name", f"resto-{item[0]}-c99de84d", "--template-file", str(item[1]),
                "--no-pretty-print", "--output", "json",
            ]), paths.items()
        ))


def prices() -> None:
    for name, service in {
        "aca": "Azure Container Apps", "cosmos": "Azure Cosmos DB",
        "broker": "Service Bus", "model": "Foundry Models",
    }.items():
        query = urlencode({"$filter": f"armRegionName eq 'eastus' and serviceName eq '{service}'"})
        url = f"https://prices.azure.com/api/retail/prices?{query}"
        pages = []
        while url:
            with urlopen(url, timeout=90) as response:
                data = json.load(response)
            pages.append({"source": url, "response": data})
            url = data.get("NextPageLink")
        (RUN / f"prices-{name}.json").write_text(
            json.dumps({"checkedAtUtc": datetime.now(timezone.utc).isoformat(), "pages": pages}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"prices-{name}: {sum(len(page['response']['Items']) for page in pages)} items", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["collect", "preview", "prices"])
    operation = parser.parse_args().operation
    {"collect": collect, "preview": preview, "prices": prices}[operation]()


if __name__ == "__main__":
    main()
