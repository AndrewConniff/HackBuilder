"""Persist portal project progress and accept revision-checked worker reports."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

STAGES = {
    "requirements": "Requirements",
    "architecture": "Architecture validation",
    "diagrams": "Architecture diagrams",
    "bicep": "Bicep creation",
    "application": "Application implementation",
    "local-validation": "Local validation",
    "deployment": "Deployment",
    "live-validation": "Live scenario validation",
    "review": "Scenario suitability review",
    "hack-plan": "Hack package planning",
    "hack-content": "Challenges and learner guide",
    "hack-starter": "Participant starter",
    "hack-coach": "Private coach package",
    "hack-validation": "Hack package validation",
}
LEGACY_STAGES = set(STAGES) - {key for key in STAGES if key.startswith("hack-")}
STATUSES = {"pending", "running", "completed", "waiting_for_user", "failed", "cancelled"}
DECISION_KINDS = {"design", "business", "deployment-preparation", "deployment"}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: object, field: str, limit: int = 6000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be nonempty text of at most {limit} characters.")
    return value.strip()


class Store:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def path(self, slug: str) -> Path:
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 40:
            raise ValueError("Invalid project slug.")
        return self.directory / f"{slug}.json"

    @contextmanager
    def locked(self):
        # A kernel lock is released on process exit, unlike an exclusive-create lock file.
        with (self.directory / "state.lock").open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if not stream.tell():
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

    def read(self, slug: str) -> dict:
        project = json.loads(self.path(slug).read_text(encoding="utf-8"))
        if (
            not isinstance(project, dict)
            or project.get("schemaVersion") != 1
            or project.get("projectSlug") != slug
            or type(project.get("revision")) is not int
            or project["revision"] < 1
            or not isinstance(project.get("stages"), dict)
            or set(project["stages"]) not in (set(STAGES), LEGACY_STAGES)
            or any(not isinstance(project.get(key), list) for key in ("decisions", "history", "authorizations"))
            or "writer" not in project
        ):
            raise ValueError("Invalid or unsupported project state. Inspect persisted state before recovery.")
        for key in STAGES:
            project["stages"].setdefault(key, {"status": "pending", "summary": ""})
        return project

    def save(self, project: dict) -> dict:
        project["revision"] += 1
        project["updatedAtUtc"] = timestamp()
        path = self.path(project["projectSlug"])
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return project

    def claim(self, request: dict, owner: str, revision: int | None = None, create: bool = False,
              initial_message: str | None = None) -> dict:
        slug = request["projectSlug"]
        with self.locked():
            if self.path(slug).exists():
                project = self.read(slug)
                if create:
                    raise ValueError("This project already exists. Select it and continue or request a revision.")
                self.check_revision(project, revision)
                if project["writer"] is not None:
                    raise ValueError("This project has an active writer. Stop or finish that job before editing.")
            else:
                project = {
                    "schemaVersion": 1,
                    "projectSlug": slug,
                    "revision": 0,
                    "request": request,
                    "stages": {key: {"status": "pending", "summary": ""} for key in STAGES},
                    "decisions": [],
                    "history": (
                        [{"message": text(initial_message, "User instruction"), "recordedAtUtc": timestamp()}]
                        if initial_message is not None else []
                    ),
                    "authorizations": [],
                    "designConfirmed": False,
                    "status": "pending",
                }
            project.update(writer=owner, latestRunId=owner, status="running")
            return self.save(project)

    @staticmethod
    def check_revision(project: dict, revision: object) -> None:
        if type(revision) is not int or revision != project["revision"]:
            raise ValueError("Project changed. Refresh before submitting this action.")

    def report(self, slug: str, owner: str, revision: int, event: dict) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"] != owner:
                raise ValueError("Worker does not own this project. Stale or external writes are rejected.")
            stage = event.get("stage")
            status = event.get("status")
            if stage not in STAGES or status not in STATUSES:
                raise ValueError("Report a known stage and workflow status.")
            summary = text(event.get("summary"), "Stage summary", 1200)
            evidence = event.get("evidence", [])
            if not isinstance(evidence, list) or any(
                not isinstance(item, str) or not item.strip() for item in evidence
            ):
                raise ValueError("Evidence must be a list of command/results or artifact references.")
            if status == "completed" and not evidence:
                raise ValueError("Completed stages require evidence references.")
            if stage == "architecture" and (
                status == "completed" or isinstance(event.get("decision"), dict)
            ) and project["stages"]["requirements"]["status"] != "completed":
                raise ValueError("Complete requirements before confirming architecture.")
            pending = [item for item in project["decisions"] if item["status"] == "pending"]
            if pending and status not in {"waiting_for_user", "failed", "cancelled"}:
                raise ValueError("Resolve the pending decision before reporting more work.")
            if stage in {"diagrams", "bicep", "application", "local-validation"} and not project["designConfirmed"]:
                raise ValueError("Confirm the architecture design before implementation.")
            if stage == "local-validation" and status == "completed":
                if any(
                    project["stages"][key]["status"] != "completed"
                    for key in ("requirements", "architecture", "diagrams", "bicep", "application")
                ):
                    raise ValueError("Complete all local implementation steps before local validation.")
            decision = event.get("decision")
            requesting_cloud = (
                status == "waiting_for_user" and isinstance(decision, dict)
                and decision.get("kind") in {"deployment-preparation", "deployment"}
            )
            if stage in {"deployment", "live-validation", "review"} and not requesting_cloud:
                if not any(item["kind"] == "deployment" for item in project["authorizations"]):
                    raise ValueError("Exact-target deployment consent is required for cloud stages.")
            if stage == "review" and status == "completed":
                raise ValueError("Suitability review is validated by the approval helper, not worker progress.")
            if stage == "deployment" and status in {"running", "completed"}:
                if project["stages"]["local-validation"]["status"] != "completed":
                    raise ValueError("Complete local validation before deployment.")
            if stage == "live-validation" and status in {"running", "completed"}:
                if project["stages"]["deployment"]["status"] != "completed":
                    raise ValueError("Complete deployment before live validation.")
            if stage == "review" and status in {"running", "completed"}:
                if project["stages"]["live-validation"]["status"] != "completed":
                    raise ValueError("Complete live validation before suitability review.")
            if status in {"running", "failed"} and project["stages"][stage]["status"] == "completed":
                if stage in {"requirements", "architecture"}:
                    raise ValueError("Request a design revision before changing confirmed requirements/architecture.")
                if stage in {"diagrams", "bicep", "application"}:
                    for key in ("local-validation", "deployment", "live-validation", "review"):
                        project["stages"][key] = {"status": "pending", "summary": "Invalidated by local changes."}
                    project["authorizations"] = []
            if decision is not None:
                if status != "waiting_for_user" or pending:
                    raise ValueError("A new decision requires waiting_for_user and no existing pending decision.")
                if not isinstance(decision, dict) or decision.get("kind") not in DECISION_KINDS:
                    raise ValueError("Decision kind is invalid.")
                choices = decision.get("choices")
                if (
                    not isinstance(choices, list)
                    or not choices
                    or len(choices) > 8
                    or any(
                        not isinstance(choice, str) or not choice.strip() or len(choice) > 200
                        for choice in choices
                    )
                    or len(set(choices)) != len(choices)
                ):
                    raise ValueError("Provide 1-8 distinct decision choices.")
                kind = decision["kind"]
                if kind == "design" and stage != "architecture":
                    raise ValueError("Design confirmation belongs to the architecture stage.")
                if kind == "design" and not evidence:
                    raise ValueError("Design confirmation requires architecture evidence.")
                if kind in {"deployment-preparation", "deployment"} and stage != "deployment":
                    raise ValueError("Cloud permission decisions belong to deployment.")
                scope = decision.get("scope")
                if kind in {"deployment-preparation", "deployment"}:
                    if not isinstance(scope, dict):
                        raise ValueError("Cloud decisions require an exact target scope.")
                    for key in ("account", "subscriptionId", "tenantId", "resourceGroup", "environment", "region"):
                        text(scope.get(key), f"Scope {key}", 500)
                    if kind == "deployment":
                        for key in ("whatIfEvidence", "estimatedCost"):
                            text(scope.get(key), key, 2000)
                        if not any(
                            item["kind"] == "deployment-preparation" and item["scope"] == {
                                key: value for key, value in scope.items()
                                if key not in {"whatIfEvidence", "estimatedCost"}
                            }
                            for item in project["authorizations"]
                        ):
                            raise ValueError("Authorize preparation for these targets before deployment consent.")
                accept = decision.get("acceptChoice")
                if kind != "business" and accept not in choices:
                    raise ValueError("Design/cloud decisions require an explicit acceptChoice.")
                if kind == "design":
                    project["designConfirmed"] = False
                    project["authorizations"] = []
                elif kind in {"deployment-preparation", "deployment"}:
                    project["authorizations"] = [
                        item for item in project["authorizations"]
                        if kind == "deployment" and item["kind"] == "deployment-preparation"
                    ]
                project["decisions"].append({
                    "id": uuid.uuid4().hex,
                    "kind": kind,
                    "stage": stage,
                    "question": text(decision.get("question"), "Decision question"),
                    "reason": text(decision.get("reason"), "Decision reason"),
                    "choices": choices,
                    "acceptChoice": accept,
                    "scope": scope,
                    "status": "pending",
                    "createdAtUtc": timestamp(),
                })
            elif status == "waiting_for_user":
                raise ValueError("waiting_for_user requires a structured decision.")
            project["stages"][stage] = {
                "status": status, "summary": summary, "evidence": evidence, "updatedAtUtc": timestamp(),
            }
            project["status"] = "waiting_for_user" if decision else "running"
            return self.save(project)

    def respond(self, slug: str, revision: int, message: str, decision_id: str | None = None,
                choice: str | None = None, revise: bool = False) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"]:
                raise ValueError("Wait for the active project writer to finish.")
            message = text(message, "User instruction")
            pending = [item for item in project["decisions"] if item["status"] == "pending"]
            if pending and not revise:
                decision = pending[0]
                if decision["id"] != decision_id or choice not in decision["choices"]:
                    raise ValueError("Answer the current decision with one of its displayed choices.")
                decision.update(status="answered", answer=choice, message=message, answeredAtUtc=timestamp())
                if choice == decision["acceptChoice"]:
                    if decision["kind"] == "design":
                        project["designConfirmed"] = True
                    elif decision["kind"] in {"deployment-preparation", "deployment"}:
                        project["authorizations"].append({
                            "kind": decision["kind"], "scope": decision["scope"],
                            "decisionId": decision["id"], "message": message, "recordedAtUtc": timestamp(),
                        })
                project["stages"][decision["stage"]]["status"] = (
                    "completed" if decision["kind"] == "design" and project["designConfirmed"] else "pending"
                )
            elif decision_id is not None:
                raise ValueError("This decision is no longer pending.")
            if revise:
                project["designConfirmed"] = False
                project["authorizations"] = []
                for decision in pending:
                    decision["status"] = "superseded"
                project["stages"] = {key: {"status": "pending", "summary": ""} for key in STAGES}
            project["history"].append({"message": message, "choice": choice, "revise": revise,
                                       "recordedAtUtc": timestamp()})
            project["status"] = "pending"
            return self.save(project)

    def finish(self, slug: str, owner: str, outcome: str) -> None:
        with self.locked():
            project = self.read(slug)
            if project["writer"] != owner:
                raise ValueError("Cannot release another project's writer.")
            project["writer"] = None
            pending = any(item["status"] == "pending" for item in project["decisions"])
            if outcome != "completed":
                project["status"] = outcome
            elif pending:
                project["status"] = "waiting_for_user"
            elif any(stage["status"] == "failed" for stage in project["stages"].values()):
                project["status"] = "failed"
            elif project["stages"]["live-validation"]["status"] == "completed":
                project["status"] = "awaiting_review"
            elif project["stages"]["deployment"]["status"] == "completed":
                project["status"] = "deployed_validation_pending"
            elif project["stages"]["local-validation"]["status"] == "completed":
                project["status"] = "local_ready"
            else:
                project["status"] = "needs_attention"
            for stage in project["stages"].values():
                if stage["status"] == "running":
                    stage["status"] = "failed" if outcome == "completed" else outcome
                    project["status"] = "needs_attention" if outcome == "completed" else outcome
                    stage["summary"] += " Worker exited before reporting a result."
            self.save(project)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["read", "report", "claim", "finish"])
    parser.add_argument("--directory", type=Path, default=os.environ.get("HACKBUILDER_PROJECT_STATE"))
    parser.add_argument("--project", default=os.environ.get("HACKBUILDER_PROJECT"))
    parser.add_argument("--owner", default=os.environ.get("HACKBUILDER_RUN_ID"))
    parser.add_argument("--revision", type=int)
    parser.add_argument("--event", type=Path, help="JSON stage report; never user consent.")
    parser.add_argument("--request", type=Path, help="Normalized intake JSON when claiming a new external project.")
    parser.add_argument("--outcome", choices=["completed", "failed", "cancelled", "interrupted"])
    args = parser.parse_args()
    try:
        if not args.directory or not args.project:
            raise ValueError("Specify the project state directory and project.")
        store = Store(Path(args.directory))
        if args.command == "read":
            result = store.read(args.project)
        elif args.command == "claim":
            owner = text(args.owner, "External writer owner", 200)
            request = (
                json.loads(args.request.read_text(encoding="utf-8")) if args.request
                else store.read(args.project)["request"]
            )
            if not isinstance(request, dict) or request.get("projectSlug") != args.project:
                raise ValueError("Request must name this project.")
            result = store.claim(request, owner, args.revision)
        elif args.command == "finish":
            if not args.outcome:
                raise ValueError("finish requires --outcome.")
            store.finish(args.project, text(args.owner, "External writer owner", 200), args.outcome)
            result = store.read(args.project)
        else:
            if not args.event:
                raise ValueError("report requires --event.")
            event = json.loads(args.event.read_text(encoding="utf-8"))
            if not isinstance(event, dict):
                raise ValueError("Event must be a JSON object.")
            result = store.report(args.project, args.owner, args.revision, event)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Workflow report rejected: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
