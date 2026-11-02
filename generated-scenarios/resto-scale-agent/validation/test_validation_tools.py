"""Validate local acceptance tooling without HTTP requests or cloud operations."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_arm", ROOT / "validation" / "audit_arm.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ValidationToolsTests(unittest.TestCase):
    def test_extracts_nested_arm_v2_and_dynamic_resource_properties(self):
        child = {"resources": [{"type": "Example/child", "properties": "[variables('configuration')]"}]}
        source = {"resources": {"nested": {"properties": {"template": child}}}}
        with tempfile.TemporaryDirectory(dir=ROOT / "evidence") as directory:
            output = Path(directory)
            self.assertEqual(2, AUDIT.extract(source, output))
            self.assertIsInstance(json.loads((output / "root.json").read_text())["resources"], list)
            self.assertEqual(child, json.loads((output / "root-0.json").read_text()))
        self.assertIsInstance(source["resources"], dict)

    def test_load_profiles_have_exact_rates_durations_and_thresholds(self):
        results = {}
        for profile, reads, writes, duration in (
            ("normal", 40, 10, "30m0s"), ("burst", 140, 10, "5m0s"), ("soak", 20, 5, "2h0m0s")
        ):
            with self.subTest(profile=profile):
                completed = subprocess.run(
                    ["k6", "inspect", "--env", f"PROFILE={profile}", str(ROOT / "validation" / "load.js")],
                    check=True, capture_output=True, text=True, timeout=30,
                )
                result = json.loads(completed.stdout)
                self.assertEqual(reads, result["scenarios"]["reads"]["rate"])
                self.assertEqual(writes, result["scenarios"]["writes"]["rate"])
                self.assertEqual(duration, result["scenarios"]["reads"]["duration"])
                self.assertEqual(duration, result["scenarios"]["writes"]["duration"])
                self.assertEqual("constant-arrival-rate", result["scenarios"]["reads"]["executor"])
                self.assertEqual(["p(95)<=500"], result["thresholds"]["read_latency"])
                self.assertEqual(["p(95)<=800"], result["thresholds"]["write_latency"])
                self.assertEqual(["rate<0.01"], result["thresholds"]["unexpected_responses"])
                self.assertEqual(["count==0"], result["thresholds"]["dropped_iterations"])
                results[profile] = {"scenarios": result["scenarios"], "thresholds": result["thresholds"]}
        (ROOT / "evidence" / "load-profiles-inspected-cc61b383.json").write_text(
            json.dumps({"scope": "static inspection only; no requests made", "profiles": results}, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
