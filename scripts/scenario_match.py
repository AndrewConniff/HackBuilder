"""Build explicit, evidence-backed reuse profiles and rank local catalog suggestions without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import scenario_adapt
import scenario_catalog

PROFILE_DIR = "reuse-profiles"
INDEX = "reuse-profiles.json"
VERSION = 1
EXTRACTOR_VERSION = 2
# These are observable retrieval features, not an architectural verdict or proof of a running implementation.
FEATURES = {
    "routing-triage": ("Routing / triage", r"\b(?:rout(?:e|es|ing)|triage|classif(?:y|ication)|sentiment)\b"),
    "handoff-transfer-of-control": ("Case handoff", r"\b(?:handoff|escalat\w*|transfer of control)\b"),
    "sequential-pipeline": ("Sequential pipeline", r"\b(?:sequential|pipeline|ordered stages)\b"),
    "concurrent-fan-out-fan-in": ("Parallel evidence checks", r"\b(?:fan.out|fan.in|parallel checks|concurrent)\b"),
    "orchestrator-workers": ("Orchestrator / workers", r"\b(?:orchestrator.workers|orchestrat\w*|supervisor)\b"),
    "planner-executor": ("Plan then execute", r"\b(?:planner.executor|execution plan|planning agent)\b"),
    "event-driven-reactive-agents": ("Event-driven workflow", r"\b(?:event.driven|service.bus|queue|webhook)\b"),
    "human-in-the-loop": ("Human decision gate", r"\b(?:human.{0,12}(?:review|approv|decision)|hitl|approval)\b"),
    "grounded-retrieval": ("Grounded document retrieval", r"\b(?:grounding|grounded|retriev\w*|rag|citations?)\b"),
    "telemetry": ("Telemetry / sensor processing", r"\b(?:telemetry|sensors?|event telemetry)\b"),
    "inventory": ("Stock / inventory workflow", r"\b(?:inventory|stock|replenish\w*|spoilage|recipes?)\b"),
    "case-management": ("Case / ticket management", r"\b(?:tickets?|cases?|helpdesk|service.desk)\b"),
    "reconciliation": ("Reconciliation / daily close", r"\b(?:reconcil\w*|daily close|p&l|profit.and.loss)\b"),
    "multilingual": ("Multilingual interaction", r"\b(?:multilingual|translation|translate|languages)\b"),
    "read-tools": ("Tool-backed assistance", r"\b(?:function.tool|tool.call|tool.loop|function.call)\b"),
    "approved-write-actions": ("Consequential write actions", r"\b(?:write.actions?|place.order|create.order|submit.order)\b"),
    "private-network": ("Private network boundary", r"\b(?:private.endpoint|private.ingress|publicnetworkaccess.{0,8}disabled)\b"),
    "public-ingress": ("Public ingress", r"\b(?:public.ingress|public.endpoint|publicnetworkaccess.{0,8}enabled)\b"),
    "entra-identity": ("Entra identity", r"\b(?:entra|azuread|azure.ad|openidconnect)\b"),
    "local-identity": ("Local application accounts", r"\b(?:local.accounts?|local.role.scoped|passwordhasher)\b"),
    "tenant-isolation": ("Tenant / site isolation", r"\b(?:tenant.isolat\w*|site.isolat\w*|store.scoped)\b"),
    "replay-recovery": ("Replay / recovery handling", r"\b(?:idempot\w*|replay|deduplic\w*|retry.policy)\b"),
    "read-only": ("Read-only assistance", r"\b(?:read.only|advice.only|no (?:writes?|write.actions?))\b"),
    "single-agent-tool-loop": ("Single-agent tool loop", r"\b(?:single.agent|tool.loop|function.call)\b"),
    "moderated-group-chat": ("Moderated agent discussion", r"\b(?:moderated.group.chat|moderator)\b"),
    "magentic-dynamic-collaboration": ("Dynamic collaboration", r"\b(?:magentic|dynamic.collaboration)\b"),
    "supervisor-hierarchical-delegation": ("Hierarchical supervisor", r"\b(?:hierarchical|supervisor)\b"),
    "deterministic-loop": ("Bounded deterministic loop", r"\b(?:deterministic.loop|bounded.loop)\b"),
    "evaluator-optimizer-reflection": ("Evaluate and improve", r"\b(?:evaluator|optimizer|reflection)\b"),
    "mixture-of-agents": ("Mixture of agents", r"\bmixture.of.agents\b"),
    "blackboard-shared-workspace": ("Shared blackboard", r"\b(?:blackboard|shared.workspace)\b"),
    "swarm-peer-to-peer": ("Peer collaboration", r"\b(?:swarm|peer.to.peer)\b"),
    "adaptive-hybrid-composite": ("Adaptive composite", r"\b(?:adaptive.hybrid|hybrid.composite)\b"),
}
CONSTRAINTS = {"private-network", "public-ingress", "entra-identity", "local-identity", "tenant-isolation"}
GENERIC = {"foundry", "agent", "agents", "assistant", "scenario", "azure", "business", "user", "users",
           "with", "that", "this", "from", "using", "should", "would", "could", "build", "create", "help"}


def signals(text: str) -> set[str]:
    result = {key for key, (_, pattern) in FEATURES.items() if re.search(pattern, text, re.IGNORECASE)}
    if re.search(r"\b(?:no|disable[ds]?|without)\s+public\s+(?:endpoints?|ingress|access)\b", text, re.IGNORECASE):
        result.discard("public-ingress")
        result.add("private-network")
    if "read-only" in result:
        result.discard("approved-write-actions")
    return result


def tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]{4,}", text.lower()) if word not in GENERIC}


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_profile(path: Path, base: Path, slug: str) -> dict:
    value = json.loads(scenario_adapt.bounded_text(path, base, 256000))
    validate_profile(value, slug)
    return value


def evidence_files(folder: Path) -> tuple[dict[str, bytes], int]:
    """Read only bounded design/code text, excluding configuration, evidence, binaries and nested links."""
    result, omitted = {}, 0
    extensions = {".md", ".cs", ".py", ".ts", ".js", ".bicep", ".yaml", ".yml"}
    paths = [folder / name for name in sorted(scenario_adapt.DOCUMENTS) if (folder / name).is_file()]
    for name in ("infra", "src"):
        directory = folder / name
        if not directory.is_dir() or directory.resolve() != folder.resolve() / name:
            raise ValueError(f"Profile evidence requires an unlinked {name} directory.")
        for current, directories, files in os.walk(directory, followlinks=False):
            parent = Path(current)
            for entry in list(directories):
                path = parent / entry
                if entry.startswith(".") or entry.lower() in scenario_adapt.EXCLUDED:
                    directories.remove(entry)
                elif path.resolve() != folder.resolve() / path.relative_to(folder) or path.is_symlink():
                    raise ValueError("Profile evidence must not contain nested links.")
            paths.extend(parent / entry for entry in sorted(files)
                         if not entry.startswith(".") and not scenario_adapt.SENSITIVE_NAMES.search(entry)
                         and Path(entry).suffix.lower() in extensions)
            if len(paths) > 200:
                raise ValueError("Profile extraction exceeds 200 text files; reduce source inputs before enrichment.")
    for path in sorted(paths):
        if path.suffix.lower() not in extensions:
            continue
        relative = path.relative_to(folder)
        if path.resolve() != folder.resolve() / relative:
            raise ValueError("Profile evidence must not contain nested links.")
        if path.stat().st_size > 256000:
            omitted += 1
            continue
        content = path.read_bytes()
        text = content.decode("utf-8-sig")
        if scenario_adapt.SECRET.search(text):
            raise ValueError(f"Potential credential in profile evidence {relative}; review before enrichment.")
        result[relative.as_posix()] = content
        if sum(len(content) for content in result.values()) > 4 * 1024 * 1024:
            raise ValueError("Profile extraction exceeds 4 MiB; reduce source inputs before enrichment.")
    return result, omitted


def enrich(root: Path, slug: str) -> dict:
    entry = next((item for item in scenario_catalog.discover(root)["scenarios"] if item["id"] == slug), None)
    if not entry or not entry["available"]:
        raise ValueError("Enrichment requires an available local reference with infrastructure and application files.")
    folder = root / "generated-scenarios" / slug
    files, omitted = evidence_files(folder)
    inputs, found = {}, {}
    for name, content in sorted(files.items()):
        inputs[name] = sha(content)
        basis = "design" if name.endswith(".md") else "code"
        for number, line in enumerate(content.decode("utf-8-sig").splitlines(), 1):
            for key in signals(line):
                evidence = found.setdefault(key, [])
                if sum(ref["basis"] == basis for ref in evidence) < 4:
                    evidence.append({"path": name, "line": number, "basis": basis})
    value = {
        "schemaVersion": VERSION, "scenarioId": slug, "manifestDigest": entry["manifestDigest"],
        "summary": entry["summary"], "metadataStatus": "needs-review",
        "extractedAtUtc": datetime.now(timezone.utc).isoformat(), "extractorVersion": EXTRACTOR_VERSION,
        "features": found, "inputs": inputs,
        "architectureSummary": "; ".join(FEATURES[key][0] for key in sorted(found)) or "Unknown; review required.",
        "patternEvidence": {
            "designMentioned": sorted(key for key, refs in found.items() if any(ref["basis"] == "design" for ref in refs)),
            "codeMentioned": sorted(key for key, refs in found.items() if any(ref["basis"] == "code" for ref in refs)),
            "implemented": "unknown-until-reviewed",
        },
        "omittedLargeTextFiles": omitted,
        "dimensions": {
            "businessCapabilities": sorted(set(found) - CONSTRAINTS),
            "dataPatterns": sorted(set(found) & {"grounded-retrieval", "telemetry", "replay-recovery"}),
            "integrationModes": sorted(set(found) & {"read-tools", "approved-write-actions", "read-only",
                                                     "event-driven-reactive-agents"}),
            "humanDecisionPoints": sorted(set(found) & {"human-in-the-loop", "handoff-transfer-of-control"}),
            "constraints": sorted(set(found) & CONSTRAINTS),
        },
        "limitations": [
            "Text-derived retrieval features require review; code references are not runtime validation.",
            "An absent feature means unknown, not unsupported. No deployment or consent evidence is included.",
            f"{omitted} text files over 256000 bytes were omitted; environment settings and runtime evidence are excluded.",
        ],
    }
    base = root / "scenarios" / PROFILE_DIR
    base.mkdir(parents=True, exist_ok=True)
    if base.resolve() != root.resolve() / "scenarios" / PROFILE_DIR:
        raise ValueError("Profile storage must not contain links.")
    path = base / f"{slug}.json"
    if path.exists() and path.resolve() != base.resolve() / path.name:
        raise ValueError("Reuse profile must be an unlinked metadata file.")
    scenario_catalog.write_json(path, value)
    return load_profile(path, root / "scenarios", slug)


def review(root: Path, slug: str, decision: dict) -> dict:
    """Apply an explicit evidence review; extraction alone never marks a profile curated."""
    path = root / "scenarios" / PROFILE_DIR / f"{slug}.json"
    value = load_profile(path, root / "scenarios", slug)
    if set(decision) != {"profileDigest", "keptFeatures", "implementedPatterns", "architectureSummary"}:
        raise ValueError("Provide profileDigest, keptFeatures, implementedPatterns and architectureSummary.")
    if decision["profileDigest"] != scenario_catalog.digest(value):
        raise ValueError("The extracted profile changed. Review the current evidence before curating.")
    entry = next((item for item in scenario_catalog.discover(root)["scenarios"] if item["id"] == slug), None)
    if not entry or freshness(root, entry, value) != "current":
        raise ValueError("Enrich the changed source again before reviewing its profile.")
    kept, implemented, summary = (decision[key] for key in ("keptFeatures", "implementedPatterns", "architectureSummary"))
    if (not isinstance(kept, list) or any(not isinstance(key, str) or key not in value["features"] for key in kept)
            or not isinstance(implemented, list)
            or any(not isinstance(key, str) or key not in kept
                   or not any(ref["basis"] == "code" for ref in value["features"][key]) for key in implemented)):
        raise ValueError("Keep only evidence-backed features; implemented patterns require inspected code evidence.")
    pattern_ids = {item["id"] for item in scenario_catalog.read_json(root / "portal" / "catalog.json")["agenticPatterns"]}
    if set(implemented) - pattern_ids:
        raise ValueError("Implemented patterns must be actual catalog pattern IDs, not workflow features.")
    if (not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 1200
            or scenario_adapt.SECRET.search(summary)
            or re.search(r"https?://|[A-Za-z]:[\\/]|/subscriptions/|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", summary)):
        raise ValueError("Use a portable architecture summary without endpoints, host paths, cloud identities or secrets.")
    value["features"] = {key: value["features"][key] for key in sorted(set(kept))}
    for key in ("designMentioned", "codeMentioned"):
        value["patternEvidence"][key] = [item for item in value["patternEvidence"][key] if item in kept]
    value["patternEvidence"]["implemented"] = sorted(set(implemented))
    for key, items in value["dimensions"].items():
        value["dimensions"][key] = [item for item in items if item in kept]
    value.update(metadataStatus="curated", architectureSummary=summary.strip(),
                 reviewedAtUtc=datetime.now(timezone.utc).isoformat())
    value["limitations"][0] = "Locally reviewed retrieval metadata is not proof of running implementation."
    scenario_catalog.write_json(path, value)
    return value


def profiles(root: Path) -> tuple[dict, list[dict]]:
    result, errors = {}, []
    path = root / "scenarios" / INDEX
    if path.is_file():
        try:
            value = json.loads(scenario_adapt.bounded_text(path, root / "scenarios", 4 * 1024 * 1024))
            if not isinstance(value, dict) or value.get("schemaVersion") != VERSION or not isinstance(value.get("profiles"), dict):
                raise ValueError("Unsupported portable reuse profile index.")
            # Validate every portable profile using the same schema as local profiles.
            for slug, profile in value["profiles"].items():
                validate_profile(profile, slug)
                result[slug] = profile
        except (OSError, ValueError, TypeError) as error:
            errors.append({"id": "reuse-profiles", "error": str(error)})
    for entry in scenario_catalog.discover(root)["scenarios"]:
        path = root / "scenarios" / PROFILE_DIR / f"{entry['id']}.json"
        if path.is_file():
            try:
                result[entry["id"]] = load_profile(path, root / "scenarios", entry["id"])
            except (OSError, ValueError, TypeError) as error:
                result.pop(entry["id"], None)
                errors.append({"id": entry["id"], "error": str(error)})
    return result, errors


def validate_profile(value: dict, slug: str) -> None:
    if not isinstance(value, dict) or value.get("scenarioId") != slug or not scenario_catalog.valid_slug(slug):
        raise ValueError("Invalid portable reuse profile identity.")
    if (value.get("schemaVersion") != VERSION or value.get("metadataStatus") not in {"needs-review", "curated"}
            or not isinstance(value.get("summary"), str) or len(value["summary"]) > 1200
            or not isinstance(value.get("features"), dict) or set(value["features"]) - FEATURES.keys()
            or not isinstance(value.get("inputs"), dict) or len(value["inputs"]) > 200):
        raise ValueError(f"Invalid portable reuse profile for {slug}.")
    for relative, digest in value["inputs"].items():
        if (not isinstance(relative, str) or not relative or relative.startswith("/")
                or "\\" in relative or ":" in relative
                or any(part in {"", ".", ".."} or part.startswith(".") for part in relative.split("/"))
                or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise ValueError("Invalid portable evidence path.")
    for evidence in value["features"].values():
        if not isinstance(evidence, list) or not evidence or len(evidence) > 8:
            raise ValueError("Invalid portable feature evidence.")
        for item in evidence:
            if (not isinstance(item, dict) or item.get("path") not in value["inputs"]
                    or type(item.get("line")) is not int or item["line"] < 1
                    or item.get("basis") not in {"code", "design"}):
                raise ValueError("Invalid portable feature evidence.")
    if not isinstance(value.get("manifestDigest"), str) or not re.fullmatch(r"[a-f0-9]{64}", value["manifestDigest"]):
        raise ValueError("Invalid portable manifest digest.")
    if (not isinstance(value.get("architectureSummary"), str) or not 1 <= len(value["architectureSummary"]) <= 1600
            or type(value.get("omittedLargeTextFiles")) is not int or value["omittedLargeTextFiles"] < 0
            or not isinstance(value.get("dimensions"), dict)
            or set(value["dimensions"]) != {"businessCapabilities", "dataPatterns", "integrationModes",
                                           "humanDecisionPoints", "constraints"}
            or not isinstance(value.get("patternEvidence"), dict)
            or set(value["patternEvidence"]) != {"designMentioned", "codeMentioned", "implemented"}):
        raise ValueError("Invalid portable architecture dimensions.")
    for entries in [*value["dimensions"].values(), value["patternEvidence"]["designMentioned"],
                    value["patternEvidence"]["codeMentioned"]]:
        if not isinstance(entries, list) or any(not isinstance(key, str) or key not in value["features"] for key in entries):
            raise ValueError("Architecture dimensions must refer to evidence-backed features.")
    implemented = value["patternEvidence"]["implemented"]
    if implemented != "unknown-until-reviewed" and (
        not isinstance(implemented, list) or any(not isinstance(key, str) or key not in value["features"]
                                                for key in implemented)
    ):
        raise ValueError("Invalid implementation evidence classification.")
    extracted = value.get("extractedAtUtc")
    if not isinstance(extracted, str) or datetime.fromisoformat(extracted).tzinfo is None:
        raise ValueError("Reuse profiles require a timezone-aware extraction timestamp.")


def freshness(root: Path, entry: dict, profile: dict) -> str:
    if profile["manifestDigest"] != entry["manifestDigest"] or profile.get("extractorVersion") != EXTRACTOR_VERSION:
        return "stale"
    if not entry["available"]:
        return "unverified"
    folder = root / "generated-scenarios" / entry["id"]
    files, omitted = evidence_files(folder)
    if ({name: sha(content) for name, content in files.items()} != profile["inputs"]
            or omitted != profile.get("omittedLargeTextFiles", 0)):
        return "stale"
    return "current"


def recommend(root: Path, data: dict) -> dict:
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 6000:
        raise ValueError("Describe the target in 1-6000 characters.")
    pattern = data.get("agenticPattern", "ai-decides")
    intake_catalog = scenario_catalog.read_json(root / "portal" / "catalog.json")
    patterns = {item["id"] for item in intake_catalog["agenticPatterns"]}
    if not isinstance(pattern, str) or pattern not in patterns:
        raise ValueError("Choose a known agentic pattern.")
    services = data.get("services", [])
    allowed = {item["id"] for item in intake_catalog["services"]}
    if not isinstance(services, list) or any(not isinstance(item, str) or item not in allowed for item in services):
        raise ValueError("Choose valid service IDs.")
    catalog = scenario_catalog.discover(root)
    stored, errors = profiles(root)
    target = signals(prompt)
    if pattern in FEATURES:
        target.add(pattern)
    matches, states = [], {}
    for entry in catalog["scenarios"]:
        profile = stored.get(entry["id"])
        try:
            state = freshness(root, entry, profile) if profile else "missing"
        except (OSError, ValueError) as error:
            state = "unreadable"
            errors.append({"id": entry["id"], "error": str(error)})
        states[entry["id"]] = state
        reliable = profile is not None and state in {"current", "unverified"}
        observed = set(profile["features"]) if reliable else signals(entry["summary"])
        shared = (target & observed) - CONSTRAINTS
        lexical = tokens(prompt) & tokens(entry["title"] + " " + entry["summary"])
        if not shared and len(lexical) < 2:
            continue
        concerns = []
        conflicts = [("private-network", "public-ingress"), ("entra-identity", "local-identity"),
                     ("read-only", "approved-write-actions")]
        for requested, opposite in conflicts:
            if requested in target and opposite in observed:
                concerns.append(f"Target needs {FEATURES[requested][0]}; source evidence mentions {FEATURES[opposite][0]}.")
        for constraint in sorted(target & CONSTRAINTS):
            if constraint not in observed:
                concerns.append(f"{FEATURES[constraint][0]} is not established by this source profile; verify or adapt.")
        if pattern != "ai-decides" and pattern not in observed:
            concerns.append("The selected runtime pattern is not established by the source profile.")
        if entry["industry"] != data.get("industry"):
            concerns.append("Different industry: adapt personas, business rules, integrations and synthetic data.")
        if state != "current":
            concerns.append(f"Technical profile is {state}; suggestions use catalog text only.")
        if profile and profile["metadataStatus"] != "curated":
            concerns.append("Extracted technical metadata needs review.")
        if entry["metadataStatus"] != "curated":
            concerns.append("Catalog manifest metadata also needs review.")
        if not entry["available"]:
            concerns.append("Reference files are not locally available; inspiration only.")
        score = len(shared) * 4 + min(len(lexical), 4) + (3 if pattern in shared else 0)
        if reliable:
            score += sum(2 for key in shared if any(ref["basis"] == "code" for ref in profile["features"][key]))
        score += len(shared & signals(entry["summary"])) * 2
        score += len((set(services) & set(entry["services"])) - {"foundry"})
        score -= 4 * sum("Target needs " in item for item in concerns)
        if score < 6:
            continue
        matches.append({
            "scenarioId": entry["id"], "title": entry["title"], "summary": entry["summary"],
            "industry": entry["industry"], "available": entry["available"], "manifestDigest": entry["manifestDigest"],
            "metadataStatus": profile["metadataStatus"] if profile else entry["metadataStatus"],
            "catalogMetadataStatus": entry["metadataStatus"],
            "profileState": state,
            "similarity": "Workflow / architecture overlap" if shared else "Business concept overlap",
            "fit": ("Potential starting point" if reliable and profile["metadataStatus"] == "curated"
                    and len(shared) >= 2 and not any("Target needs " in item for item in concerns)
                    else "Fit needs assessment"),
            "reasons": [FEATURES[key][0] for key in sorted(shared)]
                       or ["Shared business concepts: " + ", ".join(sorted(lexical)[:4])],
            "concerns": concerns, "evidence": {
                key: sorted(profile["features"][key], key=lambda ref: ref["basis"] != "code")[:2] for key in sorted(shared)
            } if reliable else {},
            "_score": score,
        })
    matches.sort(key=lambda item: (-item["_score"], not item["available"], item["scenarioId"]))
    cutoff = max(6, matches[0]["_score"] * 0.55) if matches else 6
    selected = [{key: value for key, value in item.items() if key != "_score"}
                for item in matches[:3] if item["_score"] >= cutoff]
    return {
        "schemaVersion": VERSION, "method": "local-catalog", "matches": selected,
        "catalogDigest": scenario_catalog.digest({"catalog": catalog, "profiles": stored, "states": states}),
        "inputDigest": scenario_catalog.digest(data),
        "errors": [*catalog["errors"], *errors],
        "message": "Catalog suggestions, not AI verdicts or proof of technical fit. Refine with AI for deeper assessment.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["enrich", "index", "recommend", "review"])
    parser.add_argument("scenario", nargs="?")
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        root = scenario_catalog.ROOT
        if args.command in {"recommend", "review"}:
            if args.input is None:
                raise ValueError("Recommend/review requires --input pointing to target intake / review JSON.")
            if args.command == "review":
                if not scenario_catalog.valid_slug(args.scenario):
                    raise ValueError("Review requires a scenario slug.")
                value = review(root, args.scenario, scenario_catalog.read_json(args.input))
            else:
                value = recommend(root, scenario_catalog.read_json(args.input))
        else:
            if args.input:
                raise ValueError("--input is only supported for recommend.")
            failures = []
            if args.command == "enrich":
                entries = scenario_catalog.discover(root)
                if entries["errors"]:
                    raise ValueError(f"Fix catalog errors before enrichment: {entries['errors']}")
                ids = [args.scenario] if args.scenario else [item["id"] for item in entries["scenarios"] if item["available"]]
                for slug in ids:
                    try:
                        enrich(root, slug)
                    except (OSError, ValueError) as error:
                        failures.append({"id": slug, "error": str(error)})
            elif args.scenario:
                raise ValueError("Index takes no scenario.")
            values, errors = profiles(root)
            if errors:
                raise ValueError(f"Fix reuse profile errors before indexing: {errors}")
            value = {"schemaVersion": VERSION, "profiles": values}
            (root / "scenarios").mkdir(exist_ok=True)
            scenario_catalog.write_json(root / "scenarios" / INDEX, value)
            for failure in failures:
                print(f"Profile not enriched for {failure['id']}: {failure['error']}", file=sys.stderr)
            if failures:
                print(json.dumps({**value, "enrichmentErrors": failures}, indent=2))
                return 1
        print(json.dumps(value, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Scenario matching: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
