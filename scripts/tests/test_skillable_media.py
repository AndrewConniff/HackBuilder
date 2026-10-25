"""Regression coverage for the authorized Media & Communications support extension."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".github/skills/skillable-lod-authoring"
SPEC = importlib.util.spec_from_file_location(
    "media_validator", SKILL / "scripts/validate_skillable_package.py"
)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class MediaSupportTests(unittest.TestCase):
    def test_exact_catalog_identity_preserves_prior_industries(self):
        catalog = json.loads((SKILL / "assets/industry-catalog.json").read_text(encoding="utf-8"))
        entries = {item["slug"]: item["displayName"] for item in catalog}
        self.assertEqual(len(catalog), 8)
        self.assertEqual(entries["media-communications"], "Media & Communications")
        self.assertEqual(entries["hospitality-travel"], "Hospitality & Travel")
        self.assertEqual(set(entries), validator.EXPECTED_INDUSTRIES)

    def test_shared_templates_and_validator(self):
        self.assertEqual(validator.validate_skill(), [])

    def test_no_silent_synonyms(self):
        for slug in ("media", "communications", "media-and-communications", "Media & Communications"):
            self.assertEqual(
                validator.validate_package(ROOT / "missing-package", slug),
                [f"Unsupported industry slug {slug!r}."],
            )

    def test_canonical_slug_reaches_package_validation(self):
        errors = validator.validate_package(ROOT / "missing-package", "media-communications")
        self.assertTrue(errors)
        self.assertFalse(any("Unsupported industry" in error for error in errors))

    def test_cli_accepts_canonical_slug(self):
        with patch("sys.argv", ["validator", "packages", "--industry", "media-communications"]):
            self.assertEqual(validator.parse_args().industry, "media-communications")

    def test_wrong_display_name_and_duplicate_identity_are_rejected(self):
        original = Path.read_text
        catalog_path = SKILL / "assets/industry-catalog.json"
        catalog = json.loads(original(catalog_path, encoding="utf-8"))
        for duplicate in (False, True):
            modified = [dict(entry) for entry in catalog]
            media = next(entry for entry in modified if entry["slug"] == "media-communications")
            if duplicate:
                modified.append(dict(media))
            else:
                media["displayName"] = "Media"

            def read(path, *args, **kwargs):
                if path == catalog_path:
                    return json.dumps(modified)
                return original(path, *args, **kwargs)

            with self.subTest(duplicate=duplicate), patch.object(Path, "read_text", read):
                self.assertTrue(any("Media & Communications must use" in error
                                    for error in validator.validate_skill()))


if __name__ == "__main__":
    unittest.main()
