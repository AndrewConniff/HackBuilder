"""Offline private runner contracts; these are not Azure connectivity/permission tests."""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("private_runner", ROOT / "scripts" / "private_runner.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class PrivateRunnerTests(unittest.TestCase):
    def test_readiness_checks_the_deployed_management_size(self):
        spec = importlib.util.spec_from_file_location(
            "management_readiness", ROOT / "scripts" / "check_management_readiness.py")
        readiness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(readiness)
        template = (ROOT / "infra" / "management.bicep").read_text()
        self.assertIn(f"vmSize: '{readiness.MANAGEMENT_VM_SIZE}'", template)

    def test_actual_directory_consent_without_worker_expiry(self):
        spec = importlib.util.spec_from_file_location("identity_continuity", ROOT / "scripts" / "install_identity.py")
        identity = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(identity)
        document = json.loads((ROOT / ".installation" / "equip-ai" / "directory-authorization.json").read_text())
        identity.validate_authorization(document, document["scope"], "registrations", datetime.now(timezone.utc))
        self.assertNotIn("assignments", document["directoryOperations"])

    def test_requires_self_contained_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                runner.package(Path(folder))

    def test_rejects_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "EquipAI.Web").write_bytes(b"\x7fELF")
            (root / "device.key").write_text("not-a-real-key")
            with self.assertRaises(ValueError):
                runner.package(root)

    def test_rejects_hidden_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "EquipAI.Web").write_bytes(b"\x7fELF")
            (root / ".env").write_text("test")
            with self.assertRaises(ValueError):
                runner.package(root)

    def test_staging_redirect_does_not_forward_credentials(self):
        with self.assertRaisesRegex(RuntimeError, "redirected"):
            runner.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid")

    def test_staging_targets_authenticated_nonpublic_web_data_path(self):
        with patch.object(runner.shutil, "which", return_value="az"), patch.object(
            runner.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout="unit-test-token", stderr="")
        ), patch.object(runner.urllib.request, "build_opener") as build:
            build.return_value.open.return_value.__enter__.return_value.status = 201
            runner.stage_artifact("scenario-web", "a" * 64, b"reviewed-publish")
        request = build.return_value.open.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://scenario-web.scm.azurewebsites.net/api/vfs/data/equip-ai-" + "a" * 64 + ".zip")
        self.assertEqual(request.get_method(), "PUT")
        self.assertEqual(request.data, b"reviewed-publish")
        self.assertEqual(request.get_header("Authorization"), "Bearer unit-test-token")

    def test_guest_rejects_changed_artifact_before_extraction_or_execution(self):
        spec = importlib.util.spec_from_file_location("runner_guest", ROOT / "scripts" / "runner_guest.py")
        guest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guest)
        with patch("sys.argv", ["guest", "--download-artifact", "scenario-web", "a" * 64]), patch.object(
            guest, "token", return_value="unit-test-token"
        ), patch.object(guest.urllib.request, "build_opener") as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = b"changed"
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                guest.main()

    def test_scm_status_accepts_relative_url_but_rejects_other_origins_and_http(self):
        spec = importlib.util.spec_from_file_location("runner_guest_status", ROOT / "scripts" / "runner_guest.py")
        guest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guest)
        expected = "https://scenario-web.scm.azurewebsites.net/api/deployments/latest"
        self.assertEqual(guest.deployment_status_url("scenario-web", "/api/deployments/latest"), expected)
        self.assertEqual(guest.deployment_status_url("scenario-web", expected), expected)
        explicit_port = "https://scenario-web.scm.azurewebsites.net:443/api/deployments/latest"
        self.assertEqual(guest.deployment_status_url("scenario-web", explicit_port), explicit_port)
        for location in (
            None, "https://example.invalid/api/deployments/latest",
            "http://scenario-web.scm.azurewebsites.net/api/deployments/latest",
            "https://scenario-web.scm.azurewebsites.net:444/api/deployments/latest",
            "https://user@scenario-web.scm.azurewebsites.net/api/deployments/latest",
            "https://scenario-web.scm.azurewebsites.net/api/vfs/"
        ):
            with self.assertRaises(RuntimeError):
                guest.deployment_status_url("scenario-web", location)

    def test_plan_never_invokes_azure(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "EquipAI.Web").write_bytes(b"\x7fELF")
            with patch("sys.argv", ["runner", "plan", "--publish-directory", folder]), patch.object(
                runner, "invoke", side_effect=AssertionError("Cloud call from local plan")):
                self.assertEqual(runner.main(), 0)

    def test_publish_requires_new_scope_guard(self):
        with patch("sys.argv", ["runner", "publish"]), patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                runner.main()

    def test_clean_requires_guest_success_marker(self):
        with patch("sys.argv", ["runner", "clean"]), patch.dict(
            "os.environ", {"EQUIP_PRIVATE_RUNNER_APPROVED": "true"}), patch.object(runner, "invoke", return_value=""):
            with self.assertRaises(RuntimeError):
                runner.main()

    def test_guest_script_has_digest_verification(self):
        config = {
            "AZURE_AI_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/equipment-operations",
            "AZURE_MODEL_DEPLOYMENT_NAME": "configured-model",
            "AZURE_WEB_NAME": "web",
            "AZURE_CLEANER_NAME": "cleaner",
        }
        script = runner.finish_script("a" * 64, config)
        self.assertIn("sha256sum -c", script)
        self.assertNotIn("access_token", json.dumps(config))


if __name__ == "__main__":
    unittest.main()
