"""Resolve shared and conditional prerequisites without running tools or accessing Azure."""

from __future__ import annotations

import json
from pathlib import Path

VERSION = 2
SERVICE_REQUIREMENTS = {
    "foundry": "Foundry agents use the repository .NET application baseline.",
    "cosmos-db": "Application SDK via NuGet restore; no local database emulator is required.",
    "ai-search": "Application SDK via NuGet restore; no machine-wide search SDK is required.",
    "storage": "Application SDK via NuGet restore; Azurite is optional, not a baseline requirement.",
    "sql": "Application client via NuGet restore; local SQL Server is not a baseline requirement.",
    "app-service": "Default .NET publish/zip path; Docker only for an explicitly containerized build.",
    "container-apps": "Default local image build requires the Docker CLI and a responsive Linux engine.",
    "functions": "Application packages via restore; Functions Core Tools only for an explicit local Functions host.",
    "key-vault": "Application SDK via NuGet restore and managed identity at runtime.",
    "managed-identity": "Runtime identity/RBAC validation is separate from local tooling.",
    "virtual-network": "Infrastructure through Azure CLI/Bicep; live network reachability is a separate check.",
    "api-management": "Infrastructure through Azure CLI/Bicep; live gateway tests are separate.",
    "service-bus": "Application SDK via NuGet restore; no local broker is required.",
    "monitor": "Application instrumentation through restore; live telemetry checks are separate.",
}
STAGE_REQUIREMENTS = {
    "requirements": [],
    "architecture": [],
    "diagrams": [
        "python", "venv", "python-package:diagrams", "python-package:matplotlib",
        "python-package:pillow", "pip-health", "graphviz", "diagram-render",
    ],
    "bicep": ["azure-cli", "bicep", "python-package:checkov", "pip-health"],
    "application": ["dotnet"],
    "local-validation": [
        "git", "powershell", "dotnet", "azure-cli", "bicep", "python-package:checkov", "pip-health", "nuget-https",
    ],
    "deployment": ["azure-cli", "azd", "powershell"],
}


def system_plan() -> dict:
    """Return the same fixed full-toolchain profile used by the portal System page."""
    return plan(sorted(SERVICE_REQUIREMENTS), "local", local_functions=True, load_tests=True)


def plan(
    services: object, build_mode: str = "auto", local_functions: bool = False, load_tests: bool = False,
) -> dict:
    if (
        not isinstance(services, list) or not services
        or any(not isinstance(value, str) or value not in SERVICE_REQUIREMENTS for value in services)
        or len(services) != len(set(services))
    ):
        raise ValueError("Prerequisite services must be unique known catalog IDs.")
    if build_mode not in {"auto", "local", "remote"} or type(local_functions) is not bool or type(load_tests) is not bool:
        raise ValueError("Select auto, local or remote build mode and a boolean local Functions option.")
    selected = sorted(set(services) | {"foundry"})
    mode = "local" if build_mode == "auto" and "container-apps" in selected else build_mode
    stages = {key: list(values) for key, values in STAGE_REQUIREMENTS.items()}
    if mode == "local":
        for stage in ("local-validation", "deployment"):
            stages[stage].append("docker")
    if local_functions:
        if "functions" not in selected:
            raise ValueError("A local Functions host requires the Functions service selection.")
        stages["local-validation"].append("functions-core-tools")
    if load_tests:
        stages["local-validation"].append("k6")
    return {
        "version": VERSION, "services": selected, "buildMode": mode, "localFunctions": local_functions,
        "loadTests": load_tests,
        "stages": stages,
        "serviceNotes": [{"id": value, "detail": SERVICE_REQUIREMENTS[value]} for value in selected],
        "conditions": [
            "Recheck after architecture changes services, build mode or local-host requirements.",
            "Remote builds require an explicitly chosen design and separate Azure authorization; "
            "never a failure fallback.",
            "Generated NuGet/package dependencies are verified by actual restore/build, "
            "not machine-wide SDK installation.",
            "The NuGet HTTPS/TLS probe checks Azure.Identity metadata using PowerShell under the audit account; "
            "it does not prove every configured feed or package download.",
            "Local emulators, browser automation and other new design-specific tools "
            "require explicit additional checks.",
        ],
    }


def effective_services(root: Path, request: dict, slug: str) -> list[str]:
    selected = request.get("services", ["foundry"])
    plan(selected)
    manifest = root / "generated-scenarios" / slug / "scenario-manifest.json"
    if manifest.is_file():
        value = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Scenario manifest must be an object with reviewed services.")
        additions = value.get("services")
        plan(additions)
        selected = sorted(set(selected) | set(additions))
    return selected


def requires_load_tests(root: Path, slug: str) -> bool:
    manifest = root / "generated-scenarios" / slug / "scenario-manifest.json"
    if not manifest.is_file():
        return False
    value = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Scenario manifest must be an object.")
    tools = value.get("validationTools", [])
    if not isinstance(tools, list) or any(not isinstance(tool, str) for tool in tools):
        raise ValueError("Manifest validationTools must be a list of tool names.")
    return "k6" in tools


def stage_failures(report: dict, stage: str) -> list[dict]:
    if not isinstance(report, dict) or not {"services", "buildMode", "localFunctions", "checks"} <= report.keys():
        raise ValueError("Prerequisite report is missing its scope or check results.")
    profile = plan(report["services"], report["buildMode"], report["localFunctions"], report.get("loadTests", False))
    checks = report["checks"]
    if (
        not isinstance(checks, list)
        or any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
               or type(item.get("ok")) is not bool for item in checks)
        or len({item["id"] for item in checks}) != len(checks)
    ):
        raise ValueError("Invalid prerequisite check results.")
    by_id = {item["id"]: item for item in checks}
    return [
        by_id.get(identifier, {"id": identifier, "ok": False, "detail": "Required check has no result."})
        for identifier in profile["stages"].get(stage, [])
        if identifier not in by_id or not by_id[identifier]["ok"]
    ]
