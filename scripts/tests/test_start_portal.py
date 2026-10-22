"""Check local portal discovery, lifecycle ownership and agent startup guards."""

from __future__ import annotations

import contextlib
import http.client
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("start_portal", ROOT / "scripts" / "start_portal.py")
assert SPEC is not None and SPEC.loader is not None
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class PortalStartupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.state_patch = patch.object(launcher, "STATE", self.state)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.config = {"pid": 123, "port": 8765, "token": "test-local-token"}

    def write_connection(self, config: dict | None = None) -> None:
        (self.state / "server.json").write_text(json.dumps(config or self.config), encoding="utf-8")

    def test_missing_connection_is_not_running(self) -> None:
        self.assertIsNone(launcher.running_portal())

    def test_vscode_task_uses_existing_helper_without_shell_or_auto_execution(self) -> None:
        tasks = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
        task = next(item for item in tasks if item["label"] == "Hack Builder: Open Portal")
        self.assertEqual("process", task["type"])
        self.assertEqual("python", task["command"])
        self.assertEqual(["${workspaceFolder}\\scripts\\start_portal.py"], task["args"])
        self.assertNotIn("runOptions", task)

    @unittest.skipUnless(os.name == "nt", "Windows click launcher")
    def test_click_launcher_runs_from_another_directory_and_returns_helper_status(self) -> None:
        for code in (0, 7):
            with self.subTest(code=code), tempfile.TemporaryDirectory(prefix="portal launcher ") as temp:
                root = Path(temp)
                (root / "scripts").mkdir()
                (root / "Start-HackBuilder.cmd").write_bytes((ROOT / "Start-HackBuilder.cmd").read_bytes())
                (root / "scripts" / "start_portal.py").write_text(
                    f"print('launcher-helper-ok'); raise SystemExit({code})\n", encoding="utf-8",
                )
                result = subprocess.run(
                    [os.environ["ComSpec"], "/d", "/c", str(root / "Start-HackBuilder.cmd")],
                    cwd=ROOT.parent, input="\n", capture_output=True, text=True, timeout=15, check=False,
                )
                self.assertEqual(code, result.returncode, result.stdout + result.stderr)
                self.assertIn("launcher-helper-ok", result.stdout)

    def test_authenticated_health_identifies_this_workspace(self) -> None:
        self.write_connection()
        client = Mock()
        response = client.getresponse.return_value
        response.status = 200
        response.read.return_value = json.dumps({"status": "ok", "workspace": str(ROOT)}).encode()
        with patch.object(launcher.http.client, "HTTPConnection", return_value=client) as connection:
            self.assertEqual(self.config, launcher.running_portal())
        connection.assert_called_once_with("127.0.0.1", 8765, timeout=1)
        client.request.assert_called_once_with(
            "GET", "/api/health", headers={"Authorization": "Bearer test-local-token"}
        )
        client.close.assert_called_once()

    def test_stale_connection_allows_restart(self) -> None:
        self.write_connection()
        for error in (ConnectionRefusedError(), TimeoutError()):
            client = Mock()
            client.request.side_effect = error
            with (
                self.subTest(error=type(error).__name__),
                patch.object(launcher.http.client, "HTTPConnection", return_value=client),
            ):
                self.assertIsNone(launcher.running_portal())
                client.close.assert_called_once()

    def test_invalid_local_connection_is_explicit_error(self) -> None:
        for values in ({"port": "8765"}, {"port": True}, {"port": 70000}, {"token": ""}):
            self.write_connection({**self.config, **values})
            with self.subTest(values=values), self.assertRaises(ValueError):
                launcher.running_portal()

    def test_foreign_or_unauthorized_server_is_not_replaced(self) -> None:
        self.write_connection()
        for status, body in ((403, {}), (200, {"status": "ok", "workspace": "other"})):
            client = Mock()
            client.getresponse.return_value.status = status
            client.getresponse.return_value.read.return_value = json.dumps(body).encode()
            with (
                self.subTest(status=status),
                patch.object(launcher.http.client, "HTTPConnection", return_value=client),
                patch.object(launcher.subprocess, "Popen") as spawn,
                self.assertRaises(ValueError),
            ):
                launcher.ensure_portal()
            spawn.assert_not_called()

    def test_healthy_instance_is_reused_without_spawning(self) -> None:
        with (
            patch.object(launcher, "running_portal", return_value=self.config),
            patch.object(launcher.subprocess, "Popen") as spawn,
        ):
            self.assertEqual(self.config, launcher.ensure_portal())
        spawn.assert_not_called()

    def test_owned_server_start_waits_for_authenticated_readiness(self) -> None:
        with (
            patch.object(launcher, "running_portal", side_effect=[None, self.config]),
            patch.object(launcher.subprocess, "Popen") as spawn,
        ):
            self.assertEqual(self.config, launcher.ensure_portal())
        args = spawn.call_args.args[0]
        self.assertIn("--quiet-url", args)
        self.assertEqual(str(ROOT / "scripts" / "portal_server.py"), args[1])
        self.assertEqual(ROOT, spawn.call_args.kwargs["cwd"])
        self.assertEqual(launcher.subprocess.DEVNULL, spawn.call_args.kwargs["stdin"])

    def test_start_failure_is_not_success_shaped(self) -> None:
        with (
            patch.object(launcher, "running_portal", return_value=None),
            patch.object(launcher.subprocess, "Popen") as spawn,
        ):
            spawn.return_value.poll.return_value = 1
            with self.assertRaisesRegex(RuntimeError, "startup failed"):
                launcher.ensure_portal()

    def test_start_timeout_stops_only_owned_process(self) -> None:
        with (
            patch.object(launcher, "running_portal", return_value=None),
            patch.object(launcher.time, "monotonic", side_effect=[0, 11]),
            patch.object(launcher.subprocess, "Popen") as spawn,
            self.assertRaisesRegex(RuntimeError, "10 seconds"),
        ):
            launcher.ensure_portal()
        spawn.return_value.terminate.assert_called_once()
        spawn.return_value.wait.assert_called_once_with(timeout=5)

    def test_portal_job_never_opens_browser_or_starts_server(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"HACKBUILDER_PORTAL_JOB": "1"}),
            patch("sys.argv", ["start_portal.py", "--hook"]),
            patch.object(launcher, "ensure_portal") as ensure,
            patch.object(launcher.webbrowser, "open") as browser,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(0, launcher.main())
        self.assertEqual({}, json.loads(output.getvalue()))
        ensure.assert_not_called()
        browser.assert_not_called()

    def test_hook_opens_authenticated_url_without_printing_credentials(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"HACKBUILDER_PORTAL_JOB": "0"}),
            patch("sys.argv", ["start_portal.py", "--hook"]),
            patch.object(launcher, "ensure_portal", return_value=self.config),
            patch.object(launcher.webbrowser, "open", return_value=True) as browser,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(0, launcher.main())
        browser.assert_called_once_with("http://127.0.0.1:8765/#token=test-local-token")
        self.assertEqual({}, json.loads(output.getvalue()))
        self.assertNotIn(self.config["token"], output.getvalue())

    def test_browser_failure_is_explicit(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"HACKBUILDER_PORTAL_JOB": "0"}),
            patch("sys.argv", ["start_portal.py", "--hook"]),
            patch.object(launcher, "ensure_portal", return_value=self.config),
            patch.object(launcher.webbrowser, "open", return_value=False),
            contextlib.redirect_stderr(output),
        ):
            self.assertEqual(1, launcher.main())
        self.assertIn("browser could not be opened", output.getvalue())
        self.assertNotIn(self.config["token"], output.getvalue())

    def test_protocol_failure_is_reported(self) -> None:
        with (
            patch("sys.argv", ["start_portal.py", "--hook"]),
            patch.dict(os.environ, {"HACKBUILDER_PORTAL_JOB": "0"}),
            patch.object(launcher, "ensure_portal", side_effect=http.client.BadStatusLine("invalid status")),
            contextlib.redirect_stderr(io.StringIO()) as error,
        ):
            self.assertEqual(1, launcher.main())
        self.assertIn("Portal startup", error.getvalue())

    def test_agent_uses_scoped_hook_and_interactive_fallback(self) -> None:
        text = (ROOT / ".github" / "agents" / "az-01-conductor.agent.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertIn("sessionStart:", frontmatter)
        self.assertIn("python scripts\\start_portal.py --hook", frontmatter)
        self.assertIn("HACKBUILDER_PORTAL_JOB=1", text)
        self.assertIn("does not execute scoped hooks", text)


if __name__ == "__main__":
    unittest.main()
