"""Verify source-bound brief reuse, isolated copies and measurable artifact reconciliation."""

from __future__ import annotations

import http.client
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portal_status
import portal_visualizer as portal
import scenario_adapt as adapt
import scenario_catalog as catalog


class AdaptationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "portal").mkdir()
        shutil.copy(portal.ROOT / "portal" / "catalog.json", self.root / "portal")
        shutil.copy(portal.ROOT / "microsoft_industry_verticals.csv", self.root)
        self.studio = portal.Studio(self.root)
        self.source = self.studio.folder("finance-source")
        (self.source / "infra").mkdir(parents=True)
        (self.source / "src").mkdir()
        (self.source / "infra" / "main.bicep").write_text("param name string\n", encoding="utf-8")
        (self.source / "src" / "app.cs").write_text("class FinanceApp {}\n", encoding="utf-8")
        (self.source / "src" / "seed.csv").write_text("name\nSynthetic Company\n", encoding="utf-8")
        (self.source / "01-requirements.md").write_text("## Source requirements\n", encoding="utf-8")
        self.source_request = {
            "industry": "Financial Services", "businessUnits": ["finance"], "services": ["foundry"],
            "pillars": ["security"], "domains": [], "prompt": "A finance assistant",
            "agenticPattern": "ai-decides",
        }
        catalog.refresh(self.source, request=self.source_request)
        source_state = portal_status.scenario_state(self.root, self.source.name)
        portal_status.write_json(source_state / "request.json", self.source_request)
        (source_state / "scoping.md").write_text("## Refined source brief\n\nFinance scope.\n", encoding="utf-8")
        self.data = {
            **self.source_request, "projectSlug": "retail-target", "industry": "Retail & Consumer Goods",
            "businessUnits": ["operations"], "prompt": "A retail inventory assistant",
            "reuseSource": self.selection(),
        }

    def selection(self) -> dict:
        preview, _ = adapt.preview(self.root, self.source.name)
        return {key: preview[key] for key in ("scenarioId", "manifestDigest", "artifactsDigest")}

    def prepare(self) -> tuple[Path, dict]:
        self.studio.save_brief(self.data)
        target = self.studio.folder("retail-target")
        target.mkdir()
        return target, adapt.prepare(self.root, "retail-target")

    def test_preview_prefers_refined_brief_and_never_mutates_source(self) -> None:
        before = {path: path.read_bytes() for path in self.source.rglob("*") if path.is_file()}
        preview, files = adapt.preview(self.root, self.source.name)
        self.assertIn("Refined source brief", preview["brief"])
        self.assertEqual(self.source_request["prompt"], preview["intake"]["prompt"])
        self.assertEqual(["finance"], preview["intake"]["businessUnits"])
        self.assertEqual("needs-review", preview["metadataStatus"])
        self.assertEqual(set(files), set(preview["files"]))
        self.assertFalse(self.studio.folder("retail-target").exists())
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_brief_editor_does_not_render_internal_source_file_inventory(self) -> None:
        html = (portal.ROOT / "portal" / "visualizer.html").read_text(encoding="utf-8")
        script = (portal.ROOT / "portal" / "visualizer.js").read_text(encoding="utf-8")
        self.assertIn("<summary>Source brief</summary>", html)
        self.assertIn('renderMarkdown($("reuse-brief"), source.brief)', script)
        self.assertNotIn("reuse-files", html)
        self.assertNotIn("reuse-files", script)
        self.assertNotIn("source.files", script)

    def test_preview_falls_back_to_requirements_then_manifest_summary(self) -> None:
        state = portal_status.scenario_state(self.root, self.source.name)
        (state / "scoping.md").unlink()
        (state / "request.json").unlink()
        self.assertIn("Source requirements", adapt.preview(self.root, self.source.name)[0]["brief"])
        (self.source / "01-requirements.md").unlink()
        manifest = catalog.refresh(self.source)
        preview = adapt.preview(self.root, self.source.name)[0]
        self.assertEqual(manifest["summary"], preview["brief"])

    def test_saving_adaptation_forces_existing_scoping_without_creating_workspace(self) -> None:
        with patch.object(portal.subprocess, "run") as launch:
            brief = self.studio.save_brief(self.data)
        launch.assert_not_called()
        self.assertEqual("scope", brief["intakeMode"])
        self.assertEqual(self.data["reuseSource"], brief["reuseSource"])
        self.assertEqual("Retail & Consumer Goods", brief["industry"])
        self.assertFalse(self.studio.folder("retail-target").exists())
        self.assertFalse(self.studio.scenario("retail-target")["approval"]["approved"])

    def test_changed_code_and_brief_each_require_review_again(self) -> None:
        for path in (
            self.source / "src" / "app.cs",
            portal_status.scenario_state(self.root, self.source.name) / "scoping.md",
        ):
            with self.subTest(path=path):
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "changed"):
                    self.studio.save_brief(self.data)
                self.assertFalse((portal_status.scenario_state(self.root, "retail-target") / "request.json").exists())
                path.write_bytes(original)

    def test_manifest_semantic_changes_are_bound(self) -> None:
        catalog.refresh(self.source, metadata={"summary": "New source outcome"})
        with self.assertRaisesRegex(ValueError, "changed"):
            self.studio.save_brief(self.data)

    def test_same_target_traversal_unknown_and_malformed_sources_fail(self) -> None:
        for value in (
            {**self.data["reuseSource"], "scenarioId": "../outside"},
            {**self.data["reuseSource"], "scenarioId": "retail-target"},
            {**self.data["reuseSource"], "scenarioId": "unknown"},
            {"scenarioId": self.source.name}, [], "source",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.studio.save_brief({**self.data, "reuseSource": value})
        with self.assertRaises(ValueError):
            adapt.select(self.root, self.data["reuseSource"], "../outside")

    def test_copy_preserves_source_excludes_state_and_records_target_provenance(self) -> None:
        excluded = (
            ".azure/config.json", "packages/coach/solution.md", "workflow-state.json", "scenario-validation.json",
            "src/appsettings.json", "src/appsettings.Development.json", "src/local.settings.json",
            "src/credentials.json", "src/.env", "src/bin/app.cs", "src/.runtime/agent.json",
            "infra/main.parameters.json", "infra/prod.bicepparam",
        )
        for name in excluded:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("not reusable", encoding="utf-8")
        self.data["reuseSource"] = self.selection()
        before = {path: path.read_bytes() for path in self.source.rglob("*") if path.is_file()}
        target, baseline = self.prepare()
        for name in excluded:
            self.assertFalse((target / name).exists(), name)
        self.assertEqual("pending-reconciliation", baseline["status"])
        for name, old_hash in baseline["files"].items():
            self.assertEqual(old_hash, adapt.hashlib.sha256((target / name).read_bytes()).hexdigest())
        manifest = catalog.read_json(target / catalog.MANIFEST)
        self.assertEqual("retail-target", manifest["id"])
        self.assertEqual("Retail & Consumer Goods", manifest["industry"])
        self.assertEqual(["operations"], manifest["businessUnits"])
        self.assertEqual(self.source.name, manifest["source"]["scenarioId"])
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        self.assertFalse(self.studio.scenario("retail-target")["approval"]["approved"])

    def test_preparation_refuses_missing_or_nonempty_target_and_stale_sources(self) -> None:
        self.studio.save_brief(self.data)
        with self.assertRaisesRegex(ValueError, "empty workspace"):
            adapt.prepare(self.root, "retail-target")
        target = self.studio.folder("retail-target")
        target.mkdir()
        existing = target / "existing.txt"
        existing.write_text("user work", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "empty target"):
            adapt.prepare(self.root, "retail-target")
        self.assertEqual("user work", existing.read_text())
        existing.unlink()
        (self.source / "src" / "app.cs").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            adapt.prepare(self.root, "retail-target")
        self.assertEqual([], list(target.iterdir()))

    def test_manifest_race_during_preparation_is_rejected_before_copy(self) -> None:
        self.studio.save_brief(self.data)
        target = self.studio.folder("retail-target")
        target.mkdir()
        original = adapt.preview
        calls = 0

        def preview(root: Path, source: object) -> tuple[dict, dict[str, bytes]]:
            nonlocal calls
            calls += 1
            if calls == 2:
                catalog.refresh(self.source, metadata={"summary": "Changed during preparation"})
            return original(root, source)

        with patch.object(adapt, "preview", preview), self.assertRaisesRegex(ValueError, "changed"):
            adapt.prepare(self.root, "retail-target")
        self.assertEqual([], list(target.iterdir()))

    def test_binary_static_assets_are_copied_without_text_decoding(self) -> None:
        (self.source / "src" / "favicon.ico").write_bytes(b"\x00\xff\x80")
        self.data["reuseSource"] = self.selection()
        target, baseline = self.prepare()
        self.assertEqual(b"\x00\xff\x80", (target / "src" / "favicon.ico").read_bytes())
        self.assertIn("src/favicon.ico", baseline["files"])

    def test_credentials_and_oversize_inputs_block_preview(self) -> None:
        path = self.source / "src" / "app.cs"
        path.write_text('var api_key = "ExampleCredentialOnly123456789";', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Potential credential"):
            adapt.preview(self.root, self.source.name)
        path.write_text("x" * (2 * 1024 * 1024 + 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "2 MiB"):
            adapt.preview(self.root, self.source.name)

    def test_nested_links_are_rejected_even_when_they_stay_in_source(self) -> None:
        path = self.source / "src" / "app.cs"
        original = Path.resolve

        def resolve(value: Path, *args, **kwargs) -> Path:
            return self.source / "src" / "other.cs" if value == path else original(value, *args, **kwargs)

        with patch.object(Path, "resolve", resolve), self.assertRaisesRegex(ValueError, "nested links"):
            adapt.preview(self.root, self.source.name)

    def test_reconciliation_checks_actual_kept_changed_removed_and_added_files(self) -> None:
        target, baseline = self.prepare()
        decisions = {name: {"action": "keep", "reason": "Still fits target architecture"} for name in baseline["files"]}
        decisions["src/app.cs"] = {"action": "change", "reason": "Target retail workflow"}
        (target / "src" / "app.cs").write_text("class RetailApp {}\n", encoding="utf-8")
        decisions["src/seed.csv"] = {"action": "remove", "reason": "Replaced with target-domain fixtures"}
        (target / "src" / "seed.csv").unlink()
        (target / "src" / "retail.csv").write_text("sku\nExample-01\n", encoding="utf-8")
        report = adapt.reconcile(self.root, "retail-target", decisions)
        self.assertEqual("reconciled-local-files", report["status"])
        self.assertFalse(report["runtimeValidated"])
        self.assertIn("src/retail.csv", report["files"])
        self.assertNotIn("src/seed.csv", report["files"])
        self.assertTrue((target / "adaptation-reconciliation.json").is_file())
        (target / "infra" / "main.bicep").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "keep decision"):
            adapt.reconcile(self.root, "retail-target", decisions)

    def test_incomplete_or_unimplemented_reconciliation_decisions_fail(self) -> None:
        _, baseline = self.prepare()
        decisions = {name: {"action": "keep", "reason": "Fits"} for name in baseline["files"]}
        with self.assertRaisesRegex(ValueError, "every baseline"):
            adapt.reconcile(self.root, "retail-target", {})
        for action in ("change", "remove", "invalid"):
            with self.subTest(action=action), self.assertRaises(ValueError):
                adapt.reconcile(self.root, "retail-target", {
                    **decisions, "src/app.cs": {"action": action, "reason": "Target scope"},
                })

    def test_handoff_loads_adaptation_skill_in_same_conductor(self) -> None:
        self.studio.save_brief(self.data)
        with (
            patch.object(portal.shutil, "which", return_value="code"),
            patch.object(portal.subprocess, "run", return_value=Mock(returncode=0)) as launch,
        ):
            self.studio.handoff("retail-target", "scoping")
        self.assertEqual("az-01-conductor", launch.call_args.args[0][3])
        text = (portal_status.scenario_state(self.root, "retail-target") / "scoping-handoff.txt").read_text()
        for phrase in ("az-scenario-adapt", "SCOPING ONLY", "read-only during scoping", "After brief confirmation",
                       "do not regenerate everything", "Never inherit source deployment state"):
            self.assertIn(phrase, text)
        self.assertFalse(self.studio.folder("retail-target").exists())

    def test_reuse_http_routes_are_read_only_and_reject_cross_origin(self) -> None:
        server = portal.make_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 3)
        self.addCleanup(server.shutdown)
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        self.addCleanup(client.close)
        with patch.object(portal.subprocess, "run") as execute:
            for path in ("/api/reuse-sources", "/api/reuse-source?project=finance-source"):
                client.request("GET", path)
                response = client.getresponse()
                self.assertEqual(200, response.status)
                self.assertIsInstance(json.loads(response.read()), dict)
            client.request("GET", "/api/reuse-source?project=finance-source", headers={"Origin": "https://example.test"})
            response = client.getresponse()
            self.assertEqual(403, response.status)
            response.read()
            execute.assert_not_called()
        self.assertFalse(self.studio.folder("retail-target").exists())


if __name__ == "__main__":
    unittest.main()
