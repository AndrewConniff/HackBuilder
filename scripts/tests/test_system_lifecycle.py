"""Exercise the real visualization server without starting agents or changing saved scenarios."""

from __future__ import annotations

import http.client
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SystemLifecycleTests(unittest.TestCase):
    def test_only_the_approved_portal_implementation_is_shipped(self) -> None:
        for relative in (
            "scripts/portal_server.py", "scripts/portal_workflow.py", "scripts/workflow_engine.py",
            "scripts/backend_readiness.py", "scripts/setup_backend.py",
            "portal/index.html", "portal/app.js", "portal/styles.css",
        ):
            with self.subTest(path=relative):
                self.assertFalse((ROOT / relative).exists(), f"Retired portal source was reintroduced: {relative}")
        for relative in (
            "scripts/portal_visualizer.py", "scripts/portal_status.py", "scripts/start_portal.py",
            "portal/visualizer.html", "portal/visualizer.js", "portal/visualizer.css", "portal/markdown.js",
        ):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), f"Approved portal source is missing: {relative}")

    def test_real_visualizer_preserves_state_and_has_no_worker_or_approval_endpoints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fbc-system-test-") as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "portal").mkdir()
            for name in (
                "portal_visualizer.py", "portal_status.py", "scenario_catalog.py", "hack_workflow.py",
                "azure_context.py", "check_prerequisites.py", "prerequisite_profiles.py", "scenario_chat.py",
                "scenario_adapt.py", "scenario_match.py",
            ):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
            for name in ("catalog.json", "visualizer.html", "visualizer.js", "visualizer.css", "markdown.js"):
                shutil.copyfile(ROOT / "portal" / name, root / "portal" / name)
            shutil.copyfile(ROOT / "microsoft_industry_verticals.csv", root / "microsoft_industry_verticals.csv")
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            connection = root / ".fbcbuilder-portal" / "server.json"
            marker = root / "generated-scenarios" / "saved-project" / "partial.txt"
            marker.parent.mkdir(parents=True)
            marker.write_text("Retain this interrupted work.", encoding="utf-8")
            with (root / "server.log").open("wb") as log:
                process = subprocess.Popen(
                    [sys.executable, "-B", str(root / "scripts" / "portal_visualizer.py"),
                     "--port", str(port), "--quiet-url"],
                    cwd=root, stdout=log, stderr=subprocess.STDOUT,
                )
                try:
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            self.fail((root / "server.log").read_text(encoding="utf-8"))
                        if connection.exists():
                            break
                        time.sleep(.05)
                    self.assertTrue(connection.exists(), "Server did not publish a connection record.")
                    config = json.loads(connection.read_text(encoding="utf-8"))
                    self.assertNotIn("token", config)
                    self.assertEqual("visualizer", self.call(port, "GET", "/api/catalog")[1]["portalMode"])
                    scenarios = self.call(port, "GET", "/api/scenarios")[1]
                    self.assertEqual("saved-project", scenarios[0]["projectSlug"])
                    for endpoint in ("/api/runs", "/api/system/azure-identity", "/api/runs/old/continue"):
                        self.assertEqual(404, self.call(port, "POST", endpoint)[0])
                    self.assertEqual("Retain this interrupted work.", marker.read_text(encoding="utf-8"))
                    self.assertFalse((root / ".fbcbuilder-portal" / "projects").exists())
                finally:
                    process.terminate()
                    process.wait(timeout=10)

    def call(self, port: int, method: str, path: str) -> tuple[int, object]:
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            client.request(method, path, body="{}" if method == "POST" else None,
                           headers={"Content-Type": "application/json"})
            response = client.getresponse()
            return response.status, json.loads(response.read())
        finally:
            client.close()
