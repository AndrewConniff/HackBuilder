"""Verify portable catalog metadata, adaptation isolation and backward-compatible branding."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hack_workflow
import portal_workflow
import scenario_catalog as catalog


class ScenarioCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "generated-scenarios" / "finance-source"
        (self.source / "infra").mkdir(parents=True)
        (self.source / "src").mkdir()
        (self.source / "infra" / "main.bicep").write_text("param name string\n", encoding="utf-8")
        (self.source / "src" / "app.cs").write_text("// reference\n", encoding="utf-8")
        (self.source / "workflow-state.json").write_text('{"approval": "old"}', encoding="utf-8")
        self.request = {
            "industry": "Financial Services", "businessUnits": ["finance", "it"],
            "services": ["foundry"], "pillars": ["security"], "domains": [],
        }

    def test_refresh_is_portable_and_discovery_is_read_only(self) -> None:
        missing = catalog.discover(self.root)
        self.assertFalse(missing["scenarios"][0]["available"])
        self.assertFalse((self.source / catalog.MANIFEST).exists())
        value = catalog.refresh(self.source, request=self.request)
        self.assertEqual(["finance", "it"], value["businessUnits"])
        self.assertEqual("needs-review", value["metadataStatus"])
        before = (self.source / catalog.MANIFEST).read_bytes()
        discovered = catalog.discover(self.root)
        self.assertEqual(before, (self.source / catalog.MANIFEST).read_bytes())
        self.assertTrue(discovered["scenarios"][0]["available"])
        catalog.export_index(self.root)
        serialized = (self.root / "scenarios" / "catalog.json").read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("approval", serialized)
        self.assertNotIn("workflow-state", serialized)

    def test_metadata_is_validated_not_silently_dropped(self) -> None:
        for metadata in (
            {"businessUnits": ["generic", "finance"]}, {"services": ["unknown"]},
            {"title": ""}, {"subscriptionId": "not-portable"}, {"industry": "Unknown"},
            {"businessUnits": []},
        ):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                catalog.refresh(self.source, metadata=metadata)
        self.assertFalse((self.source / catalog.MANIFEST).exists())

    def test_legacy_industry_text_is_not_silently_mapped(self) -> None:
        requirements = self.source / "01-requirements.md"
        requirements.write_text("| Industry | Retail |\n", encoding="utf-8")
        value = catalog.refresh(self.source)
        self.assertIsNone(value["industry"])
        self.assertIn("explicit classification review: Retail", value["summary"])
        self.assertEqual("needs-review", value["metadataStatus"])

    def test_inference_uses_exact_named_requirements_only(self) -> None:
        catalog.refresh(self.source)
        (self.source / "01-requirements.md").write_text(
            "| Industry | Financial Services |\n"
            "| Microsoft Foundry | Agent |\n| Azure Container Apps | Hosting |\n"
            "| WAF priorities | Security; Operational Excellence |\n"
            "| Technical domain | Identity and least privilege |\n",
            encoding="utf-8",
        )
        value = catalog.refresh(self.source)
        self.assertEqual(["foundry", "container-apps"], value["services"])
        self.assertEqual(["security", "operational-excellence"], value["pillars"])
        self.assertEqual(["identity"], value["domains"])
        self.assertEqual("needs-review", value["metadataStatus"])
        catalog.refresh(self.source, metadata={"metadataStatus": "curated", "services": ["foundry"]})
        self.assertEqual(["foundry"], catalog.refresh(self.source)["services"])

    def test_source_is_bound_to_manifest_without_copying_any_files(self) -> None:
        source = catalog.refresh(self.source, request=self.request)
        selected = catalog.select_source(self.root, self.source.name, catalog.digest(source), "energy-new")
        self.assertEqual(source, selected["manifest"])
        self.assertFalse((self.source.parent / "energy-new").exists())
        target = self.source.parent / "energy-new"
        target.mkdir()
        value = catalog.refresh(target, request={
            **self.request, "industry": "Energy & Resources", "businessUnits": ["operations"],
            "reuseSource": selected,
        })
        self.assertEqual("Energy & Resources", value["industry"])
        self.assertEqual(["operations"], value["businessUnits"])
        self.assertEqual(
            {"scenarioId": self.source.name, "manifestDigest": catalog.digest(source)}, value["source"],
        )
        self.assertFalse((target / "workflow-state.json").exists())
        self.assertFalse((target / "infra").exists())

    def test_changed_source_same_slug_existing_target_and_traversal_are_rejected(self) -> None:
        value = catalog.refresh(self.source, request=self.request)
        digest = catalog.digest(value)
        for source_id, expected, target in (
            ("../outside", digest, "energy-new"),
            (self.source.name, digest, self.source.name),
            (self.source.name, "0" * 64, "energy-new"),
            ("missing", digest, "energy-new"),
        ):
            with self.subTest(source=source_id, target=target), self.assertRaises(ValueError):
                catalog.select_source(self.root, source_id, expected, target)
        (self.source.parent / "energy-new").mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            catalog.select_source(self.root, self.source.name, digest, "energy-new")

    def test_invalid_manifest_is_visible_and_never_replaced_by_index(self) -> None:
        catalog.refresh(self.source, request=self.request)
        catalog.export_index(self.root)
        (self.source / catalog.MANIFEST).write_text("not json", encoding="utf-8")
        found = catalog.discover(self.root)
        self.assertEqual([], found["scenarios"])
        self.assertEqual(self.source.name, found["errors"][0]["id"])

    def test_imported_repository_metadata_requires_local_reference(self) -> None:
        catalog.refresh(self.source, request=self.request)
        catalog.export_index(self.root)
        self.source.rename(self.root / "offline-source")
        found = catalog.discover(self.root)
        self.assertEqual(self.source.name, found["scenarios"][0]["id"])
        self.assertFalse(found["scenarios"][0]["available"])

    def test_malicious_artifact_paths_fail(self) -> None:
        value = catalog.refresh(self.source, request=self.request)
        for artifacts in (["../secrets"], [str(self.root)], ["workflow-state.json"], [None]):
            with self.subTest(artifacts=artifacts), self.assertRaises(ValueError):
                catalog.validate({**value, "artifacts": artifacts}, self.source.name)

    def test_nested_artifact_escape_is_unavailable(self) -> None:
        value = catalog.refresh(self.source, request=self.request)
        original = Path.resolve

        def resolve(path: Path, *args, **kwargs) -> Path:
            return self.root / "outside" if path == self.source / "src" else original(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            self.assertFalse(catalog.discover(self.root)["scenarios"][0]["available"])
        self.assertEqual(value, catalog.validate(value, self.source.name))

    def test_catalog_refresh_does_not_invalidate_reference_approval_fingerprint(self) -> None:
        before = hack_workflow.reference_fingerprint(self.source)
        catalog.refresh(self.source, request=self.request)
        self.assertEqual(before, hack_workflow.reference_fingerprint(self.source))
        (self.source / "src" / "app.cs").write_text("// modified\n", encoding="utf-8")
        self.assertNotEqual(before, hack_workflow.reference_fingerprint(self.source))

    def test_fresh_state_uses_abc_but_upgrade_keeps_existing_leases(self) -> None:
        self.assertEqual(self.root / ".abcbuilder-portal", portal_workflow.state_directory(self.root))
        (self.root / ".hackbuilder-portal").mkdir()
        self.assertEqual(self.root / ".hackbuilder-portal", portal_workflow.state_directory(self.root))


if __name__ == "__main__":
    unittest.main()
