"""Run actual commands, persist each result immediately, never infer a passing check."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path.cwd()
HERE = Path(__file__).resolve().parent
PACKAGES = HERE.parent
SCENARIO = PACKAGES.parent
CHECKS = [
    ("coach-bicep-build", ["az", "bicep", "build", "--file", str(PACKAGES / "coach/infra/main.bicep")]),
    ("coach-bicep-lint", ["az", "bicep", "lint", "--file", str(PACKAGES / "coach/infra/main.bicep")]),
    ("coach-bicep-lint-resources", ["az", "bicep", "lint", "--file", str(PACKAGES / "coach/infra/resources.bicep")]),
    ("participant-bicep-build", ["az", "bicep", "build", "--file", str(PACKAGES / "participant/infra/main.bicep")]),
    ("participant-bicep-lint", ["az", "bicep", "lint", "--file", str(PACKAGES / "participant/infra/main.bicep")]),
    ("coach-locked-restore", ["dotnet", "restore", str(PACKAGES / "coach/src/CoffeeShop.Web"), "--locked-mode"]),
    ("coach-build", ["dotnet", "build", str(PACKAGES / "coach/src/CoffeeShop.Web"), "--no-restore",
                     "--nologo", "-v", "minimal"]),
    ("coach-tests", ["dotnet", "test", str(PACKAGES / "coach/tests/CoffeeShop.Tests"),
                     "--nologo", "-v", "minimal", "--logger", "trx;LogFileName=coach-tests.trx",
                     "--results-directory", str(HERE / "test-results")]),
    ("coach-assets", ["pwsh", "-NoProfile", "-File", str(PACKAGES / "coach/scripts/Build-Assets.ps1")]),
    ("coach-publish", ["dotnet", "publish", str(PACKAGES / "coach/src/CoffeeShop.Web"), "--no-restore",
                       "--nologo", "-c", "Release", "-v", "minimal"]),
    ("coach-script-guards", ["pwsh", "-NoProfile", "-File", str(HERE / "test_guards.ps1")]),
    ("starter-status", ["python", str(HERE / "verify_packages.py"), "starter"]),
    ("package-boundaries", ["python", str(HERE / "verify_packages.py"), "boundaries"]),
    ("skillable-resources", ["python", str(REPO / ".github/skills/skillable-lod-authoring/scripts"
                                         "/validate_skillable_package.py"), "--check-skill"]),
    ("hospitality-support-tests", ["python", "-m", "unittest", "discover", "-s", "scripts/tests",
                                  "-p", "test_skillable_hospitality.py"]),
    ("workflow-regression-tests", ["python", "-m", "unittest", "discover", "-s", "scripts/tests",
                                 "-p", "test_hack_workflow.py"]),
    ("skillable", ["python", str(REPO / ".github/skills/skillable-lod-authoring/scripts"
                                "/validate_skillable_package.py"), str(PACKAGES), "--industry", "hospitality-travel"]),
    ("release-archives", ["python", str(HERE / "verify_packages.py"), "archives"]),
    ("approval-recheck", ["python", "scripts/hack_workflow.py", "check-approval", str(SCENARIO)]),
]


def main():
    records = []
    evidence = {
        "schemaVersion": 1, "scope": "local-only; test doubles do not prove a new cloud runtime",
        "workingDirectory": str(REPO), "allCommandsPassed": False, "checks": records,
    }
    destination = HERE / "local-checks.json"
    if destination.is_file():
        old = json.loads(destination.read_text(encoding="utf-8"))
        attempts = HERE / "attempts"
        attempts.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        shutil.copy2(destination, attempts / f"local-checks-before-{stamp}.json")
    # Never authorize cloud operations through inherited environment.
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("COFFEE_"):
            env.pop(key)
    for name, command in CHECKS:
        argv = [shutil.which(command[0]) or command[0], *command[1:]]
        start = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=REPO, env=env, text=True, capture_output=True,
                                encoding="utf-8", errors="replace")
        record = {
            "name": name, "command": argv, "exitCode": result.returncode, "startedAtUtc": start,
            "stdout": result.stdout, "stderr": result.stderr,
        }
        records.append(record)
        evidence["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
        destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: exit {result.returncode}", flush=True)
        print(result.stdout, result.stderr, flush=True)
    evidence["allCommandsPassed"] = all(x["exitCode"] == 0 for x in records)
    destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if evidence["allCommandsPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
