"""Start or reuse the local portal and open its authenticated browser entry point."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".hackbuilder-portal"


def running_portal() -> dict | None:
    connection = STATE / "server.json"
    if not connection.exists():
        return None
    config = json.loads(connection.read_text(encoding="utf-8"))
    port, token = config.get("port"), config.get("token")
    if type(port) is not int or not 1 <= port <= 65535 or not isinstance(token, str) or not token:
        raise ValueError("Invalid local portal connection file. Inspect .hackbuilder-portal\\server.json.")
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        client.request("GET", "/api/health", headers={"Authorization": f"Bearer {token}"})
        response = client.getresponse()
        body = response.read()
        if response.status != 200:
            raise ValueError("Existing portal authentication failed. Inspect its server process before restarting.")
        health = json.loads(body)
        if health != {"status": "ok", "workspace": str(ROOT)}:
            raise ValueError("The local port is not serving this workspace's portal.")
        return config
    except (ConnectionRefusedError, TimeoutError):
        return None
    finally:
        client.close()


def ensure_portal() -> dict:
    config = running_portal()
    if config is not None:
        return config
    STATE.mkdir(exist_ok=True)
    with (STATE / "server.log").open("ab") as log:
        options = (
            {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "portal_server.py"), "--quiet-url"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            **options,
        )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        config = running_portal()
        if config is not None:
            return config
        if process.poll() is not None:
            raise RuntimeError(
                "Portal startup failed. Inspect .hackbuilder-portal\\server.log; port 8765 may be in use."
            )
        time.sleep(0.1)
    process.terminate()
    process.wait(timeout=5)
    raise RuntimeError("Portal did not become ready in 10 seconds. Inspect .hackbuilder-portal\\server.log.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", action="store_true", help="Return hook JSON without exposing the private URL.")
    args = parser.parse_args()
    if os.environ.get("HACKBUILDER_PORTAL_JOB") == "1":
        if args.hook:
            print("{}")
        else:
            print("Portal-launched CLI job: browser startup skipped.")
        return 0
    try:
        config = ensure_portal()
        url = f"http://127.0.0.1:{config['port']}/#token={config['token']}"
        if not webbrowser.open(url):
            raise RuntimeError(
                "Portal is ready, but the browser could not be opened. Retry python scripts\\start_portal.py."
            )
        if args.hook:
            print("{}")
        else:
            print(f"Portal ready at http://127.0.0.1:{config['port']}/ and opened with local authentication.")
        return 0
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
        print(f"Portal startup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
