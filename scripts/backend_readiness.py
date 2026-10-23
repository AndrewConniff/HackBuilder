"""Run deterministic prerequisite and identity audits before an agent process is allowed to start."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import azure_context
import prerequisite_profiles as profiles
from check_prerequisites import check, execution_environment, worker_cache_directories

BROWSER_SMOKE = """
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    try:
        page = browser.new_page()
        page.set_content("<title>ABC readiness</title><h1>Ready</h1>")
        assert page.title() == "ABC readiness"
        assert page.locator("h1").inner_text() == "Ready"
        print("Actual headless Chromium launch and page assertions passed.")
    finally:
        browser.close()
"""


def audit(root: Path, project: dict) -> dict:
    services = profiles.effective_services(root, project["request"], project["projectSlug"])
    load_tests = profiles.requires_load_tests(root, project["projectSlug"]) or (
        "scaling" in project["request"].get("domains", [])
    )
    environment = execution_environment(root)
    python = shutil.which("python", path=environment["PATH"]) or sys.executable
    arguments = [
        python, "-B", str(root / "scripts" / "check_prerequisites.py"), "--json",
        "--services", *services,
    ]
    if load_tests:
        arguments.append("--load-tests")
    try:
        result = subprocess.run(
            arguments, cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8",
            timeout=240, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Backend readiness audit could not complete: {error}") from error
    if result.returncode not in (0, 1):
        raise ValueError(f"Backend checker failed: {(result.stderr or result.stdout)[-1800:]}")
    report = json.loads(result.stdout)
    if not isinstance(report, dict) or report.get("profileVersion") != profiles.VERSION:
        raise ValueError("Backend prerequisite checker returned an unsupported report.")
    for stage in profiles.STAGE_REQUIREMENTS:
        profiles.stage_failures(report, stage)
    report["checks"].extend(browser_checks(root, python, environment))
    report["checks"].extend(dotnet_checks(root, environment))
    try:
        worker_cache_directories(root)
        report["checks"].append(check("worker-paths", "Scoped worker filesystem policy", True, "Approved roots resolved."))
    except ValueError as error:
        report["checks"].append(check("worker-paths", "Scoped worker filesystem policy", False, str(error)))
    try:
        identity = azure_context.identity(root)
        report["identity"] = identity
        report["checks"].append(check(
            "azure-authentication", "Azure CLI and azd authentication", True,
            f"{identity['scope']['account']}; subscription {identity['scope']['subscriptionId']}; "
            f"tenant {identity['scope']['tenantId']}. Token metadata checked; no token retained.",
        ))
    except (OSError, ValueError) as error:
        item = check("azure-authentication", "Azure CLI and azd authentication", False, str(error))
        item["fix"] = "Sign in with az login and azd auth login on this machine, then retry readiness in the portal."
        report["checks"].append(item)
    report["ready"] = all(item["ok"] for item in report["checks"])
    report["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
    report["source"] = "python-backend"
    report["notChecked"] = [
        "Organization tool approval rules (not overridden), design-specific packages not yet declared",
        "Azure RBAC/policy/providers/SKU/model capacity; require exact-target preparation consent",
        "Scenario actual restore/build, container/application/agent acceptance; verified by assigned jobs",
    ]
    return report


def dotnet_checks(root: Path, environment: dict) -> list[dict]:
    executable = shutil.which("dotnet", path=environment["PATH"])
    if not executable:
        return [check("dotnet-restore-build", ".NET package restore and compilation", False, ".NET SDK not found.")]
    with tempfile.TemporaryDirectory(prefix="abc-dotnet-readiness-") as directory:
        workspace = Path(directory)
        (workspace / "Readiness.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
            '<NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup>'
            '<PackageReference Include="Azure.Identity" Version="1.17.1" /></ItemGroup></Project>',
            encoding="utf-8",
        )
        (workspace / "Readiness.cs").write_text(
            "public class Readiness { private Azure.Identity.DefaultAzureCredential? credential; }\n", encoding="utf-8",
        )
        commands = [
            [executable, "restore", str(workspace / "Readiness.csproj"), "--configfile", str(root / "NuGet.Config"),
             "--packages", str(workspace / "packages"), "--disable-parallel"],
            [executable, "build", str(workspace / "Readiness.csproj"), "--no-restore", "--nologo"],
        ]
        evidence = []
        for command in commands:
            try:
                result = subprocess.run(
                    command, env=environment, cwd=workspace, capture_output=True, text=True, encoding="utf-8",
                    timeout=120, check=False,
                )
                evidence.append((result.stdout + result.stderr)[-2200:])
                if result.returncode:
                    item = check("dotnet-restore-build", ".NET package restore and compilation", False, "\n".join(evidence))
                    item["fix"] = "Repair the approved NuGet proxy/SDK using the recorded restore error; direct NuGet is not used."
                    return [item]
            except (OSError, subprocess.TimeoutExpired) as error:
                return [check("dotnet-restore-build", ".NET package restore and compilation", False, str(error))]
        return [check(
            "dotnet-restore-build", ".NET package restore and compilation", True,
            "Temporary net10.0 project restored Azure.Identity and dependencies through repository NuGet.Config "
            "into a temporary package directory, then compiled --no-restore. Scenario packages still need their own build.",
        )]


def browser_checks(root: Path, python: str, environment: dict) -> list[dict]:
    try:
        result = subprocess.run(
            [python, "-B", "-c", BROWSER_SMOKE], cwd=root, env=environment,
            capture_output=True, text=True, encoding="utf-8", timeout=45, check=False,
        )
        item = check("chromium-runtime", "Playwright actual Chromium launch", result.returncode == 0,
                     (result.stdout + result.stderr)[-1800:])
    except (OSError, subprocess.TimeoutExpired) as error:
        item = check("chromium-runtime", "Playwright actual Chromium launch", False, str(error))
    if not item["ok"]:
        item["fix"] = (
            "Prepare repository requirements and run .venv\\Scripts\\python.exe -m playwright install chromium "
            "outside scenario workers using approved network access, then retry. No browser installed by audit."
        )
    return [item]
