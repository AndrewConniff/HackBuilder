"""Resolve private Azure target proposals from existing identity and local scenario evidence only."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from check_prerequisites import execution_environment

FIELDS = ("account", "subscriptionId", "tenantId", "environment", "resourceGroup", "region")


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


def discover(root: Path, scenario: Path, project: dict, overrides: dict | None = None) -> dict:
    identified = identity(root)
    account = identified["scope"]
    scope = {}
    sources = {}
    conflicts = []
    saved = project.get("deploymentContext", {}).get("scope", {})
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
