"""Derive bounded readiness and cost evidence from actual saved command results."""

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
SCENARIO = DIRECTORY.parent.parent


def load(name: str):
    return json.loads((DIRECTORY / f"{name}.json").read_text(encoding="utf-8-sig"))


def save(name: str, value: object) -> None:
    (DIRECTORY / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    records = [json.loads(path.read_text()) for path in sorted(DIRECTORY.glob("*.command.json"))]
    assert all(record["exitCode"] == 0 for record in records), "Do not collapse command failures into readiness."
    whatif = load("independent-whatif")
    coverage = load("preview-coverage")
    assert coverage["sourceSha256"] == hashlib.sha256((DIRECTORY / "main.json").read_bytes()).hexdigest()
    assert whatif["status"] == "Succeeded"
    changes = Counter(change["changeType"] for change in whatif["changes"])
    web = {x["name"]["value"]: x for x in load("web-usages")["value"]}
    quota = next(x for x in load("model-quota") if x["name"]["value"] == "OpenAI.GlobalStandard.gpt4.1-mini")
    capacity = next(x for x in load("model-capacities")["value"] if
                    x["location"] == "centralus" and x["properties"]["skuName"] == "GlobalStandard")
    models = [x for x in load("model-catalog") if x.get("kind") == "AIServices"
              and x.get("skuName") == "S0" and x.get("model", {}).get("name") == "gpt-4.1-mini"
              and x.get("model", {}).get("version") == "2025-04-14"]
    assert len(models) == 1
    assert any(x["name"] == "GlobalStandard" for x in models[0]["model"]["skus"])
    storage = [x for x in load("storage-skus")["value"] if x["name"] == "Standard_LRS"
               and x["kind"] == "StorageV2" and "centralus" in [v.lower() for v in x["locations"]]]
    cognitive = [x for x in load("cognitive-skus")["value"] if x.get("kind") == "AIServices"
                 and x["name"] == "S0" and "centralus" in [v.lower() for v in x["locations"]]]
    assert len(storage) == len(cognitive) == 1
    providers = {}
    for path in DIRECTORY.glob("provider-*.json"):
        if ".command." not in path.name:
            item = json.loads(path.read_text())
            providers[item["namespace"]] = item["registrationState"]
    assert len(providers) == 10 and all(value == "Registered" for value in providers.values())
    assert web["B2"]["currentValue"] + 1 <= web["B2"]["limit"]
    assert web["*"]["currentValue"] + 1 <= web["*"]["limit"]
    assert quota["currentValue"] + 10 <= quota["limit"]
    assert capacity["properties"]["availableCapacity"] >= 10
    assert not storage[0]["restrictions"] and not cognitive[0]["restrictions"]
    assert load("group-exists") is False
    save("regional-readiness", {
        "checkedAtUtc": now, "scope": load("authorization")["scope"],
        "status": "partial_eligibility_observed_not_deployment_ready",
        "selectedRegion": None, "testedRegion": "centralus", "savedTargetsChanged": False,
        "accountAndAzdTargetMatched": True, "providers": providers,
        "appService": {
            "sku": "B2", "os": "Linux", "requiredWorkers": 1,
            "b2": web["B2"], "aggregateWorkers": web["*"],
            "b2LinuxRegionListed": True, "dotnet10Listed": True, "allocationReserved": False,
        },
        "model": {
            "kind": "AIServices", "accountSku": "S0", "name": "gpt-4.1-mini", "version": "2025-04-14",
            "deploymentType": "GlobalStandard", "requiredCapacity": 10,
            "quotaUsed": quota["currentValue"], "quotaLimit": quota["limit"],
            "availableCapacity": capacity["properties"]["availableCapacity"], "capacityReserved": False,
            "lifecycle": models[0]["model"]["lifecycleStatus"],
            "deprecation": models[0]["model"]["deprecation"],
            "restrictions": cognitive[0]["restrictions"],
            "privateAgentFeatureAndRuntimeAcceptance": "not_proven_by_catalog",
            "publicAgentFeatureSupport": load("official-guidance")["sources"][0],
        },
        "storage": {
            "sku": "Standard_LRS", "kind": "StorageV2", "restrictions": storage[0]["restrictions"],
            "usage": load("storage-usages")["value"], "privateAndTrustedIotRouting": "pending_runtime",
        },
        "iot": {
            "sku": "B2", "requiredHubs": 1, "usage": load("iot-usages")["value"],
            "providerListsCentralUs": True, "hubIncludedInWhatIf": True,
            "exactSkuAllocation": "unreserved; Get Valid Skus requires an existing hub",
            "x509AndIdentityRouteAcceptance": "pending_runtime",
        },
        "network": {
            "usage": load("network-usages"), "existingVnets": load("vnet-prefixes"),
            "plannedAddressSpace": "10.247.0.0/24", "overlapInReturnedSubscriptionVnets": False,
            "unobservedPeeredOrExternalRoutes": "unknown",
            "privateEndpointsRequired": 3, "privateDnsZonesRequired": 5,
            "privateDnsLocation": "global", "actualManagementHost": None,
        },
        "monitoring": {
            "workspaceSku": "PerGB2018", "retentionDays": 30, "dailyQuotaGb": 1,
            "workspaceAndAppInsightsRegionListed": True, "whatIfCreatesReturned": True,
            "sanitizedLoggingRuntimeVerified": False,
        },
        "identityAndRbac": {
            "managedIdentityRegionListed": True, "foundryRoleDefinitionsRead": True,
            "armWildcardPermissionsReturned": True, "directoryReadPerformed": False,
            "directoryOwnershipAndRoleAssignments": "not_currently_verified",
        },
        "policy": {
            "assignmentCount": len(load("policy-assignments")), "definitionCount": 11,
            "observedRules": "Database and SQL Defender DeployIfNotExists rules; no applicable deny identified",
            "fullReferencePolicyPassed": False, "limitations": "Nested resources not fully expanded; no runtime/Graph coverage",
        },
        "whatIf": {
            "commandExitCode": 0, "armStatus": whatif["status"], "changeCounts": dict(changes),
            "deleteCount": changes["Delete"], "modifyCount": changes["Modify"],
            "diagnostics": whatif.get("diagnostics", []), "coverage": coverage,
            "fullReferencePassed": False,
        },
        "runtime": {"status": "not_attempted", "applicationUrl": None},
        "commandCount": len(records), "allRecordedCommandExitCodesZero": True,
        "deploymentAuthorized": False, "directoryWriteAuthorized": False,
    })

    # Reuse reviewed quantities, but verify every price against the refreshed public response.
    old = json.loads((SCENARIO / ".worker/fa96363ef14f40ffa063aff3dcfd430c/cost-estimate.json").read_text())
    prices = load("retail-prices")
    public_items = [item for query in prices["queries"].values() for item in query["items"]]
    for line in old["items"]:
        matches = [x for x in public_items if x["meterId"] == line["meterId"] and x["type"] == "Consumption"
                   and x["retailPrice"] == line["unitPriceUsd"]]
        assert matches, f"Historical rate no longer matched: {line['name']}"
        line["refreshedPriceMatched"] = True
        line["tierMinimumUnits"] = sorted({x["tierMinimumUnits"] for x in matches})
    old.update({
        "checkedAtUtc": now, "publicPriceCheckedAtUtc": prices["checkedAtUtc"],
        "status": "refreshed_baseline_only_incomplete_total",
        "historicalQuantityAssumptionsReused": True,
        "monthlyBaselineBeforeLogsUsd": round(sum(x["monthlyUsd"] for x in old["items"] if x["name"] != "logs"), 2),
        "logsPricingNote": "3 GB at paid 2.76/GB retained conservatively. First 5 GB free tier not assumed available.",
        "managementPathMonthlyUsd": None, "completeMonthlyTotalUsd": None,
        "finalQuote": False, "deploymentConsentEligible": False,
        "notIncluded": [
            "Actual connected runner or new host compute, disks, connectivity, bootstrap and artifact transport.",
            "Internet egress, extra endpoint traffic, applicable Entra licensing, taxes and support.",
            "Contractual pricing, traffic variability, model tool-loop amplification beyond retained quantities.",
        ],
        "securityControlsPreserved": True,
    })
    save("cost-estimate", old)
    save("command-index", {
        "recordedAtUtc": now, "commands": records, "commandExitCodesAreNotReadinessPasses": True,
        "additionalPublicPricingCommand": "python local-evidence/centralus-20261024T2240Z/refresh_prices.py",
        "pricingSource": "retail-prices.json; public filters and actual response, no scenario data transmitted",
    })
    save("evidence-verification", {
        "checkedAtUtc": now, "compiledSourceHashMatched": True,
        "commandRecordsVerified": len(records), "allRecordedCommandExitCodesZero": True,
        "whatIfCounts": dict(changes), "noRuntimeChecksClaimed": True,
        "baselinePricesMatchedFreshPublicEvidence": True,
        "savedTargetFiles": {
            str(path.relative_to(SCENARIO)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [SCENARIO / ".azure/equip-ai/.env", SCENARIO / "deployment-target-preview.json"]
        },
    })
    print(f"Verified {len(records)} command records; {dict(changes)}; incomplete USD {old['illustrativeMonthlySubtotalUsd']} baseline.")


if __name__ == "__main__":
    main()
