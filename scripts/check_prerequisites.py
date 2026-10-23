"""Check local ABC Builder prerequisites without installing tools or accessing Azure accounts."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = (
    ("git", "Git", "git", ["--version"], None, "Git.Git"),
    ("copilot", "GitHub Copilot CLI", "copilot", ["--version"], None, "GitHub.Copilot"),
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
    return {"id": identifier, "name": name, "ok": ok, "detail": detail, "winget": winget}


def tool_check(spec: tuple) -> dict:
    identifier, name, command, arguments, major, winget = spec
    executable = shutil.which(command)
    if not executable:
        return check(identifier, name, False, f"{command} is not on this process's PATH.", winget)
    code, output = run_command([executable, *arguments])
    ok = code == 0
    if identifier == "dotnet":
        ok = ok and bool(re.search(r"(?m)^10\.\d+\.\d+\s+\[", output))
    elif major is not None:
        version = re.search(r"(\d+)\.\d+", output)
        ok = ok and version is not None and int(version[1]) >= major
    elif identifier == "graphviz":
        ok = ok and "graphviz" in output.lower()
    elif identifier == "copilot":
        ok = ok and "copilot" in output.lower()
        if ok:
            help_code, help_text = run_command([executable, "--help"])
            required = ("--agent", "--prompt", "--allow-all-tools", "--no-ask-user", "--add-dir")
            missing = [flag for flag in required if flag not in help_text]
            ok = help_code == 0 and not missing
            if not ok:
                output += f"\nPortal CLI flags unavailable: {', '.join(missing)}. {help_text[:300]}"
    return check(identifier, name, ok, f"{executable}\n{output[:1800] or 'No version output.'}", winget)


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
    for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = re.fullmatch(r"([A-Za-z0-9_-]+)>=(\d+(?:\.\d+)*)", line)
        if requirement is None:
            raise ValueError(f"Unsupported prerequisite requirement syntax: {line}")
        name, minimum = requirement.groups()
        try:
            installed = importlib.metadata.version(name)
            ok = minimum_satisfied(installed, minimum)
            detail = f"Installed {installed}; requires >= {minimum}."
        except importlib.metadata.PackageNotFoundError:
            ok, detail = False, f"Missing; install {line} in the repository .venv."
        results.append(check(f"python-package:{name}", name, ok, detail))
    code, output = run_command([sys.executable, "-B", "-m", "pip", "check"])
    results.append(check("pip-health", "Python dependency consistency", code == 0, output[:1800]))
    return results


def build_report(root: Path = ROOT, contributor: bool = False, docker: bool = False) -> dict:
    results = python_checks(root)
    specs = [*TOOLS, *(CONTRIBUTOR_TOOLS if contributor else ())]
    if docker:
        specs.append((
            "docker", "Docker CLI and running engine", "docker",
            ["info", "--format", "{{.ServerVersion}}"], None, "Docker.DockerDesktop",
        ))
    results.extend(tool_check(spec) for spec in specs)
    packages_ok = all(item["ok"] for item in results if item["id"].startswith("python-package:"))
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--contributor", action="store_true")
    parser.add_argument("--docker", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(contributor=args.contributor, docker=args.docker)
    except (OSError, ValueError) as error:
        print(f"Prerequisite check failed: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report["checks"]:
            print(f"{'READY' if item['ok'] else 'MISSING/FAILED'}: {item['name']}\n  {item['detail']}")
        print("\nNot checked: " + "; ".join(report["notChecked"]))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
