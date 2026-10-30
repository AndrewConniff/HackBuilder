"""Verify consistent first-party branding without rewriting historical scenario evidence."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_BRAND = re.compile(r"[a]bc[ _-]?builder|\b[a]bc\b", re.IGNORECASE)


class BrandingTests(unittest.TestCase):
    def test_first_party_source_and_names_use_current_brand(self) -> None:
        paths = [path for path in ROOT.iterdir() if path.is_file()]
        for directory in (".github", ".agents", ".vscode", "portal", "scripts", "tools", "system-tools", "scenarios", "docs"):
            paths.extend(
                path for path in (ROOT / directory).rglob("*")
                if path.is_file() and not {"__pycache__", "node_modules", ".venv", "bin", "obj"}.intersection(path.parts)
            )
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            with self.subTest(path=relative):
                self.assertIsNone(OLD_BRAND.search(relative))
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                self.assertIsNone(OLD_BRAND.search(text))

    def test_product_facing_surfaces_use_current_brand(self) -> None:
        for relative in (
            "portal/visualizer.html", "portal/README.md", "portal/catalog.json", "portal/visualizer.js",
            "FBCBuilder-DEV-Guide.md", "FBC-Builder-HOWTO.md", "Start-FBCBuilder.cmd",
            "AGENTS.md", "AGENTSEXPLAINED.md", ".github/copilot-instructions.md",
            "tools/vscode-chat-bridge/extension.js", "tools/vscode-chat-bridge/package.json",
            "scripts/portal_visualizer.py", "scripts/check_prerequisites.py",
            "system-tools/Install-SystemTools.ps1", "scripts/Install-Prerequisites.ps1",
        ):
            with self.subTest(path=relative):
                self.assertIn("FBC Builder", (ROOT / relative).read_text(encoding="utf-8"))
        html = (ROOT / "portal" / "visualizer.html").read_text(encoding="utf-8")
        self.assertIn("<title>FBC Builder</title>", html)
        self.assertIn("<h1>FBC Builder</h1>", html)

    def test_editor_identity_commands_and_uri_match(self) -> None:
        package = json.loads((ROOT / "tools" / "vscode-chat-bridge" / "package.json").read_text(encoding="utf-8"))
        identity = f"{package['publisher']}.{package['name']}"
        self.assertEqual("fbcbuilder.scenario-chat", identity)
        self.assertEqual("FBC Builder Scenario Chat", package["displayName"])
        self.assertEqual("fbcbuilder.linkChat", package["contributes"]["commands"][0]["command"])
        backend = (ROOT / "scripts" / "portal_visualizer.py").read_text(encoding="utf-8")
        self.assertIn(f"vscode://{identity}/", backend)
        tasks = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
        self.assertTrue(any(task["label"] == "FBC Builder: Open Portal" for task in tasks))

    def test_entry_points_are_consolidated_not_copied(self) -> None:
        self.assertEqual({"Start-FBCBuilder.cmd"}, {path.name for path in ROOT.glob("Start-*Builder.cmd")})
        self.assertEqual({"FBC-Builder-HOWTO.md"}, {path.name for path in ROOT.glob("*-Builder-*.md")})
        self.assertTrue((ROOT / "FBCBuilder-DEV-Guide.md").is_file())
        launcher = (ROOT / "Start-FBCBuilder.cmd").read_text(encoding="utf-8")
        self.assertIn("start_portal.py", launcher)
        self.assertNotIn('call "%~dp0Start-FBCBuilder.cmd"', launcher)

    def test_rebranded_document_and_screenshot_links_resolve(self) -> None:
        for relative in (
            "FBCBuilder-DEV-Guide.md", "FBC-Builder-HOWTO.md", "portal/README.md",
            "AGENTSEXPLAINED.md", "PREREQUISITES.md", "system-tools/README.md",
        ):
            path = ROOT / relative
            text = path.read_text(encoding="utf-8")
            targets = re.findall(
                r"(?:\.\./)?(?:FBCBuilder-DEV-Guide|FBC-Builder-HOWTO)\.md|docs/images/fbc-builder/[\w.-]+",
                text,
            )
            for target in targets:
                with self.subTest(document=relative, target=target):
                    self.assertTrue((path.parent / target).is_file())
