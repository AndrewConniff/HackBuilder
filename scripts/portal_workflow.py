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

import prerequisite_profiles
WORKFLOW_VERSION = 5

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
STATUSES = {"pending", "running", "completed", "waiting_for_user", "blocked", "failed", "cancelled"}
DECISION_KINDS = {"design", "business", "deployment-preparation", "deployment"}


def local_execution_authorized(project: dict) -> bool:
    consent = project.get("localToolConsent")
    return isinstance(consent, dict) and consent.get("scope") == "scenario-local-execution"


def needs_question_review(decision: dict) -> bool:
    return (
        decision.get("kind") == "business"
        and decision.get("status") in {"pending", "reviewing"}
        and not decision.get("review")
    )


def actionable_decision(decision: dict) -> bool:
    return decision.get("status") == "pending" and not needs_question_review(decision)


def state_directory(root: Path) -> Path:
    legacy = root / ".hackbuilder-portal"
    current = root / ".abcbuilder-portal"
    # Retain live leases/history on upgrades; new checkouts use the ABC name.
    return legacy if legacy.exists() and not current.exists() else current


def environment(name: str) -> str | None:
    return os.environ.get(f"ABCBUILDER_{name}") or os.environ.get(f"HACKBUILDER_{name}")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: object, field: str, limit: int = 6000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be nonempty text of at most {limit} characters.")
    return value.strip()


def setup_verification(value: object) -> str:
    command = text(value, "Setup verification", 2000)
    if re.search(r"\$(?:home|pid|host)\s*=(?!=)", command, re.IGNORECASE):
        raise ValueError(
            "The proposed check assigns a PowerShell automatic/read-only variable ($HOME/$PID/$Host). "
            "Correct the generated command using a nonreserved result variable before reporting setup. "
            "This is a command bug, not a request for broader permissions."
        )
    return command


def classify_blocker(blocker: dict, evidence: list[str]) -> dict:
    details = " ".join([blocker["action"], *evidence]).casefold()
    unidentified_approval = any(phrase in details for phrase in (
        "no interactive user response", "no structured permission metadata",
        "no structured permission.requested", "no unapproved scope metadata",
        "unresolved backend cli approval",
    ))
    if (blocker["kind"] not in {"host-permission", "workflow-error"}
            or blocker.get("category") == "unresolved-cli-approval" or not unidentified_approval):
        return blocker
    return {
        **blocker, "kind": "workflow-error", "category": "unresolved-cli-approval",
        "originalAction": blocker["action"],
        "action": (
            "The backend CLI stopped an operation without identifying the missing permission. "
            "No user setup or approval action is available. Work is preserved and the operation remains "
            "blocked pending backend diagnosis; do not retry through another execution route or broaden access."
        ),
        "diagnosticEvidence": evidence,
    }


class ProjectExistsError(ValueError):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__("This project already exists. Open the existing project or choose a new project name.")


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
        project.setdefault("localToolConsent", None)
        project.setdefault("setupBlocker", None)
        if type(project.get("preflightRequired", False)) is not bool:
            raise ValueError("Invalid prerequisite gating policy in saved project state.")
        consent = project["localToolConsent"]
        if consent is not None and (
            not local_execution_authorized(project)
            or not isinstance(consent.get("grantedAtUtc"), str) or not consent["grantedAtUtc"].strip()
        ):
            raise ValueError("Invalid local execution authorization. Review persisted project state.")
        blocker = project["setupBlocker"]
        if blocker is not None and (
            not isinstance(blocker, dict) or not isinstance(blocker.get("id"), str)
            or blocker.get("stage") not in STAGES
            or blocker.get("kind") not in {"prerequisite", "host-permission", "workflow-error"}
            or any(not isinstance(blocker.get(key), str) or not blocker[key].strip()
                   for key in ("action", "verification", "createdAtUtc"))
        ):
            raise ValueError("Invalid setup blocker. Review persisted project state.")
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
              initial_message: str | None = None, local_tool_consent: bool = False,
              preflight_required: bool = False) -> dict:
        slug = request["projectSlug"]
        with self.locked():
            if self.path(slug).exists():
                project = self.read(slug)
                if create:
                    raise ProjectExistsError(slug)
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
                    "localToolConsent": None,
                    "setupBlocker": None,
                    "status": "pending",
                }
            if local_tool_consent is True and not local_execution_authorized(project):
                project["localToolConsent"] = {
                    "scope": "scenario-local-execution", "grantedAtUtc": timestamp(),
                }
                project["history"].append({
                    "message": "User authorized local execution for this scenario; cloud and publication excluded.",
                    "recordedAtUtc": timestamp(),
                })
            project.update(writer=owner, latestRunId=owner, status="running")
            if create and request.get("localResume"):
                project["reconciliation"] = {
                    "status": "pending", "sourceRunId": request["localResume"]["sourceRunId"],
                    "summary": "Existing files retained; intake and execution evidence need reconciliation.",
                }
            if preflight_required:
                project["preflightRequired"] = True
            return self.save(project)

    def revoke_local_consent(self, slug: str, revision: int) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"]:
                raise ValueError("Stop or finish the active worker before revoking local authorization.")
            project["localToolConsent"] = None
            project["history"].append({
                "message": "User revoked local scenario execution authorization.", "recordedAtUtc": timestamp(),
            })
            return self.save(project)

    @staticmethod
    def check_revision(project: dict, revision: object) -> None:
        if type(revision) is not int or revision != project["revision"]:
            raise ValueError("Project changed. Refresh before submitting this action.")

    def reconcile_intake(self, slug: str, owner: str, revision: int, request: dict, evidence: list[str]) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"] != owner:
                raise ValueError("Only the current project writer can reconcile local intake.")
            if project.get("reconciliation", {}).get("status") != "pending":
                raise ValueError("This project has no pending local intake reconciliation.")
            if request.get("projectSlug") != slug or request.get("deploymentAuthorized") is not False:
                raise ValueError("Reconciliation must preserve the slug and cannot authorize deployment.")
            if request.get("scenarioApproved") is not False or project["designConfirmed"] or project["authorizations"]:
                raise ValueError("Reconciliation cannot import design, deployment or suitability authorization.")
            if not evidence or any(not isinstance(item, str) or not item.strip() for item in evidence):
                raise ValueError("Recovered intake requires specific local artifact evidence.")
            project["request"] = request
            project["reconciliation"].update(
                status="completed", evidence=evidence, updatedAtUtc=timestamp(),
                summary="Local intake recovered. Stage evidence remains unverified until actual checks.",
            )
            project["history"].append({
                "action": "reconcile-local-intake", "evidence": evidence, "recordedAtUtc": timestamp(),
                "message": "Recovered scenario scope from existing files; no stage completion or authorization imported.",
            })
            return self.save(project)

    def report(self, slug: str, owner: str, revision: int, event: dict) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"] != owner:
                raise ValueError("Worker does not own this project. Stale or external writes are rejected.")
            if "localToolConsent" in event or "authorizations" in event:
                raise ValueError("Worker reports cannot grant user authorization.")
            assigned_job = os.environ.get("ABCBUILDER_ASSIGNED_JOB")
            if os.environ.get("ABCBUILDER_RUN_ID") == owner and assigned_job == "question-review":
                if "decisionReview" not in event:
                    raise ValueError("Question review must classify the saved question, not report implementation.")
            if "decisionReview" in event:
                if os.environ.get("ABCBUILDER_RUN_ID") == owner and assigned_job not in {None, "question-review"}:
                    raise ValueError("Leave classification to the backend-assigned question-review operation.")
                return self._apply_question_review(project, event)
            stage = event.get("stage")
            status = event.get("status")
            if stage not in STAGES or status not in STATUSES:
                raise ValueError("Report a known stage and workflow status.")
            assigned = os.environ.get("ABCBUILDER_ASSIGNED_STAGES")
            if assigned and os.environ.get("ABCBUILDER_RUN_ID") == owner:
                allowed = json.loads(assigned)
                if stage not in allowed:
                    raise ValueError(f"The Python backend assigned {allowed}; do not advance other stages in this job.")
                expected_operation = os.environ.get("ABCBUILDER_ASSIGNED_OPERATION")
                if expected_operation and event.get("operation") != expected_operation:
                    raise ValueError(f"The backend assigned operation:{expected_operation}; include it in this report.")
            operation = event.get("operation")
            if operation not in {None, "deployment", "deployment-preparation"}:
                raise ValueError("Unknown workflow operation.")
            preparation = operation == "deployment-preparation"
            if preparation:
                if stage != "deployment":
                    raise ValueError("Preparation reports belong to deployment, not live validation or review.")
                if status not in {"pending", "running", "completed", "failed", "blocked", "cancelled"}:
                    raise ValueError("Use a separate cloud decision for preparation authorization.")
                scope = event.get("scope")
                if not isinstance(scope, dict) or not any(
                    item["kind"] == "deployment-preparation" and item["scope"] == scope
                    for item in project["authorizations"]
                ):
                    raise ValueError("Exact-target deployment-preparation consent is required for this scope.")
            elif operation == "deployment" and stage != "deployment":
                raise ValueError("Deployment operation must use the deployment stage.")
            summary = text(event.get("summary"), "Stage summary", 1200)
            evidence = event.get("evidence", [])
            if not isinstance(evidence, list) or any(
                not isinstance(item, str) or not item.strip() for item in evidence
            ):
                raise ValueError("Evidence must be a list of command/results or artifact references.")
            if status == "completed" and not evidence:
                raise ValueError("Completed stages require evidence references.")
            blocker = project["setupBlocker"]
            verification = event.get("setupVerification")
            if verification is not None:
                if (
                    not isinstance(verification, dict) or not blocker
                    or verification.get("blockerId") != blocker["id"]
                    or verification.get("passed") is not True
                    or stage != blocker["stage"] or status != "pending" or not evidence
                ):
                    raise ValueError(
                        "Setup verification requires the current blocker, pending stage and real evidence."
                    )
            if blocker and status not in {"blocked", "failed", "cancelled"} and verification is None:
                raise ValueError("Verify the setup blocker in this worker before continuing implementation.")
            setup = event.get("blocker")
            if status == "blocked":
                if (
                    not isinstance(setup, dict) or setup.get("kind") not in {
                        "prerequisite", "host-permission", "workflow-error",
                    }
                    or event.get("decision") is not None
                ):
                    raise ValueError("Setup required needs a prerequisite/host-permission blocker, not a decision.")
                proposed_check = setup_verification(setup.get("verification"))
                setup = {
                    "id": blocker["id"] if blocker else uuid.uuid4().hex,
                    "stage": stage, "kind": setup["kind"],
                    "action": text(setup.get("action"), "Setup action", 2000),
                    "verification": proposed_check,
                    "createdAtUtc": blocker["createdAtUtc"] if blocker else timestamp(),
                    "updatedAtUtc": timestamp(),
                }
                setup = classify_blocker(setup, evidence)
            elif setup is not None:
                raise ValueError("A setup blocker requires blocked status.")
            if stage == "architecture" and (
                status == "completed" or isinstance(event.get("decision"), dict)
            ) and project["stages"]["requirements"]["status"] != "completed":
                raise ValueError("Complete requirements before confirming architecture.")
            pending = [
                item for item in project["decisions"] if item["status"] in {"pending", "reviewing"}
            ]
            if pending and status not in {"waiting_for_user", "failed", "cancelled"}:
                raise ValueError("Resolve the pending decision before reporting more work.")
            if stage in {"diagrams", "bicep", "application", "local-validation"} and not project["designConfirmed"]:
                raise ValueError("Confirm the architecture design before implementation.")
            if status in {"running", "completed"}:
                prerequisite_profiles.require_stage(project, self.directory, owner, stage)
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
            if (
                stage in {"deployment", "live-validation", "review"}
                and not preparation and not requesting_cloud and status != "blocked" and verification is None
            ):
                if not any(item["kind"] == "deployment" for item in project["authorizations"]):
                    raise ValueError("Exact-target deployment consent is required for cloud stages.")
            if stage == "review" and status == "completed":
                raise ValueError("Suitability review is validated by the approval helper, not worker progress.")
            if stage == "deployment" and not preparation and status in {"running", "completed"}:
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
                question = text(decision.get("question"), "Decision question")
                if kind == "business" and any(
                    item["kind"] == "business" and item["question"].casefold() == question.casefold()
                    and item.get("review", {}).get("disposition") == "technical"
                    for item in project["decisions"]
                ):
                    raise ValueError(
                        "The backend already classified this question as implementation-owned. "
                        "Apply its recorded resolution; do not ask it again."
                    )
                project["decisions"].append({
                    "id": uuid.uuid4().hex,
                    "kind": kind,
                    "stage": stage,
                    "question": question,
                    "reason": text(decision.get("reason"), "Decision reason"),
                    "choices": choices,
                    "acceptChoice": accept,
                    "scope": scope,
                    "status": "reviewing" if kind == "business" else "pending",
                    "previousStage": dict(project["stages"][stage]),
                    "createdAtUtc": timestamp(),
                })
                if kind == "business":
                    status = "pending"
                    summary = "Backend reviewing a proposed question against saved intake and decisions."
            elif status == "waiting_for_user":
                raise ValueError("waiting_for_user requires a structured decision.")
            if verification is not None:
                project["history"].append({
                    "message": "Setup verified in the worker.", "blockerId": blocker["id"],
                    "evidence": evidence, "recordedAtUtc": timestamp(),
                })
                project["setupBlocker"] = None
            elif status == "blocked":
                project["setupBlocker"] = setup
            progress = {
                "status": status, "summary": summary, "evidence": evidence, "updatedAtUtc": timestamp(),
            }
            if preparation:
                project["deploymentPreparation"] = {**progress, "scope": event["scope"]}
                if verification is not None:
                    project["stages"][stage] = {
                        "status": "pending", "summary": "Preparation verified; actual deployment remains unauthorized.",
                    }
            else:
                project["stages"][stage] = progress
            project["status"] = "setup_required" if status == "blocked" else (
                "waiting_for_user" if decision and decision["kind"] != "business" else "running"
            )
            return self.save(project)

    def _apply_question_review(self, project: dict, event: dict) -> dict:
        review = event["decisionReview"]
        if not isinstance(review, dict):
            raise ValueError("decisionReview must be a structured classification.")
        decision = next(
            (item for item in project["decisions"]
             if item["id"] == review.get("decisionId") and needs_question_review(item)), None,
        )
        if not decision or project["setupBlocker"]:
            raise ValueError("Review only an unreviewed business question without an existing setup blocker.")
        if any(actionable_decision(item) for item in project["decisions"] if item is not decision):
            raise ValueError("Resolve the existing design/cloud/business checkpoint before question review.")
        if event.get("stage") != decision["stage"]:
            raise ValueError("Question review must retain the original stage.")
        assigned = os.environ.get("ABCBUILDER_ASSIGNED_STAGES")
        if assigned and os.environ.get("ABCBUILDER_RUN_ID") == project["writer"]:
            if decision["stage"] not in json.loads(assigned):
                raise ValueError("Question review is outside the assigned stage.")
        disposition = review.get("disposition")
        if disposition not in {"technical", "business", "external-blocker"}:
            raise ValueError("Classify as technical, business or external-blocker; unknown questions stay internal.")
        reason = text(review.get("reason"), "Classification reason", 2000)
        evidence = review.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(item, str) or not item.strip() for item in evidence
        ):
            raise ValueError("Classification requires saved intake/decision or actual diagnostic evidence.")
        record = {
            "disposition": disposition, "reason": reason, "evidence": evidence, "reviewedAtUtc": timestamp(),
        }
        if disposition == "business":
            record["unresolvedNeed"] = text(review.get("unresolvedNeed"), "Unresolved business/security need", 2000)
            record["intakeEvidence"] = text(review.get("intakeEvidence"), "Why intake/history cannot resolve it", 2000)
            impacts = review.get("choiceImpacts")
            if not isinstance(impacts, dict) or set(impacts) != set(decision["choices"]) or len(impacts) < 2:
                raise ValueError("A genuine business decision needs at least two choices with their distinct impacts.")
            record["choiceImpacts"] = {
                key: text(value, "Business/security impact", 1000) for key, value in impacts.items()
            }
            decision["status"] = "pending"
            project["stages"][decision["stage"]]["status"] = "waiting_for_user"
            project["status"] = "waiting_for_user"
        elif disposition == "external-blocker":
            blocker = review.get("blocker")
            if not isinstance(blocker, dict) or blocker.get("kind") not in {"prerequisite", "host-permission"}:
                raise ValueError("External blockers require an observed prerequisite failure or host denial.")
            setup = {
                "id": uuid.uuid4().hex, "stage": decision["stage"], "kind": blocker["kind"],
                "action": text(blocker.get("action"), "Exact external action", 2000),
                "verification": setup_verification(blocker.get("verification")),
                "createdAtUtc": timestamp(), "updatedAtUtc": timestamp(), "evidence": evidence,
            }
            text(blocker.get("observedFailure"), "Observed failure", 2000)
            setup["observedFailure"] = blocker["observedFailure"]
            setup = classify_blocker(setup, [*evidence, blocker["observedFailure"]])
            project["setupBlocker"] = setup
            decision["status"] = "superseded"
            project["stages"][decision["stage"]].update(status="blocked", summary=reason, evidence=evidence)
            project["status"] = "setup_required"
        else:
            record["resolution"] = text(review.get("resolution"), "Implementation-owned next action", 2000)
            decision["status"] = "superseded"
            previous = decision.get("previousStage", {})
            project["stages"][decision["stage"]] = (
                dict(previous) if previous.get("status") == "completed" else {
                    "status": "completed" if decision["stage"] == "architecture" and project["designConfirmed"]
                    else "pending",
                    "summary": record["resolution"], "evidence": evidence,
                }
            )
            project["status"] = "running"
        decision["review"] = record
        project["history"].append({
            "action": "backend-question-review", "decisionId": decision["id"], **record,
            "authorization": "Classification grants no execution, cloud, directory or suitability permission.",
        })
        return self.save(project)

    def respond(self, slug: str, revision: int, message: str, decision_id: str | None = None,
                choice: str | None = None, revise: bool = False) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"]:
                raise ValueError("Wait for the active project writer to finish.")
            if project["setupBlocker"]:
                raise ValueError("Setup required. Use Verify setup & retry; another approval cannot fix this blocker.")
            message = text(message, "User instruction")
            pending = [item for item in project["decisions"] if actionable_decision(item)]
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
                for decision in project["decisions"]:
                    if decision["status"] in {"pending", "reviewing"}:
                        decision["status"] = "superseded"
                project["stages"] = {key: {"status": "pending", "summary": ""} for key in STAGES}
            project["history"].append({"message": message, "choice": choice, "revise": revise,
                                       "recordedAtUtc": timestamp()})
            project["status"] = "pending"
            return self.save(project)

    def cancel_idle(self, slug: str, revision: int) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"]:
                raise ValueError("Stop the active worker before cancelling saved work.")
            project["status"] = "cancelled"
            project["history"].append({
                "action": "cancel-idle", "message": "Cancelled saved work; artifacts, decisions and consent retained.",
                "recordedAtUtc": timestamp(),
            })
            return self.save(project)

    def classify_saved_approval_failure(self, slug: str, revision: int) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"]:
                raise ValueError("Wait for the active writer before classifying a saved approval failure.")
            blocker = project["setupBlocker"]
            if not blocker:
                return project
            classified = classify_blocker(blocker, [])
            if classified == blocker:
                return project
            project["setupBlocker"] = classified
            project["history"].append({
                "action": "classify-unresolved-cli-approval", "previousBlocker": blocker,
                "recordedAtUtc": timestamp(),
                "message": "Backend diagnostic failure; denial retained. No retry or permission granted.",
            })
            return self.save(project)

    def retarget_preparation(self, slug: str, revision: int, region: str, message: str) -> dict:
        """Record an explicit user region change for read-only validation, never deployment."""
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if project["writer"]:
                raise ValueError("Finish the active worker before changing validation targets.")
            if not isinstance(region, str) or not re.fullmatch(r"[a-z][a-z0-9]+", region):
                raise ValueError("Use a canonical Azure region name.")
            context = project.get("deploymentContext")
            if not isinstance(context, dict) or not isinstance(context.get("scope"), dict):
                raise ValueError("Resolve the existing exact Azure target before retargeting.")
            scope = {**context["scope"], "region": region}
            for field in ("account", "subscriptionId", "tenantId", "environment", "resourceGroup"):
                text(scope.get(field), f"Scope {field}", 500)
            blocker = project["setupBlocker"]
            if blocker and blocker["stage"] != "deployment":
                raise ValueError("Resolve unrelated local setup before changing deployment targets.")
            pending = [d for d in project["decisions"] if d["status"] in {"pending", "reviewing"}]
            if any(d["kind"] not in {"deployment-preparation", "deployment"} for d in pending):
                raise ValueError("Resolve unrelated business/design decisions before retargeting.")
            message = text(message, "Explicit user target/preparation instruction")
            project["history"].append({
                "action": "retarget-read-only-preparation", "message": message, "recordedAtUtc": timestamp(),
                "previousScope": context["scope"], "previousBlocker": blocker,
                "previousAuthorizations": project["authorizations"],
                "previousPreparation": project.get("deploymentPreparation"),
                "authorization": "New target read-only checks only; no deployment, directory writes or quota changes.",
            })
            for decision in pending:
                decision["status"] = "superseded"
            context["scope"] = scope
            context.setdefault("sources", {})["region"] = "Explicit user validation-region change"
            context["checkedAtUtc"] = timestamp()
            project["setupBlocker"] = None
            project["authorizations"] = [{
                "kind": "deployment-preparation", "scope": scope, "message": message, "recordedAtUtc": timestamp(),
            }]
            project["deploymentPreparation"] = {
                "status": "pending", "scope": scope,
                "summary": "User requested fresh validation in this region; previous results are historical.",
            }
            for stage in ("deployment", "live-validation", "review"):
                project["stages"][stage] = {
                    "status": "pending", "summary": "Target revalidation required; no new deployment authorized.",
                }
            project["status"] = "pending"
            return self.save(project)

    def propose_deployment_context(self, slug: str, revision: int, context: dict, owner: str | None = None) -> dict:
        with self.locked():
            project = self.read(slug)
            self.check_revision(project, revision)
            if (project["writer"] and project["writer"] != owner) or project["setupBlocker"]:
                raise ValueError("Finish active work or resolve setup before reviewing Azure targets.")
            pending = [item for item in project["decisions"] if item["status"] in {"pending", "reviewing"}]
            for decision in pending:
                if not (
                    decision["kind"] == "deployment-preparation"
                    or (decision["kind"] == "business" and
                        "Provide exact Azure targets in the portal response" in decision["choices"])
                ):
                    raise ValueError("Resolve the existing unrelated decision before proposing Azure targets.")
            scope = context.get("scope", {})
            for field in ("account", "subscriptionId", "tenantId", "environment", "resourceGroup", "region"):
                text(scope.get(field), f"Scope {field}", 500)
            for decision in pending:
                decision["status"] = "superseded"
            project["deploymentContext"] = context
            project["authorizations"] = []
            project["decisions"].append({
                "id": uuid.uuid4().hex, "kind": "deployment-preparation", "stage": "deployment",
                "question": "Allow read-only Azure preflight and what-if for these proposed targets?",
                "reason": "Identity and local configuration resolved. No resource/capacity queries or cloud mutations performed.",
                "choices": ["Allow read-only preflight & what-if", "Keep the reference local only"],
                "acceptChoice": "Allow read-only preflight & what-if", "scope": scope,
                "status": "pending", "createdAtUtc": timestamp(),
            })
            project["stages"]["deployment"]["status"] = "waiting_for_user"
            project["status"] = "waiting_for_user"
            project["history"].append({
                "message": "User requested identity discovery and reviewed a proposed Azure target context; no cloud consent granted.",
                "recordedAtUtc": timestamp(),
            })
            return self.save(project)

    def finish(self, slug: str, owner: str, outcome: str) -> None:
        with self.locked():
            project = self.read(slug)
            if project["writer"] != owner:
                raise ValueError("Cannot release another project's writer.")
            project["writer"] = None
            pending = any(actionable_decision(item) for item in project["decisions"])
            if outcome != "completed":
                project["status"] = outcome
            elif project["setupBlocker"]:
                project["status"] = "setup_required"
            elif pending:
                project["status"] = "waiting_for_user"
            elif project.get("deploymentPreparation", {}).get("status") == "failed":
                project["status"] = "failed"
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
            if project["setupBlocker"] and outcome in {"completed", "failed"}:
                project["status"] = "setup_required"
            self.save(project)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["read", "report", "claim", "finish"])
    parser.add_argument("--directory", type=Path, default=environment("PROJECT_STATE"))
    parser.add_argument("--project", default=environment("PROJECT"))
    parser.add_argument("--owner", default=environment("RUN_ID"))
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
