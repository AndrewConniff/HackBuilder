"""Install the private reference through azd provision only after exact canonical deployment consent."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INSTALLATION = ROOT / ".installation"
SCOPE_VARIABLES = {
    "account": "AZURE_ACCOUNT",
    "subscriptionId": "AZURE_SUBSCRIPTION_ID",
    "tenantId": "AZURE_TENANT_ID",
    "resourceGroup": "AZURE_RESOURCE_GROUP",
    "environment": "AZURE_ENV_NAME",
    "region": "AZURE_LOCATION",
}


def execute(command: list[str], *, timeout: int = 1200) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        raise FileNotFoundError(f"Required tool unavailable: {command[0]}")
    result = subprocess.run(
        [executable, *command[1:]], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"{command[0]} {command[1]} failed ({result.returncode}): {result.stderr[-4000:]}")
    return result.stdout.strip()


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing explicit installation setting: {name}")
    return value


def authorize(project: dict, settings: dict[str, str], hostname: str) -> dict:
    if project.get("projectSlug") != "manu-multi-agent" or not project.get("designConfirmed"):
        raise ValueError("The same reference and recorded design confirmation are required.")
    if project.get("writer") != settings.get("ABCBUILDER_RUN_ID"):
        raise ValueError("Installation must run under the current project writer lease.")
    if project.get("stages", {}).get("local-validation", {}).get("status") != "completed":
        raise ValueError("Complete current local validation before deployment.")
    targets = {key: settings.get(variable) for key, variable in SCOPE_VARIABLES.items()}
    if not all(targets.values()) or targets["resourceGroup"] != f"rg-{targets['environment']}":
        raise ValueError("Explicit exact targets and the matching rg-{environment} are required.")
    for grant in reversed(project.get("authorizations", [])):
        scope = grant.get("scope", {})
        if grant.get("kind") == "deployment" and all(scope.get(key) == value for key, value in targets.items()):
            if not scope.get("whatIfEvidence") or not scope.get("estimatedCost"):
                raise ValueError("Actual what-if and itemized cost review are required.")
            if scope.get("directoryWrites") != "scenario-owned-secretless-backend-api":
                raise ValueError("The consolidated deployment grant must cover backend application/SP installation.")
            if scope.get("privateExecutionHost", "").casefold() != hostname.casefold():
                raise ValueError("Use the connected execution host named in the consolidated authorization.")
            return grant
    raise ValueError("No exact-target deployment authorization. Free text or preparation consent is insufficient.")


def guard() -> dict:
    helper = Path(required("ABCBUILDER_WORKFLOW_HELPER"))
    if helper.name != "portal_workflow.py" or not helper.is_file():
        raise ValueError("Configure the existing canonical portal_workflow.py helper, not a copied state file.")
    settings = dict(os.environ)
    settings["ABCBUILDER_RUN_ID"] = (
        os.environ.get("ABCBUILDER_RUN_ID") or required("HACKBUILDER_RUN_ID")
    )
    project = json.loads(execute([sys.executable, str(helper), "read"]))
    grant = authorize(project, settings, socket.gethostname())
    subscription = required("AZURE_SUBSCRIPTION_ID")
    account = json.loads(execute(["az", "account", "show", "--subscription", subscription, "--output", "json"]))
    if (
        account.get("id") != subscription or account.get("tenantId") != required("AZURE_TENANT_ID")
        or account.get("user", {}).get("name") != required("AZURE_ACCOUNT")
        or account.get("user", {}).get("type") != "user"
    ):
        raise ValueError("CLI identity differs from the authorized user/tenant/subscription; defaults unchanged.")
    status = execute(["azd", "auth", "login", "--check-status", "--no-prompt"])
    signed_in = re.search(r"Logged in to Azure as ([^\r\n]+)", status)
    if not signed_in or signed_in[1].strip().casefold() != required("AZURE_ACCOUNT").casefold():
        raise ValueError("Azure CLI and azd must identify the same authorized account; defaults unchanged.")
    principal = json.loads(execute([
        "az", "ad", "signed-in-user", "show", "--subscription", subscription,
        "--query", "{id:id}", "--output", "json",
    ]))
    if principal.get("id") != required("AZURE_PRINCIPAL_ID"):
        raise ValueError("The installer principal differs from the authorized preparation output.")
    return grant


def save(name: str, value: dict) -> None:
    INSTALLATION.mkdir(exist_ok=True)
    (INSTALLATION / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def set_values(values: dict[str, str]) -> None:
    for key, value in values.items():
        if not value:
            raise ValueError(f"Missing generated installation output: {key}")
        execute(["azd", "env", "set", key, value, "--environment", required("AZURE_ENV_NAME")])
        os.environ[key] = value


def before() -> None:
    guard()
    required("APIM_PUBLISHER_EMAIL")
    execute([
        "pwsh", "-NoProfile", "-File", str(ROOT / "scripts" / "Initialize-BackendIdentity.ps1"),
        "-TenantId", required("AZURE_TENANT_ID"), "-SubscriptionId", required("AZURE_SUBSCRIPTION_ID"),
        "-Account", required("AZURE_ACCOUNT"), "-AuthorizedDirectoryWrites", "-Confirm:$false",
    ])
    identity = json.loads((INSTALLATION / "backend-identity.json").read_text(encoding="utf-8-sig"))
    if (
        identity["tenantId"] != required("AZURE_TENANT_ID")
        or identity["subscriptionId"] != required("AZURE_SUBSCRIPTION_ID")
    ):
        raise ValueError("Backend identity output targets do not match.")
    previous = INSTALLATION / "workload.parameters.json"
    if previous.exists():
        parameters = json.loads(previous.read_text(encoding="utf-8"))["parameters"]
        for field, variable in {
            "environment": "AZURE_ENV_NAME", "location": "AZURE_LOCATION", "principalId": "AZURE_PRINCIPAL_ID",
        }.items():
            if parameters[field]["value"] != required(variable):
                raise ValueError("Existing workload receipt belongs to different targets.")
        if parameters["backendClientId"]["value"] != identity["backendClientId"]:
            raise ValueError("Installed backend identity changed; review before redeployment.")
        set_values({
            variable: parameters[field]["value"] for field, variable in workload_variables().items()
        } | {"DEPLOYMENT_PHASE": "workload"})
    else:
        set_values({"BACKEND_CLIENT_ID": identity["backendClientId"], "DEPLOYMENT_PHASE": "foundation"})


def workload_variables() -> dict[str, str]:
    return {
        "backendClientId": "BACKEND_CLIENT_ID", "consumerRoleDefinitionId": "FOUNDRY_CONSUMER_ROLE_ID",
        "imageDigest": "APP_IMAGE_SHA256", "salesAgentVersion": "SALES_AGENT_VERSION",
        "marketingAgentVersion": "MARKETING_AGENT_VERSION", "coordinatorAgentVersion": "COORDINATOR_AGENT_VERSION",
        "fixtureManifestHash": "FIXTURE_MANIFEST_SHA256", "signingKeyVersion": "SIGNING_KEY_VERSION",
    }


def private_tls(endpoint: str) -> dict:
    hostname = urlparse(endpoint).hostname
    if not hostname:
        raise ValueError("A real foundation endpoint is required.")
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)})
    private_ranges = tuple(ipaddress.ip_network(value) for value in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7",
    ))
    if not addresses or not all(
        any(ipaddress.ip_address(value) in network for network in private_ranges) for value in addresses
    ):
        raise ValueError(f"{hostname} does not resolve exclusively to private addresses: {addresses}")
    with socket.create_connection((hostname, 443), timeout=15) as connection:
        with ssl.create_default_context().wrap_socket(connection, server_hostname=hostname) as secured:
            return {"hostname": hostname, "addresses": addresses, "tls": secured.version()}


def after() -> None:
    grant = guard()
    values = json.loads(execute([
        "azd", "env", "get-values", "--environment", required("AZURE_ENV_NAME"), "--output", "json",
    ]))
    for key in (
        "AZURE_AI_PROJECT_ENDPOINT", "AZURE_AI_MODEL_DEPLOYMENT", "FIXTURE_BLOB_ENDPOINT",
        "SIGNING_KEY_URI", "AZURE_CONTAINER_REGISTRY_NAME", "AZURE_CONTAINER_REGISTRY_ENDPOINT",
    ):
        if not isinstance(values.get(key), str) or not values[key]:
            raise ValueError(f"Foundation did not return {key}.")
    endpoints = [
        values["AZURE_AI_PROJECT_ENDPOINT"], values["FIXTURE_BLOB_ENDPOINT"], values["SIGNING_KEY_URI"],
        "https://" + values["AZURE_CONTAINER_REGISTRY_ENDPOINT"],
        f"https://{values['AZURE_CONTAINER_REGISTRY_NAME']}.{required('AZURE_LOCATION')}.data.azurecr.io",
    ]
    save("private-connectivity.json", {
        "executionHost": socket.gethostname(), "checks": [private_tls(endpoint) for endpoint in endpoints],
        "limitation": "DNS/TLS only. Authenticated installer operations follow; this is not runtime acceptance.",
    })
    subscription = required("AZURE_SUBSCRIPTION_ID")
    roles = json.loads(execute([
        "az", "role", "definition", "list", "--name", "Foundry Agent Consumer",
        "--subscription", subscription, "--output", "json",
    ]))
    if len(roles) != 1 or roles[0].get("roleType") != "BuiltInRole":
        raise ValueError("Resolve the exact built-in Foundry Agent Consumer role; no broader fallback.")
    role_id = roles[0]["name"]
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", role_id):
        raise ValueError("Invalid consumer role output.")
    image = "abcbuilder-manu-multi-agent:authorized-installation"
    execute([
        "docker", "build", "--platform", "linux/amd64", "--tag", image,
        "--file", str(ROOT / "src" / "MobilityCommercial.Web" / "Dockerfile"), ".",
    ])
    inspected = json.loads(execute(["docker", "image", "inspect", image]))[0]
    if (
        inspected["Os"] != "linux" or inspected["Architecture"] != "amd64"
        or inspected["Config"]["User"] != "1654"
    ):
        raise ValueError("Production image must retain Linux amd64 and nonroot user 1654.")
    registry = values["AZURE_CONTAINER_REGISTRY_ENDPOINT"]
    tag = f"{registry}/mobility-commercial:{inspected['Id'].removeprefix('sha256:')}"
    execute([
        "az", "acr", "login", "--name", values["AZURE_CONTAINER_REGISTRY_NAME"],
        "--subscription", subscription,
    ])
    execute(["docker", "tag", image, tag])
    execute(["docker", "push", tag])
    published = json.loads(execute(["docker", "image", "inspect", tag]))[0]
    digests = [
        value.split("@sha256:", 1)[1] for value in published["RepoDigests"]
        if value.startswith(f"{registry}/mobility-commercial@sha256:")
    ]
    if len(digests) != 1 or not re.fullmatch(r"[0-9a-f]{64}", digests[0]):
        raise ValueError("Registry push did not return one immutable image digest.")
    os.environ.update({
        "FOUNDRY_PROJECT_ENDPOINT": values["AZURE_AI_PROJECT_ENDPOINT"],
        "FOUNDRY_MODEL_DEPLOYMENT": values["AZURE_AI_MODEL_DEPLOYMENT"],
        "FIXTURE_BLOB_ENDPOINT": values["FIXTURE_BLOB_ENDPOINT"], "SIGNING_KEY_URI": values["SIGNING_KEY_URI"],
    })
    execute([
        "dotnet", "run", "--project", str(ROOT / "tools" / "MobilityCommercial.Installer"),
        "--no-restore", "--", "--execute-authorized-installation", str(ROOT),
    ])
    installed = json.loads((INSTALLATION / "installation.json").read_text(encoding="utf-8"))
    identity = json.loads((INSTALLATION / "backend-identity.json").read_text(encoding="utf-8-sig"))
    if installed["tenantId"] != required("AZURE_TENANT_ID") or installed["subscriptionId"] != subscription:
        raise ValueError("Installation outputs do not match the authorized targets.")
    agents = {agent["name"]: agent for agent in installed["agents"]}
    parameters = {
        "environment": required("AZURE_ENV_NAME"), "location": required("AZURE_LOCATION"),
        "principalId": required("AZURE_PRINCIPAL_ID"), "deploymentPhase": "workload",
        "publisherEmail": required("APIM_PUBLISHER_EMAIL"), "backendClientId": identity["backendClientId"],
        "consumerRoleDefinitionId": role_id, "imageDigest": digests[0],
        "salesAgentVersion": agents["sales-fit"]["version"],
        "marketingAgentVersion": agents["marketing-claims"]["version"],
        "coordinatorAgentVersion": agents["handoff-coordinator"]["version"],
        "fixtureManifestHash": installed["fixtureManifestSha256"], "signingKeyVersion": installed["signingKeyVersion"],
    }
    save("workload.parameters.json", {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
        "contentVersion": "1.0.0.0", "parameters": {key: {"value": value} for key, value in parameters.items()},
    })
    guard()
    result = json.loads(execute([
        "az", "deployment", "group", "create", "--subscription", subscription,
        "--resource-group", required("AZURE_RESOURCE_GROUP"), "--name", "manu-multi-agent-reference",
        "--template-file", str(ROOT / "infra" / "main.bicep"),
        "--parameters", "@" + str(INSTALLATION / "workload.parameters.json"), "--output", "json",
    ]))
    if result["properties"]["provisioningState"] != "Succeeded":
        raise ValueError("Workload provisioning did not succeed.")
    outputs = result["properties"]["outputs"]
    set_values({key: parameters[field] for field, key in workload_variables().items()} | {
        "DEPLOYMENT_PHASE": "workload", "AZURE_CONTAINER_APP_NAME": outputs["AZURE_CONTAINER_APP_NAME"]["value"],
        "APP_PUBLIC_URL": outputs["APP_PUBLIC_URL"]["value"],
    })
    save("deployment.json", {
        "recordedAtUtc": datetime.now(timezone.utc).isoformat(), "decisionId": grant["decisionId"],
        "scope": grant["scope"], "imageDigest": digests[0], "outputs": outputs,
        "liveAcceptance": "pending",
    })
    print("Reference provisioned; live model/agent/application/negative acceptance remains required.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["before", "after", "reject-default-deploy"])
    args = parser.parse_args()
    try:
        if args.phase == "reject-default-deploy":
            raise ValueError("Use authorized azd provision --environment <exact-env>; hooks install the complete "
                             "digest-pinned reference. Default azd up/deploy/publish would independently roll out "
                             "or publish the source image.")
        (before if args.phase == "before" else after)()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Installation blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
