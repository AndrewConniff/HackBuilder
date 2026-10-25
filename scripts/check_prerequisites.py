"""Check local ABC Builder prerequisites without installing tools or accessing Azure accounts."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import prerequisite_profiles as profiles
ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH_POLICY_VERSION = 2
TOOLS = (
    ("git", "Git", "git", ["--version"], None, "Git.Git"),
    ("powershell", "PowerShell 7+", "pwsh", ["--version"], 7, "Microsoft.PowerShell"),
    ("dotnet", ".NET 10 SDK", "dotnet", ["--list-sdks"], 10, "Microsoft.DotNet.SDK.10"),
    ("graphviz", "Graphviz dot", "dot", ["-V"], None, "Graphviz.Graphviz"),
    ("azure-cli", "Azure CLI", "az", ["--version"], None, "Microsoft.AzureCLI"),
    ("azd", "Azure Developer CLI", "azd", ["version"], None, "Microsoft.Azd"),
    ("bicep", "Azure CLI Bicep component", "az", ["bicep", "version"], None, None),
)
CONTRIBUTOR_TOOLS = (
    ("node", "Node.js 22+ (portal tests / npm CLI)", "node", ["--version"], 22, "OpenJS.NodeJS.LTS"),
    ("gh", "GitHub CLI (publication)", "gh", ["--version"], None, "GitHub.cli"),
)
DIAGRAM_SMOKE = """
import tempfile
from pathlib import Path
import matplotlib
from PIL import Image
from diagrams import Diagram
from diagrams.generic.blank import Blank
with tempfile.TemporaryDirectory(prefix="abc-diagram-check-") as directory:
    filename = Path(directory) / "prerequisite-check"
    with Diagram("Prerequisite check", filename=str(filename), show=False, outformat="png"):
        Blank("Ready")
    with Image.open(filename.with_suffix(".png")) as image:
        assert image.format == "PNG" and image.width > 0 and image.height > 0
        image.verify()
print("Python diagrams and Graphviz successfully rendered and verified a PNG.")
"""
NUGET_METADATA_URL = "https://packagefeedproxy.microsoft.io/nuget/v3/index.json"
NUGET_SMOKE = (
    "$ErrorActionPreference = 'Stop'; "
    "try { "
    f"$index = Invoke-RestMethod -Uri '{NUGET_METADATA_URL}' -TimeoutSec 30 -ErrorAction Stop; "
    "$base = @($index.resources | Where-Object { $_.'@type' -eq 'PackageBaseAddress/3.0.0' }); "
    "if ($base.Count -ne 1) { throw 'Approved feed has no unique PackageBaseAddress/3.0.0 resource.' }; "
    "$baseUri = [uri]$base[0].'@id'; "
    "if (-not $baseUri.IsAbsoluteUri -or $baseUri.Scheme -ne 'https') "
    "{ throw 'Approved feed package base must be an absolute HTTPS URL.' }; "
    "$url = $baseUri.AbsoluteUri.TrimEnd('/') + '/azure.identity/index.json'; "
    "$metadata = Invoke-RestMethod -Uri $url -TimeoutSec 30 -ErrorAction Stop; "
    "if (-not ($metadata.versions -is [array]) -or $metadata.versions.Count -eq 0) "
    "{ throw 'NuGet response does not contain a nonempty versions array.' }; "
    "foreach ($version in $metadata.versions) { "
    "if ($version -isnot [string] -or [string]::IsNullOrWhiteSpace($version)) "
    "{ throw 'NuGet versions must be nonempty strings.' } }; "
    "'NuGet metadata HTTPS request and response validation passed.'; "
    "} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }"
)


def execution_environment(root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    scripts = root / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    if (scripts / ("python.exe" if os.name == "nt" else "python")).is_file():
        environment["VIRTUAL_ENV"] = str(scripts.parent)
        environment["PATH"] = str(scripts) + os.pathsep + environment.get("PATH", "")
    program_files_path = os.environ.get("ProgramFiles")
    if os.name == "nt" and program_files_path:
        program_files = Path(program_files_path)
        for command, candidate in (
            ("dot", program_files / "Graphviz" / "bin" / "dot.exe"),
            ("dotnet", program_files / "dotnet" / "dotnet.exe"),
            ("k6", program_files / "k6" / "k6.exe"),
        ):
            if not shutil.which(command, path=environment.get("PATH", "")) and candidate.is_file():
                environment["PATH"] = environment.get("PATH", "") + os.pathsep + str(candidate.parent)
                logging.getLogger("abcbuilder.portal").info(
                    "Using existing %s installation on the portal/worker PATH: %s", command, candidate.parent,
                )
    return environment


def run_command(command: list[str], timeout: int = 45) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"},
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, f"{type(error).__name__}: {error}"


def check(identifier: str, name: str, ok: bool, detail: str, winget: str | None = None) -> dict:
    if identifier.startswith("python-package:") or identifier in {"venv", "pip-health"}:
        fix = "While workers and the portal are stopped, prepare/repair the repository .venv from requirements.txt."
    elif identifier == "diagram-render":
        fix = "Repair Graphviz and the diagram Python packages, then rerun the real PNG rendering check."
    else:
        fix = "Follow PREREQUISITES.md to install or repair this tool, then verify it in the portal environment."
    return {
        "id": identifier, "name": name, "ok": ok, "detail": detail, "winget": winget,
        "state": "ready" if ok else "failed-check", "fix": "" if ok else fix,
    }


def tool_check(spec: tuple) -> dict:
    identifier, name, command, arguments, major, winget = spec
    executable = shutil.which(command)
    if not executable:
        return {
            **check(identifier, name, False, f"{command} is not on this process's PATH.", winget),
            "installed": False, "state": "not-found",
        }
    code, output = run_command([executable, *arguments])
    ok = code == 0
    if identifier == "dotnet":
        ok = ok and bool(re.search(r"(?m)^10\.\d+\.\d+\s+\[", output))
    elif major is not None:
        version = re.search(r"(\d+)\.\d+", output)
        ok = ok and version is not None and int(version[1]) >= major
    elif identifier == "graphviz":
        ok = ok and "graphviz" in output.lower()
    elif identifier == "docker":
        ok = ok and bool(re.search(r"\d+\.\d+", output)) and "linux" in output.lower()
    result = {
        **check(identifier, name, ok, f"{executable}\n{output[:1800] or 'No version output.'}", winget),
        "installed": True,
    }
    if identifier == "docker" and not ok:
        result.update(
            state="engine-unavailable",
            fix="Docker is installed. Start Docker Desktop, select the Linux engine and wait until it is ready. "
                "Rerun docker version and docker info before local container builds. Follow organizational "
                "licensing/virtualization procedures; do not reinstall merely because the engine is stopped.",
        )
    return result


def minimum_satisfied(installed: str, minimum: str) -> bool:
    match = re.fullmatch(r"(\d+(?:\.\d+)*)(.*)", installed)
    if match is None:
        return False
    actual = tuple(int(part) for part in match[1].split("."))
    required = tuple(int(part) for part in minimum.split("."))
    length = max(len(actual), len(required))
    actual += (0,) * (length - len(actual))
    required += (0,) * (length - len(required))
    return actual > required or (
        actual == required and not re.match(r"(?:a|b|rc|\.dev)", match[2])
    )


def package_requirements(root: Path) -> list[tuple[str, str]]:
    requirements = []
    for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = re.fullmatch(r"([A-Za-z0-9_-]+)>=(\d+(?:\.\d+)*)", line)
        if requirement is None:
            raise ValueError(f"Unsupported prerequisite requirement syntax: {line}")
        requirements.append(requirement.groups())
    return requirements


def python_checks(root: Path) -> list[dict]:
    results = [
        check(
            "python", "Python 3.10+", sys.version_info >= (3, 10),
            f"{sys.executable}\n{sys.version.split()[0]}", "Python.Python.3.13",
        ),
        check(
            "venv", "Repository Python environment",
            sys.prefix != sys.base_prefix and Path(sys.prefix).resolve() == (root / ".venv").resolve(),
            f"Expected {root / '.venv'}; current interpreter prefix is {sys.prefix}.",
        ),
    ]
    for name, minimum in package_requirements(root):
        try:
            installed = importlib.metadata.version(name)
            ok = minimum_satisfied(installed, minimum)
            detail = f"Installed {installed}; requires >= {minimum}."
        except importlib.metadata.PackageNotFoundError:
            ok, detail = False, f"Missing; install {name}>={minimum} in the repository .venv."
        results.append(check(f"python-package:{name}", name, ok, detail))
    code, output = run_command([sys.executable, "-B", "-m", "pip", "check"])
    results.append(check("pip-health", "Python dependency consistency", code == 0, output[:1800]))
    return results


def nuget_check() -> dict:
    executable = shutil.which("pwsh")
    if executable is None:
        code, output = 1, "PowerShell 7 (pwsh) is not on this process's PATH; HTTPS probe was not run."
    else:
        code, output = run_command(
            [executable, "-NoProfile", "-NonInteractive", "-Command", NUGET_SMOKE], timeout=75,
        )
    result = check(
        "nuget-https", "NuGet package metadata HTTPS/TLS",
        code == 0, f"{NUGET_METADATA_URL}\n{output[:1800]}\n"
        "Probe covers Azure.Identity metadata only; configured feeds and actual restore/build still need verification.",
    )
    if code != 0:
        result["fix"] = (
            "Outside the worker, have the administrator restore approved proxy, certificate trust and outbound "
            "HTTPS access for the actual portal worker account. Do not disable certificate validation, weaken TLS "
            "or bypass host restrictions. Verify from a fresh worker, then retry actual restore/build. "
            "Verify MicrosoftPackageFeedProxy in NuGet.Config and access to its service index and advertised "
            "package endpoints; do not fall back to direct NuGet.org."
        )
    return result


def build_report(root: Path = ROOT, contributor: bool = False, docker: bool = False) -> dict:
    results = python_checks(root)
    specs = [*TOOLS, *(CONTRIBUTOR_TOOLS if contributor else ())]
    if docker:
        specs.append((
            "docker", "Docker CLI and running engine", "docker",
            ["info", "--format", "{{.ServerVersion}} {{.OSType}}"], None, "Docker.DockerDesktop",
        ))
    results.extend(tool_check(spec) for spec in specs)
    results.append(nuget_check())
    renderer_packages = {"python-package:diagrams", "python-package:matplotlib", "python-package:pillow"}
    packages_ok = all(item["ok"] for item in results if item["id"] in renderer_packages)
    dot_ok = next(item["ok"] for item in results if item["id"] == "graphviz")
    if packages_ok and dot_ok:
        code, output = run_command([sys.executable, "-B", "-c", DIAGRAM_SMOKE])
        results.append(check("diagram-render", "Architecture PNG rendering smoke test", code == 0, output[:1800]))
    else:
        results.append(check(
            "diagram-render", "Architecture PNG rendering smoke test", False,
            "Blocked until the Python requirements and native Graphviz dot are available.",
        ))
    return {
        "schemaVersion": 1, "ready": all(item["ok"] for item in results),
        "pythonExecutable": sys.executable, "checks": results,
        "notChecked": [
            "Copilot/GitHub sign-in, repository trust and execution-host tool permissions",
            "Azure account, tenant, subscription, RBAC, provider registration, model quota and region capacity",
            "Scenario-specific packages, container configuration, deployment consent and suitability approval",
        ],
    }


def service_report(services: list[str], build_mode: str = "auto", local_functions: bool = False,
                   root: Path = ROOT, load_tests: bool = False) -> dict:
    profile = profiles.plan(services, build_mode, local_functions, load_tests)
    report = build_report(root, docker="docker" in profile["stages"]["local-validation"])
    if local_functions:
        report["checks"].append(tool_check((
            "functions-core-tools", "Azure Functions Core Tools 4+", "func", ["--version"], 4,
            "Microsoft.Azure.FunctionsCoreTools",
        )))
    if load_tests:
        report["checks"].append(tool_check(("k6", "k6 load-test runner", "k6", ["version"], None, "GrafanaLabs.k6")))
    report.update(
        profileVersion=profiles.VERSION, checkedAtUtc=datetime.now(timezone.utc).isoformat(),
        services=profile["services"], buildMode=profile["buildMode"], localFunctions=local_functions,
        loadTests=load_tests, plan=profile,
    )
    report["blockedStages"] = {
        stage: [item["id"] for item in profiles.stage_failures(report, stage)]
        for stage in profile["stages"]
    }
    report["ready"] = all(item["ok"] for item in report["checks"])
    return report


def planned_checks(profile: dict, root: Path = ROOT) -> list[dict]:
    names = [(spec[0], spec[1]) for spec in TOOLS]
    names += [("python", "Python 3.10+"), ("venv", "Repository Python environment")]
    names += [(f"python-package:{name}", f"{name} >= {minimum}") for name, minimum in package_requirements(root)]
    names += [
        ("pip-health", "Python dependency consistency"), ("diagram-render", "Real PNG rendering"),
        ("nuget-https", "NuGet package metadata HTTPS/TLS"),
    ]
    if "docker" in profile["stages"]["local-validation"]:
        names.append(("docker", "Docker CLI and running Linux engine"))
    if profile["localFunctions"]:
        names.append(("functions-core-tools", "Azure Functions Core Tools 4+"))
    if profile.get("loadTests"):
        names.append(("k6", "k6 load-test runner"))
    return [{
        "id": identifier, "name": name, "state": "not-checked",
        "stages": [stage for stage, tools in profile["stages"].items() if identifier in tools],
    } for identifier, name in names]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--contributor", action="store_true")
    parser.add_argument("--docker", action="store_true")
    parser.add_argument("--services", nargs="+", choices=sorted(profiles.SERVICE_REQUIREMENTS))
    parser.add_argument("--build-mode", choices=["auto", "local", "remote"], default="auto")
    parser.add_argument("--local-functions", action="store_true")
    parser.add_argument("--load-tests", action="store_true", help="Check k6 for an explicitly selected load-test design.")
    parser.add_argument("--stage", choices=list(profiles.STAGE_REQUIREMENTS))
    args = parser.parse_args()
    try:
        services = args.services
        report = (
            service_report(services, args.build_mode, args.local_functions, load_tests=args.load_tests)
            if services is not None
            else build_report(contributor=args.contributor, docker=args.docker)
        )
    except (OSError, ValueError) as error:
        print(f"Prerequisite check failed: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report["checks"]:
            print(f"{'READY' if item['ok'] else 'MISSING/FAILED'}: {item['name']}\n  {item['detail']}")
        print("\nNot checked: " + "; ".join(report["notChecked"]))
    ready = not profiles.stage_failures(report, args.stage) if args.stage and services is not None else report["ready"]
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
