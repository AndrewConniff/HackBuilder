"""Write display-only scenario progress for the local portal."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from scenario_catalog import valid_slug

ROOT = Path(__file__).resolve().parents[1]
STAGES = (
    "requirements", "architecture", "diagrams", "bicep", "application", "local-validation",
    "deployment", "live-validation", "review", "hack-content", "hack-starter", "hack-coach", "hack-validation",
)
STATUSES = ("running", "waiting_for_user", "blocked", "completed", "failed", "handed_off")


def state_directory(root: Path) -> Path:
    legacy = root / ".hackbuilder-portal"
    current = root / ".abcbuilder-portal"
    return legacy if legacy.exists() and not current.exists() else current


def scenario_state(root: Path, slug: str) -> Path:
    if not valid_slug(slug):
        raise ValueError("Use a project slug of at most 40 lowercase letters, numbers and single hyphens.")
    path = state_directory(root) / "scenarios" / slug
    if not path.resolve().is_relative_to(state_directory(root).resolve()):
        raise ValueError("Scenario status must stay in the local portal state directory.")
    return path


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def report(root: Path, slug: str, stage: str, status: str, summary: str) -> dict:
    if stage not in STAGES or status not in STATUSES:
        raise ValueError("Use a known stage and display status.")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 1200:
        raise ValueError("Summary must be 1-1200 characters; include no secrets.")
    path = scenario_state(root, slug) / "status.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    updated = datetime.now(timezone.utc).isoformat()
    value = {
        "schemaVersion": 1, "projectSlug": slug, "stage": stage, "status": status,
        "summary": summary.strip(), "updatedAtUtc": updated,
        "steps": {**previous.get("steps", {}), stage: {
            "status": status, "summary": summary.strip(), "updatedAtUtc": updated,
        }},
    }
    write_json(path, value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--status", choices=STATUSES, required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(report(ROOT, args.project, args.stage, args.status, args.summary)))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Status report failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
