"""Verify the portal only hands off, reads progress and exports bounded files."""

from __future__ import annotations

import http.client
import io
import json
import re
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal_status
import portal_visualizer as portal


class VisualizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "portal").mkdir()
        for name in ("catalog.json", "visualizer.html", "visualizer.css", "visualizer.js", "markdown.js"):
            shutil.copy(portal.ROOT / "portal" / name, self.root / "portal" / name)
        shutil.copy(portal.ROOT / "microsoft_industry_verticals.csv", self.root)
        shutil.copy(portal.ROOT / "requirements.txt", self.root)
        self.studio = portal.Studio(self.root)
        self.data = {
            "projectSlug": "test-scenario", "prompt": "A manufacturing assistant", "industry": "Manufacturing & Mobility",
            "businessUnits": ["operations"], "services": ["foundry"], "pillars": ["security"], "domains": [],
        }

    def save(self) -> Path:
        self.studio.save_brief(self.data)
        return portal_status.scenario_state(self.root, "test-scenario")

    def test_intake_saves_only_brief_and_cannot_overwrite_existing_scenario(self) -> None:
        with patch.object(portal.subprocess, "run") as execute:
            state = self.save()
            execute.assert_not_called()
        self.assertTrue((state / "request.json").exists())
        self.assertFalse(self.studio.folder("test-scenario").exists())
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.studio.save_brief(self.data)

    def test_invalid_input_and_paths_fail_before_handoff(self) -> None:
        for field, value in (("projectSlug", "../elsewhere"), ("prompt", ""), ("industry", "unknown"),
                             ("services", ["unknown"]), ("businessUnits", ["generic", "it"])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.studio.save_brief({**self.data, field: value})

    def test_scoping_intake_is_explicit_and_legacy_briefs_default_to_build(self) -> None:
        self.assertEqual("build", self.studio.intake(self.data)["intakeMode"])
        self.studio.save_brief({**self.data, "intakeMode": "scope"})
        item = self.studio.scenario("test-scenario")
        self.assertEqual("scope", item["intakeMode"])
        self.assertIn("Building has not been requested", item["progress"]["summary"])
        self.assertFalse(item["scoping"]["available"])
        for value in ("unknown", "", None, True, [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "intake mode"):
                self.studio.intake({**self.data, "intakeMode": value})

    def test_scoping_handoff_uses_real_conductor_without_build_identity_or_audit_instructions(self) -> None:
        self.studio.save_brief({**self.data, "intakeMode": "scope"})
        state = portal_status.scenario_state(self.root, "test-scenario")
        original = (state / "request.json").read_bytes()
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
            patch.object(portal.azure_context, "identity") as identity,
            patch.object(portal.check_prerequisites, "build_report") as audit,
        ):
            result = self.studio.handoff("test-scenario", "scoping")
        self.assertEqual("handed_off", result["status"])
        self.assertIn("no build or deployment", result["message"])
        identity.assert_not_called()
        audit.assert_not_called()
        self.assertEqual(2, launch.call_count)
        command = launch.call_args.args[0]
        self.assertEqual(["code", "chat", "--mode", "az-01-conductor"], command[:4])
        self.assertIn(str(state / "scoping-handoff.txt"), command)
        self.assertTrue(command[-1].startswith("Follow the attached scoping handoff"))
        text = (state / "scoping-handoff.txt").read_text()
        for fragment in ("SCOPING ONLY", "prompt-specific", "no predefined questionnaire", "scoping.md",
                         "waiting_for_user", "brief confirmation", "Do not create a scenario workspace"):
            self.assertIn(fragment, text)
        self.assertNotIn("Resolve account, tenantId", text)
        self.assertNotIn("Implement the story, architecture", text)
        self.assertEqual(original, (state / "request.json").read_bytes())
        self.assertFalse(self.studio.folder("test-scenario").exists())
        self.assertTrue((state / "scenario-chat-started.json").is_file())
        self.assertIn("AI scoping only", self.studio.scenario("test-scenario")["progress"]["summary"])
        self.assertFalse(self.studio.scenario("test-scenario")["approval"]["approved"])

    def test_scoping_notes_survive_restart_and_are_attached_to_the_build_handoff(self) -> None:
        state = self.save()
        notes = "## Refined scope\n\nConfirmed: operator approval.\n\nOpen: duplicate event recovery.\n"
        (state / "scoping.md").write_text(notes, encoding="utf-8")
        restored = portal.Studio(self.root)
        self.assertEqual(notes, restored.scenario("test-scenario")["scoping"]["text"])
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            restored.handoff("test-scenario", "scenario")
        self.assertIn(str(state / "scoping.md"), launch.call_args.args[0])
        text = (state / "scenario-handoff.txt").read_text()
        self.assertIn("Adaptive prompt scoping", text)
        self.assertIn("Do not force questions", text)
        self.assertIn("not authorization", text)

    def test_scoping_notes_are_bounded_and_do_not_follow_links_out_of_state(self) -> None:
        state = self.save()
        notes = state / "scoping.md"
        notes.write_text("x" * (64 * 1024 + 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "64 KiB"):
            self.studio.scoping_notes("test-scenario")
        notes.unlink()
        outside = self.root / "private-notes.md"
        outside.write_text("Do not expose", encoding="utf-8")
        try:
            notes.symlink_to(outside)
        except OSError:
            self.skipTest("Host does not permit symbolic links.")
        with self.assertRaisesRegex(ValueError, "inside this scenario"):
            self.studio.scoping_notes("test-scenario")

    def test_scoping_followup_reopens_the_same_scenario_chat_without_another_prompt(self) -> None:
        state = self.save()
        portal_status.write_json(state / "scenario-chat-started.json", {"phase": "scoping"})
        with (
            patch.object(self.studio, "reopen_chat", return_value={"status": "reopened"}) as reopen,
            patch.object(portal.subprocess, "run") as launch,
        ):
            self.assertEqual("reopened", self.studio.handoff("test-scenario", "scenario")["status"])
        reopen.assert_called_once_with("test-scenario", "scenario")
        launch.assert_not_called()

    def scoping_review(self) -> tuple[Path, dict]:
        state = self.save()
        (state / "scoping.md").write_text("## Scope\n\nA grocery journey.\n", encoding="utf-8")
        portal_status.report(self.root, "test-scenario", "requirements", "waiting_for_user", "Review the brief.")
        dispatch = patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"})
        dispatch.start()
        self.addCleanup(dispatch.stop)
        return state, self.studio.scoping_notes("test-scenario")

    def test_scoping_confirmation_persists_without_starting_work_or_changing_agent_evidence(self) -> None:
        state, notes = self.scoping_review()
        originals = {name: (state / name).read_bytes() for name in ("request.json", "scoping.md", "status.json")}
        with patch.object(portal.subprocess, "run") as launch:
            result = self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        launch.assert_not_called()
        self.assertIn("existing scenario agent", result["message"])
        self.studio.continue_brief.assert_called_once()
        restored = portal.Studio(self.root).scenario("test-scenario")
        self.assertTrue(restored["scoping"]["responseCurrent"])
        self.assertEqual("confirmed", restored["scoping"]["response"]["decision"])
        self.assertEqual("waiting_for_user", restored["progress"]["status"])
        self.assertFalse(restored["approval"]["approved"])
        self.assertFalse(self.studio.folder("test-scenario").exists())
        for name, original in originals.items():
            self.assertEqual(original, (state / name).read_bytes())

    def test_scoping_changes_are_saved_as_user_input_and_can_be_replaced_by_confirmation(self) -> None:
        state, notes = self.scoping_review()
        result = self.studio.respond_to_scoping(
            "test-scenario", notes["fingerprint"], "changes_requested", "  Include a late delivery.  ",
        )
        self.assertEqual("Include a late delivery.", result["response"]["changes"])
        self.assertEqual("dispatched", result["response"]["continuation"]["status"])
        self.assertEqual("changes_requested", self.studio.scoping_notes("test-scenario")["response"]["decision"])
        self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        self.assertEqual("confirmed", json.loads((state / "scoping-response.json").read_text())["decision"])

    def test_scoping_response_rejects_stale_briefs_and_non_scoping_waits(self) -> None:
        state, notes = self.scoping_review()
        self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        (state / "scoping.md").write_text("## Changed brief\n", encoding="utf-8")
        self.assertFalse(self.studio.scoping_notes("test-scenario")["responseCurrent"])
        with self.assertRaisesRegex(ValueError, "changed"):
            self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        current = self.studio.scoping_notes("test-scenario")["fingerprint"]
        for stage, status in (("architecture", "waiting_for_user"), ("requirements", "running")):
            portal_status.report(self.root, "test-scenario", stage, status, "Not a scoping response boundary.")
            with self.assertRaisesRegex(ValueError, "changed"):
                self.studio.respond_to_scoping("test-scenario", current, "confirmed")

    def test_scoping_confirmation_survives_bom_and_line_endings_but_not_changed_text(self) -> None:
        state, notes = self.scoping_review()
        self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        path = state / "scoping.md"
        text = path.read_text(encoding="utf-8-sig")
        for newline in ("\n", "\r\n", "\r"):
            for bom in ("", "\ufeff"):
                with self.subTest(newline=newline, bom=bool(bom)):
                    path.write_bytes((bom + text.replace("\n", newline)).encode("utf-8"))
                    current = self.studio.scoping_notes("test-scenario")
                    self.assertEqual(notes["fingerprint"], current["fingerprint"])
                    self.assertTrue(current["responseCurrent"])
        path.write_bytes((text + "A changed requirement.\n").encode("utf-8"))
        self.assertFalse(self.studio.scoping_notes("test-scenario")["responseCurrent"])

    def test_scoping_response_validates_decisions_and_changes_before_saving(self) -> None:
        state, notes = self.scoping_review()
        for decision, changes in (("approve-deployment", ""), ("changes_requested", " "),
                                  ("confirmed", "Unsaved change"), ("changes_requested", "x" * 8001),
                                  ("changes_requested", None)):
            with self.subTest(decision=decision, changes=type(changes)), self.assertRaises(ValueError):
                self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], decision, changes)
        self.assertFalse((state / "scoping-response.json").exists())

    def test_explicit_handoff_carries_saved_scoping_response_without_treating_it_as_build_consent(self) -> None:
        state, notes = self.scoping_review()
        self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            self.studio.handoff("test-scenario", "scoping", new_chat=True)
        self.assertIn(str(state / "scoping-response.json"), launch.call_args.args[0])
        instruction = (state / "scoping-handoff.txt").read_text()
        self.assertIn("normal scenario workflow", instruction)
        self.assertIn("SCOPING ONLY", instruction)

    def test_scoping_continuation_is_idempotent_and_preserves_a_failed_response_for_retry(self) -> None:
        state, notes = self.scoping_review()
        self.studio.continue_brief.side_effect = ValueError("Bridge unavailable")
        with self.assertRaisesRegex(ValueError, "response was saved"):
            self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        failed = json.loads((state / "scoping-response.json").read_text())
        self.assertEqual("failed", failed["continuation"]["status"])
        self.assertFalse(self.studio.folder("test-scenario").exists())
        self.studio.continue_brief.side_effect = None
        result = self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        self.assertEqual(failed["continuation"]["requestId"], result["response"]["continuation"]["requestId"])
        self.assertNotIn("error", result["response"]["continuation"])
        self.studio.respond_to_scoping("test-scenario", notes["fingerprint"], "confirmed")
        self.assertEqual(2, self.studio.continue_brief.call_count)

    def test_native_brief_continuation_checks_bridge_version_and_uses_the_same_request_id(self) -> None:
        state = self.save()
        calls = []

        def acknowledge(uri):
            from urllib.parse import parse_qs, urlsplit
            parsed = urlsplit(uri)
            query = parse_qs(parsed.query)
            calls.append(parsed.path)
            value = {"status": "ready", "version": "0.2.3"} if parsed.path == "/ping" else {"status": "dispatched"}
            portal_status.write_json(state / "chat-open" / f"{query['request'][0]}.json", value)

        with (
            patch.object(portal.scenario_chat, "resolve", return_value={"resource": "agent-host-session://copilot/existing"}),
            patch.object(self.studio, "open_chat_uri", side_effect=acknowledge),
        ):
            result = self.studio.continue_brief("test-scenario", "a" * 32)
        self.assertEqual("dispatched", result["status"])
        self.assertEqual(["/ping", "/continue"], calls)
        self.assertFalse(list((state / "chat-open").glob("*.json")))

    def test_old_bridge_and_legacy_worker_cannot_dispatch_brief_continuation(self) -> None:
        self.save()
        with (
            patch.object(portal.scenario_chat, "resolve"),
            patch.object(self.studio, "chat_bridge", return_value={"status": "ready", "version": "0.2.2"}) as command,
        ):
            with self.assertRaisesRegex(ValueError, "reports 0.2.2.*0.2.3.*Restart Extension Host"):
                self.studio.continue_brief("test-scenario", "a" * 32)
            self.assertEqual(1, command.call_count)
            portal_status.write_json(self.studio.state / "projects" / "test-scenario.json", {"writer": "old-worker"})
            with self.assertRaisesRegex(ValueError, "legacy worker"):
                self.studio.continue_brief("test-scenario", "a" * 32)
            self.assertEqual(1, command.call_count)

    def test_scoping_launch_failure_preserves_the_original_brief_and_retry_intent(self) -> None:
        self.studio.save_brief({**self.data, "intakeMode": "scope"})
        with patch.object(portal.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "launcher"):
                self.studio.handoff("test-scenario", "scoping")
        restored = portal.Studio(self.root).scenario("test-scenario")
        self.assertEqual("scope", restored["intakeMode"])
        self.assertEqual("saved", restored["progress"]["status"])
        self.assertTrue(restored["hasBrief"])
        state = portal_status.scenario_state(self.root, "test-scenario")
        self.assertFalse((state / "handoff.json").exists())
        self.assertFalse(self.studio.folder("test-scenario").exists())

    def test_pattern_catalog_matches_all_18_guide_patterns_plus_ai_choice(self) -> None:
        patterns = self.studio.catalog()["agenticPatterns"]
        guide = (portal.ROOT / ".github" / "skills" / "az-scenario-requirements" / "references"
                 / "agentic-patterns.md").read_text(encoding="utf-8")
        names = re.findall(r"^### \d{2}\. (.+)$", guide, re.MULTILINE)
        self.assertEqual(18, len(names))
        self.assertEqual(19, len(patterns))
        self.assertEqual(19, len({entry["id"] for entry in patterns}))
        self.assertEqual("ai-decides", patterns[0]["id"])
        self.assertEqual(names, [entry["name"] for entry in patterns[1:]])
        for pattern in patterns:
            self.assertTrue(pattern["description"].strip())
            with self.subTest(pattern=pattern["id"]):
                value = self.studio.intake({**self.data, "agenticPattern": pattern["id"]})
                self.assertEqual(pattern["id"], value["agenticPattern"])

    def test_pattern_defaults_to_ai_and_explicit_choice_is_persisted(self) -> None:
        self.assertEqual("ai-decides", self.studio.intake(self.data)["agenticPattern"])
        self.studio.save_brief({**self.data, "agenticPattern": "planner-executor"})
        request = portal_status.scenario_state(self.root, "test-scenario") / "request.json"
        self.assertEqual("planner-executor", json.loads(request.read_text())["agenticPattern"])

    def test_invalid_pattern_is_rejected_without_saving_a_brief(self) -> None:
        for value in ("unknown", "", None, 1, True, [], ["planner-executor"], {"id": "planner-executor"}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Choose one agentic workflow pattern"):
                self.studio.save_brief({**self.data, "agenticPattern": value})
        self.assertFalse((portal_status.scenario_state(self.root, "test-scenario") / "request.json").exists())

    def test_handoff_carries_every_pattern_choice_and_ai_selection_contract(self) -> None:
        state = self.save()
        for pattern in self.studio.catalog()["agenticPatterns"]:
            with (
                self.subTest(pattern=pattern["id"]),
                patch.object(portal.shutil, "which", return_value="code"),
                patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)),
            ):
                portal_status.write_json(state / "request.json", {**self.data, "agenticPattern": pattern["id"]})
                self.studio.handoff("test-scenario", "scenario", new_chat=True)
                text = (state / "scenario-handoff.txt").read_text(encoding="utf-8")
                if pattern["id"] == "ai-decides":
                    self.assertIn("Do not ask the user to select a pattern", text)
                    self.assertIn("described customer, exact industry, business units", text)
                else:
                    self.assertIn(f"{pattern['name']} ({pattern['id']})", text)
                    self.assertIn("before substituting another pattern", text)
                self.assertIn("agentic-patterns.md", text)
                self.assertIn("measurable runtime contract", text)
                self.assertIn("not permission to delegate Copilot work", text)

    def test_legacy_brief_handoff_defaults_to_ai_without_rewriting_existing_decisions(self) -> None:
        state = self.save()
        portal_status.write_json(state / "request.json", self.data)
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)),
        ):
            self.studio.handoff("test-scenario", "scenario")
        text = (state / "scenario-handoff.txt").read_text(encoding="utf-8")
        self.assertIn("Let AI decide", text)
        self.assertIn("reuse recorded pattern decisions", text)
        self.assertNotIn("agenticPattern", json.loads((state / "request.json").read_text()))

    def make_review(self) -> Path:
        self.save()
        path = self.studio.folder("test-scenario") / "local-evidence" / "review-1" / "deployment-review.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Deployment preparation\n\nNo deployment authorized.\n", encoding="utf-8")
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Review the next decision")
        return path

    def test_review_discovery_exposes_only_safe_named_reviews_and_chooses_latest(self) -> None:
        first = self.make_review()
        latest = first.parent.parent / "review-2" / "deployment-review.md"
        latest.parent.mkdir()
        latest.write_bytes(b"# Latest review\n")
        portal.os.utime(first, (100, 100))
        portal.os.utime(latest, (200, 200))
        (latest.parent / "authorization.json").write_text("{}", encoding="utf-8")
        review = self.studio.deployment_review("test-scenario")
        self.assertTrue(review["available"])
        self.assertEqual("local-evidence/review-2/deployment-review.md", review["path"])
        self.assertEqual("# Latest review\n", review["text"])
        self.assertEqual(64, len(review["fingerprint"]))
        files = self.studio.files("test-scenario")
        self.assertEqual(2, len(files))
        self.assertTrue(all(item["path"].endswith("/deployment-review.md") for item in files))
        self.assertEqual("reference", files[0]["audience"])

    def test_review_requires_a_waiting_boundary_and_accepts_root_location(self) -> None:
        path = self.make_review()
        root = self.studio.folder("test-scenario") / "deployment-review.md"
        path.rename(root)
        self.assertEqual("deployment-review.md", self.studio.deployment_review("test-scenario")["path"])
        for stage, status in (("deployment", "running"), ("review", "completed"), ("hack-content", "waiting_for_user")):
            portal_status.report(self.root, "test-scenario", stage, status, "Changed status")
            self.assertFalse(self.studio.deployment_review("test-scenario")["available"])

    def test_review_handoff_attaches_document_without_recording_approval_or_starting_deployment(self) -> None:
        path = self.make_review()
        review = self.studio.deployment_review("test-scenario")
        status_path = portal_status.scenario_state(self.root, "test-scenario") / "status.json"
        before = status_path.read_bytes()
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            value = self.studio.handoff("test-scenario", "deployment-review", review["fingerprint"], new_chat=True)
        command = launch.call_args.args[0]
        self.assertEqual(["code", "chat", "--mode", "az-01-conductor"], command[:4])
        self.assertIn(str(path), command)
        self.assertEqual(2, command.count("--add-file"))
        text = (status_path.parent / "deployment-review-handoff.txt").read_text(encoding="utf-8")
        self.assertIn("navigation, not approval or authorization", text)
        self.assertIn("Continue already-authorized, matching in-scope work without asking the user again", text)
        self.assertIn("do not invoke a separate deployment agent", text)
        self.assertEqual(before, status_path.read_bytes())
        self.assertFalse((self.studio.folder("test-scenario") / portal.hack_workflow.STATE_FILE).exists())
        self.assertIn("no deployment was approved or started", value["message"])

    def test_stale_review_or_status_cannot_be_handed_off(self) -> None:
        path = self.make_review()
        original = self.studio.deployment_review("test-scenario")
        path.write_text("# Changed scope\n", encoding="utf-8")
        with patch.object(portal.subprocess, "run") as launch:
            for fingerprint in (original["fingerprint"], None, ""):
                with self.assertRaisesRegex(ValueError, "review or scenario status changed"):
                    self.studio.handoff("test-scenario", "deployment-review", fingerprint)
            current = self.studio.deployment_review("test-scenario")
            portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Different decision")
            with self.assertRaisesRegex(ValueError, "review or scenario status changed"):
                self.studio.handoff("test-scenario", "deployment-review", current["fingerprint"])
            launch.assert_not_called()

    def test_handoff_preserves_both_consent_histories_without_mutating_or_inventing_approval(self) -> None:
        self.save()
        sources = []
        for directory, kind in ((".hackbuilder-portal", "deployment"), (".abcbuilder-portal", "deployment-preparation")):
            path = self.root / directory / "projects" / "test-scenario.json"
            record = {
                "projectSlug": "test-scenario", "request": {"deploymentAuthorized": False},
                "authorizations": [{"kind": kind, "scope": {"region": "centralus"},
                                    "message": f"Actual {kind} consent", "recordedAtUtc": "2026-10-23T20:00:00Z"}],
                "decisions": [{"id": kind, "status": "answered", "kind": kind, "answer": f"Actual {kind} consent"},
                              {"id": "pending", "status": "pending", "kind": "deployment"}],
            }
            portal_status.write_json(path, record)
            sources.append((path, path.read_bytes()))
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            self.studio.handoff("test-scenario", "scenario")
        saved = portal_status.scenario_state(self.root, "test-scenario")
        history = json.loads((saved / "consent-history.json").read_text())
        self.assertTrue(history["informationalOnly"])
        self.assertEqual(2, len(history["records"]))
        self.assertEqual(["deployment", "deployment-preparation"],
                         [record["authorizations"][0]["kind"] for record in history["records"]])
        self.assertTrue(all(len(record["answeredDecisions"]) == 1 for record in history["records"]))
        self.assertIn(str(saved / "consent-history.json"), launch.call_args.args[0])
        text = (saved / "scenario-handoff.txt").read_text()
        self.assertIn("BOTH current and legacy records", text)
        self.assertIn("preserve later explicit restrictions", text)
        self.assertIn("Reuse valid matching consent without another routine approval", text)
        self.assertIn("A later read-only grant does not revoke an earlier deployment grant", text)
        self.assertIn("unless the user explicitly withdraws or restricts it", text)
        self.assertIn("cannot create or revoke user consent", text)
        self.assertIn("trace restrictions to actual user responses", text)
        for path, before in sources:
            self.assertEqual(before, path.read_bytes())

    def test_reference_handoffs_prepare_consolidated_review_without_new_cloud_authority(self) -> None:
        self.make_review()
        review = self.studio.deployment_review("test-scenario")
        state = portal_status.scenario_state(self.root, "test-scenario")
        before = (state / "request.json").read_bytes()
        status_before = (state / "status.json").read_bytes()
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            for phase in ("scenario", "deployment-review"):
                with self.subTest(phase=phase):
                    launch.reset_mock()
                    self.studio.handoff("test-scenario", phase, review["fingerprint"], new_chat=True)
                    text = (state / f"{phase}-handoff.txt").read_text(encoding="utf-8")
                    for requirement in (
                        "Continue independent local preparation without a preliminary permission questionnaire",
                        "a preferred private execution path",
                        "incremental/total cost",
                        "Do not ask the user to choose runner discovery versus runner design",
                        "Defer unauthorized Azure/Entra reads and writes",
                        "Present one consolidated review of only missing authority or material new scope",
                        "This handoff grants no new cloud authority",
                    ):
                        self.assertIn(requirement, text)
                    self.assertEqual(2, launch.call_count)
                    self.assertTrue(all(call.args[0][0] == "code" for call in launch.call_args_list))
                    self.assertEqual(before, (state / "request.json").read_bytes())
                    self.assertEqual(status_before, (state / "status.json").read_bytes())
                    self.assertFalse((self.studio.folder("test-scenario") / portal.hack_workflow.STATE_FILE).exists())

    def test_consent_history_rejects_a_different_scenario(self) -> None:
        portal_status.write_json(self.root / ".hackbuilder-portal" / "projects" / "test-scenario.json",
                                 {"projectSlug": "other-scenario", "authorizations": [{"kind": "deployment"}]})
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.studio.consent_history("test-scenario")

    def system_report(self, data: dict, ready: bool = True) -> dict:
        planned = self.studio.prerequisite_plan(data)
        checks = [{**item, "ok": True, "detail": "Actual command result", "fix": ""} for item in planned["checks"]]
        if not ready:
            checks[0].update(ok=False, detail="Missing dependency", fix="Prepare the dependency and recheck.")
        return {**planned["plan"], "profileVersion": portal.prerequisite_profiles.VERSION,
                "checkedAtUtc": "2026-10-24T22:00:00+00:00", "ready": ready, "checks": checks}

    def test_system_plan_lists_unchecked_tools_without_executing_commands(self) -> None:
        with patch.object(portal.subprocess, "run") as run:
            result = self.studio.prerequisite_plan({})
        run.assert_not_called()
        self.assertIsNone(result["report"])
        self.assertIn("docker", result["plan"]["stages"]["local-validation"])
        self.assertTrue(all(item["state"] == "not-checked" for item in result["checks"]))
        self.assertIn("dotnet", {item["id"] for item in result["checks"]})
        self.assertEqual(sorted(portal.prerequisite_profiles.SERVICE_REQUIREMENTS), result["plan"]["services"])
        self.assertEqual("local", result["plan"]["buildMode"])
        self.assertTrue(result["plan"]["localFunctions"])
        self.assertTrue(result["plan"]["loadTests"])
        self.assertTrue({"docker", "functions-core-tools", "k6"} <= {item["id"] for item in result["checks"]})

    def test_system_plan_rejects_scenario_scope_without_reading_or_mutating_scenarios(self) -> None:
        state = self.save()
        before = (state / "request.json").read_bytes()
        for data in (
            {"projectSlug": "test-scenario"}, {"services": ["foundry"]},
            {"buildMode": "remote"}, {"localFunctions": False}, {"loadTests": False},
        ):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "workspace-wide"):
                self.studio.prerequisite_plan(data)
        self.assertEqual(before, (state / "request.json").read_bytes())
        with patch.object(portal.prerequisite_profiles, "effective_services") as scenario_services:
            self.studio.prerequisite_plan({})
        scenario_services.assert_not_called()

    def test_system_diagnostics_require_explicit_consent_and_serialize_checks(self) -> None:
        with patch.object(portal.subprocess, "run") as run, patch.object(portal.azure_context, "identity") as identity:
            for check in (self.studio.check_system_prerequisites, self.studio.check_system_identity):
                with self.assertRaisesRegex(ValueError, "Authorize"):
                    check({})
                with self.assertRaisesRegex(ValueError, "already running"):
                    self.studio.system_check_lock.acquire()
                    try:
                        check({"toolConsent": True})
                    finally:
                        self.studio.system_check_lock.release()
            run.assert_not_called()
            identity.assert_not_called()

    def test_system_checker_persists_real_failure_and_success_without_installing_or_gating_scenarios(self) -> None:
        data = {"toolConsent": True}
        for ready in (False, True):
            report = self.system_report(data, ready)
            with patch.object(portal.subprocess, "run", return_value=Mock(
                returncode=0 if ready else 1, stdout=json.dumps(report), stderr="",
            )) as run:
                self.assertEqual(ready, self.studio.check_system_prerequisites(data)["ready"])
            command = run.call_args.args[0]
            self.assertIn("check_prerequisites.py", command[2])
            self.assertNotIn("--record", command)
            self.assertNotIn("install", command)
            self.assertIn("--local-functions", command)
            self.assertIn("--load-tests", command)
            self.assertEqual(report, self.studio.prerequisite_plan(data)["report"])
        self.assertEqual("test-scenario", self.studio.save_brief(self.data)["projectSlug"])

    def test_system_does_not_reuse_a_narrow_legacy_report_as_workspace_readiness(self) -> None:
        report = self.system_report({})
        report.update(services=["foundry"], buildMode="auto", localFunctions=False, loadTests=False)
        portal_status.write_json(self.studio.state / "system-prerequisites.json", report)
        self.assertIsNone(self.studio.prerequisite_plan({})["report"])

    def test_system_checker_rejects_incomplete_scope_results_and_timeout_without_claiming_ready(self) -> None:
        data = {"toolConsent": True}
        report = self.system_report(data)
        report["checks"] = []
        with patch.object(portal.subprocess, "run", return_value=Mock(returncode=0, stdout=json.dumps(report))):
            with self.assertRaisesRegex(ValueError, "omitted required checks"):
                self.studio.check_system_prerequisites(data)
        with patch.object(portal.subprocess, "run", side_effect=portal.subprocess.TimeoutExpired("checker", 180)):
            with self.assertRaisesRegex(ValueError, "timed out"):
                self.studio.check_system_prerequisites(data)
        self.assertFalse(self.studio.system_check_lock.locked())
        self.assertFalse((self.studio.state / "system-prerequisites.json").exists())

    def test_identity_is_derived_from_cli_helpers_and_attached_to_continuations_without_manual_ids(self) -> None:
        state = self.save()
        identified = {"scope": {"account": "operator@example.test", "tenantId": "tenant", "subscriptionId": "sub"},
                      "authentication": {"azureCli": "Verified", "azd": "Verified"}}
        with patch.object(portal.azure_context, "identity", return_value=identified) as identify:
            result = self.studio.check_system_identity({"toolConsent": True})
        identify.assert_called_once_with(self.root)
        self.assertEqual("ready", result["status"])
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            self.studio.handoff("test-scenario", "scenario")
        self.assertIn(str(self.studio.state / "system-identity.json"), launch.call_args.args[0])
        text = (state / "scenario-handoff.txt").read_text()
        self.assertIn("Do not ask the user to type tenant/subscription IDs", text)
        self.assertIn("Never run interactive login", text)
        self.assertNotIn("accessToken", (self.studio.state / "system-identity.json").read_text())
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Continue in chat")
        self.assertTrue(self.studio.scenario("test-scenario")["actions"]["canContinue"])

    def test_identity_failure_invalidates_a_previous_ready_observation(self) -> None:
        with patch.object(portal.azure_context, "identity", side_effect=ValueError("Account names differ")):
            with self.assertRaisesRegex(ValueError, "names differ"):
                self.studio.check_system_identity({"toolConsent": True})
        value = json.loads((self.studio.state / "system-identity.json").read_text())
        self.assertEqual("failed", value["status"])

    def test_handoff_uses_interactive_vscode_custom_agent_not_copilot_worker(self) -> None:
        state = self.save()
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            value = self.studio.handoff("test-scenario", "scenario")
        self.assertEqual("handed_off", value["status"])
        self.assertNotIn("VS Code", value["message"])
        self.assertEqual(2, launch.call_count)
        self.assertEqual(["code", "--reuse-window", str(self.root)], launch.call_args_list[0].args[0])
        command = launch.call_args_list[1].args[0]
        self.assertEqual(["code", "chat", "--mode", "az-01-conductor"], command[:4])
        self.assertIn(str(state / "scenario-handoff.txt"), command)
        self.assertNotIn("--allow-all-tools", command)
        self.assertNotIn("--no-ask-user", command)
        self.assertEqual("handed_off", self.studio.scenario("test-scenario")["progress"]["status"])
        self.assertFalse((state / "status.json").exists())
        text = (state / "scenario-handoff.txt").read_text(encoding="utf-8")
        self.assertIn("Verify this workspace", text)
        self.assertIn("portal_status.py", text)
        receipt = json.loads((state / "scenario-chat-started.json").read_text())
        self.assertRegex(receipt["traceId"], r"^[a-f0-9]{32}$")
        self.assertIn(f"ABC Builder chat trace: {receipt['traceId']}.", command[-1])
        self.assertIn("launchedAtUtc", receipt)

    def test_handoff_failure_preserves_brief_and_does_not_claim_started(self) -> None:
        state = self.save()
        for result in (None, Mock(returncode=1, stderr="custom mode not found")):
            with (
                self.subTest(result=result),
                patch.object(portal.shutil, "which", return_value="code" if result else None),
                patch.object(portal.subprocess, "run", return_value=result),
                self.assertRaises(ValueError),
            ):
                self.studio.handoff("test-scenario", "scenario")
        self.assertTrue((state / "request.json").exists())
        self.assertFalse((state / "handoff.json").exists())
        self.assertEqual("saved", self.studio.scenario("test-scenario")["progress"]["status"])

    def test_followup_without_binding_never_creates_another_chat(self) -> None:
        state = self.save()
        portal_status.write_json(state / "handoff.json", {"phase": "scenario", "status": "handed_off"})
        with (
            patch.object(portal.subprocess, "run") as launch,
            patch.object(portal.scenario_chat, "resolve", side_effect=ValueError("No verified scenario chat")) as resolve,
        ):
            with self.assertRaisesRegex(ValueError, "No verified scenario chat"):
                self.studio.handoff("test-scenario", "scenario")
        launch.assert_not_called()
        resolve.assert_called_once_with(self.root, "test-scenario", "scenario")

    def test_missing_binding_is_automatically_discovered_before_native_reopening(self) -> None:
        state = self.save()
        def acknowledge(uri):
            query = portal.parse_qs(portal.urlsplit(uri).query)
            portal_status.write_json(state / "chat-open" / f"{query['request'][0]}.json", {"status": "opened"})
        with (
            patch.object(portal.scenario_chat, "resolve", return_value={"resource": "native-link"}) as resolve,
            patch.object(self.studio, "open_chat_uri", side_effect=acknowledge) as launch,
        ):
            result = self.studio.reopen_chat("test-scenario", "scenario")
        self.assertEqual("reopened", result["status"])
        resolve.assert_called_once_with(self.root, "test-scenario", "scenario")
        self.assertIn("/open?", launch.call_args.args[0])
        self.assertNotIn("/link?", launch.call_args.args[0])

    def test_replacement_requires_explicit_flag_and_clears_only_replaced_binding_after_success(self) -> None:
        state = self.save()
        portal_status.write_json(state / "chat-sessions.json", {"schemaVersion": 1, "sessions": {
            "scenario": {"resource": "agent-host-session://copilot/old"},
            "composition": {"resource": "agent-host-session://copilot/hack"},
        }})
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            value = self.studio.handoff("test-scenario", "scenario", new_chat=True)
        self.assertEqual("handed_off", value["status"])
        self.assertEqual(2, launch.call_count)
        sessions = self.studio.chat_sessions("test-scenario")
        self.assertNotIn("scenario", sessions)
        self.assertEqual("agent-host-session://copilot/hack", sessions["composition"]["resource"])

    def test_linked_scenario_and_review_reopen_the_same_chat_without_new_prompt(self) -> None:
        self.make_review()
        state = portal_status.scenario_state(self.root, "test-scenario")
        portal_status.write_json(state / "chat-sessions.json", {
            "schemaVersion": 1, "sessions": {"scenario": {"resource": "agent-host-session://copilot/existing"}},
        })
        def acknowledge(uri):
            query = portal.parse_qs(portal.urlsplit(uri).query)
            portal_status.write_json(state / "chat-open" / f"{query['request'][0]}.json", {"status": "opened"})
        with (
            patch.object(self.studio, "open_chat_uri", side_effect=acknowledge) as launch,
        ):
            review = self.studio.deployment_review("test-scenario")
            result = self.studio.handoff("test-scenario", "deployment-review", review["fingerprint"])
        self.assertEqual("reopened", result["status"])
        self.assertEqual(1, launch.call_count)
        self.assertTrue(launch.call_args.args[0].startswith("vscode://abcbuilder.scenario-chat/open?"))
        self.assertIn("phase=scenario", launch.call_args.args[0])
        self.assertFalse(list((state / "chat-open").glob("*.json")))
        self.assertFalse((state / "handoff.json").exists())

    def test_bridge_timeout_never_falls_back_to_starting_a_chat(self) -> None:
        state = self.save()
        portal_status.write_json(state / "chat-sessions.json", {
            "schemaVersion": 1, "sessions": {"scenario": {"resource": "agent-host-session://copilot/existing"}},
        })
        with (
            patch.object(self.studio, "open_chat_uri") as launch,
            patch.object(portal.time, "monotonic", side_effect=[0, 61]),
        ):
            with self.assertRaisesRegex(ValueError, "No replacement conversation"):
                self.studio.handoff("test-scenario", "scenario")
        self.assertEqual(1, launch.call_count)

    def test_windows_bridge_uses_registered_protocol_without_a_cli_relay_or_shell(self) -> None:
        self.save()
        uri = self.studio.bridge_uri("test-scenario", "scenario", "open", "a" * 32)
        with (
            patch.object(portal.sys, "platform", "win32"),
            patch.object(portal.os, "startfile", create=True) as start,
            patch.object(portal.subprocess, "run") as launch,
        ):
            self.studio.open_chat_uri(uri)
        start.assert_called_once_with(uri)
        launch.assert_not_called()
        self.assertIn("&project=test-scenario", uri)

    def test_non_windows_uri_launch_failure_is_explicit(self) -> None:
        with (
            patch.object(portal.sys, "platform", "linux"),
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=1, stderr="URI rejected")),
            self.assertRaisesRegex(ValueError, "URI rejected"),
        ):
            self.studio.open_chat_uri("vscode://abcbuilder.scenario-chat/open")

    def test_later_completed_diagrams_do_not_hide_runtime_blocker_and_review_action(self) -> None:
        self.save()
        portal_status.report(self.root, "test-scenario", "live-validation", "blocked", "Sign in; registry role required")
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Approve temporary hub role")
        portal_status.report(self.root, "test-scenario", "diagrams", "completed", "Diagrams rendered")
        value = self.studio.scenario("test-scenario")
        self.assertEqual("blocked", value["progress"]["status"])
        self.assertEqual("live-validation", value["progress"]["stage"])
        self.assertIn("Sign in", value["progress"]["summary"])
        self.assertTrue(value["actions"]["canContinue"])

    def test_composition_handoff_checks_approval_without_recording_or_inventing_it(self) -> None:
        self.save()
        with (
            patch.object(portal.hack_workflow, "check_approval", side_effect=ValueError("not approved")) as guard,
            patch.object(portal.subprocess, "run") as launch,
        ):
            with self.assertRaisesRegex(ValueError, "not approved"):
                self.studio.handoff("test-scenario", "composition")
            guard.assert_called_once()
            launch.assert_not_called()
        with (
            patch.object(portal.hack_workflow, "check_approval"),
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            self.studio.handoff("test-scenario", "composition")
            self.assertEqual("HackCreator Agent", launch.call_args.args[0][3])
        text = (portal_status.scenario_state(self.root, "test-scenario") / "composition-handoff.txt").read_text(
            encoding="utf-8",
        )
        self.assertIn("Check the recorded suitability approval", text)
        self.assertNotIn("a preferred private execution path", text)
        self.assertIn("do not deploy an event or publish", text)

    def test_active_legacy_writer_prevents_concurrent_handoff(self) -> None:
        self.save()
        old = self.studio.state / "projects" / "test-scenario.json"
        portal_status.write_json(old, {"writer": "old-worker"})
        with patch.object(portal.subprocess, "run") as launch, self.assertRaisesRegex(ValueError, "legacy worker"):
            self.studio.handoff("test-scenario", "scenario")
        launch.assert_not_called()

    def test_atomic_display_status_needs_no_lease_revision_or_approval(self) -> None:
        self.save()
        portal_status.report(self.root, "test-scenario", "bicep", "running", "Creating infrastructure")
        portal_status.report(self.root, "test-scenario", "bicep", "completed", "Build passed")
        value = portal_status.report(self.root, "test-scenario", "application", "running", "Building the app")
        self.assertEqual("completed", value["steps"]["bicep"]["status"])
        self.assertIn("updatedAtUtc", value["steps"]["bicep"])
        self.assertEqual(value["updatedAtUtc"], value["steps"]["application"]["updatedAtUtc"])
        self.assertEqual("running", self.studio.scenario("test-scenario")["progress"]["status"])
        self.assertNotIn("writer", value)
        self.assertNotIn("authorizations", value)
        self.assertFalse(list(self.studio.state.rglob("*.tmp")))
        portal_status.report(self.root, "test-scenario", "application", "completed", "Build passed")
        self.assertEqual("in_progress", self.studio.scenario("test-scenario")["progress"]["status"])
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Review the live scenario in VS Code")
        self.assertEqual("waiting_for_user", self.studio.scenario("test-scenario")["progress"]["status"])

    def test_milestones_are_ordered_persistent_and_preserve_limitations(self) -> None:
        state = self.save()
        portal_status.report(self.root, "test-scenario", "deployment", "completed", "Deployment succeeded")
        portal_status.report(self.root, "test-scenario", "live-validation", "completed", "Functional pass; load target unmet")
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Review in chat")
        before = (state / "status.json").read_bytes()
        stages = self.studio.scenario("test-scenario")["stages"]
        self.assertEqual(list(portal_status.STAGES), [stage["id"] for stage in stages])
        by_id = {stage["id"]: stage for stage in stages}
        self.assertEqual("completed", by_id["deployment"]["status"])
        self.assertEqual("Functional pass; load target unmet", by_id["live-validation"]["summary"])
        self.assertEqual("waiting_for_user", by_id["review"]["status"])
        self.assertEqual("not_reported", by_id["hack-content"]["status"])
        self.assertEqual(before, (state / "status.json").read_bytes())

    def test_artifacts_do_not_claim_build_deployment_or_approval_success(self) -> None:
        self.save()
        folder = self.studio.folder("test-scenario")
        (folder / "infra").mkdir(parents=True)
        (folder / "infra" / "main.bicep").write_text("param name string", encoding="utf-8")
        (folder / "azure.yaml").write_text("name: test", encoding="utf-8")
        stages = {stage["id"]: stage for stage in self.studio.scenario("test-scenario")["stages"]}
        self.assertEqual("available", stages["bicep"]["status"])
        for stage in ("deployment", "live-validation", "review"):
            self.assertEqual("not_reported", stages[stage]["status"])

    def test_current_approval_replaces_stale_review_display_without_rewriting_report(self) -> None:
        state = self.save()
        folder = self.studio.folder("test-scenario")
        folder.mkdir(parents=True)
        (folder / portal.hack_workflow.STATE_FILE).write_text("{}", encoding="utf-8")
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Old review prompt")
        before = (state / "status.json").read_bytes()
        with patch.object(portal.hack_workflow, "check_approval",
                          return_value={"approval": {"recordedAtUtc": "2026-10-25T00:00:00Z"}}):
            item = self.studio.scenario("test-scenario")
        self.assertEqual("approved", item["progress"]["status"])
        self.assertTrue(item["actions"]["canCompose"])
        review = next(stage for stage in item["stages"] if stage["id"] == "review")
        self.assertEqual("completed", review["status"])
        self.assertEqual("2026-10-25T00:00:00Z", review["updatedAtUtc"])
        self.assertEqual(before, (state / "status.json").read_bytes())

    def test_package_receipt_overrides_old_waiting_status_but_stale_receipt_does_not_complete(self) -> None:
        self.save()
        portal_status.report(self.root, "test-scenario", "architecture", "waiting_for_user", "Old design question")
        folder = self.studio.folder("test-scenario") / "packages" / "validation"
        folder.mkdir(parents=True)
        (folder / "composition-status.json").write_text("{}", encoding="utf-8")
        with patch.object(portal.hack_workflow, "current_packages", return_value={"status": "packages_validated"}):
            self.assertEqual("completed", self.studio.scenario("test-scenario")["progress"]["status"])
        with patch.object(portal.hack_workflow, "current_packages", side_effect=ValueError("receipt stale")):
            self.assertEqual("blocked", self.studio.scenario("test-scenario")["progress"]["status"])

    def test_step_completion_keeps_scenario_building_and_all_actions_hidden(self) -> None:
        self.save()
        portal_status.report(self.root, "test-scenario", "application", "running", "Adding tests")
        portal_status.report(self.root, "test-scenario", "diagrams", "completed", "Diagrams generated")
        value = self.studio.scenario("test-scenario")
        self.assertEqual("in_progress", value["progress"]["status"])
        self.assertEqual("Diagrams generated", value["progress"]["summary"])
        self.assertFalse(any(value["actions"].values()))

    def test_unstarted_brief_and_unknown_existing_scenario_have_distinct_states(self) -> None:
        self.save()
        value = self.studio.scenario("test-scenario")
        self.assertEqual("saved", value["progress"]["status"])
        self.assertTrue(value["actions"]["canContinue"])
        self.studio.folder("existing-scenario").mkdir(parents=True)
        value = self.studio.scenario("existing-scenario")
        self.assertEqual("unknown", value["progress"]["status"])
        self.assertIn("no current progress report", value["progress"]["summary"])

    def test_composition_action_requires_current_approval_and_no_build_in_progress(self) -> None:
        self.save()
        folder = self.studio.folder("test-scenario")
        folder.mkdir(parents=True)
        (folder / portal.hack_workflow.STATE_FILE).write_text("{}", encoding="utf-8")
        portal_status.report(self.root, "test-scenario", "review", "waiting_for_user", "Review the scenario")
        with patch.object(portal.hack_workflow, "check_approval", side_effect=ValueError("Reference changed")):
            value = self.studio.scenario("test-scenario")
            self.assertFalse(value["actions"]["canCompose"])
            self.assertEqual("Reference changed", value["approval"]["reason"])
        with patch.object(portal.hack_workflow, "check_approval", return_value={}):
            value = self.studio.scenario("test-scenario")
            self.assertTrue(value["actions"]["canCompose"])
            self.assertFalse(value["actions"]["canContinue"])
            portal_status.report(self.root, "test-scenario", "hack-content", "running", "Creating challenges")
            self.assertFalse(any(self.studio.scenario("test-scenario")["actions"].values()))

    def test_completion_report_without_package_receipt_does_not_unlock_exports(self) -> None:
        self.save()
        portal_status.report(self.root, "test-scenario", "hack-validation", "completed", "Checks complete")
        value = self.studio.scenario("test-scenario")
        self.assertEqual("in_progress", value["progress"]["status"])
        self.assertFalse(value["actions"]["canExport"])
        with self.assertRaisesRegex(ValueError, "only after current package validation"):
            self.studio.export("test-scenario", "learner")

    def test_current_receipt_does_not_unlock_exports_during_a_build(self) -> None:
        self.save()
        portal_status.report(self.root, "test-scenario", "application", "running", "Revising reference")
        with patch.object(self.studio, "package_status", return_value={"status": "packages_validated"}):
            self.assertFalse(self.studio.scenario("test-scenario")["actions"]["canExport"])
            portal_status.report(self.root, "test-scenario", "diagrams", "completed", "Diagrams updated")
            self.assertFalse(self.studio.scenario("test-scenario")["actions"]["canExport"])

    def test_exports_separate_learner_from_coach_and_exclude_runtime_secrets(self) -> None:
        self.save()
        folder = self.studio.folder("test-scenario")
        for name in ("hack", "participant", "coach", "coach-guide"):
            path = folder / "packages" / name
            path.mkdir(parents=True)
            (path / "README.md").write_text(name, encoding="utf-8")
            (path / ".env").write_text("secret", encoding="utf-8")
            (path / "private.key").write_text("secret", encoding="utf-8")
            (path / "credentials.json").write_text("secret", encoding="utf-8")
            (path / ".runtime").mkdir()
            (path / ".runtime" / "credentials.json").write_text("secret", encoding="utf-8")
        with patch.object(self.studio, "package_status", return_value={"status": "packages_validated"}):
            with zipfile.ZipFile(io.BytesIO(self.studio.export("test-scenario", "learner"))) as archive:
                self.assertEqual({"packages/hack/README.md", "packages/participant/README.md"}, set(archive.namelist()))
            with zipfile.ZipFile(io.BytesIO(self.studio.export("test-scenario", "coach"))) as archive:
                self.assertEqual({"packages/coach/README.md", "packages/coach-guide/README.md"}, set(archive.namelist()))
        with self.assertRaises(ValueError):
            self.studio.file("test-scenario", "../outside.txt")
        with self.assertRaises(ValueError):
            self.studio.file("test-scenario", "packages/hack/.env")

    def test_package_folder_is_selected_by_slug_and_opens_only_on_explicit_request(self) -> None:
        self.save()
        packages = self.studio.folder("test-scenario") / "packages"
        self.assertIsNone(self.studio.scenario("test-scenario")["packageFolder"])
        with self.assertRaisesRegex(FileNotFoundError, "no package folder"):
            self.studio.open_package_folder("test-scenario")
        packages.mkdir(parents=True)
        with (
            patch.object(portal.os, "startfile", create=True) as start,
            patch.object(portal.sys, "platform", "win32"),
        ):
            value = self.studio.scenario("test-scenario")
            self.assertEqual(str(packages.resolve()), value["packageFolder"])
            start.assert_not_called()
            self.assertEqual("opened", self.studio.open_package_folder("test-scenario")["status"])
            start.assert_called_once_with(str(packages.resolve()), "explore")
            with self.assertRaises(ValueError):
                self.studio.open_package_folder("../outside")

    def test_export_rejects_linked_files_even_when_they_target_other_package_audiences(self) -> None:
        folder = self.studio.folder("test-scenario")
        folder.mkdir(parents=True)
        path = folder / "packages" / "hack" / "solution.md"
        target = folder / "packages" / "coach" / "solution.md"
        original_resolve = Path.resolve

        def resolve(value: Path, *args, **kwargs) -> Path:
            return original_resolve(target if value == path else value, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            self.assertFalse(self.studio.safe_file(folder, path))

    def test_http_only_exposes_visualization_and_explicit_handoff(self) -> None:
        self.save()
        server = portal.make_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 3)
        self.addCleanup(server.shutdown)
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        self.addCleanup(client.close)

        def call(
            method: str, path: str, headers: dict | None = None, payload: dict | None = None,
        ) -> tuple[int, bytes]:
            client.request(method, path, body=json.dumps(payload or {}) if method == "POST" else None,
                           headers={"Content-Type": "application/json", **(headers or {})})
            result = client.getresponse()
            return result.status, result.read()

        with patch.object(portal.subprocess, "run") as execute:
            self.assertEqual(200, call("GET", "/")[0])
            status, body = call("GET", "/api/catalog")
            self.assertEqual(200, status)
            self.assertEqual("visualizer", json.loads(body)["portalMode"])
            for path, expected in (("/", b"Start building"), ("/visualizer.js", b"initializeAppearance"),
                                   ("/visualizer.css", b'data-theme="dark"'), ("/markdown.js", b"function renderMarkdown")):
                status, body = call("GET", path)
                self.assertEqual(200, status)
                self.assertIn(expected, body)
            with patch.object(server.app, "reopen_chat", return_value={"status": "reopened"}) as reopen:
                for path in ("/api/chat-open", "/api/chat-link"):
                    status, body = call("POST", path, payload={"projectSlug": "test-scenario", "phase": "scenario"})
                    self.assertEqual(200, status)
                    self.assertEqual("reopened", json.loads(body)["status"])
                self.assertEqual(2, reopen.call_count)
                reopen.assert_called_with("test-scenario", "scenario")
            with patch.object(server.app, "open_package_folder", return_value={"status": "opened"}) as browse:
                status, body = call("POST", "/api/open-package-folder", payload={"projectSlug": "test-scenario"})
                self.assertEqual(200, status)
                self.assertEqual("opened", json.loads(body)["status"])
                browse.assert_called_once_with("test-scenario")
            self.assertEqual(200, call("GET", "/api/scenarios")[0])
            status, body = call("GET", "/api/review?project=test-scenario")
            self.assertEqual(200, status)
            self.assertFalse(json.loads(body)["available"])
            with patch.object(server.app, "respond_to_scoping", return_value={"response": {"decision": "confirmed"}}) as respond:
                status, body = call("POST", "/api/scoping-response", payload={
                    "projectSlug": "test-scenario", "fingerprint": "current", "decision": "confirmed",
                })
                self.assertEqual(200, status)
                self.assertEqual("confirmed", json.loads(body)["response"]["decision"])
                respond.assert_called_once_with("test-scenario", "current", "confirmed", "")
                self.assertEqual(403, call("POST", "/api/scoping-response",
                                          {"Origin": "https://example.test"})[0])
                self.assertEqual(1, respond.call_count)
            for path in ("/api/runs", "/api/system/azure-identity", "/api/readiness/repair", "/api/runs/old/continue"):
                self.assertEqual(404, call("POST", path)[0])
            self.assertEqual(403, call("GET", "/api/scenarios", {"Origin": "https://example.test"})[0])
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
