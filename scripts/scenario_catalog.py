"""Maintain portable scenario metadata and a repository index without copying runtime state."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "scenario-manifest.json"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REFERENCE_FILES = (
    "01-requirements.md", "02-architecture-assessment.md", "04-implementation-plan.md",
    "03-architect-diagram.png", "04-runtime-diagram.png", "azure.yaml", "infra", "src",
)
BUSINESS_UNITS = (
    ("generic", "Generic"), ("executives", "Executives"), ("it", "IT"),
    ("operations", "Operations"), ("communications", "Communications"),
    ("executive-assistant", "Executive Assistant"), ("legal", "Legal"), ("hr", "HR"),
    ("business-manager", "Business Manager"), ("finance", "Finance"),
    ("sales", "Sales"), ("marketing", "Marketing"),
)


def business_units(value: object) -> list[str]:
    allowed = {key for key, _ in BUSINESS_UNITS}
    if (
        not isinstance(value, list) or not value
        or any(not isinstance(item, str) or item not in allowed for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError("Business units must be a nonempty list of unique catalog IDs.")
    if "generic" in value and len(value) != 1:
        raise ValueError("Generic cannot be combined with specific business units.")
    return value


def valid_slug(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 40 and SLUG.fullmatch(value) is not None


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must be a JSON object.")
    return value


def industry_choices() -> set[str]:
    with (ROOT / "microsoft_industry_verticals.csv").open(encoding="utf-8-sig", newline="") as stream:
        return {row["Industry"] for row in csv.DictReader(stream)}


def validate(value: dict, slug: str) -> dict:
    if value.get("schemaVersion") != 1 or value.get("id") != slug or not valid_slug(slug):
        raise ValueError("Scenario manifest version or ID is invalid.")
    for field, limit in (("title", 160), ("summary", 1200)):
        if not isinstance(value.get(field), str) or not value[field].strip() or len(value[field]) > limit:
            raise ValueError(f"Manifest {field} must be nonempty text of at most {limit} characters.")
    if value.get("industry") is not None and value["industry"] not in industry_choices():
        raise ValueError("Manifest industry must match the industry catalog.")
    business_units(value.get("businessUnits"))
    catalog = read_json(ROOT / "portal" / "catalog.json")
    for field in ("services", "pillars", "domains"):
        entries = value.get(field)
        allowed = {item["id"] for item in catalog[field]}
        if (
            not isinstance(entries, list)
            or any(not isinstance(item, str) or item not in allowed for item in entries)
            or len(set(entries)) != len(entries)
        ):
            raise ValueError(f"Manifest {field} must contain unique catalog IDs.")
    artifacts = value.get("artifacts")
    if (
        not isinstance(artifacts, list)
        or any(not isinstance(item, str) or item not in REFERENCE_FILES for item in artifacts)
        or len(set(artifacts)) != len(artifacts)
    ):
        raise ValueError("Manifest artifacts must be allowlisted relative reference paths.")
    source = value.get("source")
    if source is not None and (
        not isinstance(source, dict) or set(source) != {"scenarioId", "manifestDigest"}
        or not valid_slug(source.get("scenarioId"))
        or not isinstance(source.get("manifestDigest"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", source["manifestDigest"])
    ):
        raise ValueError("Manifest source must identify the source scenario and its manifest digest.")
    if value.get("metadataStatus") not in {"needs-review", "curated"}:
        raise ValueError("Manifest metadataStatus must be needs-review or curated.")
    return {
        "schemaVersion": 1, "id": slug,
        **{key: value[key] for key in (
            "title", "summary", "industry", "businessUnits", "services", "pillars", "domains",
            "artifacts", "source", "metadataStatus",
        )},
    }


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def inferred(folder: Path, request: dict | None = None) -> dict:
    request = request or {}
    industry = request.get("industry")
    summary = "Locally discovered reference. Review its architecture and metadata before adapting."
    requirements = folder / "01-requirements.md"
    document = ""
    if requirements.is_file():
        if not requirements.resolve().is_relative_to(folder.resolve()):
            raise ValueError("Requirements must resolve inside the reference workspace.")
        if requirements.stat().st_size > 256000:
            raise ValueError("Requirements are too large for metadata inference; provide reviewed metadata.")
        document = requirements.read_text(encoding="utf-8-sig")
    if industry is None and document:
        match = re.search(
            r"^\|\s*(?:\*\*)?Industry(?:\*\*)?\s*\|\s*([^|\n]+)\s*\|",
            document, re.MULTILINE,
        )
        if match:
            industry = match[1].strip()
            if industry not in industry_choices():
                summary += f" Source industry cell requires explicit classification review: {industry[:400]}"
                industry = None
    intake_catalog = read_json(ROOT / "portal" / "catalog.json")
    selections = {}
    for field, row_name in (("services", None), ("pillars", "WAF priorities"), ("domains", "Technical domain")):
        if field in request:
            selections[field] = request[field]
            continue
        if row_name is None:
            selections[field] = [
                item["id"] for item in intake_catalog[field] if re.search(
                    rf"^\|\s*(?:\*\*)?{re.escape(item['name'])}(?:\*\*)?\s*\|", document, re.MULTILINE,
                )
            ]
        else:
            row = re.search(rf"^\|\s*{row_name}\s*\|([^|\n]+)\|", document, re.MULTILINE)
            names = [part.strip() for part in row[1].split(";")] if row else []
            selections[field] = [item["id"] for item in intake_catalog[field] if item["name"] in names]
    return {
        "schemaVersion": 1, "id": folder.name,
        "title": folder.name.replace("-", " ").capitalize(),
        "summary": summary,
        "industry": industry,
        "businessUnits": request.get("businessUnits", ["generic"]),
        **selections,
        "artifacts": [name for name in REFERENCE_FILES if (folder / name).exists()],
        "source": (
            {key: request["reuseSource"][key] for key in ("scenarioId", "manifestDigest")}
            if request.get("reuseSource") else None
        ),
        "metadataStatus": "needs-review",
    }


def refresh(folder: Path, request: dict | None = None, metadata: dict | None = None) -> dict:
    if not folder.is_dir() or not valid_slug(folder.name):
        raise ValueError("Refresh requires an existing scenario folder with a valid project slug.")
    path = folder / MANIFEST
    if path.exists() and not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError("Scenario manifest must resolve inside its reference workspace.")
    value = read_json(path) if path.exists() else inferred(folder, request)
    if path.exists() and value.get("metadataStatus") == "needs-review":
        candidate = inferred(folder, request)
        for field in ("industry", "services", "pillars", "domains"):
            if not value.get(field) and candidate.get(field):
                value[field] = candidate[field]
    if request is not None:
        for field in ("industry", "businessUnits", "services", "pillars", "domains"):
            if field in request:
                value[field] = request[field]
        source = request.get("reuseSource")
        if source:
            value["source"] = {key: source[key] for key in ("scenarioId", "manifestDigest")}
    if metadata is not None:
        unknown = set(metadata) - {
            "title", "summary", "industry", "businessUnits", "services", "pillars", "domains", "metadataStatus",
        }
        if unknown:
            raise ValueError(f"Unknown editable manifest metadata: {', '.join(sorted(unknown))}")
        value.update(metadata)
    value["artifacts"] = [name for name in REFERENCE_FILES if (folder / name).exists()]
    value = validate(value, folder.name)
    write_json(path, value)
    return value


def discover(root: Path = ROOT) -> dict:
    scenarios, errors = [], []
    directory = root / "generated-scenarios"
    if directory.is_dir():
        for folder in sorted(directory.iterdir()):
            if not folder.is_dir() or not valid_slug(folder.name):
                continue
            try:
                path = folder / MANIFEST
                if path.exists() and not path.resolve().is_relative_to(folder.resolve()):
                    raise ValueError("Scenario manifest must resolve inside its reference workspace.")
                value = validate(read_json(path), folder.name) if path.exists() else inferred(folder)
                # Top-level scenario junctions are supported; nested escapes are never reuse inputs.
                base = folder.resolve()
                available = path.is_file() and all(
                    (folder / name).exists() and (folder / name).resolve().is_relative_to(base)
                    for name in value["artifacts"]
                ) and "infra" in value["artifacts"] and "src" in value["artifacts"]
                scenarios.append({**value, "manifestDigest": digest(value), "available": available})
            except (OSError, ValueError, TypeError) as error:
                errors.append({"id": folder.name, "error": str(error)})
    index = root / "scenarios" / "catalog.json"
    if index.is_file():
        try:
            value = read_json(index)
            if value.get("schemaVersion") != 1 or not isinstance(value.get("scenarios"), list):
                raise ValueError("Invalid repository scenario catalog.")
            known = {item["id"] for item in scenarios} | {item["id"] for item in errors}
            for item in value["scenarios"]:
                if not isinstance(item, dict):
                    raise ValueError("Repository scenario entries must be objects.")
                slug = item.get("id")
                if slug not in known:
                    manifest = validate(item, slug)
                    scenarios.append({**manifest, "manifestDigest": digest(manifest), "available": False})
                    known.add(slug)
        except (OSError, ValueError, TypeError) as error:
            errors.append({"id": "repository-catalog", "error": str(error)})
    return {"schemaVersion": 1, "scenarios": scenarios, "errors": errors}


def export_index(root: Path = ROOT) -> dict:
    catalog = discover(root)
    if catalog["errors"]:
        raise ValueError(f"Catalog errors must be fixed before export: {catalog['errors']}")
    # Only portable metadata goes into the repository; no host paths, logs or deployment evidence.
    value = {
        "schemaVersion": 1,
        "scenarios": [
            {key: value for key, value in item.items() if key != "available"}
            for item in catalog["scenarios"]
        ],
    }
    (root / "scenarios").mkdir(exist_ok=True)
    write_json(root / "scenarios" / "catalog.json", value)
    return catalog


def select_source(root: Path, source_id: object, expected_digest: object, target: str) -> dict:
    if not valid_slug(source_id) or source_id == target:
        raise ValueError("Select a different valid source scenario.")
    entry = next((item for item in discover(root)["scenarios"] if item["id"] == source_id), None)
    if entry is None or not entry["available"]:
        raise ValueError("Source scenario is unavailable. Refresh its local manifest and reference files.")
    if entry["manifestDigest"] != expected_digest:
        raise ValueError("Source manifest changed. Refresh the catalog and select it again.")
    if (root / "generated-scenarios" / target).exists():
        raise ValueError("An adaptation requires a new project slug; the target folder already exists.")
    return {"scenarioId": source_id, "manifestDigest": entry["manifestDigest"], "manifest": {
        key: value for key, value in entry.items() if key not in {"available", "manifestDigest"}
    }}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["refresh", "index"])
    parser.add_argument("scenario", type=Path, nargs="?")
    parser.add_argument("--metadata", type=Path, help="JSON object containing reviewed metadata fields.")
    args = parser.parse_args()
    try:
        if args.command == "refresh":
            if args.scenario is None:
                for folder in (ROOT / "generated-scenarios").iterdir():
                    if folder.is_dir() and valid_slug(folder.name):
                        refresh(folder)
            else:
                refresh(args.scenario, metadata=read_json(args.metadata) if args.metadata else None)
        elif args.metadata or args.scenario:
            raise ValueError("Index takes no scenario or metadata arguments.")
        catalog = export_index()
        print(json.dumps(catalog, indent=2))
        return 1 if catalog["errors"] else 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Scenario catalog: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
