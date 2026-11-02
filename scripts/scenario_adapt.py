"""Preview and prepare isolated scenario adaptations without inheriting runtime or consent state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import scenario_catalog
from portal_status import ROOT, scenario_state

DOCUMENTS = {
    "01-requirements.md", "02-architecture-assessment.md", "04-implementation-plan.md",
    "03-architect-diagram.py", "04-runtime-diagram.py", "azure.yaml",
}
EXTENSIONS = {
    ".bicep", ".cs", ".csproj", ".sln", ".slnx", ".props", ".targets", ".html", ".css", ".js", ".ts",
    ".tsx", ".jsx", ".json", ".csv", ".txt", ".md", ".py", ".ps1", ".sh", ".yaml", ".yml", ".toml",
    ".razor", ".cshtml", ".resx", ".svg", ".png", ".jpg", ".jpeg", ".ico", ".webp", ".woff", ".woff2",
    ".mjs", ".cjs", ".sql",
}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".ico", ".webp", ".woff", ".woff2"}
EXCLUDED = {
    "bin", "obj", "node_modules", "__pycache__", "venv", "packages", "evidence", "secrets",
    "credentials", "logs", "testresults", "dist", "build",
}
SENSITIVE_NAMES = re.compile(
    r"appsettings|local\.settings|credentials?|secrets?|tokens?|workflow.state|validation|"
    r"receipt|approval|consent|deployment|runtime|region.availability|\.parameters\.", re.IGNORECASE,
)
SECRET = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"(?:AccountKey|SharedAccessSignature|client_secret|api[_-]?key|password)\s*[\"']?\s*[:=]\s*[\"']?"
    r"(?!\s|[\"']|\$\{|<|@|null\b|false\b|true\b)[A-Za-z0-9+/=_-]{16,}",
    re.IGNORECASE,
)


def bounded_text(path: Path, base: Path, limit: int = 65536) -> str:
    if path.resolve() != base.resolve() / path.relative_to(base):
        raise ValueError(f"Adaptation input must not contain nested links: {path.name}")
    if path.stat().st_size > limit:
        raise ValueError(f"Adaptation input exceeds {limit} bytes: {path.name}")
    return path.read_text(encoding="utf-8-sig")


def candidates(folder: Path) -> dict[str, bytes]:
    """Return bounded source files; exclusions are not a substitute for the agent's credential review."""
    result = {}

    def include(path: Path) -> None:
        relative = path.relative_to(folder)
        if path.resolve() != folder.resolve() / relative:
            raise ValueError(f"Reusable artifacts must not contain nested links: {relative}")
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError(f"Reusable artifact exceeds 2 MiB: {relative}")
        content = path.read_bytes()
        if path.suffix.lower() not in BINARY_EXTENSIONS and SECRET.search(content.decode("utf-8-sig")):
            raise ValueError(f"Potential credential in reusable artifact {relative}; remove it before reuse.")
        result[relative.as_posix()] = content
        if len(result) > 1000 or sum(len(value) for value in result.values()) > 25 * 1024 * 1024:
            raise ValueError("Reusable artifacts exceed the 1000-file / 25 MiB limit.")

    for name in sorted(DOCUMENTS):
        path = folder / name
        if path.is_file():
            include(path)
    for name in ("infra", "src"):
        directory = folder / name
        if not directory.is_dir() or directory.resolve() != folder.resolve() / name:
            raise ValueError(f"Source requires an unlinked {name} directory.")
        for current, directories, files in os.walk(directory, followlinks=False):
            parent = Path(current)
            for entry in list(directories):
                path = parent / entry
                if entry.startswith(".") or entry.lower() in EXCLUDED:
                    directories.remove(entry)
                elif path.resolve() != folder.resolve() / path.relative_to(folder) or path.is_symlink():
                    raise ValueError(f"Reusable artifacts must not contain nested links: {path.relative_to(folder)}")
            for entry in sorted(files):
                path = parent / entry
                if name == "infra" and path.suffix.lower() == ".json" and path.with_suffix(".bicep").is_file():
                    continue
                if (entry.startswith(".") or SENSITIVE_NAMES.search(entry)
                        or (path.suffix.lower() not in EXTENSIONS and entry != "Dockerfile")):
                    continue
                include(path)
    return result


def preview(root: Path, source_id: object) -> tuple[dict, dict[str, bytes]]:
    if not scenario_catalog.valid_slug(source_id):
        raise ValueError("Choose a valid source scenario.")
    entry = next((item for item in scenario_catalog.discover(root)["scenarios"] if item["id"] == source_id), None)
    if entry is None or not entry["available"]:
        raise ValueError("Source scenario is unavailable. Refresh its local manifest and reference files.")
    folder = root / "generated-scenarios" / source_id
    files = candidates(folder)
    saved = scenario_state(root, source_id)
    request_path = saved / "request.json"
    request = json.loads(bounded_text(request_path, saved)) if request_path.is_file() else {}
    if not isinstance(request, dict):
        raise ValueError("Source request must be a JSON object.")
    notes = saved / "scoping.md"
    requirements = folder / "01-requirements.md"
    brief = (bounded_text(notes, saved) if notes.is_file() else
             bounded_text(requirements, folder) if requirements.is_file() else entry["summary"])
    prompt = request.get("prompt") or entry["summary"]
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 6000:
        raise ValueError("Source prompt must contain 1-6000 characters.")
    pattern = request.get("agenticPattern", "ai-decides")
    patterns = scenario_catalog.read_json(root / "portal" / "catalog.json")["agenticPatterns"]
    if pattern not in {item["id"] for item in patterns}:
        raise ValueError("Source pattern is no longer in the intake catalog; review its saved brief.")
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}
    snapshot = {
        "files": hashes, "brief": brief, "prompt": prompt.strip(), "agenticPattern": pattern,
    }
    return {
        "scenarioId": source_id, "manifestDigest": entry["manifestDigest"],
        "artifactsDigest": scenario_catalog.digest(snapshot), "metadataStatus": entry["metadataStatus"],
        "title": entry["title"], "brief": brief, "files": hashes,
        "intake": {
            "prompt": prompt.strip(), "agenticPattern": pattern,
            **{key: entry[key] for key in ("industry", "businessUnits", "services", "pillars", "domains")},
        },
    }, files


def select(root: Path, value: object, target: str) -> dict:
    if not scenario_catalog.valid_slug(target):
        raise ValueError("Choose a valid new target slug.")
    if not isinstance(value, dict) or set(value) != {"scenarioId", "manifestDigest", "artifactsDigest"}:
        raise ValueError("Select a source scenario and review its brief before saving.")
    if value["scenarioId"] == target:
        raise ValueError("An adaptation needs a different new project slug.")
    current, _ = preview(root, value["scenarioId"])
    if any(value[key] != current[key] for key in value):
        raise ValueError("Source brief or artifacts changed. Reload the source and review your changes before saving.")
    return {key: current[key] for key in value}


def reuse_selection(root: Path, slug: str) -> dict | None:
    """Read an explicit late source decision without rewriting the original intake."""
    saved = scenario_state(root, slug)
    path = saved / "reuse-selection.json"
    if not path.exists():
        return None
    value = json.loads(bounded_text(path, saved))
    if (not isinstance(value, dict) or value.get("schemaVersion") != 1
            or value.get("projectSlug") != slug
            or not isinstance(value.get("id"), str) or not re.fullmatch(r"[a-f0-9]{32}", value["id"])
            or value.get("status") not in {"pending-review", "reviewed"}
            or not isinstance(value.get("selectedBriefFingerprint"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", value["selectedBriefFingerprint"])):
        raise ValueError("Invalid late reuse selection. Review the saved source decision.")
    return value


def review_selection(root: Path, slug: str) -> dict:
    """Bind the agent's revised brief to the user's explicit source decision, not to approval."""
    saved = scenario_state(root, slug)
    value = reuse_selection(root, slug)
    if value is None:
        raise ValueError("No explicit late source selection has been recorded.")
    if value.get("source") is not None:
        select(root, value["source"], slug)
    text = bounded_text(saved / "scoping.md", saved)
    fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if fingerprint == value["selectedBriefFingerprint"] or f"Reuse selection: {value['id']}" not in text:
        raise ValueError("Revise scoping.md with the source assessment and exact Reuse selection marker first.")
    value.update(status="reviewed", reviewedBriefFingerprint=fingerprint)
    scenario_catalog.write_json(saved / "reuse-selection.json", value)
    return value


def effective_request(root: Path, slug: str) -> dict:
    """Resolve late reuse only after a fresh, matching brief confirmation."""
    saved = scenario_state(root, slug)
    request = json.loads(bounded_text(saved / "request.json", saved))
    if not isinstance(request, dict) or request.get("projectSlug") != slug:
        raise ValueError("Adaptation request must be a JSON object for this target slug.")
    decision = reuse_selection(root, slug)
    if decision is not None:
        text = bounded_text(saved / "scoping.md", saved)
        fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
        response = json.loads(bounded_text(saved / "scoping-response.json", saved))
        if (decision["status"] != "reviewed" or decision.get("reviewedBriefFingerprint") != fingerprint
                or not isinstance(response, dict) or response.get("fingerprint") != fingerprint
                or response.get("decision") != "confirmed"
                or response.get("continuation", {}).get("status") != "dispatched"):
            raise ValueError("Late reuse selection needs agent assessment and fresh dispatched brief confirmation.")
        request.pop("reuseSource", None)
        if decision.get("source") is not None:
            request["reuseSource"] = select(root, decision["source"], slug)
    return request


def prepare(root: Path, slug: str) -> dict:
    """Populate only an empty target workspace, preserving source and per-file baseline hashes."""
    request = effective_request(root, slug)
    source = select(root, request.get("reuseSource"), slug)
    snapshot, files = preview(root, source["scenarioId"])
    if any(snapshot[key] != source[key] for key in source):
        raise ValueError("Source artifacts changed during preparation. Review the source again.")
    target = root / "generated-scenarios" / slug
    if not target.is_dir():
        raise ValueError("Create the new empty workspace with New-AzdScenarioWorkspace.ps1 before preparation.")
    if any(target.iterdir()):
        raise ValueError("Adaptation preparation requires an empty target; never overwrite existing work.")
    receipt = {
        "schemaVersion": 1, "source": source, "files": snapshot["files"],
        "status": "pending-reconciliation",
        "excluded": "No deployment/runtime evidence, packages, environment settings, credentials or approvals.",
    }
    # Reserve the workspace before writing; an interrupted copy stays visibly incomplete and cannot be retried over.
    scenario_catalog.write_json(target / "adaptation-baseline.json", {**receipt, "status": "copying"})
    for name, content in files.items():
        path = target / Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    scenario_catalog.refresh(target, request=request)
    scenario_catalog.write_json(target / "adaptation-baseline.json", receipt)
    return receipt


def reconcile(root: Path, slug: str, decisions: dict) -> dict:
    """Verify every baseline file against explicit keep/change/remove decisions."""
    if not scenario_catalog.valid_slug(slug):
        raise ValueError("Choose a valid target slug.")
    target = root / "generated-scenarios" / slug
    baseline = json.loads(bounded_text(target / "adaptation-baseline.json", target, 256000))
    if (not isinstance(baseline, dict) or baseline.get("schemaVersion") != 1
            or baseline.get("status") != "pending-reconciliation" or not isinstance(baseline.get("files"), dict)):
        raise ValueError("A complete adaptation baseline is required before reconciliation.")
    if not isinstance(decisions, dict) or set(decisions) != set(baseline["files"]):
        raise ValueError("Provide exactly one keep/change/remove decision for every baseline file.")
    actual = candidates(target)
    for name, old_hash in baseline["files"].items():
        decision = decisions[name]
        if (not isinstance(decision, dict) or decision.get("action") not in {"keep", "change", "remove"}
                or not isinstance(decision.get("reason"), str) or not decision["reason"].strip()):
            raise ValueError(f"Provide an action and business/technical reason for {name}.")
        exists = name in actual
        unchanged = exists and hashlib.sha256(actual[name]).hexdigest() == old_hash
        action = decision["action"]
        if (action == "keep" and not unchanged or action == "change" and (not exists or unchanged)
                or action == "remove" and (target / name).exists()):
            raise ValueError(f"Artifact does not match its {action} decision: {name}")
    report = {
        "schemaVersion": 1, "source": baseline["source"], "decisions": decisions,
        "files": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(actual.items())},
        "status": "reconciled-local-files", "runtimeValidated": False,
    }
    scenario_catalog.write_json(target / "adaptation-reconciliation.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preview", "prepare", "reconcile", "review-selection", "effective-request"])
    parser.add_argument("scenario", help="Source slug for preview; new target slug for prepare.")
    parser.add_argument("--decisions", type=Path, help="Per-baseline-file action/reason JSON for reconcile.")
    args = parser.parse_args()
    try:
        if args.command == "reconcile":
            if args.decisions is None:
                raise ValueError("Reconcile requires --decisions with reviewed per-file actions and reasons.")
            value = reconcile(ROOT, args.scenario, scenario_catalog.read_json(args.decisions))
        elif args.decisions is not None:
            raise ValueError("--decisions is only supported by reconcile.")
        else:
            functions = {"prepare": prepare, "review-selection": review_selection, "effective-request": effective_request}
            value = (preview(ROOT, args.scenario)[0] if args.command == "preview"
                     else functions[args.command](ROOT, args.scenario))
        print(json.dumps(value, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Scenario adaptation: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
