"""Regression coverage for the explicitly authorized Hospitality & Travel extension."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".github/skills/skillable-lod-authoring"
spec = importlib.util.spec_from_file_location("hospitality_validator", SKILL / "scripts/validate_skillable_package.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class HospitalitySupportTests(unittest.TestCase):
    def test_exact_catalog_identity_and_existing_industries(self):
        catalog = json.loads((SKILL / "assets/industry-catalog.json").read_text(encoding="utf-8"))
        entries = {item["slug"]: item["displayName"] for item in catalog}
        self.assertEqual(len(catalog), 8)
        self.assertEqual(entries["hospitality-travel"], "Hospitality & Travel")
        self.assertEqual(set(entries), validator.EXPECTED_INDUSTRIES)
        self.assertEqual(entries["retail"], "Retail")

    def test_shared_templates_and_validator_remain_valid(self):
        self.assertEqual(validator.validate_skill(), [])

    def test_no_silent_synonyms_or_retail_mapping(self):
        for slug in ("hospitality", "hospitality-and-travel", "travel"):
            errors = validator.validate_package(ROOT / "missing-package", slug)
            self.assertEqual(errors, [f"Unsupported industry slug {slug!r}."])

    def test_canonical_hospitality_is_not_rejected_as_unsupported(self):
        errors = validator.validate_package(ROOT / "missing-package", "hospitality-travel")
        self.assertTrue(errors)
        self.assertFalse(any("Unsupported industry" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
