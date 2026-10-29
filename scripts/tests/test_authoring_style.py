"""Keep clean challenge headings valid while retaining released-page compatibility."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "skills" / "skillable-lod-authoring" / "scripts" / "validate_skillable_package.py"
SPEC = importlib.util.spec_from_file_location("skillable_validator", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class AuthoringStyleTests(unittest.TestCase):
    def test_stable_filenames_use_the_visible_zero_based_challenge_numbers(self) -> None:
        self.assertEqual(validator.CHALLENGE_PREFIXES, ("00-", "01-", "02-", "03-", "04-"))
        self.assertEqual(validator.EXPECTED_CHALLENGE_FILES, (
            "00-secure-foundation.md", "01-build-the-agent.md", "02-ground-it.md",
            "03-give-it-tools.md", "04-harden-and-demo.md",
        ))

    def test_filename_and_visible_challenge_number_must_match(self) -> None:
        for number, filename in enumerate(validator.EXPECTED_CHALLENGE_FILES):
            for displayed in (number, (number + 1) % 5):
                with self.subTest(filename=filename, displayed=displayed), tempfile.TemporaryDirectory() as temp:
                    page = Path(temp) / filename
                    page.write_text(
                        f"# \U0001f9e0 Challenge {displayed} \u2014 Example\n", encoding="utf-8",
                    )
                    errors: list[str] = []
                    validator.validate_challenge_page(page, errors)
                    mismatch = [error for error in errors if "filename number" in error]
                    self.assertEqual(bool(mismatch), displayed != number)

    def test_challenge_sections_accept_clean_and_legacy_headings(self) -> None:
        frontmatter = """---
lab:
  title: Test challenge
  module: Challenge 1
  description: Test
  duration: 30 minutes
  level: 200
  islab: true
  primarytopics: Foundry
---
"""
        title = "# Challenge 1 \u2014 Test challenge\n"
        for prefix in ("", "\u2705 "):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temp:
                page = Path(temp) / "challenge.md"
                body = "\n".join(
                    section.replace("## ", f"## {prefix}") + "\nObservable business outcome.\n"
                    for section in validator.REQUIRED_CHALLENGE_SECTIONS
                )
                page.write_text(frontmatter + title + body, encoding="utf-8")
                errors: list[str] = []
                _, scenario, duration = validator.validate_challenge_page(page, errors)
                self.assertFalse(any("section" in error.lower() for error in errors), errors)
                self.assertEqual("Observable business outcome.", scenario.strip())
                self.assertEqual(30, duration)


if __name__ == "__main__":
    unittest.main()
