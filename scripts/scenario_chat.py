"""Associate portal scenarios with native editor chats using exact handoff and progress-report evidence."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

from portal_status import ROOT, STAGES, STATUSES, scenario_state, write_json

LOG = logging.getLogger(__name__)
HANDOFF = re.compile(
    r"Follow the attached (scenario|composition|deployment-review) handoff for "
    r"([a-z0-9]+(?:-[a-z0-9]+)*). Report progress to portal_status\.py\."
    r"(?: ABC Builder chat trace: ([a-f0-9]{32})\.)?"
)


def editor_storage() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "Code" / "agentSessionData"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "agentSessionData"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Code" / "agentSessionData"


def workspace_path(value: str) -> Path | None:
    parsed = urlsplit(value)
    if parsed.scheme != "file" or parsed.netloc:
        return None
    decoded = unquote(parsed.path)
    if sys.platform == "win32":
        decoded = decoded.removeprefix("/")
    return Path(decoded).resolve()


def session_metadata(folder: Path, root: Path) -> str | None:
    database = folder / "session.db"
    if not database.is_file():
        return None
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=1)) as connection:
            if not connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_metadata'"
            ).fetchone():
                return None
            values = dict(connection.execute(
                "SELECT key, value FROM session_metadata "
                "WHERE key IN ('copilot.workingDirectory', 'defaultChatProviderData')"
            ))
    except sqlite3.Error as error:
        LOG.warning("Cannot read editor session identity at %s: %s", database, error)
        return None
    if workspace_path(values.get("copilot.workingDirectory", "")) != root:
        return None
    provider = json.loads(values.get("defaultChatProviderData", "{}"))
    sdk_id = provider.get("sdkSessionId") if isinstance(provider, dict) else None
    if not isinstance(sdk_id, str):
        return None
    try:
        return str(uuid.UUID(sdk_id))
    except ValueError as error:
        raise ValueError(f"Invalid SDK session identity in {database}.") from error


def history_evidence(
    path: Path, sdk_id: str, root: Path, slug: str, phase: str, trace_id: str | None,
) -> dict | None:
    if not path.is_file():
        return None
    matched = False
    pending = set()
    latest = None
    matched_trace = None
    scope_evidence = "original-handoff"
    reference = (root / "generated-scenarios" / slug / "01-requirements.md").resolve()
    command_pattern = re.compile(rf"portal_status\.py[\"']?\s+[\"']?{re.escape(slug)}(?:[\"']?\s|$)")
    with path.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            event = json.loads(line)
            data = event.get("data", {})
            kind = event.get("type")
            if kind == "session.start" and data.get("sessionId") != sdk_id:
                raise ValueError(f"SDK session identity does not match {path}.")
            if not matched:
                if kind != "user.message":
                    if index >= 128:
                        return None
                    continue
                marker = HANDOFF.fullmatch(data.get("content", "").strip())
                if marker:
                    conversation = "composition" if marker[1] == "composition" else "scenario"
                    if marker[2] != slug or conversation != phase or (trace_id and marker[3] != trace_id):
                        return None
                    matched_trace = marker[3]
                elif not trace_id and phase == "scenario" and any(
                    isinstance(item.get("path"), str) and Path(item["path"]).resolve() == reference
                    for item in data.get("attachments", []) if isinstance(item, dict)
                ):
                    scope_evidence = "original-reference-attachment"
                else:
                    return None
                matched = True
            if kind == "tool.execution_start" and command_pattern.search(json.dumps(data.get("arguments", {}))):
                pending.add(data.get("toolCallId"))
            elif kind == "tool.execution_complete" and data.get("toolCallId") in pending:
                pending.remove(data["toolCallId"])
                if data.get("success") is not True:
                    continue
                result = data.get("result", {})
                for output in result.get("content", "").splitlines():
                    if not output.lstrip().startswith("{"):
                        continue
                    try:
                        report = json.loads(output)
                    except json.JSONDecodeError:
                        continue
                    stage = report.get("stage")
                    if (report.get("schemaVersion") != 1 or report.get("projectSlug") != slug
                            or stage not in STAGES or report.get("status") not in STATUSES
                            or stage.startswith("hack-") != (phase == "composition")):
                        continue
                    timestamp = datetime.fromisoformat(report["updatedAtUtc"]).astimezone(timezone.utc).isoformat()
                    latest = max(latest or timestamp, timestamp)
    if not matched or (scope_evidence == "original-reference-attachment" and latest is None):
        return None
    return {"traceId": matched_trace, "lastReportedAtUtc": latest, "scopeEvidence": scope_evidence}


def resolve(
    root: Path, slug: str, phase: str, *, storage: Path | None = None, history: Path | None = None,
) -> dict:
    directory = scenario_state(root, slug)
    if phase not in {"scenario", "composition"}:
        raise ValueError("Choose scenario or composition chat.")
    filename = directory / "chat-sessions.json"
    saved = json.loads(filename.read_text(encoding="utf-8")) if filename.is_file() else {
        "schemaVersion": 1, "sessions": {},
    }
    if saved.get("schemaVersion") != 1 or not isinstance(saved.get("sessions"), dict):
        raise ValueError("Unsupported chat-sessions.json format.")
    if phase in saved["sessions"]:
        return saved["sessions"][phase]
    launch = directory / f"{phase}-chat-started.json"
    receipt = json.loads(launch.read_text(encoding="utf-8")) if launch.is_file() else {}
    trace_id = receipt.get("traceId")
    storage = storage if storage is not None else editor_storage()
    history = history if history is not None else Path.home() / ".copilot" / "session-state"
    if not storage.is_dir():
        raise ValueError("The local editor session catalog is unavailable. No new conversation was created.")
    candidates = []
    for folder in storage.iterdir():
        if not folder.is_dir():
            continue
        try:
            editor_id = str(uuid.UUID(folder.name))
        except ValueError:
            continue
        sdk_id = session_metadata(folder, root.resolve())
        if not sdk_id:
            continue
        evidence = history_evidence(history / sdk_id / "events.jsonl", sdk_id, root, slug, phase, trace_id)
        if evidence is not None:
            candidates.append({
                "editorSessionId": editor_id, "sdkSessionId": sdk_id,
                "resource": f"agent-host-session://copilot/{editor_id}?connectionAuthority=local",
                **evidence,
            })
    if not candidates:
        raise ValueError(
            f"No verified {phase} chat was found for {slug}. Its original handoff must exist in this editor profile. "
            "No new conversation was created."
        )
    reported = [item for item in candidates if item["lastReportedAtUtc"]]
    ranked = sorted(reported or candidates, key=lambda item: item["lastReportedAtUtc"] or "", reverse=True)
    if len(ranked) > 1 and ranked[0]["lastReportedAtUtc"] == ranked[1]["lastReportedAtUtc"]:
        raise ValueError(f"Multiple {phase} chats match {slug} without a unique latest progress report. "
                         "No conversation was selected or created.")
    selected = {
        **ranked[0], "linkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": "handoff-trace" if trace_id else (
            "reference-attachment-and-progress-history" if ranked[0]["scopeEvidence"] == "original-reference-attachment"
            else "handoff-and-progress-history"
        ),
        "relatedSessions": [
            {key: item[key] for key in ("editorSessionId", "sdkSessionId", "lastReportedAtUtc")}
            for item in candidates
        ],
    }
    saved["sessions"][phase] = selected
    write_json(filename, saved)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    parser.add_argument("--phase", choices=("scenario", "composition"), default="scenario")
    args = parser.parse_args()
    try:
        print(json.dumps(resolve(ROOT, args.project, args.phase)))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Chat association failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
