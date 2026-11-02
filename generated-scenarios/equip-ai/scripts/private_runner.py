"""Prepare locally or execute the reviewed private publishing path. No implicit provisioning."""

from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "efd64343-6ef4-4926-951f-d3229f38bd76"
GROUP = "rg-equip-ai"
VM = "vm-equip-management-equip-ai"
REMOTE = "/var/lib/equip-ai-install"


def package(publish: Path) -> bytes:
    """Only allow application publish outputs, never repository/identity/azd files."""
    if not (publish / "EquipAI.Web").is_file():
        raise ValueError("A self-contained Linux publish directory is required.")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(publish.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(publish)
            if path.is_symlink() or any(part.startswith(".") for part in relative.parts):
                raise ValueError("Hidden files or symlinks must not enter the installation artifact.")
            if path.suffix.lower() in {".pfx", ".pem", ".key", ".env"}:
                raise ValueError("Credential-like file rejected.")
            archive.write(path, relative.as_posix())
    return stream.getvalue()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward publishing credentials to a redirected origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(f"SCM staging unexpectedly redirected (HTTP {code}).")


def wait_application(origin: str, build_id: str, version: str) -> dict:
    """Require the actual published binary and pinned configuration, not a previous warm container."""
    parsed = urlparse(origin)
    if (parsed.scheme != "https" or parsed.hostname != "app-equip-web-equipai-kex72v.azurewebsites.net"
            or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443)
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Readiness URL does not match the approved public reference.")
    opener = urllib.request.build_opener(NoRedirect())
    last = "no response"
    for attempt in range(36):
        try:
            response = opener.open(origin.rstrip("/") + "/health", timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        except (urllib.error.URLError, TimeoutError) as error:
            last = type(error).__name__
            response = None
        if response is not None:
            with response:
                status = response.code
                content_type = response.headers.get("Content-Type", "")
                raw = response.read(8193)
            if status not in (200, 404, 502, 503, 504):
                raise RuntimeError(f"Unexpected application readiness HTTP {status}.")
            last = f"HTTP {status}"
            if status == 200 and "application/json" in content_type:
                if len(raw) > 8192:
                    raise RuntimeError("Unexpectedly large application health response.")
                health = json.loads(raw)
                if health.get("buildId") == build_id and str(health.get("agentVersion")) == version:
                    return health
                last = "previous build or agent version still serving"
        if attempt < 35:
            print(f"Waiting for exact deployed build/configuration: {last}.", flush=True)
            time.sleep(5)
    raise RuntimeError(f"Deployed application did not become ready after 36 probes: {last}.")


def stage_artifact(name: str, digest: str, payload: bytes | None) -> None:
    executable = shutil.which("az")
    if not executable:
        raise RuntimeError("Azure CLI is unavailable.")
    result = subprocess.run(
        [executable, "account", "get-access-token", "--subscription", SUBSCRIPTION,
         "--resource", "https://management.azure.com/", "--query", "accessToken", "--output", "tsv"],
        capture_output=True, text=True, check=False, timeout=120)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError(f"Cannot obtain scoped SCM publishing token: {result.stderr[-1000:]}")
    request = urllib.request.Request(
        f"https://{name}.scm.azurewebsites.net/api/vfs/data/equip-ai-{digest}.zip",
        data=payload, method="PUT" if payload is not None else "DELETE",
        headers={"Authorization": "Bearer " + result.stdout.strip(), "If-Match": "*",
                 "Content-Type": "application/octet-stream"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=300) as response:
        if response.status not in {200, 201, 204}:
            raise RuntimeError(f"SCM artifact operation failed (HTTP {response.status}).")


def invoke(script: str) -> str:
    """Action Run Command is serial, root-level and limited to 4 KiB returned output."""
    executable = shutil.which("az")
    if not executable:
        raise RuntimeError("Azure CLI is unavailable; do not install shared tooling here.")
    with tempfile.TemporaryDirectory(prefix="equip-run-") as folder:
        path = Path(folder) / "operation.sh"
        path.write_text(script, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [executable, "vm", "run-command", "invoke", "--subscription", SUBSCRIPTION,
             "--resource-group", GROUP, "--name", VM, "--command-id", "RunShellScript",
             "--scripts", f"@{path}", "--output", "json"],
            capture_output=True, text=True, check=False, timeout=5600,
        )
    if result.returncode:
        raise RuntimeError(f"Run Command failed: {result.stderr[-1500:]}")
    document = json.loads(result.stdout)
    output = "\n".join(item.get("message", "") for item in document.get("value", []))
    # ARM success is not guest-script success. Every caller requires its explicit success marker.
    return output


def finish_script(digest: str, config: dict) -> str:
    allowed = ("AZURE_AI_PROJECT_ENDPOINT", "AZURE_MODEL_DEPLOYMENT_NAME")
    values = {key: config[key] for key in allowed}
    values["AgentName"] = "equipment-operations"
    if config.get("AccountSeedDigest"):
        if not config.get("AZURE_STORAGE_ACCOUNT_NAME", "").isalnum():
            raise ValueError("Missing generated account storage name.")
        values["StorageEndpoint"] = f"https://{config['AZURE_STORAGE_ACCOUNT_NAME']}.blob.core.windows.net"
        values["AccountSeedDigest"] = config["AccountSeedDigest"]
    encoded = base64.b64encode(json.dumps(values).encode()).decode()
    guest = (ROOT / "scripts" / "runner_guest.py").read_text(encoding="utf-8")
    guest64 = base64.b64encode(guest.encode()).decode()
    return (
        f"set -eu\numask 077\nmkdir -p {REMOTE}/{digest}\ncd {REMOTE}/{digest}\n"
        f"printf '%s' '{guest64}' | base64 -d > guest.py\n"
        f"python3 guest.py --download-artifact '{config['AZURE_WEB_NAME']}' '{digest}'\n"
        f"echo '{digest}  app.zip' | sha256sum -c -\n"
        f"python3 guest.py '{encoded}' '{config['AZURE_WEB_NAME']}' '{config['AZURE_CLEANER_NAME']}'\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "publish", "clean"])
    parser.add_argument("--publish-directory", type=Path)
    args = parser.parse_args()
    # An explicit execution guard prevents accidental azd deployment before the new scope is authorized.
    if args.mode != "plan" and os.environ.get("EQUIP_PRIVATE_RUNNER_APPROVED") != "true":
        raise ValueError("New management scope must be explicitly approved before remote execution.")
    if args.mode == "clean":
        output = invoke(f"set -eu\nrm -rf {REMOTE}\necho EQUIP_CLEAN_OK\n")
        if "EQUIP_CLEAN_OK" not in output:
            raise RuntimeError("Guest cleanup did not return a success marker.")
        print("Guest installation workspace removed; VM/disk/NAT/IP still charge until removed.")
        return 0
    if args.publish_directory is None:
        raise ValueError("--publish-directory must identify reviewed Linux publish outputs.")
    payload = package(args.publish_directory)
    digest = hashlib.sha256(payload).hexdigest()
    print(json.dumps({"sha256": digest, "bytes": len(payload),
                      "transport": "authenticated-existing-web-scm-data-directory",
                      "executed": args.mode != "plan"}), flush=True)
    if args.mode == "plan":
        return 0
    config = dict(os.environ)
    for key in ("AZURE_WEB_NAME", "AZURE_CLEANER_NAME"):
        if not config.get(key, "").replace("-", "").isalnum():
            raise ValueError(f"Missing or invalid generated output: {key}")
    seed = (ROOT / ".private" / "account-seed.json").read_bytes()
    seed_digest = hashlib.sha256(seed).hexdigest()
    config["AccountSeedDigest"] = seed_digest
    finish = finish_script(digest, config)
    with ExitStack() as cleanup:
        stage_artifact(config["AZURE_WEB_NAME"], seed_digest, seed)
        cleanup.callback(stage_artifact, config["AZURE_WEB_NAME"], seed_digest, None)
        stage_artifact(config["AZURE_WEB_NAME"], digest, payload)
        cleanup.callback(stage_artifact, config["AZURE_WEB_NAME"], digest, None)
        output = invoke(finish)
        if "EQUIP_PUBLISH_OK" not in output:
            raise RuntimeError(f"Private publication/initialization failed: {output[-2000:]}")
    print(output[-3000:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
