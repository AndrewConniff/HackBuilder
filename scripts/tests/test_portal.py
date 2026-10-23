"""Test intake, authenticated HTTP operations and actual local job persistence."""

from __future__ import annotations

import http.client
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("portal_server", SCRIPTS / "portal_server.py")
assert SPEC is not None and SPEC.loader is not None
portal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(portal)
hack_workflow = portal.hack_workflow


class ProcessAliveTests(unittest.TestCase):
    def test_missing_pid_is_not_alive(self) -> None:
        self.assertFalse(portal.process_alive(None))
        self.assertFalse(portal.process_alive(0))

    def test_current_process_is_alive(self) -> None:
        self.assertTrue(portal.process_alive(os.getpid()))

    def test_running_child_is_not_terminated_by_probe(self) -> None:
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            self.assertTrue(portal.process_alive(process.pid))
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            process.wait(timeout=5)
        self.assertFalse(portal.process_alive(process.pid))

    @unittest.skipUnless(os.name == "nt", "Windows process API")
    def test_windows_process_handle_is_closed(self) -> None:
        with patch.object(portal.ctypes, "WinDLL") as load, patch.object(portal.os, "kill") as kill:
            kernel = load.return_value
            kernel.OpenProcess.return_value = 123
            for status, expected in ((258, True), (0, False)):
                with self.subTest(status=status):
                    kernel.WaitForSingleObject.return_value = status
                    self.assertEqual(expected, portal.process_alive(42))
            self.assertEqual(2, kernel.CloseHandle.call_count)
            kernel.CloseHandle.assert_called_with(123)
            kill.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows process API")
    def test_windows_missing_and_inaccessible_processes(self) -> None:
        with patch.object(portal.ctypes, "WinDLL") as load, patch.object(portal.ctypes, "get_last_error") as error:
            kernel = load.return_value
            kernel.OpenProcess.return_value = None
            for code, expected in ((87, False), (5, True)):
                with self.subTest(code=code):
                    error.return_value = code
                    self.assertEqual(expected, portal.process_alive(42))
            error.return_value = 6
            with self.assertRaises(OSError):
                portal.process_alive(42)
            kernel.WaitForSingleObject.assert_not_called()
            kernel.CloseHandle.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows process API")
    def test_windows_wait_failure_closes_handle_and_surfaces_error(self) -> None:
        with patch.object(portal.ctypes, "WinDLL") as load, patch.object(portal.ctypes, "get_last_error", return_value=6):
            kernel = load.return_value
            kernel.OpenProcess.return_value = 123
            kernel.WaitForSingleObject.return_value = 0xFFFFFFFF
            with self.assertRaises(OSError):
                portal.process_alive(42)
            kernel.CloseHandle.assert_called_once_with(123)


class IntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = portal.load_catalog()
        self.data = {
            "projectSlug": "finance-agent",
            "prompt": "Assist with synthetic portfolio risk.",
            "industry": "Financial Services",
            "services": ["cosmos-db"],
            "domains": ["high-availability"],
            "pillars": ["security"],
        }

    def test_resource_first_generates_concrete_scoped_input(self) -> None:
        self.data["prompt"] = ""
        result = portal.normalize_request(self.data, self.catalog)
        self.assertEqual(["foundry", "cosmos-db"], result["services"])
        self.assertEqual(["security", "reliability"], result["pillars"])
        self.assertFalse(result["deploymentAuthorized"])
        text = portal.scenario_prompt(result, self.catalog)
        self.assertIn("Propose a viable industry business story", text)
        self.assertIn("Azure Cosmos DB", text)
        self.assertIn("Azure deployment is NOT authorized", text)
        self.assertIn("Never approve the scenario yourself", text)
        self.assertIn("Do not request account, subscription, quota or budget confirmation", text)
        self.assertIn("design decision", text)
        self.assertEqual("delegate-supported-provisional-choice", result["preferences"]["regionModel"])

    def test_industry_catalog_matches_csv_and_single_selection(self) -> None:
        self.assertEqual(11, len(self.catalog["industries"]))
        for invalid in ("Unknown", ["Financial Services", "Government"], None):
            with self.subTest(industry=invalid), self.assertRaises(ValueError):
                portal.normalize_request({**self.data, "industry": invalid}, self.catalog)

    def test_business_unit_scope_accepts_multiple_units_and_generic_default(self) -> None:
        self.assertEqual(12, len(self.catalog["businessUnits"]))
        self.assertEqual(["generic"], portal.normalize_request(self.data, self.catalog)["businessUnits"])
        result = portal.normalize_request({**self.data, "businessUnits": ["it", "legal"]}, self.catalog)
        self.assertEqual(["it", "legal"], result["businessUnits"])
        self.assertIn("Business units: IT, Legal", portal.scenario_prompt(result, self.catalog))
        self.assertIn("synthetic data", portal.scenario_prompt(result, self.catalog))
        for invalid in ([], ["generic", "it"], ["it", "it"], ["invented"], "finance", None, [{}]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                portal.normalize_request({**self.data, "businessUnits": invalid}, self.catalog)

    def test_invalid_catalog_relationships_and_duplicates_fail(self) -> None:
        variants = [
            {**self.catalog, "schemaVersion": 2},
            {**self.catalog, "services": self.catalog["services"] * 2},
            {**self.catalog, "services": [item for item in self.catalog["services"] if item["id"] != "foundry"]},
            {**self.catalog, "domains": [{"id": "test-domain", "pillar": "nonexistent"}]},
        ]
        for catalog in variants:
            with (
                self.subTest(catalog=catalog),
                tempfile.TemporaryDirectory() as temp,
                patch.object(portal, "ASSETS", Path(temp)),
            ):
                (Path(temp) / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
                with self.assertRaises(ValueError):
                    portal.load_catalog()

    def test_invalid_service_domain_and_pillar_ids_fail(self) -> None:
        for field in ("services", "domains", "pillars"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                portal.normalize_request({**self.data, field: ["invented"]}, self.catalog)

    def test_malformed_selections_fail(self) -> None:
        for value in ("cosmos-db", None, ["cosmos-db", "cosmos-db"], [{}]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                portal.normalize_request({**self.data, "services": value}, self.catalog)

    def test_slug_does_not_allow_paths_or_shell(self) -> None:
        for slug in ("..\\other", "../other", "finance;echo", "Finance", "a" * 41, ""):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                portal.normalize_request({**self.data, "projectSlug": slug}, self.catalog)

    def test_empty_intake_and_oversized_prompt_fail(self) -> None:
        for values in ({"prompt": "", "services": []}, {"prompt": "x" * 6001}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                portal.normalize_request({**self.data, **values}, self.catalog)

    def test_cli_uses_arguments_not_shell_concatenation(self) -> None:
        prompt = 'Risk input"; echo unsafe'
        command = portal.cli_command("copilot.exe", "az-01-conductor", prompt)
        self.assertIn(prompt, command)
        self.assertEqual(prompt, command[command.index("--prompt") + 1])
        self.assertNotIn("--allow-all-paths", command)
        self.assertNotIn("--model", command)
        self.assertEqual(str(portal.ROOT.parent / "azd-projects"), command[command.index("--add-dir") + 1])


class HttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.server = portal.make_server(Path(self.temp.name) / "runs", "test-token", 0, sys.executable)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.cleanup)
        self.data = {
            "projectSlug": "test-agent",
            "prompt": "A retail assistant",
            "industry": "Retail & Consumer Goods",
            "services": ["foundry"],
            "toolConsent": True,
        }

    def cleanup(self) -> None:
        self.server.app.shutdown()
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=5)
        self.temp.cleanup()

    def call(
        self, method: str, path: str, data: object = None, token: str = "test-token", headers: dict | None = None
    ) -> tuple[int, object]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        request_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        request_headers.update(headers or {})
        body = json.dumps(data) if data is not None else None
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        payload = response.read()
        result = json.loads(payload) if "application/json" in response.getheader("Content-Type", "") else payload
        status = response.status
        connection.close()
        return status, result

    def test_public_assets_but_authenticated_api(self) -> None:
        self.assertEqual(200, self.call("GET", "/")[0])
        self.assertEqual(403, self.call("GET", "/api/catalog", token="wrong")[0])
        status, data = self.call("GET", "/api/catalog")
        self.assertEqual(200, status)
        self.assertEqual(5, len(data["pillars"]))

    def test_host_and_cross_origin_are_rejected(self) -> None:
        for headers in ({"Host": "attacker.invalid"}, {"Origin": "https://attacker.invalid"}):
            with self.subTest(headers=headers):
                self.assertEqual(403, self.call("POST", "/api/preview", self.data, headers=headers)[0])

    def test_preview_has_no_execution_side_effect(self) -> None:
        status, data = self.call("POST", "/api/preview", self.data)
        self.assertEqual(200, status)
        self.assertEqual("scenario", data["request"]["phase"])
        self.assertFalse(data["request"]["scenarioApproved"])
        self.assertEqual({}, self.server.app.workers)
        self.assertEqual([], list(self.server.app.state.glob("*/run.json")))

    def test_catalog_and_adaptation_preview_do_not_clone_or_start_work(self) -> None:
        root = Path(self.temp.name) / "repository"
        source = root / "generated-scenarios" / "source-finance"
        (source / "infra").mkdir(parents=True)
        (source / "src").mkdir()
        manifest = portal.scenario_catalog.refresh(source)
        with patch.object(portal, "ROOT", root):
            status, data = self.call("GET", "/api/scenarios")
            self.assertEqual(200, status)
            self.assertTrue(data["scenarios"][0]["available"])
            status, data = self.call("POST", "/api/preview", {
                **self.data, "reuseScenarioId": source.name,
                "reuseManifestDigest": portal.scenario_catalog.digest(manifest),
                "businessUnits": ["operations"],
            })
            self.assertEqual(200, status)
            self.assertEqual(["operations"], data["request"]["businessUnits"])
            self.assertFalse(data["request"]["scenarioApproved"])
            self.assertIn("Never copy .azure", data["prompt"])
            self.assertIn("Do not bulk-copy", data["prompt"])
            self.assertEqual(source.name, data["request"]["reuseSource"]["scenarioId"])
            self.assertFalse((source.parent / self.data["projectSlug"]).exists())
            self.assertEqual(403, self.call("GET", "/api/scenarios", token="wrong")[0])
            invalid = {
                **self.data, "reuseScenarioId": source.name, "reuseManifestDigest": "0" * 64,
            }
            self.assertEqual(400, self.call("POST", "/api/runs", invalid)[0])
            valid = {**invalid, "reuseManifestDigest": portal.scenario_catalog.digest(manifest)}
            self.server.app.projects.claim({"projectSlug": source.name}, "source-writer", create=True)
            status, error = self.call("POST", "/api/preview", valid)
            self.assertEqual(400, status)
            self.assertIn("active writer", error["error"])
            self.server.app.projects.finish(source.name, "source-writer", "cancelled")
            (source.parent / self.data["projectSlug"]).mkdir()
            status, error = self.call("POST", "/api/preview", valid)
            self.assertEqual(400, status)
            self.assertIn("already exists", error["error"])
        self.assertEqual({}, self.server.app.workers)

    def test_launch_requires_explicit_consent(self) -> None:
        for consent in (False, None, "true"):
            with self.subTest(consent=consent):
                self.assertEqual(400, self.call("POST", "/api/runs", {**self.data, "toolConsent": consent})[0])

    def create_run(self, kind: str = "scenario") -> dict:
        request = portal.normalize_request(self.data, self.server.app.catalog)
        with patch.object(self.server.app, "execute"):
            run = self.server.app.start(request, "test", kind)
        self.server.app.workers.clear()
        run["status"] = "completed"
        self.server.app.save(run)
        self.server.app.projects.finish(request["projectSlug"], run["id"], "completed")
        return run

    def test_read_running_job_probes_live_server_without_error(self) -> None:
        with patch.object(self.server.app, "execute"):
            run = self.server.app.start(
                portal.normalize_request(self.data, self.server.app.catalog), "test", "scenario"
            )
        try:
            status, body = self.call("GET", f"/api/runs/{run['id']}")
            self.assertEqual(200, status)
            self.assertEqual("running", body["status"])
            self.assertFalse(body["orphaned"])
        finally:
            self.server.app.workers.clear()

    def test_launch_writes_durable_request_and_rejects_duplicate_projects(self) -> None:
        with patch.object(self.server.app, "execute"):
            status, run = self.call("POST", "/api/runs", self.data)
            self.assertEqual(202, status)
            self.assertEqual("az-01-conductor", run["agent"])
            self.assertTrue((self.server.app.state / run["id"] / "input.txt").exists())
            self.assertEqual(409, self.call("POST", "/api/runs", self.data)[0])
        self.server.app.workers.clear()

    def wait_for(self, condition: Callable[[], bool], message: str) -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.05)
        self.fail(message)

    def test_four_real_workers_have_isolated_progress_logs_stop_and_completion(self) -> None:
        script = (
            "import os, sys, time; from pathlib import Path; "
            f"sys.path.insert(0, {str(SCRIPTS)!r}); "
            "from portal_workflow import Store; "
            "state=Path(os.environ['ABCBUILDER_PROJECT_STATE']); "
            "slug=os.environ['ABCBUILDER_PROJECT']; owner=os.environ['ABCBUILDER_RUN_ID']; "
            "s=Store(state); p=s.read(slug); "
            "s.report(slug,owner,p['revision'],dict(stage='requirements',status='completed',"
            "summary='Synthetic worker '+slug,evidence=['Test subprocess report '+slug])); "
            "print('worker='+slug, flush=True); folder=state.parent/owner; "
            "(folder/'ready').write_text(slug); "
            "exec(\"while not (folder/'release').exists(): time.sleep(0.025)\"); "
            "print('finished='+slug, flush=True)"
        )
        with patch.object(portal, "cli_command", return_value=[sys.executable, "-c", script]):
            runs = []
            try:
                for number in range(4):
                    status, run = self.call("POST", "/api/runs", {
                        **self.data, "projectSlug": f"parallel-{number}",
                    })
                    self.assertEqual(202, status, run)
                    runs.append(run)
                self.wait_for(
                    lambda: all((self.server.app.state / run["id"] / "ready").is_file() for run in runs),
                    "The four real subprocesses did not run concurrently.",
                )
                pids = {run["id"]: self.server.app.workers[run["id"]].process.pid for run in runs}
                self.assertEqual(4, len(set(pids.values())))
                for run in runs:
                    _, value = self.call("GET", f"/api/runs/{run['id']}")
                    self.assertEqual("running", value["status"])
                    self.assertEqual(
                        "Synthetic worker " + run["request"]["projectSlug"],
                        value["project"]["stages"]["requirements"]["summary"],
                    )
                    self.assertIn("worker=" + run["request"]["projectSlug"], value["output"])
                status, error = self.call("POST", "/api/runs", {**self.data, "projectSlug": "parallel-extra"})
                self.assertEqual(400, status)
                self.assertIn("All 4", error["error"])
                self.assertFalse(self.server.app.projects.path("parallel-extra").exists())
                other_portal = portal.Portal(self.server.app.state, "another-token", sys.executable)
                with self.assertRaisesRegex(ValueError, "All 4"):
                    other_portal.require_capacity()

                first, second = runs[:2]
                (self.server.app.state / first["id"] / "release").write_text("release", encoding="utf-8")
                self.wait_for(lambda: first["id"] not in self.server.app.workers, "First worker did not finish.")
                self.assertEqual("completed", self.server.app.read(first["id"])["status"])
                self.assertEqual(3, len(self.server.app.workers))
                self.assertTrue(all(portal.process_alive(pids[run["id"]]) for run in runs[1:]))
                self.assertIsNone(self.server.app.projects.read("parallel-0")["writer"])

                status, extra = self.call("POST", "/api/runs", {**self.data, "projectSlug": "parallel-extra"})
                self.assertEqual(202, status)
                runs.append(extra)
                self.wait_for(
                    lambda: (self.server.app.state / extra["id"] / "ready").is_file(),
                    "A freed worker slot was not reusable.",
                )
                status, stopped = self.call("POST", f"/api/runs/{second['id']}/stop", {})
                self.assertEqual(200, status)
                self.assertEqual("cancelled", stopped["status"])
                self.wait_for(lambda: second["id"] not in self.server.app.workers, "Stopped worker did not release.")
                self.assertFalse(portal.process_alive(pids[second["id"]]))
                self.assertTrue(all(portal.process_alive(pids[run["id"]]) for run in runs[2:4]))
                self.assertEqual(extra["id"], self.server.app.projects.read("parallel-extra")["writer"])
                self.assertEqual([], self.server.app.projects.read("parallel-extra")["authorizations"])
            finally:
                self.server.app.shutdown()
            self.assertEqual({}, self.server.app.workers)
            with self.assertRaisesRegex(ValueError, "shutting down"):
                self.server.app.require_capacity()
            for run in runs:
                self.assertIsNone(self.server.app.projects.read(run["request"]["projectSlug"])["writer"])

    def test_another_scenario_can_resume_without_releasing_the_running_projects_writer(self) -> None:
        previous = self.create_run()
        with patch.object(self.server.app, "execute"):
            _, other = self.call("POST", "/api/runs", {**self.data, "projectSlug": "other-scenario"})
            status, resumed = self.call("POST", f"/api/runs/{previous['id']}/continue", {
                "toolConsent": True, "message": "Resume just this scenario",
                "revision": self.server.app.projects.read("test-agent")["revision"],
            })
            self.assertEqual(202, status, resumed)
            self.assertEqual(2, len(self.server.app.workers))
            self.assertEqual(other["id"], self.server.app.projects.read("other-scenario")["writer"])
            self.assertEqual(resumed["id"], self.server.app.projects.read("test-agent")["writer"])
            before = self.server.app.projects.path("test-agent").read_bytes()
            status, _ = self.call("POST", f"/api/runs/{resumed['id']}/continue", {
                "toolConsent": True, "message": "Do not overlap this writer", "revision": 999,
            })
            self.assertEqual(400, status)
            self.assertEqual(before, self.server.app.projects.path("test-agent").read_bytes())

    def test_stop_before_process_launch_never_spawns_a_cli(self) -> None:
        with patch.object(portal.threading.Thread, "start"):
            with self.server.app.lock:
                run = self.server.app.start(
                    portal.normalize_request(self.data, self.server.app.catalog), "test", "scenario",
                )
        cancelled = self.server.app.cancel(run["id"])
        self.assertEqual("cancelled", cancelled["status"])
        with patch.object(portal.subprocess, "Popen") as spawn:
            self.server.app.execute(run, "test")
        spawn.assert_not_called()
        self.assertEqual({}, self.server.app.workers)
        self.assertIsNone(self.server.app.projects.read("test-agent")["writer"])

    def test_thread_start_failure_releases_its_slot_and_project_lease(self) -> None:
        with (
            patch.object(portal.threading.Thread, "start", side_effect=RuntimeError("thread unavailable")),
            self.server.app.lock,
            self.assertRaisesRegex(OSError, "worker thread"),
        ):
            self.server.app.start(
                portal.normalize_request(self.data, self.server.app.catalog), "test", "scenario",
            )
        self.assertEqual({}, self.server.app.workers)
        self.assertIsNone(self.server.app.projects.read("test-agent")["writer"])
        self.assertEqual("failed", self.server.app.runs()[0]["status"])

    def test_run_list_keeps_each_scenario_and_all_active_jobs_beyond_recent_fifty_attempts(self) -> None:
        old = {
            "id": "a" * 32, "request": {"projectSlug": "older-project"},
            "startedAtUtc": "2020-01-01T00:00:00Z", "status": "completed",
        }
        active = {**old, "id": "b" * 32, "request": {"projectSlug": "busy-project"}, "status": "running"}
        self.server.app.save(old)
        self.server.app.save(active)
        for number in range(51):
            self.server.app.save({
                **old, "id": f"{number:032x}", "request": {"projectSlug": "busy-project"},
                "startedAtUtc": f"2026-10-22T00:00:{number:02}Z",
            })
        status, runs = self.call("GET", "/api/runs")
        self.assertEqual(200, status)
        self.assertIn(old["id"], {run["id"] for run in runs})
        self.assertIn(active["id"], {run["id"] for run in runs})

    def test_missing_review_cannot_launch_composition(self) -> None:
        run = self.create_run()
        status, body = self.call(
            "POST",
            f"/api/runs/{run['id']}/compose",
            {
                "toolConsent": True,
                "message": "Approved",
                "functionalityTested": True,
                "fingerprint": "invented",
                "revision": self.server.app.projects.read("test-agent")["revision"],
            },
        )
        self.assertEqual(400, status)
        self.assertIn("evidence", body["error"])

    def reviewed_reference(self) -> Path:
        root = Path(self.temp.name) / "scenario"
        for name in hack_workflow.REQUIRED_FILES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test artifact", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "App.csproj").write_text("<Project/>", encoding="utf-8")
        (root / "scenario-validation.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "checkedAtUtc": "2026-10-22T16:00:00Z",
                    "applicationUrl": "https://example.invalid",
                    "checks": dict.fromkeys(hack_workflow.REQUIRED_CHECKS, True),
                }
            ),
            encoding="utf-8",
        )
        hack_workflow.snapshot(root)
        return root

    def test_approval_requires_test_attestation_and_matching_fingerprint(self) -> None:
        run = self.create_run()
        root = self.reviewed_reference()
        fingerprint = hack_workflow.current_review(root)["referenceFingerprint"]
        with patch.object(self.server.app, "scenario", return_value=root):
            for values in (
                {"functionalityTested": False, "fingerprint": fingerprint},
                {"functionalityTested": True, "fingerprint": "stale"},
            ):
                status, _ = self.call(
                    "POST", f"/api/runs/{run['id']}/compose", {
                        "toolConsent": True, "message": "Approved",
                        "revision": self.server.app.projects.read("test-agent")["revision"], **values,
                    }
                )
                self.assertEqual(400, status)
            with patch.object(self.server.app, "execute"):
                status, job = self.call(
                    "POST",
                    f"/api/runs/{run['id']}/compose",
                    {
                        "toolConsent": True,
                        "message": "I tested and approve this scenario.",
                        "functionalityTested": True,
                        "fingerprint": fingerprint,
                        "revision": self.server.app.projects.read("test-agent")["revision"],
                    },
                )
                self.assertEqual(202, status)
                self.assertEqual("HackCreator Agent", job["agent"])
                hack_workflow.check_approval(root)
        self.server.app.workers.clear()

    def test_failed_composition_preparation_releases_writer_without_starting_worker(self) -> None:
        run = self.create_run()
        root = self.reviewed_reference()
        fingerprint = hack_workflow.current_review(root)["referenceFingerprint"]
        with (
            patch.object(self.server.app, "scenario", return_value=root),
            patch.object(hack_workflow, "record_decision", side_effect=ValueError("Reference changed")),
            patch.object(self.server.app, "execute") as execute,
        ):
            status, value = self.call("POST", f"/api/runs/{run['id']}/compose", {
                "toolConsent": True, "message": "I tested and approve",
                "functionalityTested": True, "fingerprint": fingerprint,
                "revision": self.server.app.projects.read("test-agent")["revision"],
            })
        self.assertEqual(400, status)
        self.assertIn("Reference changed", value["error"])
        self.assertIsNone(self.server.app.projects.read("test-agent")["writer"])
        execute.assert_not_called()

    def test_historical_review_retains_attestation_without_live_endpoint_or_passed_checks(self) -> None:
        run = self.create_run()
        root = self.reviewed_reference()
        (root / "scenario-validation.json").unlink()
        hack_workflow.attest_history(
            root, "The entire scenario was deployed and worked; resources were deleted.",
            "One-off lab subscription inaccessible; URL and logs unavailable.",
        )
        hack_workflow.snapshot(root)
        with patch.object(self.server.app, "scenario", return_value=root):
            status, result = self.call("GET", f"/api/runs/{run['id']}")
            self.assertEqual(200, status)
            review = result["review"]
            self.assertTrue(review["ready"])
            self.assertEqual("historical-user-attestation", review["evidenceType"])
            self.assertIsNone(review["applicationUrl"])
            self.assertEqual({}, review["checks"])
            self.assertEqual("explicit-user-statement", review["attestation"]["source"])
            with patch.object(self.server.app, "execute"):
                status, job = self.call("POST", f"/api/runs/{run['id']}/compose", {
                    "toolConsent": True, "message": "I approve this historically tested reference.",
                    "functionalityTested": True, "fingerprint": review["fingerprint"],
                    "revision": self.server.app.projects.read("test-agent")["revision"],
                })
            self.assertEqual(202, status, job)
            self.assertEqual("HackCreator Agent", job["agent"])
            hack_workflow.check_approval(root)
        self.server.app.workers.clear()

    def test_actual_subprocess_output_persists_without_claiming_validation(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import os; print('local-executor-ok'); print('portal-job=' + os.environ['HACKBUILDER_PORTAL_JOB'])",
        ]
        with patch.object(portal, "cli_command", return_value=command):
            status, run = self.call("POST", "/api/runs", self.data)
            self.assertEqual(202, status)
            deadline = time.monotonic() + 10
            while self.server.app.workers and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual({}, self.server.app.workers)
        status, result = self.call("GET", f"/api/runs/{run['id']}")
        self.assertEqual(200, status)
        self.assertEqual("completed", result["status"])
        self.assertEqual(0, result["exitCode"])
        self.assertIn("local-executor-ok", result["output"])
        self.assertIn("portal-job=1", result["output"])
        self.assertFalse(result["review"]["ready"])
        restarted = portal.Portal(self.server.app.state, "new-token", sys.executable)
        self.assertEqual("completed", restarted.read(run["id"])["status"])

    def test_worker_reports_decision_then_portal_resumes_with_durable_history(self) -> None:
        script = (
            "import os, sys; "
            f"sys.path.insert(0, {str(SCRIPTS)!r}); "
            "from pathlib import Path; from portal_workflow import Store; "
            "s=Store(Path(os.environ['HACKBUILDER_PROJECT_STATE'])); "
            "slug=os.environ['HACKBUILDER_PROJECT']; owner=os.environ['HACKBUILDER_RUN_ID']; "
            "p=s.read(slug); "
            "p=s.report(slug,owner,p['revision'],dict(stage='requirements',status='completed',"
            "summary='Brokerage requirements recorded',evidence=['01-requirements.md'])); "
            "s.report(slug,owner,p['revision'],dict(stage='architecture',status='waiting_for_user',"
            "summary='Private backend and anonymous public chat',evidence=['02-architecture-assessment.md'],"
            "decision=dict(kind='design',question='Confirm design?',reason='Review security boundaries',"
            "choices=['Confirm','Revise'],acceptChoice='Confirm')))"
        )
        with patch.object(portal, "cli_command", return_value=[sys.executable, "-c", script]):
            _, run = self.call("POST", "/api/runs", self.data)
            deadline = time.monotonic() + 10
            while self.server.app.workers and time.monotonic() < deadline:
                time.sleep(0.05)
        self.assertEqual({}, self.server.app.workers)
        _, result = self.call("GET", f"/api/runs/{run['id']}")
        project = result["project"]
        self.assertEqual("waiting_for_user", project["status"])
        self.assertEqual("completed", result["status"])
        with patch.object(self.server.app, "execute"):
            status, next_run = self.call("POST", f"/api/runs/{run['id']}/continue", {
                "toolConsent": True, "revision": project["revision"], "message": "Keep chat anonymous",
                "decisionId": project["decisions"][0]["id"], "choice": "Confirm",
            })
        self.assertEqual(202, status, next_run)
        current = self.server.app.projects.read("test-agent")
        self.assertTrue(current["designConfirmed"])
        self.assertEqual("Keep chat anonymous", current["history"][0]["message"])
        self.assertEqual([], current["authorizations"])
        self.assertEqual("A retail assistant", current["request"]["prompt"])
        prompt = (self.server.app.state / next_run["id"] / "input.txt").read_text(encoding="utf-8")
        self.assertIn("ALL canonical decisions", prompt)
        self.assertIn("Free-text messages are not cloud authorization", prompt)
        self.server.app.workers.clear()

    def test_health_requires_authentication_and_identifies_workspace(self) -> None:
        status, health = self.call("GET", "/api/health")
        self.assertEqual(200, status)
        self.assertEqual({"status": "ok", "workspace": str(portal.ROOT)}, health)
        self.assertEqual(403, self.call("GET", "/api/health", headers={"Authorization": "Bearer invalid"})[0])

    def test_failed_process_is_not_success_shaped(self) -> None:
        with patch.object(portal, "cli_command", return_value=[sys.executable, "-c", "raise SystemExit(7)"]):
            _, run = self.call("POST", "/api/runs", self.data)
            deadline = time.monotonic() + 10
            while self.server.app.workers and time.monotonic() < deadline:
                time.sleep(0.05)
        result = self.server.app.read(run["id"])
        self.assertEqual("failed", result["status"])
        self.assertEqual(7, result["exitCode"])
        self.assertIn("failed", result["error"])

    def test_os_launch_failure_is_reported_and_releases_job(self) -> None:
        with (
            patch.object(portal.subprocess, "Popen", side_effect=OSError("test CLI missing")),
            self.assertLogs(portal.LOG, level="ERROR"),
        ):
            _, run = self.call("POST", "/api/runs", self.data)
            deadline = time.monotonic() + 10
            while self.server.app.workers and time.monotonic() < deadline:
                time.sleep(0.05)
        result = self.server.app.read(run["id"])
        self.assertEqual("failed", result["status"])
        self.assertIn("test CLI missing", result["error"])
        self.assertEqual({}, self.server.app.workers)

    def test_revision_revokes_approval_before_new_work(self) -> None:
        run = self.create_run()
        root = self.reviewed_reference()
        hack_workflow.record_decision(root, "Approved", "approved")
        with patch.object(self.server.app, "scenario", return_value=root), patch.object(self.server.app, "execute"):
            status, _ = self.call(
                "POST",
                f"/api/runs/{run['id']}/revise",
                {
                    "toolConsent": True,
                    "message": "Revise the scope before creating any hack.",
                    "revision": self.server.app.projects.read("test-agent")["revision"],
                },
            )
            self.assertEqual(202, status)
        self.server.app.workers.clear()
        with self.assertRaisesRegex(ValueError, "Explicit user approval"):
            hack_workflow.check_approval(root)

    def test_continuation_does_not_grant_scenario_approval(self) -> None:
        run = self.create_run()
        with patch.object(self.server.app, "execute"):
            status, next_run = self.call(
                "POST",
                f"/api/runs/{run['id']}/continue",
                {
                    "toolConsent": True,
                    "message": "Confirm the displayed reference deployment targets only.",
                    "revision": self.server.app.projects.read("test-agent")["revision"],
                },
            )
            self.assertEqual(202, status)
        self.server.app.workers.clear()
        prompt = (self.server.app.state / next_run["id"] / "input.txt").read_text(encoding="utf-8")
        self.assertIn("Do not infer scenario approval", prompt)
        self.assertEqual("scenario", next_run["kind"])
        self.assertEqual(run["id"], next_run["parentId"])

    def test_missing_cli_and_wrong_content_type_fail_explicitly(self) -> None:
        self.server.app.executable = None
        self.assertEqual(400, self.call("POST", "/api/runs", self.data)[0])
        self.assertEqual(400, self.call("POST", "/api/preview", self.data, headers={"Content-Type": "text/plain"})[0])

    def test_interrupted_job_is_visible_after_restart(self) -> None:
        run = self.create_run()
        run["status"] = "running"
        self.server.app.save(run)
        with patch.object(portal, "process_alive", return_value=False):
            restarted = portal.Portal(self.server.app.state, "new-token", sys.executable)
        self.assertEqual("interrupted", restarted.read(run["id"])["status"])
        self.assertIsNone(restarted.projects.read("test-agent")["writer"])

    def test_status_refresh_is_read_only_and_returns_project_not_exit_success(self) -> None:
        run = self.create_run()
        project = self.server.app.projects.read("test-agent")
        with patch.object(self.server.app, "start") as start:
            status, value = self.call("GET", f"/api/runs/{run['id']}")
            self.assertEqual(200, status)
            self.assertEqual("needs_attention", value["project"]["status"])
            self.assertEqual(project["revision"], value["project"]["revision"])
            self.call("GET", "/api/runs")
            start.assert_not_called()

    def test_refresh_reads_external_package_receipt_without_mutating_project(self) -> None:
        run = self.create_run()
        root = self.reviewed_reference()
        hack_workflow.record_decision(root, "Approved for composition", "approved")
        for name in ("coach", "participant", "hack", "coach-guide", "validation"):
            (root / "packages" / name).mkdir(parents=True)
            (root / "packages" / name / "README.md").write_text("package", encoding="utf-8")
        for name in ("08-hack-package-contract.md", "nextsteps.MD", "09-hack-event-manifest.json"):
            (root / name).write_text("package metadata", encoding="utf-8")
        (root / "packages" / "validation" / "local-checks.json").write_text(json.dumps({
            "allCommandsPassed": True,
            "checks": [{"name": name, "exitCode": 0} for name in hack_workflow.PACKAGE_CHECKS],
        }), encoding="utf-8")
        hack_workflow.record_packages(root)
        project_path = self.server.app.projects.path("test-agent")
        original = project_path.read_bytes()
        with patch.object(self.server.app, "scenario", return_value=root), patch.object(self.server.app, "start") as start:
            status, result = self.call("GET", f"/api/runs/{run['id']}")
            self.assertEqual(200, status)
            self.assertEqual("packages_validated", result["composition"]["status"])
            self.assertFalse(result["composition"]["eventDeployed"])
            self.assertEqual(original, project_path.read_bytes())
            (root / "packages" / "hack" / "README.md").write_text("edited", encoding="utf-8")
            _, stale = self.call("GET", f"/api/runs/{run['id']}")
            self.assertEqual("stale", stale["composition"]["status"])
            start.assert_not_called()

    def test_package_artifact_preview_download_and_path_boundaries(self) -> None:
        run = self.create_run()
        root = Path(self.temp.name) / "artifacts"
        public = root / "packages" / "hack" / "Instructions"
        private = root / "packages" / "coach-guide"
        releases = root / "packages" / "validation" / "release"
        for folder in (public, private, releases):
            folder.mkdir(parents=True)
        (public / "01-challenge.md").write_text("# Challenge\nBuild the agent.", encoding="utf-8")
        (private / "Finale.md").write_text("Private solution", encoding="utf-8")
        (releases / "hack.zip").write_bytes(b"zip-fixture")
        (root / "secret.txt").write_text("not served", encoding="utf-8")
        with patch.object(self.server.app, "scenario", return_value=root):
            _, result = self.call("GET", f"/api/runs/{run['id']}")
            artifacts = result["artifacts"]
            self.assertEqual(3, len(artifacts))
            self.assertTrue(next(item for item in artifacts if item["path"].endswith("Finale.md"))["private"])
            status, document = self.call(
                "GET", f"/api/runs/{run['id']}/artifact?path=packages%2Fhack%2FInstructions%2F01-challenge.md",
            )
            self.assertEqual(200, status)
            self.assertEqual("# Challenge\nBuild the agent.", document["text"])
            status, archive = self.call(
                "GET", f"/api/runs/{run['id']}/artifact?path=packages%2Fvalidation%2Frelease%2Fhack.zip",
            )
            self.assertEqual(200, status)
            self.assertEqual(b"zip-fixture", archive)
            for value in ("..%2Fsecret.txt", "secret.txt", "packages%2Fcoach%2F.env", "C:%5Csecret"):
                self.assertEqual(400, self.call("GET", f"/api/runs/{run['id']}/artifact?path={value}")[0])
            self.assertEqual(403, self.call(
                "GET", f"/api/runs/{run['id']}/artifact?path=packages%2Fcoach-guide%2FFinale.md", token="wrong",
            )[0])

    def test_disk_scenarios_are_discovered_read_only_without_creating_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "generated-scenarios" / "legacy-hack"
            folder.mkdir(parents=True)
            (folder / "README.md").write_text("Existing reference", encoding="utf-8")
            with patch.object(portal, "ROOT", root):
                status, runs = self.call("GET", "/api/runs")
                self.assertEqual(200, status)
                run = next(item for item in runs if item["request"]["projectSlug"] == "legacy-hack")
                self.assertTrue(run["discovered"])
                status, preview = self.call("GET", f"/api/runs/{run['id']}")
                self.assertEqual(200, status)
                self.assertEqual(["README.md"], preview["localInventory"])
                self.assertIsNone(preview["project"])
                status, document = self.call("GET", f"/api/runs/{run['id']}/artifact?path=README.md")
                self.assertEqual(200, status)
                self.assertEqual("Existing reference", document["text"])
                self.assertEqual(400, self.call("POST", f"/api/runs/{run['id']}/continue", {
                    "toolConsent": True, "message": "Resume",
                })[0])
                self.assertEqual([], list(self.server.app.state.glob("*/run.json")))

    def test_stale_continuation_cannot_start_worker(self) -> None:
        run = self.create_run()
        with patch.object(self.server.app, "execute") as execute:
            status, value = self.call("POST", f"/api/runs/{run['id']}/continue", {
                "toolConsent": True, "message": "Resume", "revision": 0,
            })
            self.assertEqual(400, status)
            self.assertIn("Refresh", value["error"])
            execute.assert_not_called()

    def test_legacy_continuation_persists_current_answer_without_inventing_old_progress(self) -> None:
        run = self.create_run()
        self.server.app.projects.path("test-agent").unlink()
        with patch.object(self.server.app, "execute"):
            status, _ = self.call("POST", f"/api/runs/{run['id']}/continue", {
                "toolConsent": True, "message": "Keep customer chat anonymous",
            })
        self.assertEqual(202, status)
        project = self.server.app.projects.read("test-agent")
        self.assertEqual("Keep customer chat anonymous", project["history"][0]["message"])
        self.assertFalse(project["designConfirmed"])
        self.assertTrue(all(item["status"] == "pending" for item in project["stages"].values()))
        self.server.app.workers.clear()

    def test_duplicate_project_does_not_overwrite_intake(self) -> None:
        run = self.create_run()
        before = self.server.app.projects.path("test-agent").read_bytes()
        with patch.object(self.server.app, "execute") as execute:
            status, value = self.call("POST", "/api/runs", {**self.data, "prompt": "Replace story"})
        self.assertEqual(409, status)
        self.assertIn("already exists", value["error"])
        self.assertEqual("project_exists", value["code"])
        self.assertEqual(run["id"], value["project"]["runId"])
        self.assertEqual("test-agent", value["project"]["projectSlug"])
        execute.assert_not_called()
        self.assertEqual(before, self.server.app.projects.path("test-agent").read_bytes())
        self.assertEqual("A retail assistant", self.server.app.projects.read("test-agent")["request"]["prompt"])

    def test_project_names_include_saved_records_without_scenario_folders_or_runs(self) -> None:
        run = self.create_run()
        self.server.app.projects.claim({"projectSlug": "record-only"}, "external-owner", create=True)
        before = {
            path.name: path.read_bytes() for path in self.server.app.projects.directory.glob("*.json")
        }
        status, projects = self.call("GET", "/api/projects")
        self.assertEqual(200, status)
        self.assertEqual([
            {"projectSlug": "record-only", "status": "running", "runId": None, "hasWriter": True},
            {"projectSlug": "test-agent", "status": "needs_attention", "runId": run["id"], "hasWriter": False},
        ], projects)
        self.assertEqual(403, self.call("GET", "/api/projects", token="wrong")[0])
        self.assertEqual(before, {
            path.name: path.read_bytes() for path in self.server.app.projects.directory.glob("*.json")
        })
        self.assertEqual(1, len(list(self.server.app.state.glob("*/run.json"))))

    def test_record_only_duplicate_returns_recovery_metadata_without_creating_a_run(self) -> None:
        self.server.app.projects.claim(self.data, "external-owner", create=True)
        before = self.server.app.projects.path("test-agent").read_bytes()
        with patch.object(self.server.app, "execute") as execute:
            status, value = self.call("POST", "/api/runs", self.data)
        self.assertEqual(409, status)
        self.assertEqual("project_exists", value["code"])
        self.assertIsNone(value["project"]["runId"])
        execute.assert_not_called()
        self.assertEqual([], list(self.server.app.state.glob("*/run.json")))
        self.assertEqual(before, self.server.app.projects.path("test-agent").read_bytes())

    def test_live_server_writer_is_not_reclaimed_by_second_portal(self) -> None:
        with patch.object(self.server.app, "execute"):
            _, run = self.call("POST", "/api/runs", self.data)
        restarted = portal.Portal(self.server.app.state, "new-token", sys.executable)
        self.assertEqual("running", restarted.read(run["id"])["status"])
        with self.assertRaisesRegex(ValueError, "active writer"):
            restarted.start(run["request"], "competing work", "scenario", run["id"],
                            restarted.projects.read("test-agent")["revision"])
        self.server.app.workers.clear()

    def test_orphaned_live_child_retains_lease_until_explicit_recovery(self) -> None:
        with patch.object(self.server.app, "execute"):
            _, run = self.call("POST", "/api/runs", self.data)
        self.server.app.workers.clear()
        run["serverPid"] = 12345
        run["childPid"] = 54321
        self.server.app.save(run)
        with patch.object(portal, "process_alive", side_effect=lambda pid: pid == 54321):
            restarted = portal.Portal(self.server.app.state, "new-token", sys.executable)
            self.assertEqual("running", restarted.read(run["id"])["status"])
            self.assertTrue(restarted.public_run(run)["orphaned"])
            with self.assertRaisesRegex(ValueError, "unowned PID"):
                restarted.cancel(run["id"])
            self.assertEqual(run["id"], restarted.projects.read("test-agent")["writer"])
        with patch.object(portal, "process_alive", return_value=False):
            recovered = restarted.cancel(run["id"])
        self.assertEqual("cancelled", recovered["status"])
        self.assertIsNone(restarted.projects.read("test-agent")["writer"])

    def test_invalid_body_and_paths_return_explicit_errors(self) -> None:
        self.assertEqual(400, self.call("POST", "/api/preview", [1, 2])[0])
        self.assertEqual(400, self.call("GET", "/api/runs/..")[0])
        self.assertEqual(404, self.call("GET", "/catalog.json")[0])


if __name__ == "__main__":
    unittest.main()
