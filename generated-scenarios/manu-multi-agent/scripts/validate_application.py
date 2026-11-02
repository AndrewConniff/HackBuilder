"""Compile and exercise this application's local contracts; never builds containers or contacts Azure."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".application-evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nuget-config", type=Path, default=ROOT / "NuGet.Config")
    parser.add_argument("--evidence-directory", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    evidence_directory = args.evidence_directory.resolve()
    if not evidence_directory.is_relative_to(ROOT.resolve()):
        parser.error("Evidence must remain inside this scenario.")
    evidence_directory.mkdir(parents=True, exist_ok=True)
    checks = []
    commands = [
        ("restore", ["dotnet", "restore", "MobilityCommercial.sln", "--configfile", str(args.nuget_config),
                     "--locked-mode", "--verbosity", "quiet"]),
        ("build", ["dotnet", "build", "MobilityCommercial.sln", "--no-restore", "--verbosity", "quiet"]),
        ("tests", ["dotnet", "test", r"tests\MobilityCommercial.Tests\MobilityCommercial.Tests.csproj",
                   "--no-build", "--no-restore", "--logger", "trx;LogFileName=application.trx",
                   "--results-directory", str(evidence_directory / "test-results"), "--verbosity", "minimal"]),
        ("publish", ["dotnet", "publish", r"src\MobilityCommercial.Web\MobilityCommercial.Web.csproj",
                     "--no-restore", "-c", "Release", "-o", str(evidence_directory / "publish"),
                     "--verbosity", "quiet"]),
        ("bicep-build", ["az", "bicep", "build", "--file", r"infra\main.bicep",
                         "--outfile", str(evidence_directory / "main.arm.json")]),
        ("bicep-lint", ["az", "bicep", "lint", "--file", r"infra\main.bicep"]),
        ("infrastructure-contracts", ["python", "-B", "-m", "unittest", "discover", "-s", r"infra\tests",
                                      "-p", "test_*.py", "-v"]),
        ("ui", ["python", r"tests\test_browser_ui.py"]),
    ]
    for name, command in commands:
        executable = shutil.which(command[0])
        if not executable:
            raise FileNotFoundError(f"Required tool unavailable: {command[0]}")
        environment = os.environ | {
            "ABCBUILDER_APPLICATION_UI_EXPORT": str(evidence_directory / "ui"),
            "ABCBUILDER_APPLICATION_EVIDENCE": str(evidence_directory),
        }
        result = subprocess.run(
            [executable, *command[1:]], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=240, check=False, env=environment,
        )
        log = evidence_directory / f"{name}.log"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        checks.append({"name": name, "command": subprocess.list2cmdline(command),
                       "exitCode": result.returncode, "log": str(log.relative_to(ROOT))})
        print(f"{name}: exit {result.returncode}")
        if result.returncode:
            print((result.stdout + result.stderr)[-6000:])
            break
    passed = len(checks) == len(commands) and all(check["exitCode"] == 0 for check in checks)
    if passed:
        published = evidence_directory / "publish"
        artifact_errors = []
        if sorted(path.name for path in (published / "SeedData").glob("*.json")) != [
            "claims.json", "opportunities.json", "products.json"
        ]:
            artifact_errors.append("Published seed files missing.")
        if list(published.glob("*Tests*.dll")):
            artifact_errors.append("Test assemblies must not ship in production.")
        if not (published / "FluentIcons-LICENSE.txt").is_file():
            artifact_errors.append("Fluent icon license missing.")
        for name in ("07-webapp-summary.md", "README.md", "05-implementation-reference.md"):
            for number, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), 1):
                if len(line) > 120:
                    artifact_errors.append(f"{name}:{number} exceeds 120 columns")
        passed = not artifact_errors
        checks.append({"name": "published-artifacts-and-documentation",
                       "command": "validate_application.py: published seeds/tests/license and Markdown line limits",
                       "exitCode": 0 if passed else 1, "errors": artifact_errors})
        for error in artifact_errors:
            print(error)
    if passed:
        region_evidence = ROOT / "00-region-availability.json"
        region = json.loads(region_evidence.read_text(encoding="utf-8"))
        region["sdkDecision"]["verifiedAtUtc"] = datetime.now(timezone.utc).isoformat()
        region_evidence.write_text(json.dumps(region, indent=2) + "\n", encoding="utf-8")
    hashes = {}
    for folder in ("src", "tools", "scripts", "tests"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and not any(part in {"bin", "obj", "__pycache__"} for part in path.parts):
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = {
        "schemaVersion": 1, "stage": "application", "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "allCommandsPassed": passed, "checks": checks, "sourceSha256": hashes,
        "limitations": [
            "Offline test doubles are confined to the test assembly; no live inference or signing is claimed.",
            "No Docker image built, container started, Azure query, identity installation or deployment performed.",
            "Full local-validation, authorized live acceptance and suitability approval remain separate operations.",
        ],
    }
    (evidence_directory / "validation.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
