"""Verify portal messaging preserves the native agent and approval boundaries."""

from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal_status
import portal_visualizer as portal


class ConversationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.studio = portal.Studio(self.root)
        self.slug = "test-scenario"
        self.saved = portal_status.scenario_state(self.root, self.slug)
        portal_status.write_json(self.saved / "request.json", {"projectSlug": self.slug})
        self.resource = "agent-host-session://copilot/existing"
        portal_status.write_json(self.saved / "chat-sessions.json", {
            "schemaVersion": 1, "sessions": {"scenario": {"resource": self.resource}},
        })
        self.data = {"projectSlug": self.slug, "phase": "scenario", "text": "Use supplier data.",
                     "requestId": "a" * 32}

    def bridge(self, slug: str, phase: str, action: str, request: str) -> dict:
        return {"status": "ready", "version": "0.3.0"} if action == "ping" else {"status": "dispatched"}

    def test_sending_is_persistent_idempotent_and_does_not_create_a_chat_or_approval(self) -> None:
        with (
            patch.object(portal.scenario_chat, "resolve", return_value={"resource": self.resource}),
            patch.object(self.studio, "chat_bridge", side_effect=self.bridge) as bridge,
            patch.object(portal.subprocess, "run") as launch,
        ):
            result = self.studio.send_message(self.data)
            self.assertEqual("dispatched", result["status"])
            self.assertEqual(result, self.studio.send_message(self.data))
        self.assertEqual(2, bridge.call_count)
        launch.assert_not_called()
        restored = portal.Studio(self.root).conversation(self.slug, "scenario")
        self.assertEqual("Use supplier data.", restored["messages"][0]["text"])
        self.assertNotIn("resource", restored["messages"][0])
        self.assertFalse((self.saved / "scoping-response.json").exists())
        self.assertFalse(self.studio.folder(self.slug).exists())
        self.assertEqual([], self.studio.conversation(self.slug, "composition")["messages"])

    def test_unknown_delivery_is_explicit_and_never_automatically_retried(self) -> None:
        def disconnected(slug: str, phase: str, action: str, request: str) -> dict:
            if action == "ping":
                return self.bridge(slug, phase, action, request)
            raise ValueError("No editor acknowledgement.")

        with (
            patch.object(portal.scenario_chat, "resolve", return_value={"resource": self.resource}),
            patch.object(self.studio, "chat_bridge", side_effect=disconnected) as bridge,
        ):
            result = self.studio.send_message(self.data)
            self.assertEqual("unknown", result["status"])
            self.assertIn("Check the existing VS Code chat", result["error"])
            self.assertEqual(result, self.studio.send_message(self.data))
        self.assertEqual(2, bridge.call_count)

    def test_only_proven_predispatch_failure_can_be_explicitly_retried(self) -> None:
        with (
            patch.object(portal.scenario_chat, "resolve", return_value={"resource": self.resource}),
            patch.object(self.studio, "chat_bridge", side_effect=[
                {"status": "ready", "version": "0.3.0"}, {"status": "failed", "error": "Native opener unavailable."},
                {"status": "ready", "version": "0.3.0"}, {"status": "dispatched"},
            ]),
        ):
            self.assertEqual("failed", self.studio.send_message(self.data)["status"])
            self.assertEqual("dispatched", self.studio.send_message(self.data)["status"])
        with self.assertRaisesRegex(ValueError, "another message"):
            self.studio.send_message({**self.data, "text": "Different"})

    def test_old_bridge_and_missing_session_fail_before_submission(self) -> None:
        with (
            patch.object(portal.scenario_chat, "resolve", return_value={"resource": self.resource}),
            patch.object(self.studio, "chat_bridge", return_value={"status": "ready", "version": "0.2.3"}) as bridge,
        ):
            with self.assertRaisesRegex(ValueError, "0.3.0"):
                self.studio.send_message(self.data)
        self.assertEqual(1, bridge.call_count)
        self.assertFalse((self.saved / "messages").exists())
        with patch.object(portal.scenario_chat, "resolve", side_effect=ValueError("No matching existing conversation")):
            with self.assertRaisesRegex(ValueError, "existing conversation"):
                self.studio.send_message(self.data)

    def test_invalid_input_and_legacy_worker_cannot_send(self) -> None:
        with patch.object(self.studio, "chat_bridge") as bridge:
            for change in ({"phase": "other"}, {"projectSlug": "../elsewhere"}, {"text": ""},
                           {"text": "x" * 8001}, {"requestId": "../bad"}, {"requestId": None}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    self.studio.send_message({**self.data, **change})
            portal_status.write_json(self.studio.state / "projects" / f"{self.slug}.json", {"writer": "old-worker"})
            with self.assertRaisesRegex(ValueError, "legacy worker"):
                self.studio.send_message(self.data)
        bridge.assert_not_called()

    def test_reports_keep_bounded_history_and_separate_composition_from_reference(self) -> None:
        for index in range(105):
            portal_status.report(self.root, self.slug, "requirements", "running", f"Report {index}")
        portal_status.report(self.root, self.slug, "hack-content", "waiting_for_user", "Choose challenge emphasis.")
        stored = json.loads((self.saved / "status.json").read_text())
        self.assertEqual(100, len(stored["events"]))
        reference = self.studio.conversation(self.slug, "scenario")["messages"]
        self.assertEqual(99, len(reference))
        self.assertEqual("Report 104", reference[-1]["text"])
        self.assertEqual("Choose challenge emphasis.",
                         self.studio.conversation(self.slug, "composition")["messages"][0]["text"])
        self.assertEqual("Report 104", stored["steps"]["requirements"]["summary"])

    def test_legacy_reports_are_visible_without_rewriting_them_or_resolving_sessions(self) -> None:
        path = self.saved / "status.json"
        portal_status.write_json(path, {"steps": {
            "requirements": {"status": "waiting_for_user", "summary": "Which audience?"},
        }})
        before = path.read_bytes()
        with patch.object(portal.scenario_chat, "resolve") as resolve:
            self.assertEqual("Which audience?", self.studio.conversation(self.slug, "scenario")["messages"][0]["text"])
        resolve.assert_not_called()
        self.assertEqual(before, path.read_bytes())
        portal_status.report(self.root, self.slug, "requirements", "running", "Applying the audience answer.")
        history = self.studio.conversation(self.slug, "scenario")["messages"]
        self.assertEqual(["Which audience?", "Applying the audience answer."], [item["text"] for item in history])

    def test_http_conversation_reads_do_not_dispatch_and_cross_origin_posts_are_blocked(self) -> None:
        server = portal.make_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        self.addCleanup(connection.close)
        with patch.object(server.app, "chat_bridge") as bridge:
            connection.request("GET", f"/api/conversation?project={self.slug}&phase=scenario")
            response = connection.getresponse()
            self.assertEqual(200, response.status)
            self.assertTrue(json.loads(response.read())["canSend"])
            connection.request("POST", "/api/conversation/send", json.dumps(self.data),
                               {"Content-Type": "application/json", "Origin": "https://unrelated.test"})
            response = connection.getresponse()
            self.assertEqual(403, response.status)
            response.read()
        bridge.assert_not_called()
