"""Resolve private Azure target proposals from existing identity and local scenario evidence only."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from check_prerequisites import execution_environment

FIELDS = ("account", "subscriptionId", "tenantId", "environment", "resourceGroup", "region")


def infrastructure_fingerprint(scenario: Path) -> str:
    files = [scenario / "azure.yaml"]
    infra = scenario / "infra"
    if infra.is_dir():
        files.extend(sorted(path for path in infra.rglob("*") if path.is_file() and path.suffix in {
            ".bicep", ".bicepparam", ".json",
        }))
    digest = hashlib.sha256()
    for path in files:
        if not path.is_file() or not path.resolve().is_relative_to(scenario.resolve()):
            raise ValueError("Regional checks require infrastructure files inside this scenario.")
        digest.update(path.relative_to(scenario).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    if not infra.is_dir() or not any(path.suffix == ".bicep" for path in files):
        raise ValueError("Regional checks require the actual Bicep infrastructure.")
    return digest.hexdigest()


def validate_regional_readiness(scenario: Path, project: dict, scope: dict, services: list[str]) -> list[str]:
    """Gate cloud execution on recent scenario-bound subscription evidence, not public availability."""
    if not any(item["kind"] == "deployment-preparation" and item["scope"] == scope
               for item in project.get("authorizations", [])):
        raise ValueError("Subscription regional validation requires existing exact-target preparation authorization.")
    evidence_path = scenario / "00-region-availability.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    readiness = evidence.get("regionalReadiness")
    if not isinstance(readiness, dict) or readiness.get("scope") != scope:
        raise ValueError("Regional readiness needs actual subscription checks for this exact preparation scope.")
    if readiness.get("infrastructureFingerprint") != infrastructure_fingerprint(scenario):
        raise ValueError("Regional readiness is stale after infrastructure changes; refresh subscription checks.")
    try:
        checked = datetime.fromisoformat(readiness["checkedAtUtc"])
        age = (datetime.now(timezone.utc) - checked).total_seconds()
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Regional readiness needs a timezone-aware check timestamp.") from error
    if not 0 <= age <= 900:
        raise ValueError("Regional readiness is older than 15 minutes or future-dated; refresh before deployment.")
    checks = readiness.get("checks")
    if not isinstance(checks, list) or not checks or any(not isinstance(item, dict) for item in checks):
        raise ValueError("Regional readiness needs per-resource/SKU/capability results.")
    covered = {item.get("service") for item in checks}
    if set(services) - covered:
        raise ValueError("Regional readiness omits selected services: " + ", ".join(sorted(set(services) - covered)))
    quota_totals: dict[tuple[str, str, str], dict] = {}
    for check in checks:
        for key in ("service", "resourceType", "sku", "region"):
            if not isinstance(check.get(key), str) or not check[key].strip():
                raise ValueError(f"Regional resource check needs explicit {key}.")
        if check["region"].casefold().replace(" ", "") != scope["region"].casefold().replace(" ", ""):
            raise ValueError("Regional resource evidence does not match the authorized region.")
        if check.get("status") != "passed":
            raise ValueError(f"Regional check is blocked or unknown: {check['resourceType']} / {check['sku']}.")
        facts = check.get("evidence")
        if not isinstance(facts, list) or not facts or any(
            not isinstance(item, str) or not item.strip() for item in facts
        ):
            raise ValueError("Each regional check needs real command/result references, not service catalog claims.")
        if check["resourceType"].casefold() == "microsoft.documentdb/databaseaccounts":
            properties = check.get("properties", {})
            zones = check.get("zoneRedundant")
            if type(zones) is not bool or not isinstance(properties, dict):
                raise ValueError("Cosmos evidence must specify the actual zone-redundancy requirement and properties.")
            flag = "isSubscriptionRegionAccessAllowedForAz" if zones else "isSubscriptionRegionAccessAllowedForRegular"
            if (
                properties.get(flag) is not True or properties.get("status") != "Online"
                or zones and properties.get("supportsAvailabilityZone") is not True
            ):
                raise ValueError(
                    f"Cosmos DB {scope['region']} is not eligible for this subscription/design ({flag}). "
                    "Evaluate authorized alternatives; do not downgrade zones or request quota automatically."
                )
        quotas = check.get("quotas", [])
        if not isinstance(quotas, list):
            raise ValueError("Regional quota evidence must be a list.")
        for quota in quotas:
            if not isinstance(quota, dict) or any(
                type(quota.get(key)) not in {int, float} or not 0 <= quota[key] < float("inf")
                for key in ("limit", "currentValue", "required")
            ):
                raise ValueError("Quota checks need nonnegative numeric limit, currentValue and required demand.")
            name = quota.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Quota checks require the exact provider quota name.")
            key = (check["resourceType"].split("/")[0].casefold(), check["region"].casefold(), name.casefold())
            total = quota_totals.setdefault(key, {**quota, "required": 0})
            if any(total[field] != quota[field] for field in ("limit", "currentValue")):
                raise ValueError("Inconsistent quota observations for resources sharing a subscription quota.")
            total["required"] += quota["required"]
            if total["currentValue"] + total["required"] > total["limit"]:
                raise ValueError(
                    f"Insufficient {check['resourceType']} / {check['sku']} quota in {check['region']}: "
                    f"limit {total['limit']}, used {total['currentValue']}, required {total['required']}."
                )
        resource_type = check["resourceType"].casefold()
        if resource_type in {"microsoft.compute/virtualmachines", "microsoft.compute/virtualmachinescalesets"}:
            family = check.get("vmFamily")
            if (
                not isinstance(family, str) or not family or check.get("restrictions") != []
                or check.get("zonesSupported") is not True
            ):
                raise ValueError("VM checks require exact family, SKU restrictions and requested-zone support.")
            demand = check.get("demand", {})
            if not isinstance(demand, dict) or any(
                type(demand.get(key)) is not int or demand[key] < 0 for key in ("vcpus", "instances")
            ):
                raise ValueError("VM checks need aggregate vCPU and instance demand, including scale-out.")
            for name, required in ((family, demand["vcpus"]), ("cores", demand["vcpus"]),
                                   ("virtualMachines", demand["instances"])):
                quota = next((q for q in quotas if q.get("name", "").casefold() == name.casefold()), None)
                if quota is None or quota["required"] < required:
                    raise ValueError("VM checks require family, total regional vCPU and VM-count quota headroom.")
        if resource_type == "microsoft.web/serverfarms" and not quotas:
            raise ValueError("App Service plan checks need Microsoft.Web SKU/worker quota, not Compute VM quota.")
    return [f"Subscription regional readiness verified for {len(checks)} resource/SKU checks."]


def command(root: Path, arguments: list[str]) -> str:
    environment = execution_environment(root)
    executable = shutil.which(arguments[0], path=environment.get("PATH", ""))
    if executable is None:
        raise ValueError(f"{arguments[0]} is not available on the portal worker PATH.")
    try:
        result = subprocess.run(
            [executable, *arguments[1:]], cwd=root, env=environment, capture_output=True,
            text=True, encoding="utf-8", timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"{arguments[0]} identity check could not complete: {error}") from error
    if result.returncode:
        raise ValueError(f"{arguments[0]} identity check failed: {(result.stderr or result.stdout)[-1200:]}")
    return result.stdout.strip()


def identity(root: Path) -> dict:
    account = json.loads(command(root, [
        "az", "account", "show", "--query",
        "{account:user.name,subscriptionId:id,tenantId:tenantId}", "--output", "json",
    ]))
    token_metadata = json.loads(command(root, [
        "az", "account", "get-access-token", "--query",
        "{expiresOn:expiresOn,tenant:tenant,subscription:subscription}", "--output", "json",
    ]))
    if token_metadata.get("tenant") != account.get("tenantId") or (
        token_metadata.get("subscription") != account.get("subscriptionId")
    ):
        raise ValueError("Azure CLI token metadata does not match its current account context.")
    status = command(root, ["azd", "auth", "login", "--check-status", "--no-prompt"])
    match = re.search(r"Logged in to Azure as ([^\r\n]+)", status)
    if not match:
        raise ValueError("azd did not identify its signed-in account; verify azd auth login outside the worker.")
    if match[1].strip().casefold() != str(account.get("account", "")).casefold():
        raise ValueError("Azure CLI and azd account names differ. Align them explicitly before preparation.")
    return {
        "scope": account,
        "authentication": {
            "azureCli": "Signed in; usable token metadata verified (token never retained)",
            "azd": f"Signed in as {match[1].strip()}",
            "compatibility": "Account names match; azd target-tenant access still requires authorized preflight",
        },
    }


def discover(root: Path, scenario: Path, project: dict, overrides: dict | None = None,
             identified: dict | None = None) -> dict:
    if identified is None:
        identified = identity(root)
    account = identified["scope"]
    scope = {}
    sources = {}
    conflicts = []
    context = project.get("deploymentContext")
    saved = context["scope"] if context is not None else {}
    authorized = next(
        (item["scope"] for item in reversed(project.get("authorizations", []))
         if item["kind"] == "deployment-preparation"), {},
    )
    retained = authorized or saved
    for field in ("account", "subscriptionId", "tenantId"):
        value = account.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Current Azure CLI context is missing {field}.")
        scope[field] = value
        sources[field] = "Current Azure CLI identity; token metadata checked"
        if retained.get(field) and retained[field].casefold() != value.casefold():
            conflicts.append(f"{field} differs from the previously saved target; review before consent.")
    local = {}
    azure = scenario / ".azure"
    if azure.is_dir():
        config = azure / "config.json"
        default = json.loads(config.read_text(encoding="utf-8")).get("defaultEnvironment") if config.is_file() else None
        environments = sorted(item.name for item in azure.iterdir() if item.is_dir() and (item / ".env").is_file())
        selected = default if default in environments else environments[0] if len(environments) == 1 else None
        if environments and selected is None:
            raise ValueError("Multiple local azd environments exist without a selected default. Select one explicitly.")
        if selected:
            local["environment"] = selected
            for line in (azure / selected / ".env").read_text(encoding="utf-8").splitlines():
                key, separator, value = line.partition("=")
                if separator and key in {"AZURE_LOCATION", "AZURE_RESOURCE_GROUP", "AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID"}:
                    local[key] = value.strip().strip('"').strip("'")
            for key, field in (("AZURE_SUBSCRIPTION_ID", "subscriptionId"), ("AZURE_TENANT_ID", "tenantId")):
                if local.get(key) and local[key].casefold() != scope[field].casefold():
                    raise ValueError(f"Local azd environment {key} conflicts with Azure CLI identity; reconcile explicitly.")
    evidence = scenario / "00-region-availability.json"
    architecture = json.loads(evidence.read_text(encoding="utf-8")) if evidence.is_file() else {}
    defaults = {
        "environment": (local.get("environment"), "Existing local azd environment"),
        "resourceGroup": (local.get("AZURE_RESOURCE_GROUP"), "Existing local azd resource-group setting"),
        "region": (architecture.get("provisionalRegion"), "Scenario architecture region evidence"),
    }
    for field in ("environment", "resourceGroup", "region"):
        value, source = defaults[field]
        if retained.get(field):
            value, source = retained[field], "Previously saved scenario target"
        if not value:
            if field == "environment":
                value, source = project["projectSlug"], "Scenario slug / environment naming convention"
            elif field == "resourceGroup":
                value, source = f"rg-{scope['environment']}", "Repository rg-{environment} convention"
            else:
                value, source = local.get("AZURE_LOCATION"), "Existing local azd region setting"
        scope[field] = value or ""
        sources[field] = source
    if overrides is not None and not isinstance(overrides, dict):
        raise ValueError("Target edits must be an object.")
    if overrides:
        if set(overrides) - {"environment", "resourceGroup", "region"}:
            raise ValueError("Only environment, resource group and region can be edited here; identity comes from local CLI.")
        for field, value in overrides.items():
            scope[field] = value
            sources[field] = "User-edited proposed target"
    for field in FIELDS:
        value = scope[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise ValueError(f"Target {field} is unresolved. Review scenario architecture or edit the proposed target.")
    for field in ("environment", "resourceGroup", "region"):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._()-]{0,89}", scope[field]):
            raise ValueError(f"Target {field} contains unsupported naming characters.")
    return {
        "scope": scope, "sources": sources, "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "authentication": identified["authentication"],
        "conflicts": conflicts,
        "notChecked": ["RBAC", "provider registration", "policy", "regional SKU/model quota and capacity", "what-if", "cost"],
    }
