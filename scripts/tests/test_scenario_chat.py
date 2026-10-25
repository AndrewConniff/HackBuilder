"""Verify automatic chat association uses exact scenario evidence and read-only editor identities."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal_status
import scenario_chat


class ScenarioChatTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "workspace"
        self.storage = self.base / "editor"
        self.history = self.base / "history"
        for path in (self.root, self.storage, self.history):
            path.mkdir()

    def add_session(
        self, *, slug: str = "test-scenario", phase: str = "scenario", trace: str | None = None,
        reported: str | None = None, first_request: str | None = None, workspace: Path | None = None,
        success: bool = True, attachment: Path | None = None,
    ) -> tuple[str, str]:
        editor_id, sdk_id = str(uuid.uuid4()), str(uuid.uuid4())
        folder = self.storage / editor_id
        folder.mkdir()
        with closing(sqlite3.connect(folder / "session.db")) as database, database:
            database.execute("CREATE TABLE session_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            database.executemany("INSERT INTO session_metadata VALUES (?, ?)", [
                ("copilot.workingDirectory", (workspace or self.root).as_uri()),
                ("defaultChatProviderData", json.dumps({"sdkSessionId": sdk_id})),
                ("customTitle", "A misleading title mentioning another scenario"),
            ])
        prompt = f"Follow the attached {phase} handoff for {slug}. Report progress to portal_status.py."
        if trace:
            prompt += f" ABC Builder chat trace: {trace}."
        events = [
            {"type": "session.start", "data": {"sessionId": sdk_id}},
            {"type": "user.message", "data": {
                "content": first_request if first_request is not None else prompt,
                "attachments": [{"type": "file", "path": str(attachment)}] if attachment else [],
            }},
        ]
        if reported:
            report = {
                "schemaVersion": 1, "projectSlug": slug,
                "stage": "hack-content" if phase == "composition" else "application",
                "status": "completed", "updatedAtUtc": reported,
            }
            events.extend([
                {"type": "tool.execution_start", "data": {
                    "toolCallId": "report", "arguments": {
                        "command": f"python scripts\\portal_status.py {slug} --stage application --status completed",
                    },
                }},
                {"type": "tool.execution_complete", "data": {
                    "toolCallId": "report", "success": success, "result": {"content": json.dumps(report)},
                }},
            ])
        directory = self.history / sdk_id
        directory.mkdir()
        (directory / "events.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8",
        )
        return editor_id, sdk_id

    def resolve(self, phase: str = "scenario") -> dict:
        return scenario_chat.resolve(
            self.root, "test-scenario", phase, storage=self.storage, history=self.history,
        )

    def test_exact_handoff_maps_sdk_identity_to_native_editor_identity(self) -> None:
        editor_id, sdk_id = self.add_session()
        database = self.storage / editor_id / "session.db"
        before = database.read_bytes()
        result = self.resolve()
        self.assertEqual(editor_id, result["editorSessionId"])
        self.assertEqual(sdk_id, result["sdkSessionId"])
        self.assertEqual(f"agent-host-session://copilot/{editor_id}?connectionAuthority=local", result["resource"])
        self.assertEqual(before, database.read_bytes())
        self.assertNotIn("content", json.dumps(result))

    def test_legacy_duplicates_use_latest_actual_successful_scenario_report(self) -> None:
        self.add_session(reported="2026-10-24T22:00:00Z")
        expected, _ = self.add_session(reported="2026-10-25T00:00:00Z")
        self.add_session()
        result = self.resolve()
        self.assertEqual(expected, result["editorSessionId"])
        self.assertEqual(3, len(result["relatedSessions"]))
        self.assertEqual("handoff-and-progress-history", result["source"])

    def test_ambiguous_history_never_selects_a_title_or_arbitrary_newest_chat(self) -> None:
        self.add_session()
        self.add_session(reported="2026-10-25T00:00:00Z", success=False)
        with self.assertRaisesRegex(ValueError, "Multiple scenario chats"):
            self.resolve()
        self.assertFalse((portal_status.scenario_state(self.root, "test-scenario") / "chat-sessions.json").exists())

    def test_equal_report_times_require_disambiguation(self) -> None:
        for _ in range(2):
            self.add_session(reported="2026-10-25T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "unique latest progress report"):
            self.resolve()

    def test_future_launch_trace_excludes_other_launches_even_with_newer_activity(self) -> None:
        trace = "a" * 32
        directory = portal_status.scenario_state(self.root, "test-scenario")
        portal_status.write_json(directory / "scenario-chat-started.json", {"traceId": trace})
        self.add_session(reported="2026-10-25T00:00:00Z")
        self.add_session(trace="b" * 32, reported="2026-10-25T01:00:00Z")
        expected, _ = self.add_session(trace=trace)
        result = self.resolve()
        self.assertEqual(expected, result["editorSessionId"])
        self.assertEqual(trace, result["traceId"])
        self.assertEqual("handoff-trace", result["source"])

    def test_other_scenarios_workspaces_and_maintenance_conversations_are_excluded(self) -> None:
        self.add_session(slug="test-scenario-other")
        self.add_session(workspace=self.base / "other-workspace")
        self.add_session(first_request=(
            "Fix the portal. Follow the attached scenario handoff for test-scenario. "
            "Report progress to portal_status.py."
        ))
        self.add_session(phase="composition")
        expected, _ = self.add_session()
        self.assertEqual(expected, self.resolve()["editorSessionId"])

    def test_existing_bindings_are_stable_and_composition_remains_separate(self) -> None:
        reference, _ = self.add_session()
        composition, _ = self.add_session(phase="composition")
        self.assertEqual(reference, self.resolve()["editorSessionId"])
        self.assertEqual(composition, self.resolve("composition")["editorSessionId"])
        self.add_session(reported="2026-10-25T02:00:00Z")
        self.assertEqual(reference, self.resolve()["editorSessionId"])
        saved = json.loads(
            (portal_status.scenario_state(self.root, "test-scenario") / "chat-sessions.json").read_text()
        )
        self.assertEqual({"scenario", "composition"}, set(saved["sessions"]))

    def test_pre_portal_reference_attachment_requires_actual_matching_progress(self) -> None:
        reference = self.root / "generated-scenarios" / "test-scenario" / "01-requirements.md"
        self.add_session(first_request="Update the scenario.", attachment=reference)
        self.add_session(first_request="Update the scenario.", reported="2026-10-25T02:00:00Z",
                         attachment=self.root / "generated-scenarios" / "other" / "01-requirements.md")
        expected, _ = self.add_session(first_request="Continue this reference.",
                                       reported="2026-10-25T00:00:00Z", attachment=reference)
        result = self.resolve()
        self.assertEqual(expected, result["editorSessionId"])
        self.assertEqual("reference-attachment-and-progress-history", result["source"])
        with self.assertRaisesRegex(ValueError, "No verified composition chat"):
            self.resolve("composition")

    def test_missing_catalog_and_no_matching_handoff_fail_without_creating_a_binding(self) -> None:
        with self.assertRaisesRegex(ValueError, "No verified scenario chat"):
            self.resolve()
        self.storage.rmdir()
        with self.assertRaisesRegex(ValueError, "catalog is unavailable"):
            self.resolve()

    def test_invalid_scope_and_corrupt_saved_binding_fail_explicitly(self) -> None:
        with self.assertRaisesRegex(ValueError, "project slug"):
            scenario_chat.resolve(self.root, "../outside", "scenario")
        with self.assertRaisesRegex(ValueError, "Choose scenario"):
            self.resolve("other")
        directory = portal_status.scenario_state(self.root, "test-scenario")
        portal_status.write_json(directory / "chat-sessions.json", {"schemaVersion": 0, "sessions": {}})
        with self.assertRaisesRegex(ValueError, "Unsupported chat-sessions"):
            self.resolve()

    def test_mismatched_sdk_history_cannot_be_used_as_identity_evidence(self) -> None:
        _, sdk_id = self.add_session()
        events = self.history / sdk_id / "events.jsonl"
        events.write_text(json.dumps({"type": "session.start", "data": {"sessionId": str(uuid.uuid4())}}) + "\n")
        with self.assertRaisesRegex(ValueError, "identity does not match"):
            self.resolve()


if __name__ == "__main__":
    unittest.main()
