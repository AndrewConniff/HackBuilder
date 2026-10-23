"""Execute the fixed local setup recipe; never accept arbitrary commands or change cloud resources."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from check_prerequisites import TOOLS, execution_environment


def repair(root: Path, report: dict) -> list[dict]:
    environment = execution_environment(root)
    python = root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / (
        "python.exe" if sys.platform == "win32" else "python"
    )
    packages = {spec[0]: spec[5] for spec in TOOLS if spec[5]}
    packages.update({
        "docker": "Docker.DockerDesktop", "k6": "GrafanaLabs.k6",
        "functions-core-tools": "Microsoft.Azure.FunctionsCoreTools",
    })
    commands = []
    failed = [item for item in report["checks"] if not item["ok"]]
    for item in failed:
        if item["id"] in packages and item.get("installed") is False:
            if sys.platform != "win32":
                raise ValueError(f"Native setup for {item['id']} requires the approved OS package manager.")
            winget = shutil.which("winget", path=environment["PATH"])
            if not winget:
                raise ValueError("WinGet is unavailable. Install approved App Installer; no alternative download is attempted.")
            commands.append([
                winget, "install", "--id", packages[item["id"]], "--exact", "--source", "winget", "--silent",
                "--disable-interactivity", "--accept-package-agreements", "--accept-source-agreements",
            ])
    if not python.is_file():
        raise ValueError("Repository .venv is unavailable. Repair the bootstrap environment before starting this portal.")
    if any(item["id"].startswith("python-package:") or item["id"] == "pip-health" for item in failed):
        commands.append([str(python), "-m", "pip", "install", "-r", str(root / "requirements.txt")])
    if any(item["id"] == "bicep" for item in failed):
        az = shutil.which("az", path=environment["PATH"])
        if az:
            commands.append([az, "bicep", "install"])
    if any(item["id"] == "chromium-runtime" for item in failed):
        commands.append([str(python), "-m", "playwright", "install", "chromium"])
    evidence = []
    for command in commands:
        try:
            result = subprocess.run(
                command, cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8",
                timeout=600, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError(f"Local setup could not complete {Path(command[0]).name}: {error}") from error
        evidence.append({"command": command, "exitCode": result.returncode, "output": (result.stdout + result.stderr)[-3000:]})
        if result.returncode:
            raise ValueError(f"Local setup failed for {Path(command[0]).name}: {evidence[-1]['output']}")
    return evidence
