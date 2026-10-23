"""Verify dependency unions, phase gates and run-bound prerequisite evidence."""

from __future__ import annotations

import contextlib
import io
import itertools
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_prerequisites as checker
import portal_workflow
import prerequisite_profiles as profiles

ROOT = Path(__file__).resolve().parents[2]


def report_fixture(services: list[str], failed: str | None = None) -> dict:
    profile = profiles.plan(services)
    identifiers = sorted({tool for tools in profile["stages"].values() for tool in tools})
    return {
        "profileVersion": profiles.VERSION, "services": profile["services"], "buildMode": profile["buildMode"],
        "localFunctions": False, "plan": profile, "projectSlug": "sample", "runId": "worker",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "checks": [{"id": key, "name": key, "ok": key != failed, "detail": "Synthetic check"} for key in identifiers],
        "ready": failed is None,
    }


class ProfileTests(unittest.TestCase):
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


class ReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "state" / "projects"
        self.receipt = self.directory / "preflight" / "sample.json"
        self.receipt.parent.mkdir(parents=True)
        self.project = {
            "projectSlug": "sample", "preflightRequired": True,
            "request": {"services": ["container-apps"]}, "authorizations": [],
        }

    def save(self, report: dict) -> None:
        self.receipt.write_text(json.dumps(report), encoding="utf-8")

    def test_early_work_needs_no_receipt_but_build_steps_do(self) -> None:
        for stage in ("requirements", "architecture"):
            profiles.require_stage(self.project, self.directory, "worker", stage)
        with self.assertRaisesRegex(ValueError, "preflight is required"):
            profiles.require_stage(self.project, self.directory, "worker", "diagrams")

    def test_all_failures_are_known_but_only_affected_steps_are_blocked(self) -> None:
        self.save(report_fixture(["container-apps"], "docker"))
        for stage in ("diagrams", "bicep", "application"):
            profiles.require_stage(self.project, self.directory, "worker", stage)
        with self.assertRaisesRegex(ValueError, "docker"):
            profiles.require_stage(self.project, self.directory, "worker", "local-validation")
        self.assertEqual([], self.project["authorizations"])

    def test_stale_wrong_owner_and_wrong_profile_receipts_are_rejected(self) -> None:
        baseline = report_fixture(["container-apps"])
        variants = [
            {"runId": "other"}, {"projectSlug": "other"}, {"profileVersion": 999},
            {"checkedAtUtc": (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()},
        ]
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.save({**baseline, **changed})
                profiles.require_stage(self.project, self.directory, "worker", "diagrams")

    def test_missing_duplicate_and_nonboolean_results_never_satisfy_a_gate(self) -> None:
        baseline = report_fixture(["container-apps"])
        variants = [
            [item for item in baseline["checks"] if item["id"] != "graphviz"],
            baseline["checks"] + [baseline["checks"][0]],
            [{**item, "ok": "true"} for item in baseline["checks"]],
        ]
        for checks in variants:
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                self.save({**baseline, "checks": checks})
                profiles.require_stage(self.project, self.directory, "worker", "diagrams")

    def test_manifest_changes_invalidate_scope_and_bad_manifests_are_not_ignored(self) -> None:
        self.save(report_fixture(["container-apps"]))
        manifest = self.root / "generated-scenarios" / "sample" / "scenario-manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"services": ["container-apps", "service-bus"]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "scope changed"):
            profiles.require_stage(self.project, self.directory, "worker", "diagrams")
        manifest.write_text(json.dumps({"services": ["unmapped-service"]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            profiles.require_stage(self.project, self.directory, "worker", "diagrams")


class WorkerAuditTests(unittest.TestCase):
    def test_worker_records_actual_report_and_returns_readiness_for_only_the_requested_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = portal_workflow.Store(root / "state" / "projects")
            project = store.claim(
                {"projectSlug": "sample", "services": ["container-apps"]}, "worker",
                create=True, local_tool_consent=True, preflight_required=True,
            )
            environment = {
                "ABCBUILDER_PROJECT_STATE": str(store.directory), "ABCBUILDER_PROJECT": "sample",
                "ABCBUILDER_RUN_ID": "worker",
            }
            for stage, expected_exit in (("requirements", 0), ("bicep", 0), ("local-validation", 1)):
                with (
                    self.subTest(stage=stage), patch.dict(os.environ, environment),
                    patch.object(checker, "ROOT", root),
                    patch.object(checker, "service_report", return_value=report_fixture(["container-apps"], "docker")),
                    patch.object(sys, "argv", [
                        "check_prerequisites.py", "--for-project", "--record", "--stage", stage, "--json",
                    ]),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(expected_exit, checker.main())
            receipt = json.loads((store.directory / "preflight" / "sample.json").read_text(encoding="utf-8"))
            self.assertEqual("worker", receipt["runId"])
            self.assertEqual(project, store.read("sample"))
            profiles.require_stage(project, store.directory, "worker", "bicep")
            with self.assertRaisesRegex(ValueError, "docker"):
                profiles.require_stage(project, store.directory, "worker", "local-validation")
