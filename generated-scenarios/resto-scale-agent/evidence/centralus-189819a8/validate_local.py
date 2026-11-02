"""Run local repair checks and retain exact results without restoring packages or making cloud mutations."""

import ast
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
ROOT = Path.cwd()


def main() -> None:
    checks = []
    commands = [
        ("python-wiring", [
            sys.executable, "-m", "unittest", "discover", "-s", str(SCENARIO / "validation"), "-p", "test_*.py",
        ], ROOT),
        ("application", [
            "dotnet", "test", "tests\\Restaurant.Tests\\Restaurant.Tests.csproj", "--no-restore",
            "--logger", "trx;LogFileName=final-application.trx", "--results-directory", str(RUN),
        ], SCENARIO),
    ]
    for name in ("main", "runtime"):
        commands.extend([
            (f"{name}-build", [
                "az", "bicep", "build", "--file", str(SCENARIO / "infra" / f"{name}.bicep"),
                "--outfile", str(RUN / f"{name}.arm.json"),
            ], ROOT),
            (f"{name}-lint", [
                "az", "bicep", "lint", "--file", str(SCENARIO / "infra" / f"{name}.bicep"),
            ], ROOT),
        ])
    for name, arguments, directory in commands:
        executable = shutil.which(arguments[0])
        if executable is None:
            raise RuntimeError(f"Missing prerequisite {arguments[0]}; no installation attempted.")
        result = subprocess.run(
            [executable, *arguments[1:]], cwd=directory, capture_output=True,
            text=True, encoding="utf-8", timeout=240, check=False,
        )
        record = {
            "name": name, "command": subprocess.list2cmdline(arguments), "cwd": str(directory),
            "exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
            "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        }
        (RUN / f"local-{name}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        checks.append(record)
        print(json.dumps({"name": name, "exitCode": result.returncode,
                          "stdout": result.stdout[-1300:], "stderr": result.stderr[-1000:]}), flush=True)
        if result.returncode:
            (RUN / "local-checks.json").write_text(
                json.dumps({"checks": checks, "allCommandsPassed": False}, indent=2) + "\n", encoding="utf-8",
            )
            raise RuntimeError(f"Local check {name} failed; exact evidence retained.")
    for path in [*SCENARIO.joinpath("scripts").glob("*.py"), *RUN.glob("*.py"),
                 *SCENARIO.joinpath("validation").glob("test_*.py")]:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for name in ("05-implementation-reference.md", "06-deployment-summary.md"):
        path = SCENARIO / name
        long_lines = [number for number, line in enumerate(path.read_text().splitlines(), 1) if len(line) > 120]
        if long_lines:
            raise ValueError(f"{name} exceeds 120 columns on lines {long_lines}")
    (RUN / "local-checks.json").write_text(json.dumps({
        "checks": checks, "allCommandsPassed": True,
        "additional": "Scenario Python AST and changed Markdown 120-column checks passed.",
        "limitations": "Local tests are not Graph installation, quota, deployed agent, load or runtime acceptance.",
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
