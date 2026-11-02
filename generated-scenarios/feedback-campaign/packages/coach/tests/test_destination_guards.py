"""Destination guards are exercised with mocked local inputs; no cloud calls."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cloud_io

class DestinationTests(unittest.TestCase):
    def test_request_uses_bearer_token_without_persisting_it(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{}'
        with patch.object(cloud_io, "cli", return_value="test-value-not-real"), \
                patch.object(cloud_io.urllib.request, "urlopen", return_value=response) as send:
            cloud_io.request("GET", "https://unit-test.invalid/resource", "https://unit-test.invalid")
        request = send.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-value-not-real")

    def values(self):
        return {"AZURE_SUBSCRIPTION_ID": "selected", "AZURE_TENANT_ID": "selected",
                "AZURE_LOCATION": "chosen", "AZURE_ENV_NAME": "feedback-campaign-coach",
                "AZURE_RESOURCE_GROUP": "rg-feedback-campaign-coach"}

    def test_missing_destination_fails_without_cloud(self):
        with patch.object(cloud_io, "environment", return_value={}), patch.object(cloud_io, "cli") as cli:
            with self.assertRaises(RuntimeError):
                cloud_io.verify_target()
            cli.assert_not_called()

    def test_wrong_group_fails_without_cloud(self):
        env = self.values()
        env["AZURE_RESOURCE_GROUP"] = "rg-unrelated"
        with patch.object(cloud_io, "environment", return_value=env), patch.object(cloud_io, "cli") as cli:
            with self.assertRaises(RuntimeError):
                cloud_io.verify_target()
            cli.assert_not_called()

    def test_wrong_environment_fails_without_cloud(self):
        env = self.values()
        env["AZURE_ENV_NAME"] = "01-feedback-campaign-hack"
        with patch.object(cloud_io, "environment", return_value=env), patch.object(cloud_io, "cli") as cli:
            with self.assertRaises(RuntimeError):
                cloud_io.verify_target()
            cli.assert_not_called()

    def test_matching_destination_does_not_change_defaults(self):
        with patch.object(cloud_io, "environment", return_value=self.values()), \
                patch.object(cloud_io, "cli", return_value=json.dumps(
                    {"id": "selected", "tenantId": "selected"})) as cli:
            self.assertEqual(cloud_io.verify_target()["id"], "selected")
            self.assertEqual(cli.call_count, 1)

if __name__ == "__main__":
    unittest.main()
