"""Offline safeguards for the separately approved private human-access repair."""

import base64
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_human_access as readiness
import setup_human_access as setup

with patch.dict("sys.modules", {"pwd": MagicMock()}):
    spec = importlib.util.spec_from_file_location("desktop_guest", ROOT / "scripts" / "desktop_guest.py")
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)


class HumanAccessTests(unittest.TestCase):
    def test_guest_setting_rejects_missing_or_duplicate_keys_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "xrdp.ini"
            for text in ("unrelated=value\n", "security_layer=tls\nsecurity_layer=negotiate\n"):
                path.write_text(text)
                with self.assertRaisesRegex(ValueError, "Expected one"):
                    guest.setting(path, "security_layer", "tls")
                self.assertEqual(path.read_text(), text)

    def test_guest_setting_preserves_unrelated_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "xrdp.ini"
            path.write_text("unrelated=value\nsecurity_layer=negotiate\n")
            guest.setting(path, "security_layer", "tls")
            self.assertEqual(path.read_text(), "unrelated=value\nsecurity_layer=tls\n")

    def test_desktop_password_stays_in_private_staging_not_arm_script(self):
        password = "test-only-" + "x" * 40
        with patch.object(setup, "values", return_value={"EQUIP_ENABLE_HUMAN_MANAGEMENT": "true"}), \
                patch.object(setup, "command", return_value={
                    "provisioningState": "Succeeded", "sku": {"name": "Standard"}, "enableTunneling": True
                }), patch("pathlib.Path.exists", return_value=False), \
                patch.object(setup.secrets, "token_urlsafe", return_value=password), \
                patch.object(setup, "save"), patch.object(setup, "stage_artifact") as stage, \
                patch.object(setup, "invoke", return_value="EQUIP_DESKTOP_READY") as invoke:
            setup.main()
        script = invoke.call_args.args[0]
        encoded = script.split("printf '%s' '", 1)[1].split("'", 1)[0]
        self.assertNotIn(password, base64.b64decode(encoded).decode())
        self.assertIn(password.encode(), stage.call_args_list[0].args[2])
        self.assertEqual(stage.call_count, 6)
        self.assertTrue(all(call.args[2] is None for call in stage.call_args_list[-3:]))

    def test_requires_existing_execution_guard_before_cloud_reads(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(readiness, "command") as command:
            with self.assertRaisesRegex(ValueError, "execution guard"):
                readiness.main()
            command.assert_not_called()

    def test_requires_separate_human_scope_enablement(self):
        with patch.object(readiness, "values", return_value={}), patch.object(readiness, "command") as command:
            with self.assertRaisesRegex(ValueError, "explicitly enabled"):
                readiness.main()
            command.assert_not_called()

    def test_rejects_overlapping_bastion_subnet(self):
        network = {"addressSpace": {"addressPrefixes": ["10.247.0.0/24"]},
                   "subnets": [{"name": "other", "addressPrefix": "10.247.0.192/27"}]}
        with patch.object(readiness, "values", return_value={
            "EQUIP_ENABLE_HUMAN_MANAGEMENT": "true", "EQUIP_ENABLE_MANAGEMENT": "true"
        }), patch.object(readiness, "command", return_value=network), patch.object(readiness, "rate") as rate:
            with self.assertRaisesRegex(ValueError, "overlaps"):
                readiness.main()
            rate.assert_not_called()

    def test_price_requires_one_matching_hourly_meter(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"Items": []}).encode()
        with patch.object(readiness.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "one hourly"):
                readiness.rate("Azure Bastion", "Standard Gateway")

    def test_repair_does_not_redeploy_workloads_or_vm(self):
        source = (ROOT / "infra" / "human-access-repair.bicep").read_text()
        self.assertNotIn("Microsoft.Compute/virtualMachines", source)
        self.assertNotIn("Microsoft.CognitiveServices", source)
        self.assertNotIn("Microsoft.Web/sites", source)
        self.assertIn("destinationPortRange: '3389'", source)
        self.assertIn("sourceAddressPrefix: '10.247.0.192/26'", source)
        self.assertIn("principalType: 'User'", source)


if __name__ == "__main__":
    unittest.main()
