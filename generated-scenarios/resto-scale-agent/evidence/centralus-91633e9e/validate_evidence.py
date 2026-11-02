"""Check persistence, scope, completeness, retained history and the failed preparation safety gate."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))

from azure_context import infrastructure_fingerprint, validate_regional_readiness

from prepare import SCOPE, read, write


def main() -> None:
    parsed = []
    for path in sorted(RUN.glob("*.json")):
        json.loads(path.read_text(encoding="utf-8-sig"))
        parsed.append(path.name)
    region = json.loads((SCENARIO / "00-region-availability.json").read_text())
    readiness = region["regionalReadiness"]
    assert readiness["scope"] == SCOPE
    assert readiness["infrastructureFingerprint"] == infrastructure_fingerprint(SCENARIO)
    assert readiness["deploymentReady"] is False and region["selectedRegion"] is None
    assert region["validationTargetRegion"] == "centralus"
    assert any(item["scope"]["region"] == "eastus" for item in region["regionalReadinessHistory"])
    assert "eastusPreparation" in region and "recoveryPreparation" in region
    assert any(item["region"] == "eastus" for item in region["candidateEvaluations"])
    assert len([item for item in region["candidateEvaluations"]
                if item.get("evidenceDirectory") == "evidence\\centralus-91633e9e"]) == 1
    manifest = json.loads((SCENARIO / "scenario-manifest.json").read_text())
    services = set(manifest["services"])
    assert services == {"foundry", "cosmos-db", "container-apps", "key-vault", "managed-identity", "service-bus"}
    checks = readiness["checks"]
    assert len(checks) == 26
    assert services <= {item["service"] for item in checks}
    assert Counter(item["status"] for item in checks) == {"passed": 15, "blocked": 1, "unknown": 10}
    required_types = {
        "Microsoft.CognitiveServices/accounts", "Microsoft.CognitiveServices/accounts/projects",
        "Microsoft.CognitiveServices/accounts/deployments", "Microsoft.App/managedEnvironments",
        "Microsoft.App/containerApps", "Microsoft.DocumentDB/databaseAccounts",
        "Microsoft.DocumentDB/databaseAccounts/sqlDatabases", "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers",
        "Microsoft.ServiceBus/namespaces", "Microsoft.ServiceBus/namespaces/queues",
        "Microsoft.KeyVault/vaults", "Microsoft.KeyVault/vaults/keys",
        "Microsoft.ManagedIdentity/userAssignedIdentities", "Microsoft.ContainerRegistry/registries",
        "Microsoft.Network/virtualNetworks", "Microsoft.Network/virtualNetworks/subnets",
        "Microsoft.OperationalInsights/workspaces", "Microsoft.Insights/components",
        "Microsoft.Authorization/roleAssignments", "Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments",
        "Microsoft.Insights/diagnosticSettings", "Microsoft.Authorization/policyAssignments",
        "Microsoft.Resources/resourceGroups", "Microsoft.Resources/tags", "Microsoft.Resources/deployments",
    }
    assert required_types == {item["resourceType"] for item in checks}
    now = datetime.now(timezone.utc)
    command_records = []
    for path in RUN.glob("*.json"):
        record = json.loads(path.read_text())
        if "command" not in record or "checkedAtUtc" not in record:
            continue
        assert "--subscription efd64343-6ef4-4926-951f-d3229f38bd76" in record["command"]
        assert 0 <= (now - datetime.fromisoformat(record["checkedAtUtc"])).total_seconds() < 900
        command_records.append(path.name)
    for item in checks:
        assert item["region"] == "centralus" and item["evidence"]
        assert isinstance(item["quotas"], list)
        for quota in item["quotas"]:
            assert quota["currentValue"] + quota["required"] <= quota["limit"]
    compiled = json.loads((RUN / "main.arm.json").read_text(encoding="utf-8-sig"))
    assert "defaultValue" not in compiled["parameters"]["location"]
    parameters = json.loads((SCENARIO / "infra" / "main.parameters.json").read_text())
    assert parameters["parameters"]["location"]["value"] == "${AZURE_LOCATION}"
    summary = (SCENARIO / "06-deployment-summary.md").read_text()
    template = (ROOT / ".github" / "skills" / "az-azure-artifacts" / "templates"
                / "06-deployment-summary.template.md").read_text()
    headings = [line for line in template.splitlines() if line.startswith("## ")]
    assert [line for line in summary.splitlines() if line.startswith("## ")] == headings
    assert all(len(line) <= 120 for line in summary.splitlines())
    event = read("preparation-failed")
    assert event["status"] == "failed" and event["operation"] == "deployment-preparation"
    assert event["scope"] == SCOPE and "decision" not in event and "blocker" not in event
    try:
        validate_regional_readiness(
            SCENARIO, {"authorizations": [{"kind": "deployment-preparation", "scope": SCOPE}]},
            SCOPE, list(services),
        )
    except ValueError as error:
        assert "Microsoft.CognitiveServices/accounts" in str(error)
        rejected = str(error)
    else:
        raise AssertionError("Blocked/unknown regional readiness must not unlock deployment.")
    result = {
        "passed": True, "checkedAtUtc": now.isoformat(), "scope": SCOPE,
        "infrastructureFingerprint": readiness["infrastructureFingerprint"],
        "jsonFilesParsed": parsed, "freshExplicitSubscriptionCommands": command_records,
        "completeReadinessCheckCount": 26, "servicesPreserved": sorted(services),
        "priorRejectionHistoryPreserved": True, "requiredPortableLocationPreserved": True,
        "summaryTemplateAndLineLengthsPassed": True, "guardRejectedAsExpected": rejected,
    }
    write("local-integrity", result)
    event["evidence"].append(
        "python generated-scenarios\\resto-scale-agent\\evidence\\centralus-91633e9e\\validate_evidence.py: "
        "passed; fresh explicit-subscription command records, complete 26-check dependency inventory, "
        "exact scope/hash, preserved rejection history/security/services/portable location, valid JSON, "
        "summary template/line lengths and expected deployment-guard rejection. "
        "evidence\\centralus-91633e9e\\local-integrity.json."
    )
    write("preparation-failed", event)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
