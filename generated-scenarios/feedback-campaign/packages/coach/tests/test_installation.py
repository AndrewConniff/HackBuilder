"""Local contract tests only; all cloud requests are replaced in this test module."""
import json
import sys
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cloud_io
import initialize_foundry
import setup_lab_accounts


class InstallationTests(unittest.TestCase):
    def test_local_account_prepare_only_discovers_installer_without_directory_writes(self):
        with patch.object(setup_lab_accounts, "verify_target", return_value={"tenantId": "test-tenant"}), \
                patch.object(setup_lab_accounts, "cli", return_value="test-installer") as calls:
            setup_lab_accounts.main("prepare")
        self.assertEqual(("az", "ad", "signed-in-user", "show", "--query", "id", "--output", "tsv"),
                         calls.call_args_list[0].args)
        self.assertTrue(all(call.args[0] == "azd" and call.args[1:3] == ("env", "set")
                            for call in calls.call_args_list[1:]))

    def test_active_hooks_do_not_require_entra_app_installation(self):
        root = Path(__file__).resolve().parents[1]
        hooks = (root / "azure.yaml").read_text(encoding="utf-8")
        self.assertIn("scripts/setup_lab_accounts.py prepare", hooks)
        self.assertIn("scripts/setup_lab_accounts.py install", hooks)
        self.assertNotIn("scripts/identity_setup.py", hooks)
        parameters = json.loads((root / "infra/main.parameters.json").read_text())["parameters"]
        self.assertNotIn("authClientId", parameters)
        self.assertNotIn("tenantId", parameters)
        self.assertIn(".private/", (root / ".gitignore").read_text())

    def test_target_mismatch_never_changes_defaults(self):
        with patch.object(cloud_io, "environment", return_value={"AZURE_SUBSCRIPTION_ID": "selected", "AZURE_TENANT_ID": "selected","AZURE_LOCATION": "chosen", "AZURE_ENV_NAME": "feedback-campaign-coach","AZURE_RESOURCE_GROUP": "rg-feedback-campaign-coach"}), \
                patch.object(cloud_io, "cli", return_value=json.dumps({"id": "wrong", "tenantId": "wrong"})) as cli:
            with self.assertRaises(RuntimeError):
                cloud_io.verify_target()
            self.assertEqual(1, cli.call_count)
            self.assertNotIn("set", cli.call_args.args)




    def test_unchanged_agent_and_promoted_rules_are_not_overwritten(self):
        instructions = (cloud_io.ROOT / "src/FeedbackCampaign.Web/Policy/agent-instructions.txt").read_text(encoding="utf-8")
        env = {"FOUNDRY_PROJECT_ENDPOINT": "https://not-a-service.invalid/api/projects/campaign",
               "FOUNDRY_MODEL_DEPLOYMENT": "campaign-model", "TABLE_ENDPOINT": "https://not-storage.invalid",
               "AZURE_SUBSCRIPTION_ID": "test", "AZURE_RESOURCE_GROUP": "rg-test", "AZURE_WEBAPP_NAME": "test"}
        calls = []

        def request(method, url, audience, body=None, headers=None, missing_ok=False):
            calls.append((method, url, body))
            if "/agents/" in url:
                return {"versions": {"latest": {"id": "test-version-id", "version": "7",
                        "definition": {"kind": "prompt", "model": "campaign-model", "instructions": instructions}}}}
            return {"Payload": "existing"}  # Existing active/rules rows must never be overwritten.

        with patch.object(initialize_foundry, "verify_target"), patch.object(initialize_foundry, "environment", return_value=env), \
                patch.object(initialize_foundry, "request", side_effect=request), patch.object(initialize_foundry, "receipt"), \
                patch.object(initialize_foundry, "cli"), patch("builtins.print"):
            initialize_foundry.main()
        self.assertTrue(all(c[0] == "GET" for c in calls))



if __name__ == "__main__":
    unittest.main()
