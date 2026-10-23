"""Start or reuse the local portal and open its authenticated browser entry point."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from check_prerequisites import execution_environment
from portal_workflow import WORKFLOW_VERSION, state_directory

ROOT = Path(__file__).resolve().parents[1]
STATE = state_directory(ROOT)


def running_portal(expected_pid: int | None = None, expected_startup_id: str | None = None) -> dict | None:
    connection = STATE / "server.json"
    if not connection.exists():
        return None
    config = json.loads(connection.read_text(encoding="utf-8"))
    port, token = config.get("port"), config.get("token")
    if type(port) is not int or not 1 <= port <= 65535 or not isinstance(token, str) or not token:
        raise ValueError(f"Invalid local portal connection file. Inspect {STATE / 'server.json'}.")
    if expected_pid is not None and config.get("pid") != expected_pid:
        return None
    if expected_startup_id is not None and config.get("startupId") != expected_startup_id:
        return None
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    identified = False
    try:
        client.request("GET", "/api/health", headers={"Authorization": f"Bearer {token}"})
        response = client.getresponse()
        body = response.read()
        if response.status != 200:
            raise ValueError("Existing portal authentication failed. Inspect its server process before restarting.")
        health = json.loads(body)
        if health != {"status": "ok", "workspace": str(ROOT)}:
            raise ValueError("The local port is not serving this workspace's portal.")
        identified = True
        client.request("GET", "/api/catalog", headers={"Authorization": f"Bearer {token}"})
        response = client.getresponse()
        body = response.read()
        if response.status != 200:
            raise ValueError("Existing portal version check failed. Inspect its server before restarting.")
        catalog = json.loads(body)
        if (
            not isinstance(catalog, dict)
            or type(catalog.get("workflowVersion")) is not int
            or catalog["workflowVersion"] != WORKFLOW_VERSION
            or catalog.get("systemControlsVersion") != 1
            or catalog.get("prerequisitesVersion") != 1
        ):
            pid = config.get("pid")
            label = str(pid) if type(pid) is int and pid > 0 else "unknown"
            raise ValueError(
                f"An outdated portal server is still running (PID {label}). "
                "The launcher reuses servers; it does not restart them. "
                "Finish or stop active workers, stop that server, then run Start-ABCBuilder.cmd again."
            )
        return config
    except (ConnectionRefusedError, TimeoutError) as error:
        if identified:
            raise RuntimeError(
                "The existing portal answered health but its version check timed out or disconnected. "
                "No replacement was started; inspect that server before restarting."
            ) from error
        return None
    finally:
        client.close()


def ensure_portal() -> dict:
    config = running_portal()
    if config is not None:
        return config
    STATE.mkdir(exist_ok=True)
    environment = execution_environment(ROOT)
    startup_id = secrets.token_hex(32)
    environment["ABCBUILDER_PORTAL_STARTUP_ID"] = startup_id
    virtual_environment = ROOT / ".venv"
    python = virtual_environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        python = Path(sys.executable)
    with (STATE / "server.log").open("ab") as log:
        options = (
            {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(
            [str(python), str(ROOT / "scripts" / "portal_server.py"), "--quiet-url"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            env=environment,
            **options,
        )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        config = running_portal(expected_startup_id=startup_id)
        if config is not None:
            return config
        if process.poll() is not None:
            raise RuntimeError(
                f"Portal startup failed. Inspect {STATE / 'server.log'}; port 8765 may be in use."
            )
        time.sleep(0.1)
    process.terminate()
    process.wait(timeout=5)
    raise RuntimeError(f"Portal did not become ready in 10 seconds. Inspect {STATE / 'server.log'}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", action="store_true", help="Return hook JSON without exposing the private URL.")
    args = parser.parse_args()
    if os.environ.get("ABCBUILDER_PORTAL_JOB") == "1" or os.environ.get("HACKBUILDER_PORTAL_JOB") == "1":
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
