"""Runs only on the private VM. Uses IMDS for SCM publishing; never prints bearer tokens."""

import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile


def token() -> str:
    query = urllib.parse.urlencode({"api-version": "2018-02-01", "resource": "https://management.azure.com/"})
    request = urllib.request.Request(
        "http://169.254.169.254/metadata/identity/oauth2/token?" + query, headers={"Metadata": "true"})
    # IMDS must never traverse an inherited HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=30) as response:
        return json.load(response)["access_token"]


def deployment_status_url(name: str, location: str | None) -> str:
    if not location:
        raise RuntimeError("SCM did not return a deployment status URL.")
    origin = f"https://{name}.scm.azurewebsites.net/"
    resolved = urllib.parse.urljoin(origin, location)
    parsed = urllib.parse.urlparse(resolved)
    if (parsed.scheme != "https" or parsed.hostname != urllib.parse.urlparse(origin).hostname
            or (parsed.port or 443) != 443 or parsed.username is not None or parsed.password is not None
            or not parsed.path.startswith("/api/deployments/")):
        raise RuntimeError("SCM did not return a same-origin HTTPS deployment status URL.")
    return resolved


def publish(name: str, payload: bytes) -> None:
    uri = f"https://{name}.scm.azurewebsites.net/api/zipdeploy?isAsync=true"
    request = urllib.request.Request(
        uri, data=payload, method="POST",
        headers={"Authorization": "Bearer " + token(), "Content-Type": "application/zip"})
    with urllib.request.urlopen(request, timeout=120) as response:
        location = deployment_status_url(name, response.headers.get("Location"))
    for _ in range(120):
        time.sleep(5)
        request = urllib.request.Request(location, headers={"Authorization": "Bearer " + token()})
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
        if result.get("status") == 4:
            return
        if result.get("status") == 3:
            raise RuntimeError("SCM deployment failed; inspect scoped deployment logs without tokens.")
    raise TimeoutError("SCM deployment did not complete within ten minutes.")


def download_artifact(name: str, digest: str) -> bytes:
    if not name.replace("-", "").isalnum() or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError("Invalid scoped artifact source or digest.")
    request = urllib.request.Request(
        f"https://{name}.scm.azurewebsites.net/api/vfs/data/equip-ai-{digest}.zip",
        headers={"Authorization": "Bearer " + token()})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise RuntimeError("SCM artifact download unexpectedly redirected.")

    with urllib.request.build_opener(NoRedirect()).open(request, timeout=300) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Downloaded artifact SHA-256 does not match the approved local artifact.")
    return payload


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "--download-artifact":
        name, digest = sys.argv[2:4]
        Path("app.zip").write_bytes(download_artifact(name, digest))
        print("EQUIP_ARTIFACT_OK")
        return
    config = json.loads(base64.b64decode(sys.argv[1]))
    names = sys.argv[2:4]
    if len(names) != 2 or any(not name.replace("-", "").isalnum() for name in names):
        raise ValueError("Invalid generated app names.")
    endpoint = urllib.parse.urlparse(config["AZURE_AI_PROJECT_ENDPOINT"])
    if endpoint.scheme != "https" or not endpoint.hostname or not endpoint.hostname.endswith(".services.ai.azure.com"):
        raise ValueError("Invalid Foundry project endpoint.")
    # Confirm actual private resolution before any publication or initialization.
    import ipaddress
    for host in (endpoint.hostname, names[1] + ".scm.azurewebsites.net"):
        addresses = [item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]
        if not addresses or any(not ipaddress.ip_address(address).is_private for address in addresses):
            raise RuntimeError("Private DNS acceptance failed.")
    with zipfile.ZipFile("app.zip") as archive:
        root = Path("app").resolve()
        for member in archive.infolist():
            if not (root / member.filename).resolve().is_relative_to(root):
                raise ValueError("Unsafe archive path.")
        archive.extractall(root)
    executable = root / "EquipAI.Web"
    executable.chmod(0o700)
    result = subprocess.run(
        [str(executable), "--install-agent"], cwd=root, env={**os.environ, **config},
        capture_output=True, text=True, timeout=600, check=False)
    if result.returncode:
        raise RuntimeError(
            f"Agent installation failed ({result.returncode}): {result.stderr[-2000:]}; "
            "no inference or publication success is implied.")
    receipt = json.loads(result.stdout.strip().splitlines()[-1])
    if config.get("AccountSeedDigest"):
        seed_path = Path.cwd() / "account-seed.json"
        seed_path.write_bytes(download_artifact(names[0], config["AccountSeedDigest"]))
        result = subprocess.run(
            [str(executable), "--install-accounts"], cwd=root,
            env={**os.environ, **config, "AccountSeed": str(seed_path)},
            capture_output=True, text=True, timeout=600, check=False)
        if result.returncode:
            raise RuntimeError(f"Local account installation failed: {result.stderr[-2000:]}")
        seed_path.unlink()
    # Return generated version, not a fabricated inference receipt; local hook captures it.
    for name in names:
        publish(name, Path("app.zip").read_bytes())
    print(json.dumps({"agent": receipt, "publishedApps": names,
                      "runtimeAcceptance": "pending", "privateDns": "passed",
                      "localAccountsInstalled": bool(config.get("AccountSeedDigest"))}))
    print("EQUIP_PUBLISH_OK")


if __name__ == "__main__":
    main()
