"""Exercise real portal restart and shutdown using an isolated repository copy."""

from __future__ import annotations

import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from portal_server import process_alive, stop_process_tree


class SystemLifecycleTests(unittest.TestCase):
    def test_real_restart_reloads_backend_preserves_state_and_rotates_authentication(self) -> None:
        with tempfile.TemporaryDirectory(prefix="abc-system-test-") as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "portal").mkdir()
            for name in (
                "portal_server.py", "portal_workflow.py", "hack_workflow.py",
                "scenario_catalog.py", "check_prerequisites.py",
                "prerequisite_profiles.py",
            ):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
            shutil.copyfile(ROOT / "portal" / "catalog.json", root / "portal" / "catalog.json")
            shutil.copyfile(ROOT / "requirements.txt", root / "requirements.txt")
            shutil.copyfile(ROOT / "microsoft_industry_verticals.csv", root / "microsoft_industry_verticals.csv")
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            connection = root / ".abcbuilder-portal" / "server.json"
            marker = root / "generated-scenarios" / "saved-project" / "partial.txt"
            marker.parent.mkdir(parents=True)
            marker.write_text("Retain this interrupted work.", encoding="utf-8")
            with (root / "server.log").open("wb") as log:
                process = subprocess.Popen(
                    [sys.executable, "-B", str(root / "scripts" / "portal_server.py"),
                     "--port", str(port), "--quiet-url"],
                    cwd=root, stdout=log, stderr=subprocess.STDOUT,
                    env={**os.environ, "ABCBUILDER_PORTAL_RESTART_TOKEN": "isolated-test-token"},
                )
                server_pid = process.pid
                try:
                    config = self.wait_for_connection(connection)
                    before = self.call(port, config["token"], "GET", "/api/system")[1]
                    status, result = self.call(
                        port, config["token"], "POST", "/api/system/restart", {"confirmed": True},
                    )
                    self.assertEqual(202, status)
                    replacement = self.wait_for_connection(connection, previous_token=config["token"])
                    server_pid = replacement["pid"]
                    self.assertEqual(result["restartToken"], replacement["token"])
                    self.assertNotEqual(config["token"], replacement["token"])
                    self.assertEqual(403, self.call(port, config["token"], "GET", "/api/system")[0])
                    after = self.call(port, replacement["token"], "GET", "/api/system")[1]
                    self.assertNotEqual(before["startedAtUtc"], after["startedAtUtc"])
                    self.assertEqual(str(root), after["workspace"])
                    self.assertTrue(after["canStopServer"])
                    self.assertEqual("Retain this interrupted work.", marker.read_text(encoding="utf-8"))
                    self.assertEqual(202, self.call(
                        port, replacement["token"], "POST", "/api/system/stop", {"confirmed": True},
                    )[0])
                    deadline = time.monotonic() + 10
                    while (connection.exists() or process_alive(server_pid)) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertFalse(connection.exists(), "Stopped server must remove its connection record.")
                    self.assertFalse(process_alive(server_pid), "Replacement server must exit after shutdown.")
                finally:
                    if connection.exists():
                        config = json.loads(connection.read_text(encoding="utf-8"))
                        try:
                            self.call(port, config["token"], "POST", "/api/system/stop", {"confirmed": True})
                        except (OSError, http.client.HTTPException) as error:
                            print(f"Isolated test server cleanup failed: {error}", file=sys.stderr)
                    deadline = time.monotonic() + 10
                    while process_alive(server_pid) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    if process_alive(server_pid):
                        stop_process_tree(server_pid)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)

    def wait_for_connection(self, path: Path, previous_token: str | None = None) -> dict:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if path.exists():
                config = json.loads(path.read_text(encoding="utf-8"))
                if config["token"] != previous_token:
                    try:
                        status, _ = self.call(config["port"], config["token"], "GET", "/api/health")
                        if status == 200:
                            return config
                    except (OSError, http.client.HTTPException):
                        # The connection record is published just before the accept loop starts.
                        pass
            time.sleep(0.05)
        log = path.parent.parent / "server.log"
        detail = log.read_text(encoding="utf-8")[-4000:] if log.is_file() else "No server log was written."
        self.fail(f"Isolated portal did not publish a healthy connection within 15 seconds.\n{detail}")

    def call(self, port: int, token: str, method: str, path: str, data: dict | None = None) -> tuple[int, dict]:
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            client.request(
                method, path, body=json.dumps(data) if data is not None else None,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()
