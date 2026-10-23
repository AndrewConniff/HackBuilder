"""Exercise durable project decisions, stage evidence and cooperating writer ownership."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal_workflow as workflow


class ProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = workflow.Store(Path(self.temp.name))
        self.request = {"projectSlug": "finance-test", "prompt": "An investment broker", "services": ["foundry"]}
        self.project = self.store.claim(self.request, "worker-1", create=True)

    def report(self, stage: str = "architecture", status: str = "running", **values) -> dict:
        self.project = self.store.report("finance-test", "worker-1", self.project["revision"], {
            "stage": stage, "status": status, "summary": "Verified stage result",
            "evidence": ["02-architecture-assessment.md"], **values,
        })
        return self.project

    def ask_design(self) -> dict:
        self.report("requirements", "completed", evidence=["01-requirements.md"])
        return self.report(status="waiting_for_user", decision={
            "kind": "design", "question": "Confirm private design?",
            "reason": "Check dependencies and security boundaries",
            "choices": ["Confirm design", "Revise"], "acceptChoice": "Confirm design",
        })

    def answer(self, choice: str) -> dict:
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        decision = self.project["decisions"][-1]
        self.project = self.store.respond("finance-test", self.project["revision"], choice, decision["id"], choice)
        self.project = self.store.claim(self.request, "worker-1", self.project["revision"])
        return self.project

    def test_design_checkpoint_blocks_implementation_and_is_not_suitability_approval(self) -> None:
        with self.assertRaisesRegex(ValueError, "Confirm the architecture"):
            self.report("bicep")
        self.ask_design()
        with self.assertRaisesRegex(ValueError, "pending decision"):
            self.report("requirements")
        self.answer("Confirm design")
        self.report("bicep", "completed")
        self.assertTrue(self.project["designConfirmed"])
        self.assertEqual([], self.project["authorizations"])
        self.assertNotIn("approval", self.project)
        self.assertEqual("completed", self.project["stages"]["architecture"]["status"])

    def ask_technical_question(self) -> dict:
        self.ask_design()
        self.answer("Confirm design")
        self.report("bicep", "completed")
        return self.report("architecture", "waiting_for_user", decision={
            "kind": "business", "question": "Which generated client IDs were installed?",
            "reason": "Legacy manual identity handoff", "choices": ["Return receipt"],
        })

    def classify(self, **values) -> dict:
        return self.report("architecture", decisionReview={
            "decisionId": self.project["decisions"][-1]["id"], "disposition": "technical",
            "reason": "Generated identities are implementation outputs.",
            "resolution": "Wire idempotent creation and capture real outputs during authorized deployment.",
            "evidence": ["Original intake requests a standalone reference; no supplied identity reuse."], **values,
        })

    def test_backend_question_review_preserves_confirmed_work_without_granting_consent(self) -> None:
        self.ask_technical_question()
        before = self.store.read("finance-test")
        self.assertEqual("reviewing", before["decisions"][-1]["status"])
        self.assertFalse(workflow.actionable_decision(before["decisions"][-1]))
        after = self.classify()
        self.assertEqual("superseded", after["decisions"][-1]["status"])
        self.assertEqual("completed", after["stages"]["architecture"]["status"])
        self.assertEqual(before["stages"]["bicep"], after["stages"]["bicep"])
        self.assertTrue(after["designConfirmed"])
        self.assertEqual(before["authorizations"], after["authorizations"])
        self.assertEqual("running", after["status"])
        self.assertEqual("backend-question-review", after["history"][-1]["action"])
        self.assertNotIn("answer", after["decisions"][-1])
        with self.assertRaisesRegex(ValueError, "Project changed"):
            self.store.report("finance-test", "worker-1", before["revision"], {})
        with self.assertRaisesRegex(ValueError, "already classified"):
            self.report("architecture", "waiting_for_user", decision={
                "kind": "business", "question": "Which generated client IDs were installed?",
                "reason": "Repeat", "choices": ["Return receipt"],
            })

    def test_question_review_cannot_bypass_design_or_writer(self) -> None:
        self.ask_design()
        with self.assertRaisesRegex(ValueError, "unreviewed business"):
            self.classify()
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        with self.assertRaisesRegex(ValueError, "does not own"):
            self.classify()
        self.assertFalse(self.store.read("finance-test")["designConfirmed"])

    def test_business_question_requires_gap_and_choice_impacts_before_exposure(self) -> None:
        self.ask_technical_question()
        with self.assertRaisesRegex(ValueError, "Unresolved business"):
            self.classify(disposition="business")
        self.assertEqual("reviewing", self.store.read("finance-test")["decisions"][-1]["status"])
        self.project["decisions"][-1]["choices"] = ["Education only", "Personal recommendations"]
        self.project = self.store.save(self.project)
        self.classify(
            disposition="business", unresolvedNeed="Whether to include regulated personalized advice.",
            intakeEvidence="Intake says assistant but does not specify advice scope.",
            choiceImpacts={"Education only": "General education only.",
                          "Personal recommendations": "Requires additional advice/compliance controls."},
        )
        decision = self.project["decisions"][-1]
        self.assertTrue(workflow.actionable_decision(decision))
        self.assertEqual("waiting_for_user", self.project["status"])
        self.assertEqual([], self.project["authorizations"])
        self.answer("Education only")
        self.assertEqual("Education only", self.project["decisions"][-1]["answer"])

    def test_verified_external_failure_becomes_blocker_not_question(self) -> None:
        self.ask_technical_question()
        self.classify(disposition="external-blocker", blocker={
            "kind": "host-permission", "observedFailure": "Actual Graph operation denied by tenant policy.",
            "action": "Tenant operator must permit scenario-owned registration creation.",
            "verification": "Read-only check of effective registration policy.",
        }, evidence=["Captured denied operation, code Authorization_RequestDenied."])
        self.assertEqual("setup_required", self.project["status"])
        self.assertEqual("superseded", self.project["decisions"][-1]["status"])
        self.assertEqual("host-permission", self.project["setupBlocker"]["kind"])
        self.assertEqual([], self.project["authorizations"])

    def test_incomplete_classification_stays_internal_and_cannot_grant_permissions(self) -> None:
        self.ask_technical_question()
        for invalid in (
            {"disposition": "unknown"}, {"evidence": []},
            {"disposition": "external-blocker", "blocker": {
                "kind": "host-permission", "action": "Ask an admin",
                "verification": "Check policy",
            }},
        ):
            with self.assertRaises(ValueError):
                self.classify(**invalid)
            self.assertEqual("reviewing", self.store.read("finance-test")["decisions"][-1]["status"])
        with self.assertRaisesRegex(ValueError, "cannot grant"):
            self.report("architecture", authorizations=[{"kind": "deployment"}], decisionReview={})
        with patch.dict(os.environ, {
            "ABCBUILDER_RUN_ID": "worker-1", "ABCBUILDER_ASSIGNED_JOB": "question-review",
        }):
            with self.assertRaisesRegex(ValueError, "not report implementation"):
                self.report("bicep", "completed")
        self.assertEqual([], self.store.read("finance-test")["authorizations"])

    def test_legacy_question_is_reviewed_without_changing_answered_decisions(self) -> None:
        self.ask_technical_question()
        self.project["decisions"][-1]["status"] = "pending"
        self.project["decisions"][-1].pop("previousStage")
        self.project = self.store.save(self.project)
        answered = dict(self.project["decisions"][0])
        self.assertTrue(workflow.needs_question_review(self.project["decisions"][-1]))
        with self.assertRaisesRegex(ValueError, "no longer pending"):
            self.store.finish("finance-test", "worker-1", "completed")
            self.project = self.store.read("finance-test")
            self.store.respond("finance-test", self.project["revision"], "Return receipt",
                               self.project["decisions"][-1]["id"], "Return receipt")
        self.project = self.store.claim(self.request, "worker-1", self.project["revision"])
        self.classify()
        self.assertEqual(answered, self.project["decisions"][0])
        self.assertEqual("completed", self.project["stages"]["architecture"]["status"])

    def test_cancel_idle_keeps_pending_decision_and_progress(self) -> None:
        self.ask_design()
        self.store.finish("finance-test", "worker-1", "completed")
        before = self.store.read("finance-test")
        after = self.store.cancel_idle("finance-test", before["revision"])
        self.assertEqual("cancelled", after["status"])
        self.assertEqual(before["stages"], after["stages"])
        self.assertEqual(before["decisions"], after["decisions"])
        self.assertEqual(before["authorizations"], after["authorizations"])

    def test_explicit_region_retarget_preserves_local_work_and_invalidates_cloud_grants(self) -> None:
        self.ask_design()
        self.answer("Confirm design")
        self.report("bicep", "completed")
        self.store.finish("finance-test", "worker-1", "completed")
        project = self.store.read("finance-test")
        scope = {
            "account": "operator", "subscriptionId": "sub", "tenantId": "tenant",
            "environment": "test", "resourceGroup": "rg-test", "region": "eastus2",
        }
        project["deploymentContext"] = {"scope": scope}
        project["authorizations"] = [{"kind": "deployment", "scope": scope}]
        project = self.store.save(project)
        changed = self.store.retarget_preparation(
            "finance-test", project["revision"], "eastus", "Try East US read-only validation.",
        )
        self.assertEqual("eastus", changed["deploymentContext"]["scope"]["region"])
        self.assertEqual(["deployment-preparation"], [a["kind"] for a in changed["authorizations"]])
        self.assertEqual(project["stages"]["bicep"], changed["stages"]["bicep"])
        self.assertTrue(changed["designConfirmed"])
        self.assertEqual("pending", changed["stages"]["deployment"]["status"])
        self.assertEqual("eastus2", changed["history"][-1]["previousScope"]["region"])
        self.assertEqual("deployment", changed["history"][-1]["previousAuthorizations"][0]["kind"])
        with self.assertRaisesRegex(ValueError, "Project changed"):
            self.store.retarget_preparation("finance-test", project["revision"], "eastus", "Stale request")

    def test_local_consent_survives_resume_and_restart_without_granting_cloud_access(self) -> None:
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        self.assertIsNone(self.project["localToolConsent"])
        self.project = self.store.claim(
            self.request, "worker-1", self.project["revision"], local_tool_consent=True,
        )
        consent = self.project["localToolConsent"]
        self.store.finish("finance-test", "worker-1", "completed")
        self.store = workflow.Store(Path(self.temp.name))
        self.project = self.store.read("finance-test")
        self.project = self.store.claim(self.request, "worker-1", self.project["revision"])
        self.assertEqual(consent, self.project["localToolConsent"])
        self.assertEqual([], self.project["authorizations"])
        self.assertFalse(self.project["designConfirmed"])
        other = self.store.claim({"projectSlug": "other"}, "other-worker", create=True)
        self.assertFalse(workflow.local_execution_authorized(other))

    def test_portal_preflight_policy_gates_build_steps_but_not_requirements_or_design(self) -> None:
        self.ask_design()
        self.answer("Confirm design")
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        self.project = self.store.claim(
            self.request, "worker-1", self.project["revision"], preflight_required=True,
        )
        self.report("requirements", "completed")
        with self.assertRaisesRegex(ValueError, "preflight is required"):
            self.report("bicep")
        self.assertTrue(self.project["preflightRequired"])
        self.assertEqual([], self.project["authorizations"])

    def test_local_consent_revocation_requires_idle_current_revision(self) -> None:
        with self.assertRaisesRegex(ValueError, "active worker"):
            self.store.revoke_local_consent("finance-test", self.project["revision"])
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        self.project = self.store.claim(
            self.request, "worker-1", self.project["revision"], local_tool_consent=True,
        )
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        with self.assertRaisesRegex(ValueError, "Project changed"):
            self.store.revoke_local_consent("finance-test", self.project["revision"] - 1)
        project = self.store.revoke_local_consent("finance-test", self.project["revision"])
        self.assertFalse(workflow.local_execution_authorized(project))
        self.assertEqual([], project["authorizations"])

    def test_legacy_read_does_not_infer_or_persist_consent(self) -> None:
        path = self.store.path("finance-test")
        project = self.store.read("finance-test")
        project.pop("localToolConsent")
        project.pop("setupBlocker")
        path.write_text(json.dumps(project), encoding="utf-8")
        before = path.read_bytes()
        self.assertIsNone(self.store.read("finance-test")["localToolConsent"])
        self.assertEqual(before, path.read_bytes())
        with self.assertRaisesRegex(ValueError, "cannot grant"):
            self.report("requirements", localToolConsent={"scope": "scenario-local-execution"})

    def test_setup_blocker_is_not_a_decision_and_requires_worker_verification(self) -> None:
        setup = {
            "kind": "prerequisite", "action": "Correct Graphviz PATH outside the worker.",
            "verification": "Check dot and render a PNG from this worker.",
        }
        self.report("requirements", "blocked", blocker=setup, evidence=["Synthetic probe: dot unavailable"])
        blocker = self.project["setupBlocker"]
        self.assertEqual([], self.project["decisions"])
        self.report("requirements", "blocked", blocker=setup)
        self.assertEqual(blocker["id"], self.project["setupBlocker"]["id"])
        self.store.finish("finance-test", "worker-1", "completed")
        self.project = self.store.read("finance-test")
        self.assertEqual("setup_required", self.project["status"])
        with self.assertRaisesRegex(ValueError, "Verify setup"):
            self.store.respond("finance-test", self.project["revision"], "I approve; it is corrected")
        self.project = self.store.claim(self.request, "worker-1", self.project["revision"])
        with self.assertRaisesRegex(ValueError, "Verify the setup"):
            self.report("requirements")
        for verification, evidence in (
            ({"blockerId": "stale", "passed": True}, ["probe"]),
            ({"blockerId": blocker["id"], "passed": False}, ["probe failed"]),
            ({"blockerId": blocker["id"], "passed": True}, []),
        ):
            with self.subTest(verification=verification), self.assertRaises(ValueError):
                self.report("requirements", "pending", setupVerification=verification, evidence=evidence)
        self.report("requirements", "pending", setupVerification={"blockerId": blocker["id"], "passed": True},
                    evidence=["Synthetic verification: dependency now resolves and render passed"])
        self.assertIsNone(self.project["setupBlocker"])
        self.assertEqual(blocker["id"], self.project["history"][-1]["blockerId"])
        self.report("requirements", "completed")
        self.assertEqual([], self.project["authorizations"])

    def test_generated_command_bugs_cannot_become_permission_blockers(self) -> None:
        for name in ("home", "HOME", "pid", "Host"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "command bug"):
                self.report("requirements", "blocked", blocker={
                    "kind": "host-permission", "action": "Grant profile access",
                    "verification": f"${name} = Invoke-WebRequest http://127.0.0.1:8080",
                })
        self.assertIsNone(self.store.read("finance-test")["setupBlocker"])

    def test_setup_verification_cannot_claim_stage_completion_or_cloud_permission(self) -> None:
        self.report("deployment", "blocked", blocker={
            "kind": "host-permission", "action": "Review the denied local probe in the execution host.",
            "verification": "Repeat only the permitted original local probe.",
        })
        identifier = self.project["setupBlocker"]["id"]
        with self.assertRaises(ValueError):
            self.report("deployment", "completed", setupVerification={"blockerId": identifier, "passed": True})
        self.report("deployment", "pending", setupVerification={"blockerId": identifier, "passed": True})
        self.assertEqual([], self.project["authorizations"])
        with self.assertRaisesRegex(ValueError, "Exact-target"):
            self.report("deployment", "running")

    def test_unidentified_cli_approval_is_not_an_actionable_host_setup_request(self) -> None:
        self.report("deployment", "blocked", blocker={
            "kind": "host-permission",
            "action": "Inspect CLI evidence. No structured permission metadata was returned.",
            "verification": "Original denied command; do not rerun.",
        }, evidence=["Permission denied because no interactive user response was available."])
        blocker = self.project["setupBlocker"]
        self.assertEqual("workflow-error", blocker["kind"])
        self.assertEqual("unresolved-cli-approval", blocker["category"])
        self.assertIn("No user setup or approval action", blocker["action"])
        self.assertEqual("Original denied command; do not rerun.", blocker["verification"])
        self.assertEqual([], self.project["authorizations"])

    def test_saved_unidentified_approval_migration_keeps_denial_and_permissions(self) -> None:
        self.report("deployment", "blocked", blocker={
            "kind": "host-permission", "action": "Review the specifically identified denied path.",
            "verification": "Original command",
        })
        self.store.finish("finance-test", "worker-1", "completed")
        project = self.store.read("finance-test")
        project["setupBlocker"]["action"] = "No structured permission metadata was returned. Inspect CLI logs."
        project = self.store.save(project)
        before = dict(project["setupBlocker"])
        migrated = self.store.classify_saved_approval_failure("finance-test", project["revision"])
        self.assertEqual("workflow-error", migrated["setupBlocker"]["kind"])
        self.assertEqual(before["id"], migrated["setupBlocker"]["id"])
        self.assertEqual(before["verification"], migrated["setupBlocker"]["verification"])
        self.assertEqual(project["authorizations"], migrated["authorizations"])
        self.assertIsNone(migrated["writer"])
        self.assertEqual(before, migrated["history"][-1]["previousBlocker"])

    def test_rejected_design_cannot_start_implementation(self) -> None:
        self.ask_design()
        self.answer("Revise")
        with self.assertRaisesRegex(ValueError, "Confirm the architecture"):
            self.report("application")

    def test_worker_must_supply_evidence_and_known_event_shape(self) -> None:
        for values in (
            {"stage": "invented"},
            {"status": "success"},
            {"status": "completed", "evidence": []},
            {"status": "waiting_for_user"},
            {"summary": ""},
            {"evidence": [1]},
            {"status": "waiting_for_user", "decision": []},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.report(**values)

    def test_stale_revision_and_wrong_owner_rejected(self) -> None:
        for owner, revision in (("worker-1", 0), ("another-chat", self.project["revision"])):
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                self.store.report("finance-test", owner, revision, {
                    "stage": "requirements", "status": "running", "summary": "start",
                })
        with self.assertRaisesRegex(ValueError, "active writer"):
            workflow.Store(Path(self.temp.name)).claim(self.request, "worker-2", self.project["revision"])

    def test_unknown_state_schema_fails_explicitly_without_resetting_progress(self) -> None:
        self.project["schemaVersion"] = 2
        path = self.store.path("finance-test")
        path.write_text(json.dumps(self.project), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported project state"):
            self.store.read("finance-test")
        self.assertEqual(2, json.loads(path.read_text(encoding="utf-8"))["schemaVersion"])

    def test_legacy_project_gains_composition_stages_without_read_side_effects(self) -> None:
        path = self.store.path("finance-test")
        project = self.store.read("finance-test")
        project["stages"] = {key: value for key, value in project["stages"].items()
                             if key in workflow.LEGACY_STAGES}
        path.write_text(json.dumps(project), encoding="utf-8")
        original = path.read_bytes()
        restored = self.store.read("finance-test")
        self.assertEqual("pending", restored["stages"]["hack-content"]["status"])
        self.assertEqual(project["revision"], restored["revision"])
        self.assertEqual(original, path.read_bytes())

    def test_decision_and_history_survive_restart_and_multiple_answers(self) -> None:
        self.ask_design()
        self.store.finish("finance-test", "worker-1", "completed")
        self.store = workflow.Store(Path(self.temp.name))
        self.project = self.store.read("finance-test")
        self.assertEqual("waiting_for_user", self.project["status"])
        with self.assertRaisesRegex(ValueError, "displayed choices"):
            self.store.respond("finance-test", self.project["revision"], "good to go")
        decision = self.project["decisions"][0]
        self.project = self.store.respond(
            "finance-test", self.project["revision"], "Yes, as shown", decision["id"], "Confirm design",
        )
        self.project = self.store.respond("finance-test", self.project["revision"], "Keep chat anonymous")
        self.assertEqual(["Yes, as shown", "Keep chat anonymous"], [h["message"] for h in self.project["history"]])
        self.assertTrue(self.project["designConfirmed"])
        self.assertEqual(self.request, self.project["request"])

    def test_local_ready_requires_reported_validation_and_failure_is_not_hidden(self) -> None:
        self.ask_design()
        self.answer("Confirm design")
        for stage in ("diagrams", "bicep", "application"):
            self.report(stage, "completed")
        self.report("local-validation", "completed", evidence=["dotnet test: 18 passed"])
        self.store.finish("finance-test", "worker-1", "completed")
        self.assertEqual("local_ready", self.store.read("finance-test")["status"])
        self.project = self.store.claim(self.request, "worker-1", self.store.read("finance-test")["revision"])
        self.report("bicep", "failed", summary="Bicep compiler failed")
        self.store.finish("finance-test", "worker-1", "completed")
        self.assertEqual("failed", self.store.read("finance-test")["status"])

    def test_zero_exit_with_unfinished_stage_needs_attention(self) -> None:
        self.report("requirements")
        self.store.finish("finance-test", "worker-1", "completed")
        project = self.store.read("finance-test")
        self.assertEqual("needs_attention", project["status"])
        self.assertEqual("failed", project["stages"]["requirements"]["status"])

    def cloud_decision(self, kind: str, scope: dict) -> dict:
        return self.report("deployment", "waiting_for_user", decision={
            "kind": kind, "question": f"Authorize {kind} for displayed targets?",
            "reason": "Review exact targets and scope", "choices": ["Authorize", "Decline"],
            "acceptChoice": "Authorize", "scope": scope,
        })

    def test_cloud_permissions_are_separate_exact_scoped_and_revocable(self) -> None:
        scope = dict(account="user@example.invalid", subscriptionId="subscription", tenantId="tenant",
                     resourceGroup="rg-finance", environment="finance-dev", region="eastus2")
        with self.assertRaisesRegex(ValueError, "deployment consent"):
            self.report("deployment", "running")
        self.cloud_decision("deployment-preparation", scope)
        self.answer("Authorize")
        self.assertEqual("deployment-preparation", self.project["authorizations"][0]["kind"])
        with self.assertRaisesRegex(ValueError, "deployment consent"):
            self.report("deployment", "running")
        with self.assertRaisesRegex(ValueError, "whatIfEvidence"):
            self.cloud_decision("deployment", scope)
        deployment = {**scope, "whatIfEvidence": "what-if.txt: 8 creates, 0 deletes",
                      "estimatedCost": "USD 120/month estimate"}
        with self.assertRaisesRegex(ValueError, "these targets"):
            self.cloud_decision("deployment", {**deployment, "region": "westus"})
        self.cloud_decision("deployment", deployment)
        self.answer("Authorize")
        with self.assertRaisesRegex(ValueError, "local validation"):
            self.report("deployment", "running")
        self.ask_design()
        self.answer("Confirm design")
        for stage in ("diagrams", "bicep", "application", "local-validation"):
            self.report(stage, "completed")
        self.cloud_decision("deployment-preparation", scope)
        self.answer("Authorize")
        self.cloud_decision("deployment", deployment)
        self.answer("Authorize")
        self.report("deployment", "running")
        self.store.finish("finance-test", "worker-1", "cancelled")
        self.project = self.store.read("finance-test")
        self.project = self.store.respond(
            "finance-test", self.project["revision"], "Change security design", revise=True,
        )
        self.assertFalse(self.project["designConfirmed"])
        self.assertEqual([], self.project["authorizations"])
        self.assertTrue(all(stage["status"] == "pending" for stage in self.project["stages"].values()))

    def test_repair_invalidates_local_validation_and_old_cloud_consent(self) -> None:
        self.ask_design()
        self.answer("Confirm design")
        for stage in ("diagrams", "bicep", "application", "local-validation"):
            self.report(stage, "completed")
        scope = dict(account="user", subscriptionId="s", tenantId="t",
                     resourceGroup="rg", environment="dev", region="eastus2")
        self.cloud_decision("deployment-preparation", scope)
        self.answer("Authorize")
        self.cloud_decision("deployment", {**scope, "whatIfEvidence": "actual what-if", "estimatedCost": "$100"})
        self.answer("Authorize")
        self.report("application", "running")
        self.assertEqual("pending", self.project["stages"]["local-validation"]["status"])
        self.assertEqual([], self.project["authorizations"])

    def test_preparation_progress_reuses_scope_without_marking_deployment_completed(self) -> None:
        scope = dict(account="user", subscriptionId="s", tenantId="t",
                     resourceGroup="rg", environment="dev", region="eastus2")
        self.cloud_decision("deployment-preparation", scope)
        self.answer("Authorize")
        for status in ("running", "completed"):
            self.report("deployment", status, operation="deployment-preparation", scope=scope)
        self.assertEqual("completed", self.project["deploymentPreparation"]["status"])
        self.assertEqual("pending", self.project["stages"]["deployment"]["status"])
        self.assertEqual(["deployment-preparation"], [a["kind"] for a in self.project["authorizations"]])
        for stage in ("deployment", "live-validation", "review"):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "deployment consent"):
                self.report(stage, "running")
        for change in ("region", "resourceGroup", "subscriptionId", "account", "tenantId", "environment"):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "preparation consent"):
                self.report("deployment", "running", operation="deployment-preparation",
                            scope={**scope, change: "other"})
        with self.assertRaisesRegex(ValueError, "Preparation reports belong"):
            self.report("live-validation", "completed", operation="deployment-preparation", scope=scope)
        with self.assertRaisesRegex(ValueError, "Unknown workflow operation"):
            self.report("deployment", "running", operation="anything", scope=scope)

    def test_preparation_requires_consent_and_reports_failure_without_deployment(self) -> None:
        scope = dict(account="user", subscriptionId="s", tenantId="t",
                     resourceGroup="rg", environment="dev", region="eastus2")
        with self.assertRaisesRegex(ValueError, "preparation consent"):
            self.report("deployment", "running", operation="deployment-preparation", scope=scope)
        self.cloud_decision("deployment-preparation", scope)
        self.answer("Authorize")
        self.report("deployment", "failed", operation="deployment-preparation", scope=scope)
        self.assertEqual("failed", self.project["deploymentPreparation"]["status"])
        self.assertEqual("pending", self.project["stages"]["deployment"]["status"])

    def test_product_defect_can_be_reported_without_claiming_missing_host_permissions(self) -> None:
        self.report("requirements", "blocked", blocker={
            "kind": "workflow-error", "action": "Portal workflow failed; maintainer repair required, no new consent.",
            "verification": "Run the workflow regression test.",
        })
        self.assertEqual("workflow-error", self.store.read("finance-test")["setupBlocker"]["kind"])

    def test_declining_replacement_cloud_consent_revokes_old_deployment_permission(self) -> None:
        scope = dict(account="user", subscriptionId="s", tenantId="t",
                     resourceGroup="rg", environment="dev", region="eastus2")
        self.cloud_decision("deployment-preparation", scope)
        self.answer("Authorize")
        self.cloud_decision("deployment", {**scope, "whatIfEvidence": "actual what-if", "estimatedCost": "$100"})
        self.answer("Authorize")
        self.cloud_decision("deployment-preparation", {**scope, "region": "westus"})
        self.answer("Decline")
        self.assertEqual([], self.project["authorizations"])

    def test_report_cli_uses_backend_environment_and_rejects_stale_write(self) -> None:
        event = Path(self.temp.name) / "event.json"
        event.write_text(json.dumps({
            "stage": "requirements", "status": "completed", "summary": "Requirements recorded",
            "evidence": ["01-requirements.md"],
        }), encoding="utf-8")
        command = [sys.executable, str(Path(workflow.__file__)), "report",
                   "--revision", str(self.project["revision"]), "--event", str(event)]
        env = {**os.environ, "HACKBUILDER_PROJECT_STATE": self.temp.name,
               "HACKBUILDER_PROJECT": "finance-test", "HACKBUILDER_RUN_ID": "worker-1"}
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        stale = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(1, stale.returncode)
        self.assertIn("Project changed", stale.stderr)

    def test_external_chat_claim_uses_same_lease_as_portal(self) -> None:
        self.store.finish("finance-test", "worker-1", "completed")
        revision = self.store.read("finance-test")["revision"]
        command = [
            sys.executable, str(Path(workflow.__file__)), "claim", "--directory", self.temp.name,
            "--project", "finance-test", "--owner", "vscode-repair", "--revision", str(revision),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        project = self.store.read("finance-test")
        self.assertEqual("vscode-repair", project["writer"])
        with self.assertRaisesRegex(ValueError, "active writer"):
            self.store.claim(self.request, "portal-attempt", project["revision"])
        command = [
            sys.executable, str(Path(workflow.__file__)), "finish", "--directory", self.temp.name,
            "--project", "finance-test", "--owner", "vscode-repair", "--outcome", "completed",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIsNone(self.store.read("finance-test")["writer"])


if __name__ == "__main__":
    unittest.main()
