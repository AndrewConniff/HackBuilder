"""Verify persisted scope, complete dependency coverage, failures, freshness and retained regional history."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prepare import REGION, RUN, SCENARIO, SCOPE, read, write

sys.path.insert(0, str(Path.cwd() / "scripts"))

from azure_context import infrastructure_fingerprint, validate_regional_readiness


def main() -> None:
    now = datetime.now(timezone.utc)
    region = json.loads((SCENARIO / "00-region-availability.json").read_text())
    readiness = region["regionalReadiness"]
    assert readiness["scope"] == SCOPE and region["validationTargetRegion"] == REGION
    assert readiness["infrastructureFingerprint"] == infrastructure_fingerprint(SCENARIO)
    assert readiness["deploymentReady"] is False and region["selectedRegion"] is None
    assert {item["scope"]["region"] for item in region["regionalReadinessHistory"]} >= {"eastus", "centralus"}
    assert all(key in region for key in ("eastusPreparation", "centralusPreparation", "recoveryPreparation"))
    assert {item["region"] for item in region["candidateEvaluations"]} >= {"eastus2", "eastus", "centralus", "westus2"}
    services = set(json.loads((SCENARIO / "scenario-manifest.json").read_text())["services"])
    assert services == {"foundry", "cosmos-db", "container-apps", "key-vault", "managed-identity", "service-bus"}
    checks = readiness["checks"]
    assert len(checks) == 26 and services <= {item["service"] for item in checks}
    assert Counter(item["status"] for item in checks) == {"passed": 11, "blocked": 5, "unknown": 10}
    expected_types = {
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
    assert expected_types == {item["resourceType"] for item in checks}
    for item in checks:
        assert item["region"] == REGION and item["evidence"] and isinstance(item["quotas"], list)
        for quota in item["quotas"]:
            assert quota["currentValue"] + quota["required"] <= quota["limit"]
    cosmos = next(item for item in checks if item["resourceType"] == "Microsoft.DocumentDB/databaseAccounts")
    assert cosmos["zoneRedundant"] is True and cosmos["properties"]["isSubscriptionRegionAccessAllowedForAz"] is False
    assert cosmos["status"] == "blocked"
    assert read("model-capacity")["result"] == {"value": []}
    assert read("cost-review")["modelRates"] is None
    assert read("cost-review")["monthlyExamples"]["model24MInput7_2MOutput"] is None
    commands = []
    for path in RUN.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        if "command" not in record:
            continue
        assert f"--subscription {SCOPE['subscriptionId']}" in record["command"]
        assert 0 <= (now - datetime.fromisoformat(record["checkedAtUtc"])).total_seconds() < 900
        commands.append(path.name)
    assert len(commands) == 25
    assert "defaultValue" not in read("main.arm")["parameters"]["location"]
    parameters = json.loads((SCENARIO / "infra" / "main.parameters.json").read_text())
    assert parameters["parameters"]["location"]["value"] == "${AZURE_LOCATION}"
    assert read("group-exists-final")["result"] is False
    summary = (SCENARIO / "06-deployment-summary.md").read_text()
    template = (Path.cwd() / ".github" / "skills" / "az-azure-artifacts" / "templates"
                / "06-deployment-summary.template.md").read_text()
    assert [line for line in summary.splitlines() if line.startswith("## ")] == [
        line for line in template.splitlines() if line.startswith("## ")
    ]
    assert all(len(line) <= 120 for line in summary.splitlines())
    event = read("preparation-failed")
    assert event["scope"] == SCOPE and event["status"] == "failed"
    assert event["operation"] == "deployment-preparation" and "decision" not in event and "blocker" not in event
    try:
        validate_regional_readiness(
            SCENARIO, {"authorizations": [{"kind": "deployment-preparation", "scope": SCOPE}]}, SCOPE, list(services),
        )
    except ValueError as error:
        assert "Microsoft.DocumentDB/databaseAccounts" in str(error)
        rejection = str(error)
    else:
        raise AssertionError("Failed preparation incorrectly unlocks deployment.")
    result = {
        "passed": True, "checkedAtUtc": now.isoformat(), "scope": SCOPE,
        "infrastructureFingerprint": readiness["infrastructureFingerprint"],
        "completeReadinessCheckCount": len(checks), "freshExplicitSubscriptionCommands": commands,
        "servicesSecurityAndPortableRegionPreserved": True, "priorRejectionHistoryPreserved": True,
        "missingModelCapacityAndPriceNotFabricated": True, "guardRejectedAsExpected": rejection,
        "summaryTemplateAndLineLengthsPassed": True,
    }
    write("local-integrity", result)
    event["evidence"].append(
        f"python generated-scenarios\\resto-scale-agent\\evidence\\{RUN.name}\\validate_evidence.py: passed; "
        "25 fresh explicit-subscription command records; complete 26-check inventory; exact scope/hash; "
        "prior rejection history/security/services/portable region preserved; no fabricated model capacity/prices; "
        f"summary template/line lengths and failed-readiness guard checked. evidence\\{RUN.name}\\local-integrity.json."
    )
    write("preparation-failed", event)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
