"""Run the approved reference runtime installation after azd shared provisioning, without additional approval stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from prepare_runtime import parameters
from setup_identity import Installer, callback, consume, verify_access

ROOT = Path(__file__).resolve().parents[1]
TARGET_KEYS = ("account", "subscriptionId", "tenantId", "resourceGroup", "environment", "region")


def authorized_scope(state: dict, plan_digest: str) -> dict:
    """Require current canonical exact-target authorization, never an old file, flag or free-text answer."""
    if (state.get("projectSlug") != ROOT.name or not state.get("writer")
            or state["writer"] != (os.environ.get("ABCBUILDER_RUN_ID") or os.environ.get("HACKBUILDER_RUN_ID"))
            or state.get("stages", {}).get("local-validation", {}).get("status") != "completed"):
        raise PermissionError("The current canonical scenario writer and completed local validation are required.")
    grants = [entry for entry in state.get("authorizations", []) if entry.get("kind") == "deployment"
              and entry.get("scope", {}).get("installationPlanDigest") == plan_digest]
    if len(grants) != 1:
        raise PermissionError("One current exact-target deployment grant for this complete installation plan is required.")
    scope = grants[0]["scope"]
    if any(not isinstance(scope.get(key), str) or not scope[key] for key in TARGET_KEYS):
        raise ValueError("Incomplete canonical deployment target.")
    if scope["resourceGroup"] != f"rg-{scope['environment']}":
        raise ValueError("Canonical environment and resource group disagree.")
    return {key: scope[key] for key in TARGET_KEYS}


def run(arguments: list[str], *, environment: dict | None = None, timeout: int = 120) -> str:
    """Fail on actual command errors; do not change shared defaults, retry denied writes or print secret material."""
    executable = shutil.which(arguments[0])
    if not executable:
        raise RuntimeError(f"Required installed tool is unavailable: {arguments[0]}")
    result = subprocess.run([executable, *arguments[1:]], cwd=ROOT, env=environment,
                            capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{arguments[0]} {arguments[1]} failed ({result.returncode}): {result.stderr.strip()}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    state_directory = os.environ.get("ABCBUILDER_PROJECT_STATE") or os.environ.get("HACKBUILDER_PROJECT_STATE")
    if not state_directory:
        raise PermissionError("Run only from the authorized portal worker; no local file grants deployment permission.")
    helper = Path(state_directory).parents[1] / "scripts" / "portal_workflow.py"
    state = json.loads(run([sys.executable, str(helper), "read"]))
    plan = ROOT / "scripts" / "reference-installation-plan.json"
    scope = authorized_scope(state, hashlib.sha256(plan.read_bytes()).hexdigest())
    if args.verify_only:
        raise SystemExit("Use azd provision for the ordered immutable-image reference installation. "
                         "Plain azd deploy/up image replacement is intentionally blocked.")
    receipt_file = ROOT / "evidence" / "identity-installation.json"
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    consume(receipt, scope["tenantId"], scope["subscriptionId"], scope["environment"], scope["region"])
    if receipt["scope"] != scope:
        raise ValueError("Retained identity installation does not match the current canonical target.")
    installer = Installer(scope, receipt_file, authorized=True)
    objects = installer.inspect(receipt)
    env_values = json.loads(run(["azd", "env", "get-values", "--environment", scope["environment"], "--output", "json"]))
    for key, expected in (("AZURE_ENV_NAME", scope["environment"]), ("AZURE_RESOURCE_GROUP", scope["resourceGroup"]),
                          ("AZURE_SUBSCRIPTION_ID", scope["subscriptionId"]), ("AZURE_TENANT_ID", scope["tenantId"]),
                          ("AZURE_LOCATION", scope["region"])):
        if env_values.get(key) != expected:
            raise ValueError(f"Scenario-local azd target mismatch: {key}")
    commands = ["az", "deployment", "group", "list", "--subscription", scope["subscriptionId"],
                "--resource-group", scope["resourceGroup"], "--output", "json"]
    deployments = json.loads(run(commands))
    candidates = []
    for deployment in deployments:
        properties = deployment["properties"]
        outputs = {key.upper(): value for key, value in properties.get("outputs", {}).items()}
        if (properties.get("provisioningState") == "Succeeded"
                and outputs.get("AZURE_ENV_NAME", {}).get("value") == scope["environment"]
                and "RUNTIME_IDENTITIES" in outputs):
            candidates.append((properties["timestamp"], outputs))
    if not candidates:
        raise ValueError("No successful exact-scenario shared deployment output exists.")
    outputs = max(candidates, key=lambda item: item[0])[1]
    def value(name: str) -> str:
        result = outputs[name]["value"]
        if not isinstance(result, str) or not result:
            raise ValueError(f"Expected nonempty installed string output: {name}")
        return result
    for name, expected in (("AZURE_LOCATION", scope["region"]), ("AZURE_SUBSCRIPTION_ID", scope["subscriptionId"]),
                           ("AZURE_TENANT_ID", scope["tenantId"]), ("AZURE_RESOURCE_GROUP", scope["resourceGroup"])):
        if value(name) != expected:
            raise ValueError(f"Actual infrastructure target mismatch: {name}")
    application_url = f"https://ca-resto-web-{value('RESOURCE_SUFFIX')}.{value('AZURE_CONTAINER_APPS_ENVIRONMENT_DOMAIN')}"
    redirect = callback(application_url)
    run_id = (os.environ.get("ABCBUILDER_RUN_ID") or os.environ.get("HACKBUILDER_RUN_ID"))
    evidence = ROOT / "evidence" / f"runtime-installation-{run_id}"
    evidence.mkdir(exist_ok=True)

    def save(name: str, result: dict) -> None:
        (evidence / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if redirect not in objects["client"].get("spa", {}).get("redirectUris", []):
        installer.graph("patch", f"/applications/{receipt['client']['objectId']}",
                        {"spa": {"redirectUris": [*objects["client"].get("spa", {}).get("redirectUris", []), redirect]}})
        objects = installer.inspect(receipt)
    verification = verify_access(installer, receipt, objects, redirect)
    save("identity-verification", verification)
    if not verification["passed"]:
        raise PermissionError("Owned staff access is incomplete. Historical denied consent is not retried; "
                              "use the tenant-approved operator-only remediation and read-only verification.")
    usage = json.loads(run(["az", "containerapp", "env", "list-usages", "--subscription", scope["subscriptionId"],
                            "--resource-group", scope["resourceGroup"],
                            "--name", value("AZURE_CONTAINER_APPS_ENVIRONMENT_NAME"), "--output", "json"]))
    entries = usage["value"] if isinstance(usage, dict) else usage
    cores = next(entry for entry in entries if entry["name"]["value"] == "ManagedEnvironmentConsumptionCores")
    save("environment-core-quota", cores)
    if cores["currentValue"] + 28 > cores["limit"]:
        raise ValueError("Actual environment quota cannot cover the conservative 28-vCPU rollout.")
    engine = json.loads(run(["docker", "info", "--format", "{{json .OSType}}"]))
    if engine != "linux":
        raise RuntimeError("A responsive Linux Docker engine is required; no remote-build fallback is allowed.")
    registry = value("AZURE_CONTAINER_REGISTRY_NAME")
    tag = f"restaurant:reference-{uuid4().hex}"
    image_tag = f"{value('AZURE_CONTAINER_REGISTRY_ENDPOINT')}/{tag}"
    run(["docker", "build", "--platform", "linux/amd64", "--file", r"src\Restaurant.Web\Dockerfile",
         "--tag", image_tag, "."], timeout=1800)
    run(["az", "acr", "login", "--subscription", scope["subscriptionId"], "--name", registry])
    run(["docker", "push", image_tag], timeout=900)
    digest = json.loads(run(["az", "acr", "repository", "show", "--subscription", scope["subscriptionId"],
                             "--name", registry, "--image", tag, "--query", "digest", "--output", "json"]))
    image = f"{value('AZURE_CONTAINER_REGISTRY_ENDPOINT')}/restaurant@{digest}"
    project = json.loads(run(["az", "rest", "--subscription", scope["subscriptionId"], "--method", "get",
                              "--url", "https://management.azure.com" + value("FOUNDRY_PROJECT_ID")
                              + "?api-version=2025-06-01", "--output", "json"]))
    endpoints = project["properties"]["endpoints"]
    expected_endpoint = (f"https://{value('FOUNDRY_ACCOUNT_NAME')}.services.ai.azure.com/api/projects/"
                         + str(value("FOUNDRY_PROJECT_NAME")).rsplit("/", 1)[-1])
    matches = [entry for entry in endpoints.values() if entry.rstrip("/") == expected_endpoint]
    if len(matches) != 1:
        raise ValueError("Exactly one discovered endpoint must match this Foundry account/direct-child project.")
    endpoint = matches[0]
    versions_file = evidence / "agent-versions.json"
    initialize_env = os.environ | {
        "INITIALIZER_TENANT_ID": scope["tenantId"], "INITIALIZER_SUBSCRIPTION_ID": scope["subscriptionId"],
        "COSMOS_ENDPOINT": value("COSMOS_ENDPOINT"), "COSMOS_DATABASE": "restaurant",
        "FOUNDRY_PROJECT_ENDPOINT": endpoint, "FOUNDRY_MODEL_DEPLOYMENT": value("FOUNDRY_MODEL_DEPLOYMENT"),
        "AGENT_VERSIONS_OUTPUT": str(versions_file), "STAFF_AUTH_MODE": "entra", "APP_ROLE": "web",
        "ASPNETCORE_ENVIRONMENT": "Production",
    }
    run(["dotnet", "run", "--project", r"src\Restaurant.Web", "--no-launch-profile", "--",
         "--contentRoot", str(ROOT / "src" / "Restaurant.Web"), "--initialize"],
        environment=initialize_env, timeout=600)
    versions = json.loads(versions_file.read_text(encoding="utf-8"))
    runtime = parameters(outputs, versions, scope["environment"], scope["region"], image, endpoint,
                         scope["tenantId"], receipt, scope["subscriptionId"])
    save("runtime-parameters", runtime)
    arguments = ["--subscription", scope["subscriptionId"], "--resource-group", scope["resourceGroup"],
                 "--name", "restaurant-runtime", "--template-file", r"infra\runtime.bicep",
                 "--parameters", f"@{evidence / 'runtime-parameters.json'}"]
    preview = json.loads(run(["az", "deployment", "group", "what-if", *arguments, "--no-pretty-print",
                              "--output", "json"], timeout=600))
    save("runtime-what-if", preview)
    if preview.get("status") != "Succeeded" or any(
        entry.get("changeType") in ("Delete", "Unsupported") for entry in preview["changes"]
    ):
        raise ValueError("Runtime what-if has deletions or unresolved expansions; installation stopped before rollout.")
    installed = json.loads(run(["az", "deployment", "group", "create", *arguments, "--output", "json"], timeout=1800))
    save("runtime-deployment", installed)
    if installed["properties"]["provisioningState"] != "Succeeded":
        raise RuntimeError("Runtime deployment did not succeed.")
    save("installation", {"scope": scope, "image": image, "applicationUrl": application_url,
                           "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
                           "status": "installed-not-live-validated"})
    print("Reference installation completed. Real staff sign-in, model/agent, business, load and fault acceptance remain required.")


if __name__ == "__main__":
    main()
