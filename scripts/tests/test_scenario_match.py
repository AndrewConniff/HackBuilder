"""Verify useful cross-industry retrieval, evidence freshness and explicit target-preserving reuse decisions."""

from __future__ import annotations

import http.client
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hack_workflow
import portal_status
import portal_visualizer as portal
import scenario_adapt as adapt
import scenario_catalog as catalog
import scenario_match as match


class MatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "portal").mkdir()
        shutil.copy(portal.ROOT / "portal" / "catalog.json", self.root / "portal")
        shutil.copy(portal.ROOT / "microsoft_industry_verticals.csv", self.root)
        self.studio = portal.Studio(self.root)
        self.source = self.add_source(
            "finance-triage", "Financial Services",
            "Event-driven ticket triage and routing with human approval and grounded retrieval.",
            "// Event-driven queue routes tickets for human approval with grounded retrieval.\n",
        )
        self.add_source("retail-stock", "Retail & Consumer Goods",
                        "Inventory and stock replenishment with daily reconciliation.", "// Inventory reconciliation.\n")
        self.target = {
            "projectSlug": "retail-target", "prompt": "Route incoming service tickets using event-driven triage. "
            "Retrieve grounded documents and request human approval before escalation.",
            "industry": "Retail & Consumer Goods", "businessUnits": ["operations"], "agenticPattern": "ai-decides",
            "services": ["foundry"], "pillars": ["security"], "domains": [], "intakeMode": "scope",
        }

    def add_source(self, slug: str, industry: str, summary: str, code: str) -> Path:
        folder = self.studio.folder(slug)
        (folder / "infra").mkdir(parents=True)
        (folder / "src").mkdir()
        (folder / "infra" / "main.bicep").write_text("param name string\n", encoding="utf-8")
        (folder / "src" / "app.cs").write_text(code, encoding="utf-8")
        (folder / "02-architecture-assessment.md").write_text(summary + "\n", encoding="utf-8")
        catalog.refresh(folder, request={"industry": industry}, metadata={
            "title": slug.replace("-", " ").title(), "summary": summary, "metadataStatus": "curated",
        })
        match.enrich(self.root, slug)
        return folder

    def snapshot(self) -> dict:
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def selection(self) -> dict:
        source = adapt.preview(self.root, self.source.name)[0]
        return {key: source[key] for key in ("scenarioId", "manifestDigest", "artifactsDigest")}

    def scope(self) -> tuple[Path, str]:
        self.studio.save_brief(self.target)
        saved = portal_status.scenario_state(self.root, "retail-target")
        (saved / "scoping.md").write_text("## Target brief\n\n" + self.target["prompt"], encoding="utf-8")
        portal_status.report(self.root, "retail-target", "requirements", "waiting_for_user", "Review the brief.")
        return saved, self.studio.scoping_notes("retail-target")["fingerprint"]

    def test_cross_industry_workflow_beats_same_industry_poor_match(self) -> None:
        result = match.recommend(self.root, self.target)
        self.assertEqual("local-catalog", result["method"])
        self.assertEqual("finance-triage", result["matches"][0]["scenarioId"])
        self.assertNotIn("retail-stock", [item["scenarioId"] for item in result["matches"]])
        self.assertIn("Different industry", " ".join(result["matches"][0]["concerns"]))
        self.assertEqual("needs-review", result["matches"][0]["metadataStatus"])
        self.assertEqual("current", result["matches"][0]["profileState"])
        self.assertTrue(result["matches"][0]["evidence"])
        self.assertNotIn("_score", result["matches"][0])

    def test_recommendation_is_read_only_and_never_dispatches_or_creates_workspace(self) -> None:
        before = self.snapshot()
        with patch.object(portal.subprocess, "run") as run:
            match.recommend(self.root, self.target)
        run.assert_not_called()
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.studio.folder("retail-target").exists())

    def test_profile_enrichment_does_not_change_source_or_approval_fingerprint(self) -> None:
        before = hack_workflow.reference_fingerprint(self.source)
        manifest = (self.source / catalog.MANIFEST).read_bytes()
        match.enrich(self.root, self.source.name)
        self.assertEqual(before, hack_workflow.reference_fingerprint(self.source))
        self.assertEqual(manifest, (self.source / catalog.MANIFEST).read_bytes())
        self.assertFalse((self.source / "reuse-profile.json").exists())

    def test_common_services_and_vague_prompt_do_not_force_suggestions(self) -> None:
        for prompt in ("Build an AI assistant for Azure Foundry.", "A helpful scenario for users."):
            result = match.recommend(self.root, {**self.target, "prompt": prompt})
            self.assertEqual([], result["matches"])

    def test_curated_retrieval_evaluation_cases(self) -> None:
        cases = [
            ("cross-industry-triage", self.target["prompt"], "Retail & Consumer Goods", "finance-triage"),
            ("stock-and-close", "Manage stock inventory replenishment and daily reconciliation.",
             "Financial Services", "retail-stock"),
            ("shared-service-only", "Build an Azure Foundry assistant for our users.", "Financial Services", None),
            ("same-industry-only", "Improve my retail customer business with a useful assistant.",
             "Retail & Consumer Goods", None),
            ("triage-domain-transfer", "Triage service cases, route tickets and retrieve grounded evidence.",
             "Manufacturing & Mobility", "finance-triage"),
            ("inventory-domain-transfer", "Reconcile inventory stock and plan replenishment after daily close.",
             "Manufacturing & Mobility", "retail-stock"),
        ]
        for label, prompt, industry, expected in cases:
            with self.subTest(case=label):
                result = match.recommend(self.root, {**self.target, "prompt": prompt, "industry": industry})
                first = result["matches"][0]["scenarioId"] if result["matches"] else None
                self.assertEqual(expected, first)

    def test_explicit_security_mismatch_is_visible_not_silently_overridden(self) -> None:
        (self.source / "infra" / "main.bicep").write_text("// Public ingress and local accounts\n", encoding="utf-8")
        match.enrich(self.root, self.source.name)
        result = match.recommend(self.root, {
            **self.target, "prompt": self.target["prompt"] + " Private endpoint and Entra identity are required.",
        })
        source = next(item for item in result["matches"] if item["scenarioId"] == self.source.name)
        self.assertIn("Target needs Private network boundary", " ".join(source["concerns"]))
        self.assertIn("Target needs Entra identity", " ".join(source["concerns"]))

    def test_source_change_or_new_file_invalidates_profile_and_digest(self) -> None:
        first = match.recommend(self.root, self.target)
        (self.source / "src" / "new.cs").write_text("// A new integration\n", encoding="utf-8")
        second = match.recommend(self.root, self.target)
        self.assertEqual("stale", second["matches"][0]["profileState"])
        self.assertEqual({}, second["matches"][0]["evidence"])
        self.assertNotEqual(first["catalogDigest"], second["catalogDigest"])

    def test_remote_profile_remains_inspiration_only(self) -> None:
        catalog.export_index(self.root)
        values, _ = match.profiles(self.root)
        catalog.write_json(self.root / "scenarios" / match.INDEX, {"schemaVersion": 1, "profiles": values})
        shutil.rmtree(self.source)
        result = match.recommend(self.root, self.target)
        source = result["matches"][0]
        self.assertFalse(source["available"])
        self.assertEqual("unverified", source["profileState"])
        self.assertIn("inspiration only", " ".join(source["concerns"]))

    def test_malformed_profile_is_reported_and_catalog_fallback_is_honest(self) -> None:
        path = self.root / "scenarios" / match.PROFILE_DIR / f"{self.source.name}.json"
        value = catalog.read_json(path)
        value["inputs"]["../escape.cs"] = "0" * 64
        catalog.write_json(path, value)
        result = match.recommend(self.root, self.target)
        self.assertTrue(result["errors"])
        self.assertEqual("missing", result["matches"][0]["profileState"])

    def test_read_only_request_validation_and_relevant_input_digest(self) -> None:
        first = match.recommend(self.root, self.target)
        second = match.recommend(self.root, {**self.target, "agenticPattern": "routing-triage"})
        self.assertNotEqual(first["inputDigest"], second["inputDigest"])
        for invalid in ({"prompt": ""}, {"agenticPattern": []}, {"services": ["made-up"]}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                match.recommend(self.root, {**self.target, **invalid})

    def test_explicit_review_can_remove_false_positives_without_claiming_runtime(self) -> None:
        path = self.root / "scenarios" / match.PROFILE_DIR / f"{self.source.name}.json"
        value = catalog.read_json(path)
        reviewed = match.review(self.root, self.source.name, {
            "profileDigest": catalog.digest(value), "keptFeatures": ["routing-triage"],
            "implementedPatterns": ["routing-triage"], "architectureSummary": "A tool-backed ticket triage flow.",
        })
        self.assertEqual("curated", reviewed["metadataStatus"])
        self.assertEqual(["routing-triage"], reviewed["patternEvidence"]["implemented"])
        self.assertEqual({"routing-triage"}, set(reviewed["features"]))
        self.assertIn("runtime", " ".join(reviewed["limitations"]))

    def test_profile_records_design_versus_code_and_unknown_implementation(self) -> None:
        profile = catalog.read_json(self.root / "scenarios" / match.PROFILE_DIR / f"{self.source.name}.json")
        self.assertEqual("unknown-until-reviewed", profile["patternEvidence"]["implemented"])
        self.assertIn("human-in-the-loop", profile["dimensions"]["humanDecisionPoints"])
        self.assertEqual({"code", "design"}, {ref["basis"] for ref in profile["features"]["routing-triage"]})

    def test_compiled_bicep_json_is_not_a_reusable_source_input(self) -> None:
        (self.source / "infra" / "main.json").write_text("x" * (3 * 1024 * 1024), encoding="utf-8")
        match.enrich(self.root, self.source.name)
        self.assertNotIn("infra/main.json", adapt.preview(self.root, self.source.name)[0]["files"])

    def test_late_selection_requires_agent_revision_and_fresh_confirmation(self) -> None:
        saved, fingerprint = self.scope()
        original = (saved / "request.json").read_bytes()
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}) as dispatch:
            self.studio.select_reuse({
                "projectSlug": "retail-target", "fingerprint": fingerprint, "reuseSource": self.selection(),
            })
        dispatch.assert_called_once()
        self.assertEqual(original, (saved / "request.json").read_bytes())
        self.assertFalse(self.studio.scoping_notes("retail-target")["canConfirm"])
        with self.assertRaisesRegex(ValueError, "assess"):
            self.studio.respond_to_scoping("retail-target", fingerprint, "confirmed")
        with self.assertRaises(ValueError):
            adapt.effective_request(self.root, "retail-target")
        decision = adapt.reuse_selection(self.root, "retail-target")
        (saved / "scoping.md").write_text(
            f"## Reviewed target\n\nReuse selection: {decision['id']}\n"
            "Keep routing; change industry data; no authority or deployment results carry over.", encoding="utf-8",
        )
        adapt.review_selection(self.root, "retail-target")
        current = self.studio.scoping_notes("retail-target")
        self.assertTrue(current["canConfirm"])
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}):
            self.studio.respond_to_scoping("retail-target", current["fingerprint"], "confirmed")
        request = adapt.effective_request(self.root, "retail-target")
        self.assertEqual(self.target["prompt"], request["prompt"])
        self.assertEqual(self.target["industry"], request["industry"])
        self.assertEqual(self.selection(), request["reuseSource"])
        target = self.studio.folder("retail-target")
        target.mkdir()
        receipt = adapt.prepare(self.root, "retail-target")
        self.assertEqual(self.source.name, receipt["source"]["scenarioId"])
        self.assertEqual(original, (saved / "request.json").read_bytes())

    def test_late_selection_rejects_stale_brief_source_and_already_dispatched_build(self) -> None:
        saved, fingerprint = self.scope()
        data = {"projectSlug": "retail-target", "fingerprint": fingerprint, "reuseSource": self.selection()}
        with self.assertRaisesRegex(ValueError, "current brief"):
            self.studio.select_reuse({**data, "fingerprint": "0" * 64})
        (self.source / "src" / "app.cs").write_text("// changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.studio.select_reuse(data)
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}):
            self.studio.respond_to_scoping("retail-target", fingerprint, "confirmed")
        with self.assertRaisesRegex(ValueError, "already dispatched"):
            self.studio.select_reuse({**data, "reuseSource": self.selection()})
        self.assertFalse((saved / "reuse-selection.json").exists())

    def test_failed_late_dispatch_is_retryable_but_success_is_not_replayed(self) -> None:
        _, fingerprint = self.scope()
        data = {"projectSlug": "retail-target", "fingerprint": fingerprint, "reuseSource": self.selection()}
        with patch.object(self.studio, "continue_brief", side_effect=ValueError("not linked")):
            with self.assertRaisesRegex(ValueError, "not acknowledged"):
                self.studio.select_reuse(data)
        first = adapt.reuse_selection(self.root, "retail-target")
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}) as dispatch:
            self.studio.select_reuse(data)
            self.studio.select_reuse(data)
        dispatch.assert_called_once()
        self.assertEqual(first["id"], adapt.reuse_selection(self.root, "retail-target")["id"])

    def test_explicit_late_build_fresh_clears_effective_source_not_original_intake(self) -> None:
        self.target["reuseSource"] = self.selection()
        saved, fingerprint = self.scope()
        original = (saved / "request.json").read_bytes()
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}):
            self.studio.select_reuse({
                "projectSlug": "retail-target", "fingerprint": fingerprint, "reuseSource": None,
            })
        decision = adapt.reuse_selection(self.root, "retail-target")
        (saved / "scoping.md").write_text(
            f"## Fresh build\n\nReuse selection: {decision['id']}\nBuild fresh; no source files.", encoding="utf-8",
        )
        adapt.review_selection(self.root, "retail-target")
        current = self.studio.scoping_notes("retail-target")
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}):
            self.studio.respond_to_scoping("retail-target", current["fingerprint"], "confirmed")
        self.assertNotIn("reuseSource", adapt.effective_request(self.root, "retail-target"))
        self.assertEqual(original, (saved / "request.json").read_bytes())

    def test_changed_source_or_revised_brief_invalidates_late_review_binding(self) -> None:
        saved, fingerprint = self.scope()
        with patch.object(self.studio, "continue_brief", return_value={"status": "dispatched"}):
            self.studio.select_reuse({
                "projectSlug": "retail-target", "fingerprint": fingerprint, "reuseSource": self.selection(),
            })
        decision = adapt.reuse_selection(self.root, "retail-target")
        (saved / "scoping.md").write_text(
            f"## Revised brief\n\nReuse selection: {decision['id']}\nReviewed source fit.", encoding="utf-8",
        )
        adapt.review_selection(self.root, "retail-target")
        current = self.studio.scoping_notes("retail-target")
        (self.source / "src" / "app.cs").write_text("// source changes after review\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.studio.respond_to_scoping("retail-target", current["fingerprint"], "confirmed")
        with (saved / "scoping.md").open("a", encoding="utf-8") as stream:
            stream.write("\nNew constraints.")
        self.assertFalse(self.studio.scoping_notes("retail-target")["canConfirm"])

    def test_new_endpoints_have_origin_protection_and_no_implicit_dispatch(self) -> None:
        server = portal.make_server(self.root, 0)
        self.addCleanup(server.server_close)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.shutdown)
        for endpoint, origin, expected in (
            ("/api/reuse-recommendations", None, 200),
            ("/api/reuse-recommendations", "https://example.test", 403),
            ("/api/reuse-selection", "https://example.test", 403),
        ):
            connection = http.client.HTTPConnection(*server.server_address)
            headers = {"Content-Type": "application/json"}
            if origin:
                headers["Origin"] = origin
            with patch.object(server.app, "continue_brief") as dispatch:
                connection.request("POST", endpoint, json.dumps(self.target), headers)
                response = connection.getresponse()
                self.assertEqual(expected, response.status)
                response.read()
                dispatch.assert_not_called()
            connection.close()


if __name__ == "__main__":
    unittest.main()
