"""Scenario-scoped cloud helpers. Import is local-only; calls require actual user authorization."""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = {
    "subscriptionId": "efd64343-6ef4-4926-951f-d3229f38bd76",
    "tenantId": "16b3c013-d300-468d-ac64-7eda0820b6d3",
}


def cli(*args: str) -> str:
    result = subprocess.run([shutil.which(args[0]) or args[0], *args[1:]], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        # Do not forward provider bodies, tokens or CLI debug output.
        raise RuntimeError(f"{args[0]} {args[1]} failed (exit {result.returncode}); inspect scoped sign-in/permissions.")
    return result.stdout.strip()


def environment() -> dict:
    return json.loads(cli("azd", "env", "get-values", "--output", "json"))


def verify_target() -> dict:
    account = json.loads(cli("az", "account", "show", "--output", "json"))
    if account["id"] != TARGET["subscriptionId"] or account["tenantId"] != TARGET["tenantId"]:
        raise RuntimeError("CLI target differs from reviewed target. No defaults changed.")
    return account


def request(method: str, url: str, audience: str, body: dict | None = None,
            headers: dict | None = None, missing_ok: bool = False) -> dict | None:
    """Bearer token stays in process memory; it is never persisted or logged."""
    token = cli("az", "account", "get-access-token", "--resource", audience,
                "--query", "accessToken", "--output", "tsv")
    values = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
    values.update(headers or {})
    call = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                  values, method=method)
    try:
        with urllib.request.urlopen(call, timeout=65) as response:
            data = response.read()
            return json.loads(data) if data else {}
    except urllib.error.HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise RuntimeError(f"Scoped {method} request failed: HTTP {error.code}. No broader permissions were requested.") from None


def receipt(name: str, value: dict) -> None:
    path = ROOT / "evidence" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
