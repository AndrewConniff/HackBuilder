"""Test owned-container runtime validation, diagnostics and cleanup without Docker."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_container_runtime as runtime


class ContainerRuntimeTests(unittest.TestCase):
    def test_success_is_loopback_read_only_nonroot_and_cleanup_scoped(self) -> None:
        container = "a" * 64
        metadata = json.dumps([{"Os": "linux", "Architecture": "amd64", "Config": {"User": "1654"}}])
        with (
            patch.object(runtime, "docker", side_effect=[metadata, container, "127.0.0.1:12345", "logs", container]) as run,
            patch.object(runtime, "get", side_effect=[(200, "Healthy"), (200, "Fourth Coffee")]),
        ):
            report = runtime.verify("example:owned", "Fourth Coffee")
        self.assertTrue(report["ok"])
        start = run.call_args_list[1].args
        self.assertIn("--pull=never", start)
        self.assertIn("--read-only", start)
        self.assertIn("127.0.0.1::8080", start)
        self.assertNotIn("--volume", start)
        self.assertEqual(("stop", "--time", "5", container), run.call_args_list[-1].args)

    def test_http_failure_collects_logs_and_stops_owned_container(self) -> None:
        container = "b" * 64
        metadata = json.dumps([{"Os": "linux", "Architecture": "amd64", "Config": {"User": "1654"}}])
        with (
            patch.object(runtime, "docker", side_effect=[metadata, container, "127.0.0.1:12345", "startup error", container]),
            patch.object(runtime, "get", return_value=(503, "not ready")),
            patch.object(runtime.time, "monotonic", side_effect=[0, 0, 2]),
            patch.object(runtime.time, "sleep"),
        ):
            report = runtime.verify("example:owned", "Fourth Coffee", timeout=1)
        self.assertFalse(report["ok"])
        self.assertIn("HTTP 503", report["error"])
        self.assertEqual("startup error", report["logs"])
        self.assertTrue(report["cleanupPassed"])

    def test_cleanup_failure_never_reports_success(self) -> None:
        metadata = json.dumps([{"Os": "linux", "Architecture": "amd64", "Config": {"User": "1654"}}])
        with (
            patch.object(runtime, "docker", side_effect=[
                metadata, "c" * 64, "127.0.0.1:12345", "logs", RuntimeError("stop denied"),
            ]),
            patch.object(runtime, "get", side_effect=[(200, "Healthy"), (200, "Fourth Coffee")]),
        ):
            report = runtime.verify("example:owned", "Fourth Coffee")
        self.assertFalse(report["ok"])
        self.assertIn("cleanup failed", report["error"])

    def test_invalid_input_and_root_images_cannot_start_container(self) -> None:
        with patch.object(runtime, "docker") as run:
            with self.assertRaises(ValueError):
                runtime.verify("unqualified", "marker")
            run.assert_not_called()
        for user in ("", "0", "root", "0:0"):
            with (
                self.subTest(user=user),
                patch.object(runtime, "docker", return_value=json.dumps([
                    {"Os": "linux", "Architecture": "amd64", "Config": {"User": user}},
                ])) as run,
            ):
                self.assertFalse(runtime.verify("example:owned", "marker")["ok"])
                run.assert_called_once()
