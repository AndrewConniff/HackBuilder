"""Verify backend stage selection, real evidence gates and fixed setup commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backend_readiness
import portal_server
import portal_workflow
import setup_backend
import workflow_engine


class BackendTests(unittest.TestCase):
    def test_assigned_job_treats_generated_ids_as_deployment_outputs(self) -> None:
        instruction = workflow_engine.instruction({
            "name": "deployment-preparation", "stages": ["deployment"],
            "operation": "deployment-preparation", "scope": {"tenantId": "retained-tenant"},
        })
        self.assertIn("not user inputs", instruction)
        self.assertIn("Never request them in a business decision or manual receipt questionnaire", instruction)
        self.assertIn("must not block independent read-only preparation", instruction)
        self.assertIn("Do not fabricate IDs", instruction)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = portal_workflow.Store(self.root / "projects")
        self.request = {"projectSlug": "bounded-test", "services": ["foundry"], "prompt": "A brokerage assistant"}
        self.project = self.store.claim(self.request, "owner", create=True, local_tool_consent=True)

    def test_selects_incomplete_stage_and_stops_for_real_decision(self) -> None:
        self.assertEqual("requirements", workflow_engine.next_operation(self.project)["name"])
        self.project["stages"]["requirements"]["status"] = "completed"
        self.assertEqual("architecture", workflow_engine.next_operation(self.project)["name"])
        self.project["decisions"].append({"status": "pending"})
        self.assertIsNone(workflow_engine.next_operation(self.project))
        self.project["decisions"] = []
        self.project["stages"]["architecture"]["status"] = "completed"
        self.assertIsNone(workflow_engine.next_operation(self.project))
        self.project["designConfirmed"] = True
        self.assertEqual("diagrams", workflow_engine.next_operation(self.project)["name"])

    def test_legacy_and_new_business_questions_are_classified_before_user_decisions(self) -> None:
        for status in ("pending", "reviewing"):
            self.project["decisions"] = [{
                "id": "question-1", "kind": "business", "status": status, "stage": "requirements",
            }]
            operation = workflow_engine.next_operation(self.project)
            self.assertEqual("question-review", operation["name"])
            self.assertEqual("question-1", operation["decisionId"])
            self.assertIn("Do not ask the user to classify", workflow_engine.instruction(operation))
        self.project["decisions"][0]["status"] = "pending"
        self.project["decisions"][0]["review"] = {"disposition": "business"}
        self.assertIsNone(workflow_engine.next_operation(self.project))

    def test_startup_recovery_resumes_only_eligible_waiting_question_once(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        try:
            with patch.object(portal_server.threading.Thread, "start"):
                run = portal.start(self.request, "test", "scenario", local_tool_consent=True)
            portal.projects.finish("bounded-test", run["id"], "completed")
            portal.workers.pop(run["id"])
            project = portal.projects.read("bounded-test")
            project["decisions"] = [{
                "id": "legacy", "kind": "business", "status": "pending", "stage": "requirements",
            }]
            project["status"] = "waiting_for_user"
            portal.projects.save(project)
            run.update(status="completed")
            portal.save(run)
            with patch.object(portal, "start") as start:
                portal.recover_pending_questions()
                portal.recover_pending_questions()
            self.assertEqual(1, start.call_count)
            portal.question_recovery_attempted.clear()
            run["status"] = "paused"
            portal.save(run)
            with patch.object(portal, "start") as start:
                portal.recover_pending_questions()
            start.assert_not_called()
            run["status"] = "completed"
            portal.save(run)
            project = portal.projects.read("bounded-test")
            project["localToolConsent"] = None
            portal.projects.save(project)
            with patch.object(portal, "start") as start:
                portal.recover_pending_questions()
            start.assert_not_called()
        finally:
            portal.shutdown()

    def test_concurrent_status_reads_and_atomic_run_saves_do_not_collide(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        run = {"id": "a" * 32, "startedAtUtc": "2026-10-23T00:00:00Z", "status": "completed"}
        portal.save(run)

        def access(index: int) -> None:
            for iteration in range(40):
                if index % 2:
                    portal.save({**run, "counter": iteration})
                else:
                    self.assertEqual(run["id"], portal.read(run["id"])["id"])
                    self.assertEqual(1, len(portal.runs()))

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(access, range(8)))
        self.assertEqual([], list((portal.state / run["id"]).glob("*.tmp")))

    def test_preparation_never_becomes_deployment_without_exact_consent(self) -> None:
        for stage in workflow_engine.LOCAL_STAGES:
            self.project["stages"][stage]["status"] = "completed"
        self.project["designConfirmed"] = True
        self.assertEqual("target-review", workflow_engine.next_operation(self.project)["name"])
        scope = {"subscriptionId": "subscription", "region": "eastus"}
        self.project["authorizations"] = [{"kind": "deployment-preparation", "scope": scope}]
        self.assertEqual("deployment-preparation", workflow_engine.next_operation(self.project)["operation"])
        self.project["deploymentPreparation"] = {"status": "completed", "scope": scope}
        self.assertEqual("deployment-decision", workflow_engine.next_operation(self.project)["name"])
        self.project["authorizations"].append({"kind": "deployment", "scope": scope})
        self.assertEqual("deployment", workflow_engine.next_operation(self.project)["name"])
        self.project["stages"]["deployment"]["status"] = "completed"
        self.assertEqual("live-validation", workflow_engine.next_operation(self.project)["name"])
        self.assertEqual([], self.project["decisions"])

    def test_cloud_question_review_does_not_reuse_older_deployment_grant_or_what_if(self) -> None:
        for stage in workflow_engine.LOCAL_STAGES:
            self.project["stages"][stage]["status"] = "completed"
        self.project["designConfirmed"] = True
        scope = {"subscriptionId": "retained", "region": "eastus"}
        self.project["authorizations"] = [
            {"kind": "deployment-preparation", "scope": scope, "recordedAtUtc": "2026-10-23T10:00:00+00:00"},
            {"kind": "deployment", "scope": scope, "recordedAtUtc": "2026-10-23T11:00:00+00:00"},
        ]
        self.project["deploymentPreparation"] = {
            "status": "completed", "scope": scope, "updatedAtUtc": "2026-10-23T10:30:00+00:00",
        }
        self.project["decisions"] = [{
            "kind": "business", "stage": "deployment", "status": "superseded",
            "review": {"disposition": "technical", "reviewedAtUtc": "2026-10-23T12:00:00+00:00"},
        }]
        retained = list(self.project["authorizations"])
        self.assertEqual("deployment-preparation", workflow_engine.next_operation(self.project)["name"])
        self.assertEqual(retained, self.project["authorizations"])
        self.project["deploymentPreparation"]["updatedAtUtc"] = "2026-10-23T12:30:00+00:00"
        self.assertEqual("deployment-decision", workflow_engine.next_operation(self.project)["name"])
        self.project["authorizations"][-1]["recordedAtUtc"] = "2026-10-23T13:00:00+00:00"
        self.assertEqual("deployment", workflow_engine.next_operation(self.project)["name"])

    def test_report_cannot_escape_backend_assigned_stage(self) -> None:
        with patch.dict(os.environ, {"ABCBUILDER_RUN_ID": "owner", "ABCBUILDER_ASSIGNED_STAGES": '["requirements"]'}):
            with self.assertRaisesRegex(ValueError, "Python backend assigned"):
                self.store.report("bounded-test", "owner", self.project["revision"], {
                    "stage": "architecture", "status": "running", "summary": "Out of order",
                })
        self.assertEqual("pending", self.store.read("bounded-test")["stages"]["architecture"]["status"])

    def test_completion_requires_real_artifacts_and_dotnet_project(self) -> None:
        with self.assertRaisesRegex(ValueError, "required nonempty artifact"):
            workflow_engine.validate_completed(self.root, self.root, {"name": "requirements"})
        (self.root / "01-requirements.md").write_text("Actual story", encoding="utf-8")
        self.assertEqual([], workflow_engine.validate_completed(self.root, self.root, {"name": "requirements"}))
        with self.assertRaisesRegex(ValueError, "no project"):
            workflow_engine.validate_completed(self.root, self.root, {"name": "application"})

    def test_local_import_recovers_validated_scope_before_revalidating_existing_assets(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        folder = self.root / "generated-scenarios" / "import-test"
        folder.mkdir(parents=True)
        original = b"Original brokerage requirements."
        (folder / "01-requirements.md").write_bytes(original)
        intake = {
            "projectSlug": "import-test", "prompt": "A brokerage assistant from existing requirements.",
            "industry": "Financial Services", "businessUnits": ["finance"], "services": ["foundry", "key-vault"],
            "pillars": ["security"], "domains": [],
            "recoveryEvidence": ["01-requirements.md: brokerage finance scope, Foundry and Key Vault."],
        }
        prefix = (
            "import os,sys,json; from pathlib import Path; "
            f"sys.path.insert(0,{str(Path(portal_server.__file__).parent)!r}); "
            "from portal_workflow import Store; s=Store(Path(os.environ['ABCBUILDER_PROJECT_STATE'])); "
            "slug=os.environ['ABCBUILDER_PROJECT']; owner=os.environ['ABCBUILDER_RUN_ID']; p=s.read(slug); "
        )
        scripts = [
            prefix + f"out=Path(os.environ['ABCBUILDER_PROJECT_STATE']).parent/owner/'recovered-intake.json'; "
            f"out.write_text({json.dumps(intake)!r},encoding='utf-8')",
            prefix + "s.report(slug,owner,p['revision'],dict(stage='requirements',status='completed',"
            "summary='Existing story verified',evidence=['01-requirements.md']))",
            prefix + "s.report(slug,owner,p['revision'],dict(stage='architecture',status='waiting_for_user',"
            "summary='Existing architecture checked',evidence=['Actual architecture review'],decision=dict("
            "kind='design',question='Confirm recovered design?',reason='Review current evidence',"
            "choices=['Confirm','Revise'],acceptChoice='Confirm')))",
        ]
        try:
            with (
                patch.object(portal_server, "ROOT", self.root),
                patch.object(portal_server.threading.Thread, "start"),
                patch.object(portal, "readiness", return_value={"ready": True}) as readiness,
                patch.object(workflow_engine, "validate_completed", return_value=[]),
                patch.object(portal_server, "cli_command", side_effect=[
                    [sys.executable, "-c", script] for script in scripts
                ]) as launch,
            ):
                preview = next(r for r in portal.discovered() if r["request"]["projectSlug"] == "import-test")
                run = portal.resume_local(preview, True)
                self.assertEqual("reconcile-local", workflow_engine.next_operation(
                    portal.projects.read("import-test"),
                )["name"])
                portal.execute(run, "Resume existing local assets.")
            result = portal.projects.read("import-test")
            self.assertEqual(3, launch.call_count)
            self.assertEqual(2, readiness.call_count)
            self.assertEqual("completed", result["reconciliation"]["status"])
            self.assertEqual(["finance"], result["request"]["businessUnits"])
            self.assertEqual(["foundry", "key-vault"], portal.read(run["id"])["request"]["services"])
            self.assertEqual("waiting_for_user", result["status"], portal.read(run["id"]))
            self.assertEqual("completed", result["stages"]["requirements"]["status"])
            self.assertEqual("pending", result["stages"]["application"]["status"])
            self.assertFalse(result["designConfirmed"])
            self.assertEqual([], result["authorizations"])
            self.assertEqual(original, (folder / "01-requirements.md").read_bytes())
            self.assertIsNone(result["writer"])
        finally:
            portal.shutdown()

    def test_local_reconciliation_rejects_stale_writer_and_permission_import(self) -> None:
        request = {**self.request, "projectSlug": "recovery-test",
                   "localResume": {"sourceRunId": "local-preview"}}
        project = self.store.claim(request, "owner", create=True, local_tool_consent=True)
        recovered = {
            **request, "industry": "Financial Services", "deploymentAuthorized": False, "scenarioApproved": False,
        }
        with self.assertRaisesRegex(ValueError, "current project writer"):
            self.store.reconcile_intake("recovery-test", "other", project["revision"], recovered, ["requirements"])
        with self.assertRaisesRegex(ValueError, "cannot authorize"):
            self.store.reconcile_intake("recovery-test", "owner", project["revision"],
                                        {**recovered, "deploymentAuthorized": True}, ["requirements"])
        with self.assertRaisesRegex(ValueError, "artifact evidence"):
            self.store.reconcile_intake("recovery-test", "owner", project["revision"], recovered, [])
        result = self.store.reconcile_intake("recovery-test", "owner", project["revision"], recovered, ["requirements"])
        with self.assertRaisesRegex(ValueError, "Project changed"):
            self.store.reconcile_intake("recovery-test", "owner", project["revision"], recovered, ["requirements"])
        self.assertEqual("completed", result["reconciliation"]["status"])
        self.assertTrue(all(s["status"] == "pending" for s in result["stages"].values()))
        self.assertEqual([], result["authorizations"])

    def test_local_import_missing_scope_fails_visibly_without_touching_reference(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        folder = self.root / "generated-scenarios" / "unclassified"
        folder.mkdir(parents=True)
        (folder / "README.md").write_text("Partial local project.", encoding="utf-8")
        script = (
            "import os; from pathlib import Path; "
            "p=Path(os.environ['ABCBUILDER_PROJECT_STATE']).parent/os.environ['ABCBUILDER_RUN_ID']; "
            "(p/'recovered-intake.json').write_text("
            "'{\"projectSlug\":\"unclassified\",\"industry\":null,\"recoveryEvidence\":[\"README.md\"]}',"
            "encoding='utf-8')"
        )
        try:
            with (
                patch.object(portal_server, "ROOT", self.root),
                patch.object(portal_server.threading.Thread, "start"),
                patch.object(portal, "readiness", return_value={"ready": True}),
                patch.object(portal_server, "cli_command", return_value=[sys.executable, "-c", script]) as launch,
                self.assertLogs(portal_server.LOG, level="ERROR"),
            ):
                run = portal.resume_local(portal.discovered()[0], True)
                portal.execute(run, "Recover existing scope.")
            saved = portal.read(run["id"])
            self.assertEqual("failed", saved["status"])
            self.assertIn("Select exactly one industry", saved["error"])
            self.assertEqual(1, launch.call_count)
            project = portal.projects.read("unclassified")
            self.assertEqual("pending", project["reconciliation"]["status"])
            self.assertEqual([], project["authorizations"])
            self.assertIsNone(project["writer"])
            self.assertEqual("Partial local project.", (folder / "README.md").read_text(encoding="utf-8"))
        finally:
            portal.shutdown()

    def test_readiness_aggregates_browser_and_authentication_failures(self) -> None:
        from scripts.tests.test_prerequisite_profiles import report_fixture

        fixture = report_fixture(["foundry"])
        with (
            patch.object(backend_readiness.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 0, json.dumps(fixture), "",
            )),
            patch.object(backend_readiness, "browser_checks", return_value=[
                {"id": "chromium-runtime", "name": "Browser", "ok": False},
            ]),
            patch.object(backend_readiness, "dotnet_checks", return_value=[]),
            patch.object(backend_readiness.azure_context, "identity", side_effect=ValueError("azd signed out")),
        ):
            report = backend_readiness.audit(self.root, self.project)
        self.assertFalse(report["ready"])
        self.assertEqual(
            {"chromium-runtime", "azure-authentication"},
            {item["id"] for item in report["checks"] if not item["ok"]},
        )
        self.assertNotIn("identity", report)

    def test_setup_accepts_only_fixed_recipe_and_does_not_install_stopped_docker(self) -> None:
        python = self.root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / (
            "python.exe" if sys.platform == "win32" else "python"
        )
        python.parent.mkdir(parents=True)
        python.touch()
        report = {"checks": [
            {"id": "docker", "ok": False, "installed": True, "fix": "untrusted arbitrary command"},
            {"id": "chromium-runtime", "ok": False},
        ]}
        with patch.object(setup_backend.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "done", "")) as run:
            evidence = setup_backend.repair(self.root, report)
        self.assertEqual(1, len(evidence))
        self.assertEqual([str(python), "-m", "playwright", "install", "chromium"], run.call_args.args[0])
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_failed_readiness_never_spawns_agent_and_releases_writer(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        try:
            with (
                patch.object(portal_server.threading.Thread, "start"),
                patch.object(portal, "readiness", return_value={
                    "ready": False, "checks": [{"name": "Docker", "ok": False}, {"name": "azd", "ok": False}],
                }),
                patch.object(portal_server.subprocess, "Popen") as spawn,
            ):
                run = portal.start(self.request, "test", "scenario", local_tool_consent=True)
                portal.execute(run, "test")
            spawn.assert_not_called()
            result = portal.read(run["id"])
            self.assertEqual("failed", result["status"])
            self.assertIn("Docker, azd", result["error"])
            self.assertIsNone(portal.projects.read("bounded-test")["writer"])
        finally:
            portal.shutdown()

    def test_bounded_subprocesses_advance_automatically_and_stop_at_design(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        prefix = (
            "import os,sys; from pathlib import Path; "
            f"sys.path.insert(0,{str(Path(portal_server.__file__).parent)!r}); "
            "from portal_workflow import Store; s=Store(Path(os.environ['ABCBUILDER_PROJECT_STATE'])); "
            "slug=os.environ['ABCBUILDER_PROJECT']; owner=os.environ['ABCBUILDER_RUN_ID']; p=s.read(slug); "
        )
        scripts = [
            prefix + "s.report(slug,owner,p['revision'],dict(stage='requirements',status='completed',"
            "summary='Story complete',evidence=['Test story']))",
            prefix + "s.report(slug,owner,p['revision'],dict(stage='architecture',status='waiting_for_user',"
            "summary='Architecture ready',evidence=['Test architecture'],decision=dict(kind='design',question='Confirm?',reason='Design review',"
            "choices=['Confirm','Revise'],acceptChoice='Confirm')))",
        ]
        try:
            with (
                patch.object(portal_server.threading.Thread, "start"),
                patch.object(portal, "readiness", return_value={"ready": True}),
                patch.object(workflow_engine, "validate_completed", return_value=[]),
                patch.object(portal_server, "cli_command", side_effect=[
                    [sys.executable, "-c", script] for script in scripts
                ]) as launch,
            ):
                run = portal.start(self.request, "test", "scenario", local_tool_consent=True)
                portal.execute(run, "test")
            self.assertEqual(2, launch.call_count)
            result = portal.projects.read("bounded-test")
            self.assertEqual("waiting_for_user", result["status"], portal.read(run["id"]))
            self.assertEqual("completed", result["stages"]["requirements"]["status"])
            self.assertIsNone(result["writer"])
            self.assertEqual([], result["authorizations"])
        finally:
            portal.shutdown()

    def test_technical_question_is_reviewed_and_continues_without_user_response(self) -> None:
        portal = portal_server.Portal(self.root / "runs", "test-token", sys.executable)
        prefix = (
            "import os,sys; from pathlib import Path; "
            f"sys.path.insert(0,{str(Path(portal_server.__file__).parent)!r}); "
            "from portal_workflow import Store; s=Store(Path(os.environ['ABCBUILDER_PROJECT_STATE'])); "
            "slug=os.environ['ABCBUILDER_PROJECT']; owner=os.environ['ABCBUILDER_RUN_ID']; p=s.read(slug); "
        )
        scripts = [
            prefix + "s.report(slug,owner,p['revision'],dict(stage='requirements',status='waiting_for_user',"
            "summary='Technical question',decision=dict(kind='business',question='Provide generated IDs?',"
            "reason='Old handoff',choices=['Return IDs'])))",
            prefix + "s.report(slug,owner,p['revision'],dict(stage='requirements',decisionReview=dict("
            "decisionId=p['decisions'][-1]['id'],disposition='technical',reason='Deployment output',"
            "resolution='Capture real IDs during separately authorized deployment',"
            "evidence=['Intake asks for a new standalone reference'])))",
            prefix + "s.report(slug,owner,p['revision'],dict(stage='requirements',status='completed',"
            "summary='Story complete',evidence=['Test story']))",
            prefix + "s.report(slug,owner,p['revision'],dict(stage='architecture',status='waiting_for_user',"
            "summary='Architecture ready',evidence=['Test architecture'],decision=dict(kind='design',"
            "question='Confirm?',reason='Design review',choices=['Confirm','Revise'],acceptChoice='Confirm')))",
        ]
        try:
            with (
                patch.object(portal_server.threading.Thread, "start"),
                patch.object(portal, "readiness", return_value={"ready": True}),
                patch.object(workflow_engine, "validate_completed", return_value=[]),
                patch.object(portal_server, "cli_command", side_effect=[
                    [sys.executable, "-c", script] for script in scripts
                ]) as launch,
            ):
                run = portal.start(self.request, "test", "scenario", local_tool_consent=True)
                portal.execute(run, "test")
            self.assertEqual(4, launch.call_count)
            result = portal.projects.read("bounded-test")
            self.assertEqual("waiting_for_user", result["status"], portal.read(run["id"]))
            self.assertEqual("superseded", result["decisions"][0]["status"])
            self.assertNotIn("answer", result["decisions"][0])
            self.assertEqual("design", result["decisions"][-1]["kind"])
            self.assertIsNone(result["writer"])
            self.assertEqual([], result["authorizations"])
        finally:
            portal.shutdown()
