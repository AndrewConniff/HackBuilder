"""Select bounded scenario operations from durable state, never from CLI exit status."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from check_prerequisites import execution_environment
from portal_workflow import actionable_decision, needs_question_review

VERSION = 5
LOCAL_STAGES = ("requirements", "architecture", "diagrams", "bicep", "application", "local-validation")


def next_operation(project: dict) -> dict | None:
    if project.get("setupBlocker"):
        stage = project["setupBlocker"]["stage"]
        return {"name": "verify-blocker", "stages": [stage], "operation": None}
    if any(actionable_decision(item) for item in project["decisions"]):
        return None
    if project.get("reconciliation", {}).get("status") == "pending":
        return {"name": "reconcile-local", "stages": [], "operation": None}
    question = next((item for item in project["decisions"] if needs_question_review(item)), None)
    if question:
        return {"name": "question-review", "stages": [question["stage"]], "operation": None,
                "decisionId": question["id"]}
    for stage in LOCAL_STAGES:
        if project["stages"][stage]["status"] != "completed":
            if stage not in {"requirements", "architecture"} and not project["designConfirmed"]:
                return None
            return {"name": stage, "stages": [stage], "operation": None}
    preparation = next(
        (item for item in reversed(project["authorizations"]) if item["kind"] == "deployment-preparation"), None,
    )
    deployment = next(
        (item for item in reversed(project["authorizations"]) if item["kind"] == "deployment"), None,
    )
    cloud_review = max((
        datetime.fromisoformat(item["review"]["reviewedAtUtc"])
        for item in project["decisions"]
        if item.get("stage") in {"deployment", "live-validation", "review"}
        and item.get("review", {}).get("disposition") == "technical"
    ), default=None)

    def after_cloud_review(record: dict, field: str) -> bool:
        return cloud_review is None or bool(
            record.get(field) and datetime.fromisoformat(record[field]) > cloud_review
        )

    if deployment and not after_cloud_review(deployment, "recordedAtUtc"):
        deployment = None
    if deployment:
        for stage in ("deployment", "live-validation", "review"):
            if project["stages"][stage]["status"] != "completed":
                return {"name": stage, "stages": [stage], "operation": None}
        return None
    if preparation:
        progress = project.get("deploymentPreparation", {})
        if (
            progress.get("status") != "completed" or progress.get("scope") != preparation["scope"]
            or not after_cloud_review(progress, "updatedAtUtc")
        ):
            return {
                "name": "deployment-preparation", "stages": ["deployment"],
                "operation": "deployment-preparation", "scope": preparation["scope"],
            }
        return {"name": "deployment-decision", "stages": ["deployment"], "operation": None}
    declined = any(
        item.get("status") == "answered" and item.get("answer") == "Keep the reference local only"
        for item in project["decisions"]
    )
    if declined:
        return None
    return {"name": "target-review", "stages": ["deployment"], "operation": None}


def signature(project: dict) -> str:
    return json.dumps({
        "stages": project["stages"], "preparation": project.get("deploymentPreparation"),
        "blocker": project.get("setupBlocker"), "decisions": project["decisions"],
        "reconciliation": project.get("reconciliation"),
    }, sort_keys=True)


def regional_instruction() -> str:
    return (
            "\nSUBSCRIPTION REGIONAL READINESS CONTRACT:\n"
            "During authorized deployment-preparation, verify the ENTIRE planned resource set against the actual "
            "subscription BEFORE deployment consent or any provisioning. Read current architecture and exact SKUs/"
            "features, not just provider location lists. Test Foundry model/version/deployment type and usable quota; "
            "Cosmos subscription regional access and exact zone/serverless/backup capabilities; compute exact SKU, "
            "restrictions, zones, aggregate scale-out quota; App Service Microsoft.Web SKU/worker quotas; and other "
            "service-specific restrictions, policy and provider state. B2 App Service worker quota is NOT a Compute "
            "VM-family quota. Never infer the provider/resource type from a short size label. "
            "For Cosmos use az cosmosdb locations list --subscription <authorized-subscription> --output json; "
            "supportsAvailabilityZone=true alone does NOT pass: require status Online and the relevant actual "
            "isSubscriptionRegionAccessAllowedForAz or isSubscriptionRegionAccessAllowedForRegular flag true. "
            "For VMs use az vm list-skus --location <authorized-region> --resource-type virtualMachines --all "
            "--subscription <authorized-subscription> and az vm list-usage with the same location/subscription. "
            "Check NotAvailableForSubscription/restrictions and requested zones, plus current usage + aggregate "
            "required demand <= limit for family, total regional vCPUs and VM count. Unknown, missing data, "
            "denied queries and quota zero with positive demand do NOT pass. "
            "For unsupported targets evaluate alternatives WITHIN authorized read-only region scope first; outside "
            "that scope prepare a consolidated target/design recommendation, not unauthorized queries. "
            "Do not force quota/support remediation for the first failing region when an acceptable alternative "
            "may exist. Do not silently change region, hosting service, security, residency, reliability or costs. "
            "Refresh after capacity/provider failure. What-if is not allocation/capacity proof. Availability/quota "
            "checks reduce predictable failures but cannot reserve live capacity.\n"
            "Write regionalReadiness in 00-region-availability.json with scope:<EXACT preparation scope>, "
            "checkedAtUtc:<actual timezone-aware check time>, infrastructureFingerprint:<current hash from "
            "azure_context.infrastructure_fingerprint(Path(scenario)) using scripts on Python import path>, "
            "checks:[{service:<catalog ID or supporting-service ID>,resourceType:<actual ARM type>,"
            "sku:<exact SKU or explicit not-applicable>,region:<authorized region>,status:passed|blocked|unknown,"
            "evidence:[<specific real command/results>],quotas:[{name:<provider quota name>,limit:<number>,"
            "currentValue:<number>,required:<additional aggregate demand>}]}]. Include EVERY selected and supporting "
            "resource/SKU, including separate Foundry model/feature checks. For global resources record the "
            "authorized deployment region and explicit evidence explaining nonregional applicability. "
            "Cosmos account checks additionally need zoneRedundant:<actual bool from IaC> and properties:<actual "
            "location response properties>. Compute VM/VMSS checks additionally need vmFamily:<exact family>, "
            "restrictions:[], zonesSupported:true for requested placement, demand:{vcpus:<aggregate int>,"
            "instances:<aggregate int>} and quota records named <vmFamily>, cores, virtualMachines. "
            "App Service plan checks require actual Microsoft.Web quota records. Demand includes proposed max "
            "instances/temporary rollout nodes, not merely one initial instance. Never fabricate observations. "
            "The backend rejects missing, stale (>15 minutes), changed-infrastructure, wrong-scope, blocked or "
            "unknown evidence before consent/deployment. Keep existing region candidate/rejection evidence too.\n"
    )


def instruction(operation: dict) -> str:
    if operation["name"] == "reconcile-local":
        return (
            "\nBACKEND-OWNED LOCAL PROJECT RESUMPTION: inventory and recover intake ONLY. "
            "This is the SAME existing scenario, not a new adaptation. Preserve its slug and reference files. "
            "Read requirements, architecture, scenario-manifest.json, azure.yaml, infrastructure and project "
            "metadata as evidence; do not read credentials, .env, token caches or secret values. "
            "Do not rewrite the reference, implement, query Azure, deploy or compose packages. "
            "Recover the existing business story, industry, businessUnits, services, pillars and domains using "
            "current repository catalogs. Prefer explicit requirements over inferred needs-review metadata. "
            "Map an unambiguous legacy label to its exact current catalog value and cite that evidence. "
            "Do not invent a story, silently drop services or change security. For absent businessUnits use "
            "the documented Generic fallback and record that limitation. Truly ambiguous business scope "
            "must be reported as a job error with exact missing evidence, not guessed. "
            "Inventory ALL existing service dependencies for upfront readiness. "
            "Write JSON to the exact backend-provided recovery output path with fields projectSlug, prompt, "
            "industry, businessUnits, services, pillars, domains and recoveryEvidence:[specific artifact references "
            "and recovered facts]. Use exact catalog IDs, prompt at most 6000 characters. "
            "Do not include secrets, authorization scopes, approval records or stage-completion claims. "
            "Do not report stages through portal_workflow.py for this inventory job. Return after writing. "
            "The backend validates the intake and toolchain, then assigns evidence-based reconciliation of "
            "each stage. Reuse working assets rather than scaffold over them. File presence and legacy "
            "packages do not prove validation, design confirmation, deployment or suitability approval.\n"
        )
    if operation["name"] == "question-review":
        return (
            "\nBACKEND-OWNED QUESTION REVIEW: perform only classification, not implementation or cloud calls.\n"
            f"Read canonical state for decision {operation['decisionId']}. Read original intake, ALL answered "
            "decisions and relevant scenario evidence before classifying. Do not ask the user to classify it. "
            "Technical design choices with viable defaults, tool use already authorized, generated IDs/endpoints/"
            "receipts, missing pre-creation values and matters answered in intake/history belong to the backend. "
            "For these, record disposition:technical with an explicit next action; do NOT choose a user answer, "
            "invent IDs/evidence, change selected services/security or grant permissions. Actual prerequisite "
            "failures/host denials belong to external-blocker with observed evidence, not a questionnaire. "
            "Only genuinely unresolved business scope or material security trade-offs reach the user. "
            "Unknown/insufficient evidence is a job error, not permission to expose an unclassified question. "
            "Never convert a missing cloud/directory authorization into technical approval. Preserve design, "
            "exact-target consent, suitability and confirmed decisions. If authorization is needed, resolution "
            "must direct the next operation to the existing scoped authorization path, not execute it.\n"
            "For a technical question interrupting a cloud stage, the backend requires refreshed preparation "
            "and renewed exact-target consent before using an older deployment grant. Classification is not retry consent.\n"
            "Report using portal_workflow.py report --event <JSON-file> --revision <current>, with "
            f"stage:{operation['stages'][0]}, decisionReview:{{decisionId:{operation['decisionId']}, "
            "disposition:technical|business|external-blocker, reason:<classification rationale>, "
            "evidence:[<specific intake/history/artifact or observed diagnostic references>]}. "
            "technical additionally requires resolution:<implementation-owned next action>. "
            "business additionally requires unresolvedNeed:<business/security ambiguity>, "
            "intakeEvidence:<why saved input/answers do not resolve it>, "
            "choiceImpacts:{<each original choice>:<distinct business/security consequence>}; at least two choices. "
            "external-blocker additionally requires blocker:{kind:prerequisite|host-permission, "
            "observedFailure:<actual failed check/result>, action:<specific external fix>, "
            "verification:<exact read-only verification>}. Return immediately after the accepted report. "
            "Do not make a new decision or report any stage complete.\n"
        )
    return (
        "\nBACKEND-OWNED BOUNDED JOB (takes precedence over general continuation instructions):\n"
        f"Assigned operation: {operation['name']}. Allowed reporting stages: {operation['stages']}.\n"
        "Perform ONLY this operation. Read persisted artifacts/decisions; do not repeat completed work. "
        "The Python backend owns prerequisite checks, owner-bound receipts, stage selection and continuation. "
        "For imported local projects, revalidate the assigned existing artifacts without restarting or "
        "scaffolding over the solution. Reuse correct files and report actual fresh evidence; repair only gaps. "
        "Do not ask users for technical readiness approval or run the full tool audit again at job start. "
        "Backend receipts may be refreshed by check_prerequisites.py only if expired or dependencies change. "
        "Report actual evidence through portal_workflow.py. Finish this operation and return; the backend "
        "will automatically select the next operation without user approval. Do not perform the next stage. "
        "Architecture must end with its structured design decision; target-review must direct the user to "
        "the Azure readiness card (no account-ID questionnaire). Deployment-decision must use retained "
        "actual what-if/cost evidence and the authorized preparation scope. "
        "Solution-created client IDs, object IDs, endpoints and installation receipts are deployment outputs, "
        "not user inputs. Never request them in a business decision or manual receipt questionnaire. "
        "Plan and wire idempotent creation/output capture through the authorized deployment. Missing IDs before "
        "creation must not block independent read-only preparation; mark identity-dependent checks pending. "
        "Do not fabricate IDs, treat ARM what-if as Graph permission or bypass actual tenant restrictions. "
        "For verify-blocker, verify it, report pending with actual setupVerification evidence, and return. "
        "Never infer stage completion from files or exit status. Missing evidence is a product/job error, "
        "Proposed business questions are held internally for backend classification; do not ask the user "
        "to judge their importance. Resolve routine implementation choices from intake, history and evidence. "
        "not a new user permission request. Real changed business/security decisions and real host denials "
        "still stop; do not bypass them.\n"
        + (f"Preparation reports MUST include operation:deployment-preparation and scope:{json.dumps(operation['scope'])}.\n"
           if operation.get("operation") == "deployment-preparation" else "")
        + (regional_instruction() if operation["name"] in {
            "deployment-preparation", "deployment-decision", "deployment",
        } else "")
    )


def validate_completed(root: Path, scenario: Path, operation: dict) -> list[str]:
    stage = operation["name"]
    required = {
        "requirements": ["01-requirements.md"],
        "architecture": ["02-architecture-assessment.md", "00-region-availability.json"],
        "diagrams": ["03-architect-diagram.png", "04-runtime-diagram.png"],
        "bicep": ["azure.yaml", "infra/main.bicep"],
    }.get(stage, [])
    for relative in required:
        path = scenario / relative
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Completed {stage} is missing required nonempty artifact {relative}.")
        if path.suffix == ".png":
            header = path.read_bytes()[:24]
            if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or not all(struct.unpack(">II", header[16:24])):
                raise ValueError(f"Diagram is not a nonempty PNG: {relative}.")
    environment = execution_environment(root)
    commands = []
    if stage in {"application", "local-validation"}:
        projects = list((scenario / ("src" if stage == "application" else "tests")).rglob("*.csproj"))
        if not projects:
            raise ValueError(f"Completed {stage} has no project under {'src' if stage == 'application' else 'tests'}.")
        dotnet = shutil.which("dotnet", path=environment["PATH"])
        if not dotnet:
            raise ValueError(".NET SDK disappeared before backend application validation.")
        for project in projects:
            commands.extend([
                [dotnet, "restore", str(project), "--configfile", str(root / "NuGet.Config"), "-p:NuGetAudit=false"],
                [dotnet, "build" if stage == "application" else "test", str(project), "--no-restore", "--nologo"],
            ])
    with tempfile.TemporaryDirectory(prefix="abc-operation-validation-") as directory:
        if stage == "bicep":
            az = shutil.which("az", path=environment["PATH"])
            if not az:
                raise ValueError("Azure CLI disappeared before backend Bicep validation.")
            source = str(scenario / "infra" / "main.bicep")
            commands.extend([
                [az, "bicep", "build", "--file", source, "--outfile", str(Path(directory) / "main.json")],
                [az, "bicep", "lint", "--file", source],
            ])
        evidence = []
        for command in commands:
            try:
                result = subprocess.run(
                    command, env=environment, cwd=scenario, capture_output=True, text=True, encoding="utf-8",
                    timeout=240, check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError(f"Backend {stage} validation could not complete: {error}") from error
            output = (result.stdout + result.stderr)[-3500:]
            if result.returncode:
                raise ValueError(f"Backend {stage} validation failed: {subprocess.list2cmdline(command)}\n{output}")
            evidence.append(f"{subprocess.list2cmdline(command)}\nExit 0\n{output}")
    return evidence
