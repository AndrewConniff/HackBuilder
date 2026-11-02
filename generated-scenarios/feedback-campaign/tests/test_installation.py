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
import identity_setup
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
        with patch.object(cloud_io, "cli", return_value=json.dumps({"id": "wrong", "tenantId": "wrong"})) as cli:
            with self.assertRaises(RuntimeError):
                cloud_io.verify_target()
            self.assertEqual(1, cli.call_count)
            self.assertNotIn("set", cli.call_args.args)

    def test_name_collision_never_adopts_unrelated_application(self):
        with patch.object(identity_setup, "graph", return_value={"value": [{"id": "test", "tags": []}]}):
            with self.assertRaises(RuntimeError):
                identity_setup.find_application()

    def test_owned_registration_can_be_reused(self):
        app = {"id": "test-not-real", "tags": [identity_setup.MARKER]}
        with patch.object(identity_setup, "graph", return_value={"value": [app]}):
            self.assertEqual(app, identity_setup.find_application())

    def test_new_registration_does_not_duplicate_automatic_owner(self):
        app = {"id": "test-app", "appId": "test-client"}
        calls = []

        def graph(method, path, body=None):
            calls.append((method, path))
            if path.startswith("me?"):
                return {"id": "test-me"}
            if path == "applications":
                return app
            if "/owners?" in path:
                return {"value": [{"id": "test-me"}]}
            if path.startswith("servicePrincipals?"):
                return {"value": [{"id": "test-sp"}]}
            if path.endswith("/appRoleAssignedTo") and method == "GET":
                return {"value": []}
            return {}

        context = SimpleNamespace(identity=lambda repo: {"scope": {"tenantId": "test-tenant"}})
        with patch.dict(sys.modules, {"azure_context": context}), \
                patch.object(identity_setup, "verify_target", return_value={"tenantId": "test-tenant"}), \
                patch.object(identity_setup, "find_application", return_value=None), \
                patch.object(identity_setup, "graph", side_effect=graph), \
                patch.object(identity_setup, "cli"), patch.object(identity_setup, "receipt"):
            identity_setup.main("prepare")
        self.assertNotIn(("POST", "applications/test-app/owners/$ref"), calls)

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

    def test_acceptance_role_removes_only_installers_scenario_assignments(self):
        def role_id(role):
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{identity_setup.MARKER}/{role}"))
        env = {"AUTH_OBJECT_ID": "test-app", "INSTALLER_OBJECT_ID": "test-me", "AUTH_SERVICE_PRINCIPAL_ID": "test-sp"}
        assignments = [
            {"id": "keep-own", "principalId": "test-me", "appRoleId": role_id("ProductManager")},
            {"id": "remove-own", "principalId": "test-me", "appRoleId": role_id("ControlAdmin")},
            {"id": "keep-other", "principalId": "test-other", "appRoleId": role_id("ControlAdmin")},
        ]

        def graph(method, path, body=None):
            if path.startswith("me?"):
                return {"id": "test-me"}
            if "?$select=appId" in path:
                return {"appId": "test-client"}
            if method == "GET":
                return {"value": assignments}
            return {}

        with patch.object(identity_setup, "verify_target", return_value={}), \
                patch.object(identity_setup, "environment", return_value=env), \
                patch.object(identity_setup, "find_application", return_value={"id": "test-app", "appId": "test-client"}), \
                patch.object(identity_setup, "receipt"), \
                patch.object(identity_setup, "graph", side_effect=graph) as calls, \
                patch.object(sys, "argv", ["identity_setup.py", "acceptance-role", "ProductManager"]):
            identity_setup.main("acceptance-role")
        deletes = [call.args[1] for call in calls.call_args_list if call.args[0] == "DELETE"]
        self.assertEqual(["servicePrincipals/test-sp/appRoleAssignedTo/remove-own"], deletes)


if __name__ == "__main__":
    unittest.main()
