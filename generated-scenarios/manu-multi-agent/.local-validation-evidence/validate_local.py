"""Validate the production image offline without installing identities or weakening gateway authentication."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(__file__).resolve().parent
REPOSITORY = Path(r"C:\HackBuilder")
IMAGE = "abcbuilder-manu-multi-agent:platform-repair"
HELPER = REPOSITORY / "scripts" / "check_container_runtime.py"


def run(name: str, command: list[str], timeout: int = 240) -> dict:
    executable = shutil.which(command[0])
    if executable is None:
        raise FileNotFoundError(f"Required executable unavailable: {command[0]}")
    result = subprocess.run(
        [executable, *command[1:]], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, check=False,
    )
    log = EVIDENCE / f"{name}.log"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    return {
        "name": name, "command": subprocess.list2cmdline(command),
        "exitCode": result.returncode, "log": str(log.relative_to(ROOT)),
    }


def test_settings() -> dict[str, str]:
    # These values exercise syntax only. Network isolation prevents their use as cloud targets.
    tenant = "11111111-1111-4111-8111-111111111111"
    return {
        "Foundry__ProjectEndpoint": "https://offline-validation.services.ai.azure.com/api/projects/offline",
        "Foundry__ModelDeployment": "offline-not-a-deployed-model",
        "Foundry__SalesAgentName": "sales-fit", "Foundry__SalesAgentVersion": "1",
        "Foundry__MarketingAgentName": "marketing-claims", "Foundry__MarketingAgentVersion": "1",
        "Foundry__CoordinatorAgentName": "handoff-coordinator", "Foundry__CoordinatorAgentVersion": "1",
        "Fixtures__BlobEndpoint": "https://offlinevalidation.blob.core.windows.net/",
        "Fixtures__ContainerName": "synthetic-fixtures", "Fixtures__ManifestSha256": "a" * 64,
        "Signing__KeyUri": "https://offline-validation.vault.azure.net/keys/offline/123abc",
        "Signing__Algorithm": "PS256", "BackendAuth__TenantId": tenant,
        "BackendAuth__Audience": "22222222-2222-4222-8222-222222222222",
        "BackendAuth__GatewayObjectId": "33333333-3333-4333-8333-333333333333",
        "BackendAuth__Authority": f"https://login.microsoftonline.com/{tenant}/v2.0",
        "AZURE_CLIENT_ID": "44444444-4444-4444-8444-444444444444",
        "Limits__MaxInputCharacters": "4000", "Limits__MaxOutputTokens": "800",
        "Limits__MaxResponsesRequests": "7", "Limits__MaxCumulativeTokens": "30000",
        "Limits__DeadlineSeconds": "90", "Limits__MaxConcurrentHandoffs": "4",
    }


def configured_backend() -> dict:
    spec = importlib.util.spec_from_file_location("container_runtime", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Repository container helper could not be loaded.")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    container_name = f"abcbuilder-manu-validation-{uuid.uuid4().hex[:12]}"
    container_id = None
    report = {
        "ok": False, "checks": [], "logs": "", "error": None, "cleanupPassed": False,
        "configuration": "Explicit isolated test values, not installation outputs or runtime certification.",
    }
    try:
        environment = []
        for key, value in test_settings().items():
            environment.extend(["--env", f"{key}={value}"])
        container_id = helper.docker(
            "run", "--detach", "--pull=never", "--read-only", "--platform", "linux/amd64",
            "--network", "none", "--name", container_name,
            "--label", "abcbuilder.scenario=manu-multi-agent",
            *environment, IMAGE,
        )
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            raise RuntimeError(f"Invalid owned container ID: {container_id}")
        state = json.loads(helper.docker("inspect", container_id))[0]
        if (
            state["Config"]["User"] != "1654" or not state["HostConfig"]["ReadonlyRootfs"]
            or state["Mounts"] or state["HostConfig"]["NetworkMode"] != "none"
            or state["NetworkSettings"]["Ports"].get("8080/tcp")
        ):
            raise RuntimeError("Configured backend container isolation contract failed.")

        def get_protected(path: str) -> tuple[int, str]:
            if path not in ("/", "/app.js", "/app.css", "/api/opportunities", "/api/products", "/api/claims"):
                raise ValueError("Only explicit protected test routes are permitted.")
            response = helper.docker(
                "exec", container_id, "/bin/bash", "-c",
                "exec 3<>/dev/tcp/127.0.0.1/8080; "
                f"printf 'GET {path} HTTP/1.1\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' >&3; "
                "cat <&3",
            )

            class ResponseStream:
                def makefile(self, *_args: object) -> io.BytesIO:
                    return io.BytesIO(response.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))

            parsed = http.client.HTTPResponse(ResponseStream())
            parsed.begin()
            return parsed.status, parsed.read().decode("utf-8")

        deadline = time.monotonic() + 30
        while True:
            try:
                get_protected("/")
                break
            except (OSError, RuntimeError, http.client.HTTPException):
                if time.monotonic() >= deadline:
                    raise
                if not json.loads(helper.docker("inspect", container_id))[0]["State"]["Running"]:
                    raise RuntimeError("Configured backend exited before responding.") from None
                time.sleep(0.5)
        for path in ("/", "/app.js", "/app.css", "/api/opportunities", "/api/products", "/api/claims"):
            status, body = get_protected(path)
            payload = json.loads(body)
            if status != 401 or payload.get("code") != "authentication_required":
                raise RuntimeError(
                    f"{path}: expected explicit authentication-required 401; received {status}: {body}"
                )
            uuid.UUID(payload["correlationId"])
            if "Adventure Works Cycles" in body or "internalMargin" in body:
                raise RuntimeError(f"Unauthorized route leaked application content: {path}")
            report["checks"].append(f"GET {path}: HTTP 401, authentication_required, valid correlation ID, no data")
        report["checks"].append(
            "Read-only nonroot amd64 container; no mounts, external network or published ports; in-container loopback"
        )
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError,
            http.client.HTTPException) as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        cleanup_errors = []
        if container_id and re.fullmatch(r"[0-9a-f]{64}", container_id):
            try:
                report["logs"] = helper.docker("logs", "--tail", "80", container_id)
                helper.docker("rm", "--force", container_id)
            except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                cleanup_errors.append(str(error))
        report["cleanupPassed"] = not cleanup_errors
        if cleanup_errors:
            report["error"] = f"{report['error'] or ''}; cleanup failed: {'; '.join(cleanup_errors)}"
    report["ok"] = report["error"] is None and report["cleanupPassed"]
    return report


def main() -> int:
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-directory", type=Path, default=EVIDENCE)
    parser.add_argument("--application-evidence", type=Path, default=ROOT / ".application-evidence")
    args = parser.parse_args()
    EVIDENCE = args.evidence_directory.resolve()
    application_evidence = args.application_evidence.resolve()
    if not all(path.is_relative_to(ROOT.resolve()) for path in (EVIDENCE, application_evidence)):
        parser.error("Evidence must remain inside this scenario.")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    checks = []
    prior = json.loads((application_evidence / "validation.json").read_text(encoding="utf-8"))
    differences = [
        name for name, expected in prior["sourceSha256"].items()
        if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected
    ]
    dockerfile = r"src\MobilityCommercial.Web\Dockerfile"
    docker_text = (ROOT / dockerfile).read_text(encoding="utf-8")
    prior_passed = (
        prior["allCommandsPassed"] is True and len(prior["checks"]) == 9
        and all(check["exitCode"] == 0 for check in prior["checks"])
        and differences in ([], [dockerfile])
        and "FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0 AS build" in docker_text
        and "FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime" in docker_text
    )
    checks.append({
        "name": "retained-application-evidence",
        "command": "Verify recorded application source hashes; permit only the native SDK Dockerfile repair",
        "exitCode": 0 if prior_passed else 1, "sourceDifferences": differences,
        "originalEvidence": str((application_evidence / "validation.json").relative_to(ROOT)),
    })
    if prior_passed:
        checks.append(run("recovered-image-build", [
            "docker", "build", "--platform", "linux/amd64", "--tag", IMAGE,
            "--file", dockerfile, ".",
        ], timeout=600))
    if all(check["exitCode"] == 0 for check in checks):
        checks.append(run("image-inspect", ["docker", "image", "inspect", IMAGE]))
        image = json.loads((EVIDENCE / "image-inspect.log").read_text(encoding="utf-8"))[0]
        checks.append({
            "name": "image-contract", "command": "Verify owned image OS, architecture and nonroot runtime user",
            "exitCode": 0 if image["Os"] == "linux" and image["Architecture"] == "amd64"
            and image["Config"]["User"] == "1654" else 1, "imageId": image["Id"],
        })
    if all(check["exitCode"] == 0 for check in checks):
        helper_check = run("unconfigured-container-helper", [
            sys.executable, str(HELPER), "--image", IMAGE, "--marker", "Adventure Works Cycles", "--timeout", "3",
        ])
        helper_report = json.loads((EVIDENCE / "unconfigured-container-helper.log").read_text(encoding="utf-8"))
        expected_rejection = (
            helper_check["exitCode"] == 1 and helper_report["ok"] is False
            and helper_report["cleanupPassed"] is True
            and "Required setting missing: Foundry:ProjectEndpoint" in helper_report["logs"]
        )
        checks.append({
            **helper_check, "name": "unconfigured-startup-rejected", "observedExitCode": helper_check["exitCode"],
            "exitCode": 0 if expected_rejection else 1, "expected": "Unconfigured production startup must fail",
            "genericLivenessPassed": False,
        })
    if all(check["exitCode"] == 0 for check in checks):
        environment = []
        for key, value in test_settings().items():
            environment.extend(["--env", f"{key}={value}"])
        checks.append(run("isolated-configuration-check", [
            "docker", "run", "--rm", "--pull=never", "--read-only", "--network", "none",
            "--platform", "linux/amd64", *environment, IMAGE, "--check-configuration",
        ]))
        if "Configuration valid. No Azure calls performed." not in (
            EVIDENCE / "isolated-configuration-check.log"
        ).read_text(encoding="utf-8"):
            checks[-1]["exitCode"] = 1
    if all(check["exitCode"] == 0 for check in checks):
        backend = configured_backend()
        (EVIDENCE / "offline-backend.json").write_text(json.dumps(backend, indent=2) + "\n", encoding="utf-8")
        checks.append({
            "name": "configured-backend-authentication", "command": "validate_local.py: configured_backend()",
            "exitCode": 0 if backend["ok"] else 1, "report": str((EVIDENCE / "offline-backend.json").relative_to(ROOT)),
        })
    passed = len(checks) == 7 and all(check["exitCode"] == 0 for check in checks)
    report = {
        "schemaVersion": 1, "stage": "local-validation",
        "status": "passed_local_checks" if passed else "failed",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "allCommandsPassed": passed, "image": IMAGE, "checks": checks,
        "sourceSha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in prior["sourceSha256"]
            if (ROOT / name).is_file()
        },
        "limitations": [
            "The generic helper's unauthenticated health/homepage success contract is intentionally not satisfied.",
            "Actual configured container routes return authenticated-backend 401 responses, not a public homepage.",
            "Test settings are explicit syntax-only fixtures, isolated from networks; no real IDs are claimed.",
            "Retained tests cover offline authenticated success, JWT failures, coordination, signing and browser UX.",
            "Real installation outputs, identity configuration, private networking and Foundry await cloud consent.",
            "No Azure operation, directory write, deployment, live inference, approval or package work performed.",
        ],
    }
    (EVIDENCE / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "local-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for check in checks:
        print(f"{check['name']}: {'passed' if check['exitCode'] == 0 else 'FAILED'}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
