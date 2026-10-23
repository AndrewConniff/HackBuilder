"""Test private target discovery without tokens, mutations or Azure resource queries."""

from __future__ import annotations

import json
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import azure_context
import portal_workflow


class AzureContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scenario = self.root / "generated-scenarios" / "example"
        self.scenario.mkdir(parents=True)
        (self.scenario / "00-region-availability.json").write_text(
            '{"provisionalRegion":"eastus2"}', encoding="utf-8",
        )
        self.project = {"projectSlug": "example", "authorizations": []}
        self.identity = {"account": "operator@example.test", "subscriptionId": "sub-id", "tenantId": "tenant-id"}

    def responses(self, azd: str = "operator@example.test") -> list[str]:
        return [
            json.dumps(self.identity),
            '{"expiresOn":"future","subscription":"sub-id","tenant":"tenant-id"}',
            f"Logged in to Azure as {azd}",
        ]

    def test_command_resolves_windows_cli_entrypoint_and_does_not_use_shell(self) -> None:
        with (
            patch.object(azure_context.shutil, "which", return_value=r"C:\Tools\az.cmd"),
            patch.object(azure_context.subprocess, "run", return_value=
                         subprocess.CompletedProcess([], 0, stdout="{}", stderr="")) as run,
        ):
            self.assertEqual("{}", azure_context.command(self.root, ["az", "account", "show"]))
        self.assertEqual(r"C:\Tools\az.cmd", run.call_args.args[0][0])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_discovery_reuses_architecture_and_conventions_without_resource_queries(self) -> None:
        with patch.object(azure_context, "command", side_effect=self.responses()) as command:
            result = azure_context.discover(self.root, self.scenario, self.project)
        self.assertEqual("eastus2", result["scope"]["region"])
        self.assertEqual("example", result["scope"]["environment"])
        self.assertEqual("rg-example", result["scope"]["resourceGroup"])
        self.assertNotIn("accessToken", json.dumps(result))
        self.assertEqual(3, command.call_count)
        self.assertIn("--check-status", command.call_args_list[-1].args[1])
        self.assertIn("metadata", result["authentication"]["azureCli"])

    def test_identity_mismatch_and_local_environment_conflicts_block_proposal(self) -> None:
        with (
            patch.object(azure_context, "command", side_effect=self.responses("other@example.test")),
            self.assertRaisesRegex(ValueError, "names differ"),
        ):
            azure_context.discover(self.root, self.scenario, self.project)
        env = self.scenario / ".azure" / "existing"
        env.mkdir(parents=True)
        (env / ".env").write_text('AZURE_SUBSCRIPTION_ID="wrong"\n', encoding="utf-8")
        with (
            patch.object(azure_context, "command", side_effect=self.responses()),
            self.assertRaisesRegex(ValueError, "conflicts"),
        ):
            azure_context.discover(self.root, self.scenario, self.project)

    def test_existing_azd_environment_and_explicit_edits(self) -> None:
        env = self.scenario / ".azure" / "existing"
        env.mkdir(parents=True)
        (env / ".env").write_text('AZURE_RESOURCE_GROUP="rg-existing"\n', encoding="utf-8")
        with patch.object(azure_context, "command", side_effect=self.responses()):
            result = azure_context.discover(self.root, self.scenario, self.project, {"region": "westus3"})
        self.assertEqual("existing", result["scope"]["environment"])
        self.assertEqual("rg-existing", result["scope"]["resourceGroup"])
        self.assertEqual("westus3", result["scope"]["region"])
        self.assertEqual("User-edited proposed target", result["sources"]["region"])

    def test_context_review_supersedes_only_target_question_and_never_grants_consent(self) -> None:
        store = portal_workflow.Store(self.root / "state")
        p = store.claim({"projectSlug": "example"}, "worker", create=True)
        p = store.report("example", "worker", p["revision"], {
            "stage": "requirements", "status": "waiting_for_user", "summary": "Targets needed",
            "decision": {
                "kind": "business", "question": "Targets?", "reason": "Deferred",
                "choices": ["Provide exact Azure targets in the portal response", "Keep local"], "acceptChoice": None,
            },
        })
        store.finish("example", "worker", "completed")
        p = store.read("example")
        with patch.object(azure_context, "command", side_effect=self.responses()):
            context = azure_context.discover(self.root, self.scenario, self.project)
        updated = store.propose_deployment_context("example", p["revision"], context)
        self.assertEqual([], updated["authorizations"])
        self.assertEqual("superseded", updated["decisions"][0]["status"])
        self.assertEqual("deployment-preparation", updated["decisions"][-1]["kind"])
        self.assertEqual(context["scope"], updated["decisions"][-1]["scope"])
        with self.assertRaisesRegex(ValueError, "changed"):
            store.propose_deployment_context("example", p["revision"], context)
