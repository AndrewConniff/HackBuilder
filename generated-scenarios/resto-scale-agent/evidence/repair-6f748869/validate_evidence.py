"""Verify retained repair evidence and reference metadata without cloud operations."""

import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))

from azure_context import infrastructure_fingerprint
from scenario_catalog import refresh

SPEC = importlib.util.spec_from_file_location("repair_prepare", RUN / "prepare.py")
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def main() -> None:
    for path in RUN.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8-sig"))
    fingerprint = infrastructure_fingerprint(SCENARIO)
    region = json.loads((SCENARIO / "00-region-availability.json").read_text())
    review = read("installation-review")
    assert (
        review["infrastructureFingerprint"] == region["repairPreparation"]["infrastructureFingerprint"] == fingerprint
    )
    assert review["scope"] == region["repairPreparation"]["scope"] == PREPARE.SCOPE
    assert review["authorizationRequired"] is True and review["liveAcceptancePassed"] is False
    assert read("identity")["exitCode"] == 0
    assert read("resources-before")["exitCode"] == 3
    assert "ResourceGroupNotFound" in read("resources-before")["stderr"]
    assert read("group-exists-reconciled")["result"] is False
    assert read("group-exists-final")["result"] is False
    assert read("vault-name-availability")["result"]["nameAvailable"] is True
    assert read("foundry-name-availability")["result"]["isSubdomainAvailable"] is True
    assert len(PREPARE.VAULT_NAME) == 24
    assert (
        read("vault-name-request")["name"] == region["repairPreparation"]["replacementVaultName"] == PREPARE.VAULT_NAME
    )
    provider_states = {item["namespace"].casefold(): item["registrationState"]
                       for item in read("providers")["result"]}
    providers = (
        "Microsoft.Resources", "Microsoft.Authorization", "Microsoft.ManagedIdentity", "Microsoft.Network",
        "Microsoft.OperationalInsights", "Microsoft.Insights", "Microsoft.ContainerRegistry",
        "Microsoft.DocumentDB", "Microsoft.ServiceBus", "Microsoft.KeyVault", "Microsoft.CognitiveServices",
        "Microsoft.App",
    )
    assert all(provider_states[name.casefold()] == "Registered" for name in providers)
    counts = {}
    for name, expected in (("full", {"Create": 33, "Unsupported": 13}), ("vault", {"Create": 3}),
                           ("cosmos", {"Create": 7})):
        record = read(f"what-if-{name}")
        assert record["exitCode"] == 0 and record["result"]["status"] == "Succeeded"
        counts[name] = dict(Counter(change["changeType"] for change in record["result"]["changes"]))
        assert counts[name] == expected
    validation = read("validate-full")["result"]["properties"]
    assert validation["provisioningState"] == "Succeeded"
    assert len([item for item in validation["diagnostics"] if item["code"] == "NestedDeploymentShortCircuited"]) == 8
    grants = [change["after"]["properties"] for change in read("what-if-cosmos")["result"]["changes"]
              if "/sqlRoleAssignments/" in change["resourceId"]]
    assert len(grants) == 1 and grants[0]["scope"] == region["repairPreparation"]["cosmosScope"]
    assert grants[0]["principalId"] == read("main.parameters")["parameters"]["principalId"]["value"]
    assert region["repairPreparation"]["currentConsumptionQuota"] is None
    assert region["foundationDeployment"]["consumptionQuota"]["limit"] == 500
    tests = (RUN / "infrastructure-tests.txt").read_text(encoding="utf-8-sig")
    assert "Ran 3 tests" in tests and "OK" in tests and "FAILED" not in tests
    for name, template in (
        ("05-implementation-reference.md", "05-implementation-reference.template.md"),
        ("06-deployment-summary.md", "06-deployment-summary.template.md"),
    ):
        lines = (SCENARIO / name).read_text().splitlines()
        assert not [(index, len(line)) for index, line in enumerate(lines, 1) if len(line) > 120], name
        headings = [line for line in lines if line.startswith("## ")]
        template_lines = (ROOT / ".github" / "skills" / "az-azure-artifacts" / "templates" / template).read_text()
        assert headings == [line for line in template_lines.splitlines() if line.startswith("## ")], name
    manifest = refresh(SCENARIO, metadata=json.loads((SCENARIO / "reviewed-metadata.json").read_text()))
    assert manifest["metadataStatus"] == "curated" and manifest["businessUnits"] == ["generic"]
    assert not (SCENARIO / "scenario-validation.json").exists()
    result = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "scope": PREPARE.SCOPE,
        "infrastructureFingerprint": fingerprint, "passed": True, "whatIfCounts": counts,
        "registeredProviderNamespacesChecked": len(providers),
        "groupExists": False, "currentConsumptionQuota": None,
        "compiledRegressionTestsPassed": 3, "markdownTemplateAndLineLengthChecksPassed": True,
        "scenarioOnlyCatalogRefresh": True, "sharedCatalogExported": False,
        "cloudMutations": False, "liveAcceptancePassed": False,
        "limitations": "Evidence integrity only; skipped validation, unresolved grants, directory capability, "
        "future environment quota, runtime outputs/preview and live performance/authentication remain unverified.",
    }
    (RUN / "evidence-integrity.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
