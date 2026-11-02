"""Participant destination guard only. Import performs no cloud operation."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cli(*args: str) -> str:
    result = subprocess.run([shutil.which(args[0]) or args[0], *args[1:]], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{args[0]} {args[1]} failed (exit {result.returncode}); inspect scoped access.")
    return result.stdout.strip()


def environment() -> dict:
    return json.loads(cli("azd", "env", "get-values", "--output", "json"))


def verify_target() -> dict:
    """Require explicit participant-only target choices before authorized provision."""
    env = environment()
    required = ("AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID", "AZURE_LOCATION",
                "AZURE_ENV_NAME", "AZURE_RESOURCE_GROUP")
    if any(not env.get(key) or env[key].startswith(("<", "[")) for key in required):
        raise RuntimeError("Choose explicit destination subscription, tenant, region, environment and group.")
    name = env["AZURE_ENV_NAME"]
    valid = bool(re.fullmatch(r"(0[1-9]|1[0-9]|20)-feedback-campaign-hack", name))
    if not valid or env["AZURE_RESOURCE_GROUP"] != "rg-" + name:
        raise RuntimeError("Destination environment/group violates participant isolation.")
    account = json.loads(cli("az", "account", "show", "--output", "json"))
    if account["id"] != env["AZURE_SUBSCRIPTION_ID"] or account["tenantId"] != env["AZURE_TENANT_ID"]:
        raise RuntimeError("CLI target differs from explicit destination. No defaults changed.")
    return account
