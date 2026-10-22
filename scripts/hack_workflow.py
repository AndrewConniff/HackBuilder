"""Record scenario review and reject missing or stale hack-authoring approval."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

STATE_FILE = "workflow-state.json"
REQUIRED_CHECKS = {"deployment", "modelInference", "agentInvocation", "applicationChat", "negativeCase"}
HISTORICAL_ATTESTATION = "historical-user-attestation"
REQUIRED_FILES = (
    "00-region-availability.json",
    "01-requirements.md",
    "02-architecture-assessment.md",
    "03-architect-diagram.png",
    "04-runtime-diagram.png",
    "azure.yaml",
    "infra/main.bicep",
    "06-deployment-summary.md",
    "scenario-validation.json",
    "demoguide/demoguide.md",
)
EXCLUDED_DIRECTORIES = {
    "packages",
    ".git",
    ".azure",
    ".venv",
    "venv",
    "bin",
    "obj",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    "node_modules",
}
EXCLUDED_ROOT_FILES = {
    STATE_FILE,
    "README.md",
    "08-hack-package-contract.md",
    "09-hack-event-manifest.json",
    "nextsteps.MD",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return value


def validate_reference(root: Path) -> None:
    for name in REQUIRED_FILES:
        path = root / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty reference artifact: {name}")
    if not (root / "src").is_dir() or not any((root / "src").rglob("*.csproj")):
        raise ValueError("The reference must include the real application under src.")
    evidence = read_object(root / "scenario-validation.json")
    evidence_type = evidence.get("evidenceType", "runtime-validation")
    if evidence_type == HISTORICAL_ATTESTATION:
        attestation = evidence.get("attestation")
        if (
            evidence.get("status") != "user-attested"
            or not isinstance(attestation, dict)
            or attestation.get("successfulDeployment") is not True
            or attestation.get("fullScenarioWorked") is not True
            or attestation.get("resourceState") != "deleted"
            or attestation.get("source") != "explicit-user-statement"
            or not isinstance(attestation.get("statement"), str)
            or not attestation["statement"].strip()
            or not isinstance(attestation.get("unavailableReason"), str)
            or not attestation["unavailableReason"].strip()
            or evidence.get("applicationUrl") is not None
            or evidence.get("checkedAtUtc") is not None
            or evidence.get("checks") != {}
        ):
            raise ValueError("Historical evidence requires an explicit, complete user attestation, not passed checks.")
        recorded_at = attestation.get("recordedAtUtc")
        if not isinstance(recorded_at, str):
            raise ValueError("Historical attestation must record when the user statement was captured.")
        if datetime.fromisoformat(recorded_at.replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError("Historical attestation timestamp must include a timezone.")
        return
    if evidence_type != "runtime-validation":
        raise ValueError("Unsupported scenario evidence type.")
    if evidence.get("status") != "passed":
        raise ValueError("Live scenario validation has not passed.")
    checks = evidence.get("checks")
    if not isinstance(checks, dict) or not REQUIRED_CHECKS.issubset(checks):
        raise ValueError("Live validation is missing required checks.")
    if any(value is not True for value in checks.values()):
        raise ValueError("Every supplied live acceptance check must be true.")
    url = urlparse(evidence.get("applicationUrl", ""))
    if url.scheme != "https" or not url.hostname:
        raise ValueError("Live validation must name a deployed HTTPS application URL.")
    checked_at = evidence.get("checkedAtUtc")
    if not isinstance(checked_at, str):
        raise ValueError("Live validation must include checkedAtUtc.")
    timestamp = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("checkedAtUtc must include a timezone.")


def reference_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    files = []
    for directory, children, names in os.walk(root):
        children[:] = sorted(name for name in children if name not in EXCLUDED_DIRECTORIES)
        for name in sorted(names):
            path = Path(directory) / name
            if path.parent == root and name in EXCLUDED_ROOT_FILES:
                continue
            if name == ".env" or name.startswith(".env."):
                continue
            files.append(path)
    for path in sorted(files):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def save_state(root: Path, state: dict) -> None:
    (root / STATE_FILE).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict:
    validate_reference(root)
    state = {
        "schemaVersion": 1,
        "phase": "scenario-review",
        "scenarioStatus": "ready-for-review",
        "referenceFingerprint": reference_fingerprint(root),
        "reviewRequestedAtUtc": utc_now(),
        "approval": None,
        "evidenceType": read_object(root / "scenario-validation.json").get("evidenceType", "runtime-validation"),
    }
    save_state(root, state)
    return state


def attest_history(root: Path, message: str, unavailable_reason: str) -> None:
    if not message.strip() or not unavailable_reason.strip():
        raise ValueError("An explicit user statement and reason historical evidence is unavailable are required.")
    path = root / "scenario-validation.json"
    if path.exists():
        raise ValueError("Scenario evidence already exists. Do not overwrite runtime evidence with an attestation.")
    evidence = {
        "schemaVersion": 1,
        "evidenceType": HISTORICAL_ATTESTATION,
        "status": "user-attested",
        "checkedAtUtc": None,
        "applicationUrl": None,
        "checks": {},
        "attestation": {
            "source": "explicit-user-statement",
            "statement": message.strip(),
            "recordedAtUtc": utc_now(),
            "successfulDeployment": True,
            "fullScenarioWorked": True,
            "resourceState": "deleted",
            "unavailableReason": unavailable_reason.strip(),
        },
        "limitations": [
            "Historical deployment is reported by the user, not independently verified by this assistant.",
            "Deployment time, endpoint, subscription details and granular test results are unavailable.",
            "No per-check success, live endpoint, subscription capacity or current deployability is inferred.",
            "Future deployment requires fresh target verification, consent and recorded runtime acceptance.",
        ],
    }
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(evidence, indent=2) + "\n")


def current_review(root: Path) -> dict:
    validate_reference(root)
    state = read_object(root / STATE_FILE)
    if state.get("schemaVersion") != 1 or state.get("scenarioStatus") != "ready-for-review":
        raise ValueError("A validated scenario review snapshot is required.")
    if state.get("referenceFingerprint") != reference_fingerprint(root):
        raise ValueError("Reference changed: revalidate, snapshot, review and obtain new user approval.")
    return state


def record_decision(root: Path, message: str, decision: str) -> dict:
    if decision not in {"approved", "rejected"}:
        raise ValueError("Review decision must be approved or rejected.")
    if not message.strip():
        raise ValueError("The explicit user response is required.")
    state = current_review(root)
    state["approval"] = {
        "decision": decision,
        "message": message.strip(),
        "recordedAtUtc": utc_now(),
        "referenceFingerprint": state["referenceFingerprint"],
    }
    state["phase"] = "hack-authoring" if decision == "approved" else "scenario-revision"
    save_state(root, state)
    return state


def check_approval(root: Path) -> dict:
    state = current_review(root)
    approval = state.get("approval")
    if not isinstance(approval, dict) or approval.get("decision") != "approved":
        raise ValueError("Explicit user approval of this scenario review is required before hack authoring.")
    if (
        state.get("phase") != "hack-authoring"
        or approval.get("referenceFingerprint") != state["referenceFingerprint"]
        or not isinstance(approval.get("message"), str)
        or not approval["message"].strip()
        or not approval.get("recordedAtUtc")
    ):
        raise ValueError("Approval is incomplete or does not match the current reviewed reference.")
    return state


PACKAGE_CHECKS = {
    "coach-bicep-build", "coach-bicep-lint", "participant-bicep-build", "participant-bicep-lint",
    "coach-build", "coach-tests", "coach-script-guards", "starter-status", "package-boundaries",
    "skillable", "release-archives",
}


def package_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    paths = [root / name for name in ("08-hack-package-contract.md", "nextsteps.MD", "09-hack-event-manifest.json")]
    packages = root / "packages"
    for directory, children, names in os.walk(packages):
        children[:] = sorted(name for name in children if name not in EXCLUDED_DIRECTORIES)
        for name in sorted(names):
            path = Path(directory) / name
            if path == packages / "validation" / "composition-status.json":
                continue
            paths.append(path)
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def record_packages(root: Path) -> dict:
    approval = check_approval(root)
    evidence = read_object(root / "packages" / "validation" / "local-checks.json")
    checks = evidence.get("checks")
    if (
        evidence.get("allCommandsPassed") is not True
        or not isinstance(checks, list)
        or any(not isinstance(item, dict) or type(item.get("exitCode")) is not int
               or item["exitCode"] != 0 for item in checks)
        or not PACKAGE_CHECKS.issubset({item.get("name") for item in checks})
    ):
        raise ValueError("Package validation must include successful required commands.")
    for name in ("coach", "participant", "hack", "coach-guide"):
        if not (root / "packages" / name).is_dir():
            raise ValueError(f"Missing package: {name}")
    result = {
        "schemaVersion": 1,
        "status": "packages_validated",
        "checkedAtUtc": utc_now(),
        "referenceFingerprint": approval["referenceFingerprint"],
        "packageFingerprint": package_fingerprint(root),
        "eventDeployed": False,
    }
    path = root / "packages" / "validation" / "composition-status.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return result


def current_packages(root: Path) -> dict:
    approval = check_approval(root)
    result = read_object(root / "packages" / "validation" / "composition-status.json")
    if (
        result.get("schemaVersion") != 1
        or result.get("status") != "packages_validated"
        or result.get("referenceFingerprint") != approval["referenceFingerprint"]
        or result.get("packageFingerprint") != package_fingerprint(root)
        or result.get("eventDeployed") is not False
    ):
        raise ValueError("Package validation is stale or incomplete. Revalidate and record packages again.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("snapshot", "approve", "reject", "check-approval", "attest-history", "record-packages"),
    )
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--message", default="")
    parser.add_argument("--unavailable-reason", default="")
    args = parser.parse_args()
    root = args.scenario.resolve()
    try:
        if args.command == "record-packages":
            record_packages(root)
        elif args.command == "attest-history":
            attest_history(root, args.message, args.unavailable_reason)
        elif args.command == "snapshot":
            snapshot(root)
        elif args.command in {"approve", "reject"}:
            record_decision(root, args.message, "approved" if args.command == "approve" else "rejected")
        else:
            check_approval(root)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Workflow blocked: {error}\n")
    print(f"{args.command}: passed for {root.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
