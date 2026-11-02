"""Verify resumed preparation artifacts without cloud access or deployment authorization."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
sys.path.insert(0, str(Path.cwd() / "scripts"))

from azure_context import infrastructure_fingerprint


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    region = read(SCENARIO / "00-region-availability.json")
    readiness = region["regionalReadiness"]
    final = read(RUN / "scope-and-fingerprint-final.json")
    progress = read(RUN / "preparation-completed.json")
    scope = final["scope"]
    assert scope["region"] == "centralus"
    assert readiness["scope"] == progress["scope"] == scope
    assert readiness["infrastructureFingerprint"] == final["infrastructureFingerprint"]
    assert final["infrastructureFingerprint"] == infrastructure_fingerprint(SCENARIO)
    assert readiness["deploymentReady"] is False and region["selectedRegion"] is None
    assert len(readiness["checks"]) == 26
    assert Counter(item["status"] for item in readiness["checks"]) == {"passed": 17, "unknown": 9}
    assert progress["status"] == "completed" and progress["operation"] == "deployment-preparation"
    assert "blocker" not in progress
    assert all(item["evidence"] for item in readiness["checks"])
    cosmos = next(
        item for item in readiness["checks"] if item["resourceType"] == "Microsoft.DocumentDB/databaseAccounts"
    )
    assert cosmos["zoneRedundant"] is True
    assert cosmos["properties"]["isSubscriptionRegionAccessAllowedForAz"] is True
    assert {item["scope"]["region"] for item in region["regionalReadinessHistory"]} >= {
        "eastus", "centralus", "westus2",
    }
    assert set(region["candidateRegions"]) >= {"eastus2", "eastus", "centralus", "westus2"}
    records = [read(RUN / f"{name}.json") for name in (
        "identity", "providers", "cosmos-locations", "model-quota", "model-capacity",
        "foundry-domain-availability", "what-if-full", "validate-full", "group-exists-final",
        "aca-usage-latest", "quota-provider",
    )]
    assert readiness["checkedAtUtc"] == min(record["checkedAtUtc"] for record in records)
    assert all("--subscription " + scope["subscriptionId"] in record["command"] for record in records)
    preview = read(RUN / "what-if-full.json")["result"]
    assert Counter(item["changeType"] for item in preview["changes"]) == {"Create": 33, "Unsupported": 13}
    assert read(RUN / "foundry-domain-availability.json")["result"]["isSubdomainAvailable"] is True
    assert read(RUN / "group-exists-final.json")["result"] is False
    assert read(RUN / "installation-plan.json")["directoryWritesAuthorized"] is False
    assert read(RUN / "controller-review-check.json")["result"].startswith("Historical")
    original = read(RUN / "local-checks.json")
    assert original["allCommandsPassed"] is False
    assert next(item for item in original["checks"] if item["name"] == "runtime-lint")["exitCode"] == 4294967295
    retry = read(SCENARIO / "evidence" / "resume-cbd218af-verification.json")
    assert retry["runtimeLint"]["exitCode"] == 0 and retry["cloudOperationsThisResume"] == []
    assert retry["deploymentAuthorized"] is False and retry["directoryWritesAuthorized"] is False
    manifest = read(SCENARIO / "scenario-manifest.json")
    assert manifest["businessUnits"] == ["generic"] and manifest["metadataStatus"] == "curated"
    assert set(manifest["services"]) <= {item["service"] for item in readiness["checks"]}
    report = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "scope": scope,
        "infrastructureFingerprint": final["infrastructureFingerprint"],
        "checks": [
            "Complete 26-check inventory; unknown dependencies remain unknown; no selected deployment-ready region.",
            "Original observations retained; exact subscription, repaired name, what-if and final hash verified.",
            "Earlier regional rejection history, Generic scope and curated target-only manifest retained.",
            "Original failed lint retained alongside actual successful same-command retry.",
            "Current controller review path inspected; no canonical backend edits or cloud writes.",
        ],
        "limitations": "Artifact integrity only; no refreshed subscription eligibility or live runtime acceptance.",
    }
    (RUN / "finalization-integrity.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
