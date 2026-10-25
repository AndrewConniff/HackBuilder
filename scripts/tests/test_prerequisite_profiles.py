"""Verify shared dependency profiles and stage-specific diagnostic results."""

from __future__ import annotations

import itertools
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_prerequisites as checker
import prerequisite_profiles as profiles

ROOT = Path(__file__).resolve().parents[2]


def report_fixture(services: list[str], failed: str | None = None) -> dict:
    profile = profiles.plan(services)
    identifiers = sorted({tool for tools in profile["stages"].values() for tool in tools})
    return {
        "profileVersion": profiles.VERSION, "services": profile["services"], "buildMode": profile["buildMode"],
        "localFunctions": False, "plan": profile,
        "checks": [{"id": key, "name": key, "ok": key != failed, "detail": "Synthetic check"} for key in identifiers],
        "ready": failed is None,
    }


class ProfileTests(unittest.TestCase):
    def test_nuget_tls_is_listed_and_blocks_only_restore_validation(self) -> None:
        profile = profiles.plan(["foundry"])
        planned = next(item for item in checker.planned_checks(profile) if item["id"] == "nuget-https")
        self.assertEqual(["local-validation"], planned["stages"])
        self.assertEqual("not-checked", planned["state"])
        report = report_fixture(["foundry"], "nuget-https")
        for stage in ("requirements", "architecture", "application", "diagrams", "bicep"):
            self.assertEqual([], profiles.stage_failures(report, stage))
        self.assertEqual(["nuget-https"], [
            item["id"] for item in profiles.stage_failures(report, "local-validation")
        ])

    def test_every_catalog_service_has_a_profile_and_pairwise_selection_is_a_union(self) -> None:
        catalog = json.loads((ROOT / "portal" / "catalog.json").read_text(encoding="utf-8"))
        services = [item["id"] for item in catalog["services"]]
        self.assertEqual(set(services), set(profiles.SERVICE_REQUIREMENTS))
        for left, right in itertools.combinations(services, 2):
            combined = profiles.plan([left, right])
            for stage, tools in combined["stages"].items():
                expected = set(profiles.plan([left])["stages"][stage]) | set(
                    profiles.plan([right])["stages"][stage],
                )
                self.assertEqual(expected, set(tools), (left, right, stage))
                self.assertEqual(len(tools), len(set(tools)))

    def test_docker_is_for_local_image_operations_not_scaffolding(self) -> None:
        profile = profiles.plan(["container-apps"])
        for stage in ("requirements", "architecture", "diagrams", "bicep", "application"):
            self.assertNotIn("docker", profile["stages"][stage])
        self.assertIn("docker", profile["stages"]["local-validation"])
        self.assertIn("docker", profile["stages"]["deployment"])
        self.assertNotIn("docker", profiles.plan(["app-service"])["stages"]["local-validation"])
        self.assertNotIn("docker", profiles.plan(["container-apps"], "remote")["stages"]["local-validation"])
        self.assertIn("docker", profiles.plan(["app-service"], "local")["stages"]["local-validation"])

    def test_optional_functions_host_and_unknown_inputs_are_explicit(self) -> None:
        self.assertNotIn("functions-core-tools", profiles.plan(["functions"])["stages"]["local-validation"])
        self.assertIn("functions-core-tools", profiles.plan(
            ["functions"], local_functions=True,
        )["stages"]["local-validation"])
        for services in ([], ["unknown"], ["foundry", "foundry"], "foundry", [None]):
            with self.subTest(services=services), self.assertRaises(ValueError):
                profiles.plan(services)
        with self.assertRaises(ValueError):
            profiles.plan(["foundry"], local_functions=True)
        with self.assertRaises(ValueError):
            profiles.plan(["foundry"], "unknown")

    def test_missing_duplicate_and_nonboolean_results_never_pass(self) -> None:
        baseline = report_fixture(["container-apps"])
        missing = {**baseline, "checks": [item for item in baseline["checks"] if item["id"] != "graphviz"]}
        self.assertEqual(["graphviz"], [item["id"] for item in profiles.stage_failures(missing, "diagrams")])
        for checks in (
            baseline["checks"] + [baseline["checks"][0]],
            [{**item, "ok": "true"} for item in baseline["checks"]],
        ):
            with self.subTest(checks=checks), self.assertRaisesRegex(ValueError, "Invalid prerequisite"):
                profiles.stage_failures({**baseline, "checks": checks}, "diagrams")


if __name__ == "__main__":
    unittest.main()
