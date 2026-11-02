"""Offline checks for live acceptance safeguards; no Azure calls or real credentials."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from private_runner import wait_application
import probe_foundry_runtime as runtime_probe
import probe_response_permission as permission_probe
spec = importlib.util.spec_from_file_location("live_validation", ROOT / "scripts" / "validate_live.py")
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


class LiveValidationTests(unittest.TestCase):
    def test_platform_warmup_does_not_depend_on_account_storage(self):
        source = (ROOT / "infra" / "main.bicep").read_text()
        self.assertIn("WEBSITE_WARMUP_PATH: '/health'", source)
        self.assertIn("WEBSITES_CONTAINER_START_TIME_LIMIT: '600'", source)

    def test_native_probe_requires_the_explicit_execution_guard(self):
        with patch("sys.argv", ["probe"]), patch.dict("os.environ", {}, clear=True), \
                patch.object(runtime_probe, "invoke") as invoke:
            with self.assertRaisesRegex(ValueError, "execution guard"):
                runtime_probe.main()
            invoke.assert_not_called()

    def test_sdk_probe_removes_staged_artifact_after_success(self):
        with patch.object(runtime_probe, "package", return_value=b"test-publish"), \
                patch.object(runtime_probe, "stage_artifact") as stage, \
                patch.object(runtime_probe, "invoke", return_value="EQUIP_SDK_PROBE_OK"):
            self.assertIn("EQUIP_SDK_PROBE_OK", runtime_probe.invoke_sdk())
        self.assertEqual(stage.call_count, 2)
        self.assertEqual(stage.call_args_list[0].args[2], b"test-publish")
        self.assertIsNone(stage.call_args_list[1].args[2])

    def test_sdk_probe_retains_failure_and_removes_staged_artifact(self):
        with patch.object(runtime_probe, "package", return_value=b"test-publish"), \
                patch.object(runtime_probe, "stage_artifact") as stage, \
                patch.object(runtime_probe, "save_result") as save, \
                patch.object(runtime_probe, "invoke", return_value="guest failed"):
            with self.assertRaisesRegex(RuntimeError, "did not pass"):
                runtime_probe.invoke_sdk()
        save.assert_called_once_with("private-sdk-probe-failed.json", "guest failed")
        self.assertIsNone(stage.call_args_list[-1].args[2])

    def test_permission_probe_removes_assignment_and_role_after_request_failure(self):
        definition = {"id": "/subscriptions/test/providers/Microsoft.Authorization/roleDefinitions/test", "name": "test"}
        assignment = {"id": "/subscriptions/test/providers/Microsoft.Authorization/roleAssignments/probe"}
        with patch.object(permission_probe, "values", return_value={"APPLICATION_URL": "https://example.invalid"}), \
                patch.object(permission_probe, "command", side_effect=[definition, assignment, None, None]) as command, \
                patch.object(permission_probe, "save") as save, \
                patch("pathlib.Path.read_text", return_value='{"accounts":[{}]}'), \
                patch.object(permission_probe, "Session") as session:
            session.return_value.request.side_effect = [{}, TimeoutError("test dependency timeout")]
            with self.assertRaises(TimeoutError):
                permission_probe.main()
        self.assertEqual(command.call_args_list[-2].args[0][1:4], ["role", "assignment", "delete"])
        self.assertEqual(command.call_args_list[-1].args[0][1:4], ["role", "definition", "delete"])
        role = save.call_args_list[0].args[1]
        self.assertEqual(role["DataActions"], ["Microsoft.CognitiveServices/accounts/OpenAI/responses/write"])
        self.assertEqual(role["Actions"], [])
        self.assertEqual(save.call_args_list[-1].args[1]["results"], [])

    def test_readiness_requires_the_current_binary_and_pinned_version(self):
        def reply(build, version):
            response = MagicMock()
            response.__enter__.return_value = response
            response.code = 200
            response.headers = {"Content-Type": "application/json"}
            response.read.return_value = json.dumps({"buildId": build, "agentVersion": version}).encode()
            return response
        opener = MagicMock()
        opener.open.side_effect = [reply("old", "1"), reply("new", "1"), reply("new", "2")]
        with patch("private_runner.urllib.request.build_opener", return_value=opener), \
                patch("private_runner.time.sleep") as sleep:
            actual = wait_application("https://app-equip-web-equipai-kex72v.azurewebsites.net/", "new", "2")
        self.assertEqual(actual["buildId"], "new")
        self.assertEqual(sleep.call_count, 2)

    def test_readiness_rejects_unapproved_origins(self):
        with self.assertRaisesRegex(ValueError, "approved public reference"):
            wait_application("https://example.invalid", "new", "1")

    def test_iot_audience_has_no_trailing_slash(self):
        source = (ROOT / "scripts" / "validate_live.py").read_text()
        self.assertIn('"--resource", "https://iothubs.azure.net"', source)
        self.assertNotIn('"https://iothubs.azure.net/"', source)

    def test_redirects_never_forward_credentials(self):
        with self.assertRaisesRegex(RuntimeError, "not forwarded"):
            live.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid")

    def test_live_execution_requires_the_explicit_guard(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "execution guard"):
                live.values()

    def test_bootstrap_does_not_run_the_historical_directory_installer(self):
        source = (ROOT / "scripts" / "private_lifecycle.py").read_text()
        self.assertNotIn('"registrations"', source)
        self.assertNotIn('"redirect"', source)
        self.assertIn("--prepare-accounts", source)

    def test_account_hash_seed_is_not_inside_the_publish_tree(self):
        source = (ROOT / "scripts" / "private_runner.py").read_text()
        self.assertIn('ROOT / ".private" / "account-seed.json"', source)
        self.assertIn('cleanup.callback(stage_artifact, config["AZURE_WEB_NAME"], seed_digest, None)', source)
        guest = (ROOT / "scripts" / "runner_guest.py").read_text()
        self.assertIn("seed_path.unlink()", guest)

    def test_no_later_login_or_signup_bypass(self):
        source = (ROOT / "src" / "EquipAI.Web" / "Program.cs").read_text()
        self.assertNotIn("AddJwtBearer", source)
        self.assertNotIn("login.microsoftonline.com", source)
        self.assertIn('RequireRole("Operations.Tacoma", "Operations.Statewide")', source)


if __name__ == "__main__":
    unittest.main()
