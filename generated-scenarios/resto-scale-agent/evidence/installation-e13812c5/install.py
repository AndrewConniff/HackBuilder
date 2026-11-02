"""Execute only the consolidated exact-target reference installation and retain actual evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))
from azure_context import infrastructure_fingerprint

SPEC = importlib.util.spec_from_file_location("saved_preparation", RUN.parent / "centralus-91633e9e" / "prepare.py")
PREPARATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARATION)
PREPARATION.RUN = RUN
PREPARATION.COLLECTOR.RUN = RUN
SCOPE = PREPARATION.SCOPE
SUBSCRIPTION = SCOPE["subscriptionId"]
GROUP = SCOPE["resourceGroup"]
EXPECTED_HASH = "2371ff53fd0c9ff35ca3e337f30911f0bd4b4bf019dcd27f13cb0456dfb25ed7"


def write(name: str, value: object) -> None:
    (RUN / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def command(name: str, arguments: list[str], timeout: int = 240, cwd: Path = SCENARIO) -> dict:
    if (RUN / f"{name}.json").exists():
        raise FileExistsError(f"Preserve the previous command evidence: {name}")
    executable = shutil.which(arguments[0])
    if executable is None:
        raise RuntimeError(f"Required executable is unavailable: {arguments[0]}")
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(
        [executable, *arguments[1:]], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, check=False,
    )
    record = {
        "command": subprocess.list2cmdline(arguments), "cwd": str(cwd), "startedAtUtc": started,
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "exitCode": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
    }
    for suffix, content in (("stdout", result.stdout), ("stderr", result.stderr)):
        (RUN / f"{name}.{suffix}.txt").write_text(content, encoding="utf-8")
    if result.returncode == 0 and result.stdout.strip():
        try:
            record["result"] = json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    write(name, record)
    print(json.dumps({"name": name, "exitCode": result.returncode, "stderr": result.stderr[:1000]}), flush=True)
    if result.returncode:
        raise RuntimeError(f"Command failed; stop and inspect {name}.json without retry or alternate execution.")
    return record


def azure(name: str, arguments: list[str]) -> object:
    return command(name, ["az", *arguments])["result"]


def preflight() -> None:
    if infrastructure_fingerprint(SCENARIO) != EXPECTED_HASH:
        raise ValueError("Infrastructure differs from the reviewed consolidated grant.")
    write("authorization-scope", {"scope": SCOPE, "decisionId": "3f3d19a20079404991c95dfe6d23b93f"})
    PREPARATION.collect()
    for name in (
        "identity", "group-exists", "providers", "features", "cosmos-locations", "model-quota",
        "model-eligibility", "model-capacity", "foundry-skus", "aca-usage", "aca-profiles",
        "servicebus-skus", "network-usage", "region-zones", "policy", "rbac",
    ):
        if read(name)["exitCode"] != 0 or "result" not in read(name):
            raise RuntimeError(f"Exact-target preparation failed: {name}")
    if read("group-exists")["result"] is not False:
        raise ValueError("Group now exists; review ownership and actual incremental changes before writes.")
    operator = azure("operator", [
        "rest", "--subscription", SUBSCRIPTION, "--method", "get",
        "--url", "https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName", "--output", "json",
    ])
    if operator["id"] != "214d672b-df87-4f3b-94fd-7863032546c1":
        raise ValueError("Current operator differs from the authorized assignment principal.")
    command("azd-auth", ["azd", "auth", "login", "--check-status", "--no-prompt"])
    values = command("azd-environment", [
        "azd", "env", "get-values", "--environment", SCOPE["environment"], "--output", "json",
    ])["result"]
    for key, value in (
        ("AZURE_ENV_NAME", SCOPE["environment"]), ("AZURE_SUBSCRIPTION_ID", SUBSCRIPTION),
        ("AZURE_TENANT_ID", SCOPE["tenantId"]), ("AZURE_RESOURCE_GROUP", GROUP),
        ("AZURE_LOCATION", SCOPE["region"]), ("AZURE_PRINCIPAL_ID", operator["id"]),
        ("FOUNDRY_MODEL_NAME", "gpt-5.4-mini"), ("FOUNDRY_MODEL_VERSION", "2026-03-17"),
        ("FOUNDRY_MODEL_DEPLOYMENT_TYPE", "GlobalStandard"),
    ):
        if values.get(key) != value:
            raise ValueError(f"Isolated azd environment mismatch: {key}")
    command("docker-engine", ["docker", "info", "--format", "{{json .OSType}}"])
    if read("docker-engine").get("result") != "linux":
        raise ValueError("A running Linux Docker engine is required.")
    for name, provider, body, version in (
        ("vault", "Microsoft.KeyVault", {"name": "kv-resto-dc9a173f4d0b5f6", "type": "Microsoft.KeyVault/vaults"},
         "2024-11-01"),
        ("foundry", "Microsoft.CognitiveServices",
         {"subdomainName": "ai-resto-6f6767a4ef6b5c6bb82c4a11edebfdec",
          "type": "Microsoft.CognitiveServices/accounts", "kind": "AIServices"}, "2024-10-01"),
    ):
        write(f"{name}-name-request", body)
        result = azure(f"{name}-name-availability", [
            "rest", "--subscription", SUBSCRIPTION, "--method", "post",
            "--url", f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/{provider}/"
            f"{'checkNameAvailability' if name == 'vault' else 'checkDomainAvailability'}?api-version={version}",
            "--body", f"@{RUN / f'{name}-name-request.json'}",
            "--headers", "Content-Type=application/json", "--output", "json",
        ])
        if result.get("nameAvailable" if name == "vault" else "isSubdomainAvailable") is not True:
            raise ValueError(f"Required scenario-owned {name} name is unavailable.")
    command("bicep-build", [
        "az", "bicep", "build", "--file", str(SCENARIO / "infra" / "main.bicep"),
        "--outfile", str(RUN / "main.arm.json"),
    ])
    command("bicep-lint", ["az", "bicep", "lint", "--file", str(SCENARIO / "infra" / "main.bicep")])
    document = json.loads((RUN.parent / "repair-6f748869" / "preview-full.arm.json").read_text())
    deployment = document["resources"][1]
    deployment["name"] = "resto-installation-e13812c5"
    deployment["properties"]["template"] = read("main.arm")
    deployment["properties"]["parameters"]["guestSigningKeyExpiration"]["value"] = (
        datetime.now(timezone.utc) + timedelta(days=180)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    write("preview-full.arm", document)
    preview = azure("what-if-full", [
        "deployment", "sub", "what-if", "--subscription", SUBSCRIPTION, "--location", SCOPE["region"],
        "--name", "resto-installation-e13812c5", "--template-file", str(RUN / "preview-full.arm.json"),
        "--no-pretty-print", "--output", "json",
    ])
    counts = Counter(item["changeType"] for item in preview["changes"])
    if preview["status"] != "Succeeded" or counts != {"Create": 33, "Unsupported": 13}:
        raise ValueError(f"Preview differs from the reviewed grant: {dict(counts)}")
    write("preview-counts", dict(counts))


def provision() -> None:
    if infrastructure_fingerprint(SCENARIO) != EXPECTED_HASH:
        raise ValueError("Infrastructure differs from the reviewed consolidated grant.")
    if read("preview-counts") != {"Create": 33, "Unsupported": 13}:
        raise ValueError("Exact repaired preview has not passed.")
    providers = {item["namespace"].casefold(): item["registrationState"] for item in read("providers")["result"]}
    for name in (
        "Microsoft.Resources", "Microsoft.App", "Microsoft.CognitiveServices", "Microsoft.DocumentDB",
        "Microsoft.ServiceBus", "Microsoft.KeyVault", "Microsoft.ManagedIdentity", "Microsoft.Network",
        "Microsoft.ContainerRegistry", "Microsoft.Insights", "Microsoft.OperationalInsights", "Microsoft.Authorization",
    ):
        if providers.get(name.casefold()) != "Registered":
            raise ValueError(f"Provider not registered; registration is not authorized: {name}")
    cosmos = next(item["properties"] for item in read("cosmos-locations")["result"] if item["name"] == "Central US")
    if (cosmos["status"] != "Online" or cosmos["isSubscriptionRegionAccessAllowedForAz"] is not True
            or cosmos["isSubscriptionRegionAccessAllowedForRegular"] is not True):
        raise ValueError("Required Cosmos regional access is not available.")
    quota = next(item for item in read("model-quota")["result"]
                 if item["name"]["value"] == "OpenAI.GlobalStandard.gpt-5.4-mini")
    if quota["currentValue"] + 100 > quota["limit"]:
        raise ValueError("Model quota cannot cover the installation.")
    capacity = next(item["properties"] for item in read("model-capacity")["result"]["value"]
                    if item["name"] == "GlobalStandard")
    if capacity["availableCapacity"] < 100:
        raise ValueError("Model metadata cannot cover the requested capacity.")
    eligible = [item for item in read("model-eligibility")["result"]
                if item.get("model", {}).get("name") == "gpt-5.4-mini"
                and item["model"].get("version") == "2026-03-17"]
    if not eligible:
        raise ValueError("Exact model/version is absent from current regional eligibility.")
    environments = next(item for item in read("aca-usage")["result"]["value"]
                        if item["name"]["value"] == "ManagedEnvironmentCount")
    networks = next(item for item in read("network-usage")["result"]
                    if item["name"]["value"] == "VirtualNetworks")
    for item in (environments, networks):
        if int(item["currentValue"]) + 1 > int(item["limit"]):
            raise ValueError("Environment or VNet count quota is insufficient.")
    if not any(item["roleDefinitionId"].rsplit("/", 1)[-1] == "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
               for item in read("rbac")["result"]):
        raise ValueError("Reviewed deployment Owner grant no longer exists.")
    write("preflight-summary", {
        "scope": SCOPE, "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "infrastructureFingerprint": EXPECTED_HASH, "whatIfCounts": read("preview-counts"),
        "cosmosZonalAccess": True, "modelQuota": quota, "modelCapacity": capacity,
        "limitations": "Metadata cannot reserve allocation. Directory capability, installed environment cores, "
        "output-dependent grants and runtime acceptance remain pending. Current reviewed costs unchanged.",
    })
    absent = azure("group-exists-before-write", [
        "group", "exists", "--subscription", SUBSCRIPTION, "--name", GROUP, "--output", "json",
    ])
    if absent is not False:
        raise ValueError("Group appeared during preparation; ownership review required.")
    wrapper = read("preview-full.arm")
    tags = wrapper["resources"][0].get("tags")
    if not tags or tags.get("Project") != "resto-scale-agent":
        raise ValueError("Reviewed resource-group ownership tags are missing.")
    group = azure("group-created", [
        "group", "create", "--subscription", SUBSCRIPTION, "--name", GROUP, "--location", SCOPE["region"],
        "--tags", *[f"{key}={value}" for key, value in tags.items()], "--output", "json",
    ])
    if group["location"] != SCOPE["region"] or group.get("tags") != tags:
        raise ValueError("Created group does not match reviewed ownership/location.")
    command("azd-provision", [
        "azd", "provision", "--environment", SCOPE["environment"], "--subscription", SUBSCRIPTION,
        "--location", SCOPE["region"], "--cwd", str(SCENARIO), "--no-prompt",
    ], timeout=1800)
    azure("deployments-after-provision", [
        "deployment", "group", "list", "--subscription", SUBSCRIPTION, "--resource-group", GROUP,
        "--query", "[].{name:name,state:properties.provisioningState,outputs:properties.outputs}",
        "--output", "json",
    ])
    azure("resources-after-provision", [
        "resource", "list", "--subscription", SUBSCRIPTION, "--resource-group", GROUP, "--output", "json",
    ])


def identity() -> None:
    if read("azd-provision")["exitCode"] != 0:
        raise ValueError("Stop after a failed provision; directory work must not continue.")
    command("identity-install", [
        "python", str(SCENARIO / "scripts" / "setup_identity.py"),
        "--scope", str(SCENARIO / "evidence" / "identity-install-scope.json"),
        "--receipt", str(SCENARIO / "evidence" / "identity-installation.json"),
        "--authorize-directory-install",
    ], timeout=600)


def capture() -> None:
    deployments = read("deployments-after-provision")["result"]
    roots = [item for item in deployments if item["name"].startswith("resto-scale-agent-")]
    if len(roots) != 1 or any(item["state"] != "Succeeded" for item in deployments):
        raise ValueError("Shared installation contains a failed/ambiguous deployment.")
    outputs = {key.upper(): value for key, value in roots[0]["outputs"].items()}
    write("infrastructure-outputs", outputs)
    usage = azure("environment-usage", [
        "containerapp", "env", "list-usages", "--subscription", SUBSCRIPTION,
        "--resource-group", GROUP, "--name", outputs["AZURE_CONTAINER_APPS_ENVIRONMENT_NAME"]["value"],
        "--output", "json",
    ])
    entries = usage.get("value", []) if isinstance(usage, dict) else usage
    cores = next(item for item in entries if item["name"]["value"] == "ManagedEnvironmentConsumptionCores")
    if cores["currentValue"] + 28 > cores["limit"]:
        raise ValueError("Actual environment quota cannot cover the reviewed 28 rollout vCPU.")
    for name, arguments in {
        "project": [
            "rest", "--method", "get", "--subscription", SUBSCRIPTION,
            "--url", "https://management.azure.com" + outputs["FOUNDRY_PROJECT_ID"]["value"]
            + "?api-version=2025-06-01", "--output", "json",
        ],
        "cosmos-installed-grants": [
            "cosmosdb", "sql", "role", "assignment", "list", "--subscription", SUBSCRIPTION,
            "--resource-group", GROUP, "--account-name", "cosmos-resto-4tvlzr5zf2rxi", "--output", "json",
        ],
        "vault-installed": [
            "keyvault", "show", "--subscription", SUBSCRIPTION, "--resource-group", GROUP,
            "--name", "kv-resto-dc9a173f4d0b5f6", "--output", "json",
        ],
    }.items():
        azure(name, arguments)


def operator_access() -> None:
    command("operator-access-owned-principal", ["python", str(RUN / "operator_access.py")], timeout=600)


def reconcile() -> None:
    receipt = json.loads((SCENARIO / "evidence" / "identity-installation.json").read_text())
    for kind in ("api", "client"):
        azure(f"{kind}-assignments-final", [
            "rest", "--subscription", SUBSCRIPTION, "--method", "get",
            "--url", f"https://graph.microsoft.com/v1.0/servicePrincipals/"
            f"{receipt[kind]['servicePrincipalId']}/appRoleAssignedTo", "--output", "json",
        ])
        azure(f"{kind}-principal-final", [
            "rest", "--subscription", SUBSCRIPTION, "--method", "get",
            "--url", f"https://graph.microsoft.com/v1.0/servicePrincipals/{receipt[kind]['servicePrincipalId']}",
            "--output", "json",
        ])
    from urllib.parse import urlencode

    query = urlencode({"$filter": f"clientId eq '{receipt['client']['servicePrincipalId']}' "
                       f"and resourceId eq '{receipt['api']['servicePrincipalId']}'"})
    azure("consent-final", [
        "rest", "--subscription", SUBSCRIPTION, "--method", "get",
        "--url", "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?" + query, "--output", "json",
    ])
    azure("resources-final", [
        "resource", "list", "--subscription", SUBSCRIPTION, "--resource-group", GROUP, "--output", "json",
    ])
    azure("deployment-final", [
        "deployment", "group", "show", "--subscription", SUBSCRIPTION, "--resource-group", GROUP,
        "--name", next(item["name"] for item in read("deployments-after-provision")["result"]
                       if item["name"].startswith("resto-scale-agent-")), "--output", "json",
    ])
    write("operator-consent-request", {
        "clientId": receipt["client"]["servicePrincipalId"], "consentType": "Principal",
        "principalId": "214d672b-df87-4f3b-94fd-7863032546c1",
        "resourceId": receipt["api"]["servicePrincipalId"], "scope": "access_as_user",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("preflight", "provision", "identity", "capture", "operator-access", "reconcile"),
    )
    args = parser.parse_args()
    {"preflight": preflight, "provision": provision, "identity": identity,
     "capture": capture, "operator-access": operator_access, "reconcile": reconcile}[args.operation]()
