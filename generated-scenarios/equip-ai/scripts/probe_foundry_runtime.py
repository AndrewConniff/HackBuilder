"""Diagnose the approved private Foundry path without printing tokens or model output."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json

from install_identity import save
from private_runner import ROOT, invoke, package, stage_artifact
from validate_live import values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", action="store_true", help="Run the same .NET SDK on the existing private VM.")
    args = parser.parse_args()
    values()
    if args.sdk:
        result = invoke_sdk()
        save_result("private-sdk-probe.json", result)
        print(result)
        return
    code = r'''
import json, socket, urllib.request, urllib.error, urllib.parse
account = "ai-equip-equipai-kex72v"
project = f"https://{account}.services.ai.azure.com/api/projects/equipment-operations"
query = urllib.parse.urlencode({"api-version": "2018-02-01", "resource": "https://ai.azure.com/"})
request = urllib.request.Request(
    "http://169.254.169.254/metadata/identity/oauth2/token?" + query, headers={"Metadata": "true"})
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=30) as response:
    bearer = json.load(response)["access_token"]
results = []
operations = [
    ("project-agent-list", project + "/agents?api-version=2025-11-15-preview", None),
    ("project-model-response", project + "/openai/v1/responses",
     {"model": "equip-support", "input": "Reply with OK.", "store": False, "max_output_tokens": 32}),
    ("project-agent-response", project + "/openai/v1/responses",
     {"agent_reference": {"type": "agent_reference", "name": "equipment-operations", "version": "1"},
      "input": "Refuse to control equipment.", "store": False, "max_output_tokens": 128}),
]
for name, url, body in operations:
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + bearer, "Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(request, timeout=90)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read()
        details = {"name": name, "status": response.code, "bytes": len(raw),
                   "requestId": response.headers.get("apim-request-id"),
                   "server": response.headers.get("Server")}
        if response.code >= 400 and raw:
            try:
                error = json.loads(raw).get("error", {})
                details["errorCode"] = error.get("code")
                details["errorMessage"] = error.get("message", "")[:400]
            except json.JSONDecodeError:
                details["errorBodyType"] = response.headers.get("Content-Type")
        results.append(details)
print(json.dumps({"host": socket.gethostname(),
    "dns": socket.gethostbyname(account + ".services.ai.azure.com"), "results": results}))
'''
    encoded = base64.b64encode(code.encode()).decode()
    result = invoke(f"set -eu\nprintf '%s' '{encoded}' | base64 -d | python3\n")
    save_result("private-runtime-probes.json", result)
    print(result)


def save_result(name: str, result: str) -> None:
    save(ROOT / "local-evidence" / "resume-20261028" / name, {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "identity": "Existing management VM managed identity; not deploying-user or web-identity acceptance",
        "output": result,
    })


def invoke_sdk() -> str:
    payload = package(ROOT / "local-evidence" / "resume-20261028" / "probe-publish")
    digest = hashlib.sha256(payload).hexdigest()
    name = "app-equip-web-equipai-kex72v"
    code = r'''
import hashlib, io, json, os, pathlib, subprocess, urllib.parse, urllib.request, zipfile
digest = DIGEST
root = pathlib.Path("/var/lib/equip-ai-install") / ("probe-" + digest)
root.mkdir(mode=0o700, exist_ok=True)
query = urllib.parse.urlencode({"api-version": "2018-02-01", "resource": "https://management.azure.com/"})
request = urllib.request.Request("http://169.254.169.254/metadata/identity/oauth2/token?" + query,
    headers={"Metadata": "true"})
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=30) as response:
    bearer = json.load(response)["access_token"]
request = urllib.request.Request(
    "https://app-equip-web-equipai-kex72v.scm.azurewebsites.net/api/vfs/data/equip-ai-" + digest + ".zip",
    headers={"Authorization": "Bearer " + bearer})
with urllib.request.urlopen(request, timeout=300) as response:
    payload = response.read()
if hashlib.sha256(payload).hexdigest() != digest:
    raise ValueError("Artifact digest mismatch.")
with zipfile.ZipFile(io.BytesIO(payload)) as archive:
    for member in archive.infolist():
        if not (root / member.filename).resolve().is_relative_to(root.resolve()):
            raise ValueError("Unsafe artifact path.")
    archive.extractall(root)
executable = root / "EquipAI.Web"
executable.chmod(0o700)
config = {"AZURE_AI_PROJECT_ENDPOINT":
    "https://ai-equip-equipai-kex72v.services.ai.azure.com/api/projects/equipment-operations",
    "AgentName": "equipment-operations", "AgentVersion": "1"}
result = subprocess.run([str(executable), "--probe-agent"], cwd=root,
    env={**os.environ, **config}, capture_output=True, text=True, timeout=180, check=False)
print(json.dumps({"operation": "private-sdk-agent-probe", "exitCode": result.returncode,
    "stdout": result.stdout[-1500:], "stderr": result.stderr[-1500:]}))
if result.returncode:
    raise RuntimeError("Private SDK probe failed.")
print("EQUIP_SDK_PROBE_OK")
'''.replace("DIGEST", repr(digest))
    stage_artifact(name, digest, payload)
    try:
        encoded = base64.b64encode(code.encode()).decode()
        result = invoke(f"set -eu\nprintf '%s' '{encoded}' | base64 -d | python3\n")
        if "EQUIP_SDK_PROBE_OK" not in result:
            save_result("private-sdk-probe-failed.json", result)
            raise RuntimeError("Private SDK probe did not pass; see redacted diagnostic evidence.")
        return result
    finally:
        stage_artifact(name, digest, None)


if __name__ == "__main__":
    main()
