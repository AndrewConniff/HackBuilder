"""Verify readiness collection fails closed without contacting Azure."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "check_readiness", Path(__file__).resolve().parents[1] / "scripts" / "check_readiness.py"
)
assert SPEC is not None and SPEC.loader is not None
READINESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READINESS)


class ReadinessTests(unittest.TestCase):
    """Keep target mismatch and failed cloud observations from looking successful."""

    def test_target_mismatch_stops_before_cloud_collection(self) -> None:
        identity = types.SimpleNamespace(identity=lambda _: {"scope": {"account": "wrong"}})
        with patch.dict(sys.modules, {"azure_context": identity}), patch.object(
            READINESS.subprocess, "run"
        ) as run, self.assertRaisesRegex(ValueError, "differs from authorized target"):
            READINESS.collect(Path("repository"))
        run.assert_not_called()

    def test_command_failure_is_recorded_and_blocks_success(self) -> None:
        identity = types.SimpleNamespace(identity=lambda _: {"scope": {
            "account": "petender@microsoft.com",
            "subscriptionId": READINESS.SUBSCRIPTION,
            "tenantId": READINESS.TENANT,
        }})
        denied = subprocess.CompletedProcess([], 1, "", "AuthorizationFailed")
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(sys.modules, {"azure_context": identity}), patch.object(
                READINESS, "ROOT", Path(directory)
            ), patch.object(READINESS.shutil, "which", return_value="az.exe"), patch.object(
                READINESS.subprocess, "run", return_value=denied
            ), self.assertRaisesRegex(RuntimeError, "Readiness collection failed"):
                READINESS.collect(Path("repository"))
            evidence = json.loads((Path(directory) / "evidence" / "readiness.json").read_text())
            self.assertTrue(evidence["observations"])
            self.assertTrue(all(value["exitCode"] == 1 for value in evidence["observations"].values()))
            self.assertNotIn("passed", evidence)


if __name__ == "__main__":
    unittest.main()
