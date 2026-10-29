"""Verify one owned local container on loopback without mounts, cloud access or permission changes."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import subprocess
import time
import uuid


def docker(*arguments: str) -> str:
    result = subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, encoding="utf-8", timeout=45, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"docker {arguments[0]} failed ({result.returncode}): {result.stdout}{result.stderr}")
    return (result.stdout + result.stderr if arguments[0] == "logs" else result.stdout).strip()


def get(port: int, path: str) -> tuple[int, str]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read(1024 * 1024).decode("utf-8")
    finally:
        connection.close()


def verify(image: str, marker: str, timeout: int = 90) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*:[A-Za-z0-9_.-]+", image):
        raise ValueError("Specify an existing explicitly tagged local image.")
    if not marker.strip() or not 1 <= timeout <= 180:
        raise ValueError("Specify a nonempty homepage marker and timeout of 1-180 seconds.")
    report = {
        "image": image, "ok": False, "checks": [], "logs": "", "error": None,
        "cleanupPassed": False, "scope": "local-shell-liveness-only; no Azure or agent invocation",
    }
    container_id = None
    try:
        metadata = json.loads(docker("image", "inspect", image))
        if len(metadata) != 1 or metadata[0]["Os"] != "linux" or metadata[0]["Architecture"] != "amd64":
            raise RuntimeError("The owned image must be linux/amd64.")
        user = metadata[0]["Config"].get("User", "")
        if not user or user.split(":")[0] in {"0", "root"}:
            raise RuntimeError("The image must declare a non-root runtime user.")
        report["checks"].append(f"Image inspected: linux/amd64; user={user}")
        container_id = docker(
            "run", "--detach", "--rm", "--pull=never", "--read-only", "--platform", "linux/amd64",
            "--name", f"abcbuilder-verify-{uuid.uuid4().hex[:12]}",
            "--label", "abcbuilder.purpose=local-runtime-verification",
            "--publish", "127.0.0.1::8080", "--env", "APP_ROLE=web", image,
        )
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            raise RuntimeError(f"Docker returned an invalid owned container ID: {container_id}")
        binding = docker("port", container_id, "8080/tcp")
        match = re.fullmatch(r"127\.0\.0\.1:(\d+)", binding)
        if not match:
            raise RuntimeError(f"Expected one loopback-only port binding; received {binding!r}.")
        port = int(match[1])
        deadline = time.monotonic() + timeout
        last_failure = "No health response received."
        while time.monotonic() < deadline:
            try:
                status, _ = get(port, "/health/live")
                if status == 200:
                    break
                last_failure = f"Health returned HTTP {status}."
            except (OSError, http.client.HTTPException) as error:
                last_failure = f"{type(error).__name__}: {error}"
            time.sleep(0.5)
        else:
            raise RuntimeError(f"Container health did not pass within {timeout}s: {last_failure}")
        report["checks"].append("GET /health/live: HTTP 200 on loopback")
        status, content = get(port, "/")
        if status != 200 or marker not in content:
            raise RuntimeError(f"Homepage failed: HTTP {status}; expected marker present={marker in content}.")
        report["checks"].append(f"GET /: HTTP 200; marker={marker}")
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError, http.client.HTTPException) as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        if container_id and re.fullmatch(r"[0-9a-f]{64}", container_id):
            try:
                report["logs"] = docker("logs", "--tail", "40", container_id)
            except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                report["logs"] = f"Log collection failed: {error}"
                report["error"] = f"{report['error'] or ''}\n{report['logs']}".strip()
            try:
                docker("stop", "--time", "5", container_id)
                report["cleanupPassed"] = True
            except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                report["error"] = f"{report['error'] or ''}\nOwned-container cleanup failed: {error}".strip()
    report["ok"] = report["error"] is None and report["cleanupPassed"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    try:
        report = verify(args.image, args.marker, args.timeout)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
