"""Collect explicitly authorized Central US reads and a non-deploying ARM preview."""

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
SCENARIO = DIRECTORY.parent.parent
SUBSCRIPTION = "efd64343-6ef4-4926-951f-d3229f38bd76"
TENANT = "16b3c013-d300-468d-ac64-7eda0820b6d3"
BASE = f"https://management.azure.com/subscriptions/{SUBSCRIPTION}"
AZ = shutil.which("az")
AZD = shutil.which("azd")


def save(name: str, value: object) -> None:
    (DIRECTORY / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load(name: str):
    return json.loads((DIRECTORY / f"{name}.json").read_text(encoding="utf-8-sig"))


def run(name: str, command: list[str], timeout: int = 600) -> int:
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = subprocess.run(
            command, cwd=SCENARIO, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
        )
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = error.stderr or b""
        stdout = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else stderr
        stderr += "\nCollector timeout; operation outcome unknown."
        code = 124
    (DIRECTORY / f"{name}.json").write_text(stdout, encoding="utf-8")
    (DIRECTORY / f"{name}.stderr.txt").write_text(stderr, encoding="utf-8")
    save(f"{name}.command", {
        "command": subprocess.list2cmdline(command), "cwd": str(SCENARIO),
        "startedAtUtc": started, "finishedAtUtc": datetime.now(timezone.utc).isoformat(),
        "exitCode": code, "stdout": f"{name}.json", "stderr": f"{name}.stderr.txt",
    })
    print(f"{name}: exit {code}", flush=True)
    return code


def az(name: str, arguments: list[str]) -> int:
    return run(name, [AZ, *arguments, "--subscription", SUBSCRIPTION, "--output", "json"])


def rest(name: str, path: str, version: str, parameters: dict | None = None) -> int:
    save(f"{name}.query", {"api-version": version, **(parameters or {})})
    return az(name, [
        "rest", "--method", "get", "--url", BASE + path,
        "--url-parameters", f"@{DIRECTORY / (name + '.query.json')}",
    ])


def identity() -> None:
    assert az("account", [
        "account", "show", "--query",
        "{account:user.name,subscriptionId:id,tenantId:tenantId,state:state}",
    ]) == 0
    account = load("account")
    assert account == {
        "account": "petender@microsoft.com", "subscriptionId": SUBSCRIPTION,
        "tenantId": TENANT, "state": "Enabled",
    }, "Identity differs from the authorized target; stop."
    assert run("azd-auth", [AZD, "auth", "login", "--check-status"]) == 0
    assert run("azd-values", [AZD, "env", "get-values", "--environment", "equip-ai", "--no-prompt"]) == 0
    text = (DIRECTORY / "azd-values.json").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
    values = {key: value.strip('"') for key, value in values.items()}
    assert values["AZURE_SUBSCRIPTION_ID"] == SUBSCRIPTION
    assert values["AZURE_ENV_NAME"] == "equip-ai" and values["AZURE_LOCATION"] == "centralus"
    save("saved-target-observation", {
        key: values.get(key) for key in ("AZURE_ENV_NAME", "AZURE_LOCATION", "AZURE_SUBSCRIPTION_ID")
    })


def quotas() -> None:
    rest("web-usages", "/providers/Microsoft.Web/locations/centralus/usages", "2025-03-01")
    az("web-b2-linux-regions", ["appservice", "list-locations", "--sku", "B2", "--linux-workers-enabled"])
    az("web-runtimes", ["webapp", "list-runtimes", "--os", "linux"])
    az("model-catalog", ["cognitiveservices", "model", "list", "--location", "centralus"])
    az("model-quota", ["cognitiveservices", "usage", "list", "--location", "centralus"])
    rest("model-capacities", "/providers/Microsoft.CognitiveServices/modelCapacities", "2024-10-01", {
        "modelFormat": "OpenAI", "modelName": "gpt-4.1-mini", "modelVersion": "2025-04-14",
    })
    rest("cognitive-skus", "/providers/Microsoft.CognitiveServices/skus", "2025-06-01")
    rest("storage-skus", "/providers/Microsoft.Storage/skus", "2025-06-01")
    rest("storage-usages", "/providers/Microsoft.Storage/locations/centralus/usages", "2025-06-01")
    rest("iot-usages", "/providers/Microsoft.Devices/usages", "2023-06-30")
    az("network-usages", ["network", "list-usages", "--location", "centralus"])


def support() -> None:
    namespaces = [
        "Microsoft.Web", "Microsoft.Storage", "Microsoft.Devices", "Microsoft.CognitiveServices",
        "Microsoft.Network", "Microsoft.ManagedIdentity", "Microsoft.OperationalInsights",
        "Microsoft.Insights", "Microsoft.Authorization", "Microsoft.Resources",
    ]
    for namespace in namespaces:
        az("provider-" + namespace, ["provider", "show", "--namespace", namespace])
    az("group-exists", ["group", "exists", "--name", "rg-equip-ai"])
    az("vnet-prefixes", ["network", "vnet", "list", "--query", "[].{name:name,prefixes:addressSpace.addressPrefixes}"])
    rest("arm-permissions", "/providers/Microsoft.Authorization/permissions", "2022-04-01")
    az("foundry-roles", ["role", "definition", "list", "--query", "[?starts_with(roleName, 'Foundry')]"])
    az("policy-assignments", [
        "policy", "assignment", "list", "--scope", f"/subscriptions/{SUBSCRIPTION}",
        "--disable-scope-strict-match",
    ])
    definitions = set()
    for index, assignment in enumerate(load("policy-assignments")):
        definition = assignment["policyDefinitionId"]
        if az(f"policy-definition-{index}", [
            "rest", "--method", "get", "--url",
            "https://management.azure.com" + definition, "--url-parameters", "api-version=2023-04-01",
        ]) == 0:
            definitions.update(
                item["policyDefinitionId"]
                for item in load(f"policy-definition-{index}").get("properties", {}).get("policyDefinitions", [])
            )
    for index, definition in enumerate(sorted(definitions)):
        az(f"policy-rule-{index}", [
            "rest", "--method", "get", "--url",
            "https://management.azure.com" + definition, "--url-parameters", "api-version=2023-04-01",
        ])


def preview() -> int:
    # Compile current source; never reuse a historical deployment template.
    code = run("bicep-build", [
        AZ, "bicep", "build", "--file", str(SCENARIO / "infra/main.bicep"),
        "--outfile", str(DIRECTORY / "main.json"),
    ])
    if code:
        return code
    source = (DIRECTORY / "main.json").read_bytes()
    template = json.loads(source)
    del template["resources"]["runtimeConfiguration"]
    template.pop("outputs", None)
    template.pop("metadata", None)
    del template["parameters"]["apiClientId"]
    del template["parameters"]["spaClientId"]
    roles = {item["roleName"]: item["name"] for item in load("foundry-roles")}
    values = {
        "environment": "equip-ai", "location": "centralus", "tenantId": TENANT, "principalId": "",
        "agentConsumerRoleId": roles["Foundry Agent Consumer"],
        "agentRuntimeRoleId": roles["Foundry Project Runtime User"],
        "agentInstallerRoleId": roles["Foundry User"],
        "modelName": "gpt-4.1-mini", "modelVersion": "2025-04-14",
        "modelDeploymentName": "equip-support", "modelSku": "GlobalStandard", "modelCapacity": 10,
        "vnetPrefix": "10.247.0.0/24", "integrationPrefix": "10.247.0.0/26",
        "endpointPrefix": "10.247.0.64/26",
    }
    assert set(template["parameters"]) <= values.keys()
    save("independent-preview", {
        "$schema": "https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#",
        "languageVersion": "2.0", "contentVersion": "1.0.0.0",
        "resources": {
            "targetGroup": {
                "type": "Microsoft.Resources/resourceGroups", "apiVersion": "2024-03-01",
                "name": "rg-equip-ai", "location": "centralus",
                "tags": {"Environment": "equip-ai", "ManagedBy": "Bicep", "Project": "equip-ai",
                         "SecurityControl": "Ignore"},
            },
            "independentReference": {
                "type": "Microsoft.Resources/deployments", "apiVersion": "2025-04-01",
                "name": "equip-ai-independent-preview", "resourceGroup": "rg-equip-ai",
                "dependsOn": ["targetGroup"],
                "properties": {
                    "mode": "Incremental", "expressionEvaluationOptions": {"scope": "inner"},
                    "template": template, "parameters": {key: {"value": values[key]} for key in template["parameters"]},
                },
            },
        },
    })
    save("preview-coverage", {
        "sourceSha256": hashlib.sha256(source).hexdigest(), "partial": True,
        "excludedSymbolicResources": ["runtimeConfiguration"],
        "retainedSymbolicResources": list(template["resources"]),
        "identityPlaceholdersUsed": False, "exactFullReferenceWhatIfPassed": False,
        "principalId": "", "installerAssignmentsOmittedIntentionally": True,
        "excludedChecks": [
            "Runtime appsettings with Entra client IDs; historical IDs not treated as verified.",
            "Installer-specific assignments; principalId intentionally empty, not an invented principal.",
            "Graph operations, identity propagation, private publishing, initialization and runtime tests.",
        ],
    })
    return az("independent-whatif", [
        "deployment", "sub", "what-if", "--name", "equip-ai-readonly-20261024T2240Z",
        "--location", "centralus", "--template-file", str(DIRECTORY / "independent-preview.json"),
        "--no-pretty-print",
    ])


if __name__ == "__main__":
    assert AZ and AZD, "Use existing tools only."
    stage = sys.argv[1]
    if stage == "preview":
        raise SystemExit(preview())
    {"identity": identity, "quotas": quotas, "support": support}[stage]()
