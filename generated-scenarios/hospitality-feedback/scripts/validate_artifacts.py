"""Validate local provenance, compiled resource footprint and non-live evidence boundaries."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict | list:
    """Read a UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resource_types(value: object) -> list[str]:
    """Collect resource types from nested compiled ARM deployment templates."""
    result = []
    if isinstance(value, dict):
        if "type" in value and "apiVersion" in value:
            result.append(value["type"].lower())
        for item in value.values():
            result.extend(resource_types(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(resource_types(item))
    return result


def validate() -> None:
    """Prove artifact consistency without connecting to Azure."""
    source = read_json(ROOT / "data/provenance.json")
    fixtures = read_json(ROOT / "data/feedback.json")
    with Path(source["peopleSource"]).open(encoding="utf-8-sig", newline="") as handle:
        people = list(csv.DictReader(handle))
    with Path(source["companySource"]).open(encoding="utf-8-sig", newline="") as handle:
        companies = list(csv.reader(handle))
    assert companies[source["companyRecord"]] == [source["companyName"], source["companyDomain"]]
    assert len(fixtures) == 12 and len({f["feedbackId"] for f in fixtures}) == 12
    assert {f["language"] for f in fixtures} == {"en", "es", "fr", "ja"}
    for mapping in source["peopleMapping"]:
        person = people[mapping["recordNumberExcludingHeader"] - 1]
        fixture = next(f for f in fixtures if f["feedbackId"] == mapping["feedbackId"])
        assert fixture["guestId"] == mapping["guestId"]
        assert fixture["guestName"] == mapping["guestName"] == person[mapping["nameColumn"]]
    types = resource_types(read_json(ROOT / ".local/main.json"))
    assert "microsoft.cognitiveservices/accounts/projects" in types
    assert "microsoft.storage/storageaccounts" in types
    assert "microsoft.web/sites" in types
    assert not any("microsoft.documentdb" in item for item in types)
    assert not any("microsoft.machinelearningservices/workspaces" in item for item in types)
    for path in ["scenario-validation.json", "workflow-state.json", "nextsteps.MD", "packages"]:
        assert not (ROOT / path).exists(), f"Premature live acceptance, approval or composition: {path}"
    for name in ["local-validation.json", "local-application.json", "browser-local.json"]:
        evidence = read_json(ROOT / "evidence" / name)
        assert evidence["status"] == "passed"
        assert evidence["liveModelInference"] is False
        assert evidence["liveAgentInvocation"] is False
    assert read_json(ROOT / "target-authorization.example.json")["authorized"] is False
    for name in ["03-architect-diagram.png", "04-runtime-diagram.png", "evidence/local-browser.png"]:
        assert (ROOT / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    result = {
        "status": "passed",
        "scope": "local_artifact_integrity_only",
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "fixtureCount": 12,
        "checks": {
            "catalogProvenance": True,
            "compiledFoundryDirectProject": True,
            "noCustomerCosmosOrHub": True,
            "localEvidenceSeparatedFromLive": True,
            "diagramAndScreenshotPngSignatures": True,
            "noApprovalOrComposition": True,
        },
        "liveAzureAcceptance": False,
    }
    (ROOT / "evidence/artifact-integrity.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    validate()
