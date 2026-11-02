"""Verify read-only CLI invocation without querying Azure."""

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "check_readiness", Path(__file__).resolve().parents[1] / "scripts" / "check_readiness.py"
)
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)


class AzureQueryTests(unittest.TestCase):
    def test_batch_or_missing_quota_cannot_substitute_for_exact_inference_quota(self):
        self.assertFalse(readiness.has_exact_model_quota([]))
        self.assertFalse(readiness.has_exact_model_quota([
            {"name": "OpenAI.GlobalBatch.gpt-4.1", "used": 0, "limit": 200000}
        ]))
        self.assertFalse(readiness.has_exact_model_quota([
            {"name": "OpenAI.GlobalStandard.gpt4.1", "used": 0}
        ]))
        self.assertTrue(readiness.has_exact_model_quota([
            {"name": "OpenAI.GlobalStandard.gpt4.1", "used": 0, "limit": 1000}
        ]))

    def test_windows_queries_bypass_batch_parser(self):
        executable = r"C:\Azure\CLI2\wbin\az.CMD"
        query = "[?contains(name.value,'gpt-4.1')].{name:name.value}"
        with patch.object(readiness.shutil, "which", return_value=executable), \
                patch.object(Path, "is_file", return_value=True), \
                patch.object(readiness.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "[]", "")
            self.assertEqual(
                "[]", readiness.azure_query(Path.cwd(), ["usage", "--query", query], {"PATH": "configured"})
            )
            arguments = run.call_args.args[0]
            self.assertEqual(["-m", "azure.cli"], arguments[1:3])
            self.assertEqual(query, arguments[-1])
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertEqual(180, run.call_args.kwargs["timeout"])

    def test_failed_query_is_not_success(self):
        with patch.object(readiness.shutil, "which", return_value="az.exe"), \
                patch.object(readiness.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 1, "", "AuthorizationFailed")
            with self.assertRaisesRegex(ValueError, "AuthorizationFailed"):
                readiness.azure_query(Path.cwd(), ["rest"], {})

    def test_timeout_remains_explicit(self):
        with patch.object(readiness.shutil, "which", return_value="az.exe"), \
                patch.object(readiness.subprocess, "run", side_effect=subprocess.TimeoutExpired("az", 180)):
            with self.assertRaisesRegex(ValueError, "could not complete"):
                readiness.azure_query(Path.cwd(), ["vm", "list-skus"], {})


if __name__ == "__main__":
    unittest.main()
