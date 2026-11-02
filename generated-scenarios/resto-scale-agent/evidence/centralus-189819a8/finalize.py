"""Finalize retained Central US preparation without treating dependent checks as deployment readiness."""

import ast
import copy
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
sys.path.insert(0, str(Path.cwd() / "scripts"))
sys.path.insert(0, str(RUN))

from azure_context import infrastructure_fingerprint, validate_regional_readiness
from scenario_catalog import refresh

from prepare import FOUNDRY_NAME, SCOPE


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def write(name: str, value: object) -> None:
    (RUN / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def fact(name: str, result: str) -> str:
    record = read(name)
    return (
        f"{record['command']}: exit {record['exitCode']}; {result}; "
        f"observed {record['checkedAtUtc']}; evidence\\centralus-189819a8\\{name}.json"
    )


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    observations = [
        read(name)["checkedAtUtc"] for name in (
            "identity", "providers", "cosmos-locations", "model-quota", "model-capacity",
            "foundry-domain-availability", "what-if-full", "validate-full", "group-exists-final",
            "aca-usage-latest", "quota-provider",
        )
    ]
    observed_at = min(observations)
    fingerprint = infrastructure_fingerprint(SCENARIO)
    spec = importlib.util.spec_from_file_location("prior_costs", RUN.parent / "centralus-91633e9e" / "finalize.py")
    prior_costs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior_costs)
    prior_costs.read = read
    cost = prior_costs.costs()
    cost["limitations"] = [
        "Fresh Central US exact public meters; ancillary planning allowances are not individually requoted.",
        "Not a quote, capacity reservation, cap, approved budget or deployment authorization.",
        "Storage, requests, telemetry, restore, egress, zone billing and taxes can add costs.",
        "Independent preview/name repair does not establish unknown Consumption quota or live capacity.",
    ]
    write("cost-review", cost)
    full = read("what-if-full")["result"]
    counts = dict(Counter(change["changeType"] for change in full["changes"]))
    assert counts == {"Create": 33, "Unsupported": 13}
    assert full["status"] == "Succeeded" and full["error"] is None and not full.get("diagnostics")
    unsupported = [change for change in full["changes"] if change["changeType"] == "Unsupported"]
    assert all("reference(" in change["resourceId"] and change.get("unsupportedReason") for change in unsupported)
    write("unsupported-expansion", {
        "status": "not-an-unsupported-resource-finding", "count": len(unsupported),
        "reason": "ARM cannot calculate new managed-identity-dependent grant resource IDs before installation.",
        "changes": unsupported,
    })
    validation = read("validate-full")["result"]["properties"]
    assert validation["provisioningState"] == "Succeeded"
    skipped = [item["target"].rsplit("/", 1)[-1] for item in validation.get("diagnostics", [])]
    assert len(skipped) == 8
    assert read("foundry-domain-availability")["result"]["isSubdomainAvailable"] is True
    assert read("group-exists")["result"] is False and read("group-exists-final")["result"] is False
    assert read("quota-provider")["result"]["registrationState"] == "NotRegistered"
    assert all("MissingRegistrationForResourceProvider" in read(name)["stderr"]
               for name in ("aca-quota", "aca-quota-usage"))
    for name in ("registry", "cosmos", "broker", "vault", "foundry"):
        result = read(f"what-if-{name}")["result"]
        assert result["status"] == "Succeeded" and not result.get("diagnostics")
        assert all(change["changeType"] == "Create" for change in result["changes"])
    compiled = json.loads((RUN / "main.arm.json").read_text(encoding="utf-8-sig"))
    wrapper = json.loads((RUN / "preview-full.arm.json").read_text())
    assert wrapper["resources"][1]["properties"]["template"] == compiled
    assert "foundry-v2" in compiled["variables"]["foundryAccountName"]
    assert "defaultValue" not in compiled["parameters"]["location"]

    region_path = SCENARIO / "00-region-availability.json"
    region = json.loads(region_path.read_text())
    history = region.setdefault("regionalReadinessHistory", [])
    previous = region["regionalReadiness"]
    if previous not in history:
        history.append(previous)
    baseline = next(item for item in history if item["scope"] == SCOPE)
    checks = copy.deepcopy(baseline["checks"])
    preview = fact("what-if-full", "33 creates, 13 identity-dependent Unsupported expansions; zero modifies/deletes")
    validated = fact("validate-full", f"Succeeded but skipped {', '.join(skipped)}")
    providers = {item["namespace"].casefold(): item["registrationState"] for item in read("providers")["result"]}
    properties = next(item["properties"] for item in read("cosmos-locations")["result"]
                      if item["name"] == "Central US")
    assert properties["status"] == "Online" and properties["supportsAvailabilityZone"] is True
    assert properties["isSubscriptionRegionAccessAllowedForAz"] is True
    quota = next(item for item in read("model-quota")["result"]
                 if item["name"]["value"] == "OpenAI.GlobalStandard.gpt-5.4-mini")
    capacity = next(item for item in read("model-capacity")["result"]["value"] if item["name"] == "GlobalStandard")
    assert quota["limit"] - quota["currentValue"] >= 100
    assert capacity["properties"]["availableCapacity"] >= 100
    model = next(item for item in read("model-eligibility")["result"]
                 if item["kind"] == "AIServices" and item["model"]["name"] == "gpt-5.4-mini"
                 and item["model"]["version"] == "2026-03-17")
    assert model["model"]["capabilities"]["agentsV2"] == "true"
    assert model["model"]["capabilities"]["responses"] == "true"
    usage = next(item for item in read("aca-usage-latest")["result"]["value"]
                 if item["name"]["value"] == "ManagedEnvironmentCount")
    assert usage["currentValue"] + 1 <= usage["limit"]
    quota_evidence = [
        fact("aca-usage", "supported direct subscription/region API lists no Consumption core quota"),
        fact("aca-usage-latest", "latest supported 2026-07-01 API also lists no Consumption core quota"),
        fact("aca-quota", "regional Microsoft.Quota quotas GET failed MissingRegistrationForResourceProvider"),
        fact("aca-quota-usage", "regional Microsoft.Quota usages GET failed MissingRegistrationForResourceProvider"),
        fact("quota-provider", "Microsoft.Quota NotRegistered; registration is an unauthorized mutation"),
        "Official quotas documentation scopes Consumption cores to an environment; no default/zero limit assumed.",
        "Missing environment is not evidence of zero quota. No test allocation, provider registration or quota request.",
    ]
    for item in checks:
        resource_type = item["resourceType"]
        provider = resource_type.split("/")[0]
        assert providers[provider.casefold()] == "Registered", f"Provider registration not established: {provider}"
        item.update(status="passed", quotas=[], evidence=[
            fact("providers", f"{provider} Registered"), preview,
            "Passing only the stated metadata/template evaluation, not allocation, runtime or excluded grants.",
        ])
        if resource_type.startswith("Microsoft.DocumentDB/databaseAccounts"):
            item["evidence"].extend([
                fact("cosmos-locations", "Central US Online, zones supported, subscription AZ/regular access true"),
                fact("what-if-cosmos", "exact zonal autoscale/Continuous7Days independent preview accepted"),
            ])
            if resource_type == "Microsoft.DocumentDB/databaseAccounts":
                item.update(properties=properties, zoneRedundant=True)
        if resource_type == "Microsoft.CognitiveServices/accounts":
            item["evidence"].extend([
                fact("foundry-domain-availability", f"replacement {FOUNDRY_NAME} available; not reserved"),
                fact("what-if-foundry", "independent AIServices S0 account and exact model preview: 3 creates"),
                "Exact group absent; no reusable owned account verified; legacy conflict was not adopted or purged.",
            ])
        if resource_type == "Microsoft.CognitiveServices/accounts/deployments":
            item["quotas"] = [{
                "name": quota["name"]["value"], "limit": quota["limit"],
                "currentValue": quota["currentValue"], "required": 100,
            }]
            item["evidence"].extend([
                fact("model-eligibility", "exact gpt-5.4-mini/2026-03-17 GlobalStandard; agentsV2/responses true"),
                fact("model-quota", f"global quota {quota['currentValue']}/{quota['limit']}, additional 100"),
                fact("model-capacity", f"Central US availableCapacity {capacity['properties']['availableCapacity']}"),
            ])
        if resource_type == "Microsoft.CognitiveServices/accounts/projects":
            item["evidence"].append(validated)
            if "feature" in item:
                item["evidence"].append(
                    "Saved dated official Central US Agents/Responses/Function support in "
                    "evidence\\centralus-91633e9e\\public-feature-evidence.json; runtime installation remains pending."
                )
            else:
                item["status"] = "unknown"
                item["evidence"].append("Project Create expanded by what-if, but provider validation skipped it.")
        if resource_type in ("Microsoft.App/managedEnvironments", "Microsoft.App/containerApps"):
            item["status"] = "unknown"
            item["evidence"].extend(quota_evidence)
            item["evidence"].append("Demand: 14 steady-max vCPU/28 replicas; 28 rollout vCPU/56 replicas.")
            if resource_type == "Microsoft.App/managedEnvironments":
                item["quotas"] = [{
                    "name": "ManagedEnvironmentCount", "limit": usage["limit"],
                    "currentValue": usage["currentValue"], "required": 1,
                }]
                item["evidence"].append(fact("aca-profiles", "Consumption profile listed; not a core quota"))
                item["evidence"].append(fact("region-zones", "Central US logical zones 1, 2 and 3"))
            else:
                item["evidence"].append(
                    "Runtime what-if not run: actual environment outputs/image digest/agent versions/identity "
                    "installation receipt are not installed. Their absence is expected, not user input."
                )
        for prefix, name in (
            ("Microsoft.ContainerRegistry/", "registry"), ("Microsoft.KeyVault/", "vault"),
            ("Microsoft.ServiceBus/", "broker"),
        ):
            if resource_type.startswith(prefix):
                item["evidence"].append(fact(f"what-if-{name}", "exact independent provider preview succeeded"))
        if resource_type == "Microsoft.ServiceBus/namespaces":
            item["evidence"].append(fact("servicebus-skus", "Premium Central US supports zones and partitions"))
        if resource_type == "Microsoft.Network/virtualNetworks":
            network = next(value for value in read("network-usage")["result"]
                           if value["name"]["value"] == "VirtualNetworks")
            item["quotas"] = [{
                "name": "VirtualNetworks", "limit": int(network["limit"]),
                "currentValue": int(network["currentValue"]), "required": 1,
            }]
            item["evidence"].append(fact("network-usage", "actual VNet quota covers one additional isolated VNet"))
        if resource_type in (
            "Microsoft.Insights/components", "Microsoft.Authorization/roleAssignments",
            "Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments", "Microsoft.Insights/diagnosticSettings",
            "Microsoft.Resources/deployments", "Microsoft.Authorization/policyAssignments",
        ):
            item["status"] = "unknown"
            item["evidence"].extend([
                validated, "ARM unsupported expansion is not a proven unsupported resource.",
                "Output-dependent grant/policy/diagnostic/provider checks remain pending installation, not passed.",
            ])
        if resource_type == "Microsoft.Authorization/policyAssignments":
            item["evidence"].append(fact("policy", "three policy assignments read; not compliance certification"))
        if resource_type == "Microsoft.Resources/resourceGroups":
            item["evidence"].append(fact("group-exists-final", "false; target remains absent"))
        if resource_type in (
            "Microsoft.Authorization/roleAssignments", "Microsoft.Resources/tags",
            "Microsoft.Resources/deployments", "Microsoft.Authorization/policyAssignments",
            "Microsoft.Insights/diagnosticSettings",
        ):
            item["evidence"].append("Global/nonregional extension or control-plane object scoped to Central US parents.")
    readiness = {
        "scope": SCOPE, "checkedAtUtc": observed_at, "compiledAtUtc": now,
        "infrastructureFingerprint": fingerprint,
        "checks": checks, "deploymentReady": False,
        "limitations": [
            "Exact model/zones/security/SKUs retained; unknown quotas/grants/provider validation are not passed.",
            "Independent previews do not cover excluded grants or reserve capacity.",
            "Directory installation and actual cloud deployment remain unauthorized.",
            "Retained observation times are not refreshed by finalization; recheck eligibility before provisioning.",
        ],
    }
    region.update({
        "regionalReadiness": readiness, "checkedAtUtc": observed_at, "validationTargetRegion": "centralus",
        "selectedRegion": None, "evidenceStatus": "centralus_prepared_for_staged_foundation_consent_not_runtime_ready",
        "recommendation": "Review the consolidated installation plan without requesting generated IDs. "
        "The current agent-owned controller permits an explicit staged foundation consent decision. "
        "Refresh independent eligibility before authorized provisioning; keep quota and generated-output "
        "checks pending and runtime rollout locked. No current deployment or directory authorization.",
        "outstandingLiveChecks": [
            "Actual ACA Consumption core quota unavailable: direct supported APIs omit it; Microsoft.Quota "
            "reads fail MissingRegistrationForResourceProvider; registration not authorized.",
            "Thirteen managed-identity-dependent grant expansions unsupported by what-if; actual IDs are outputs.",
            "Full provider validation skips eight modules; project/diagnostic/policy acceptance remains pending.",
            "Separate directory consent/installation and approved staff assignments; live authentication untested.",
            "Actual-output runtime preview, image/agent installation and live acceptance not run.",
        ],
    })
    region["centralusRepairPreparation"] = {
        "scope": SCOPE, "checkedAtUtc": observed_at, "compiledAtUtc": now,
        "infrastructureFingerprint": fingerprint,
        "foundryName": FOUNDRY_NAME, "nameAvailable": True, "fullWhatIf": counts,
        "validationSkippedModules": skipped, "evidenceDirectory": "evidence\\centralus-189819a8",
        "mutationsPerformed": False,
    }
    region.setdefault("candidateEvaluations", []).append({
        "scope": SCOPE, "region": "centralus", "checkedAtUtc": observed_at, "compiledAtUtc": now,
        "result": "incomplete-installation-dependent-evidence",
        "evidenceDirectory": "evidence\\centralus-189819a8",
        "passedFacts": ["Repaired domain available; independent account/model preview passed.",
                        "Cosmos AZ access true; exact Central US model quota/capacity sufficient."],
        "rejectionReasons": ["Runtime readiness incomplete: unknown Consumption quota and installation-dependent checks."],
    })
    region["model"]["quota"].update(
        limit=quota["limit"], currentValue=quota["currentValue"],
        available=quota["limit"] - quota["currentValue"],
        evidence="evidence\\centralus-189819a8\\model-quota.json",
    )
    region["model"]["capacity"].update(
        region="centralus", availableCapacity=capacity["properties"]["availableCapacity"],
        status="observed_not_reserved",
        evidence="evidence\\centralus-189819a8\\model-capacity.json",
    )
    region["model"]["quotaCapacityStatus"] = "centralus_metadata_headroom_observed_refresh_before_provisioning"
    region_path.write_text(json.dumps(region, indent=2) + "\n", encoding="utf-8")
    try:
        validate_regional_readiness(
            SCENARIO, {"authorizations": [{"kind": "deployment-preparation", "scope": SCOPE}]},
            SCOPE, json.loads((SCENARIO / "scenario-manifest.json").read_text())["services"],
        )
    except ValueError as error:
        rejection = str(error)
    else:
        raise AssertionError("Backend incorrectly accepted unknown installation-dependent readiness.")
    server = ast.parse((Path.cwd() / "scripts" / "portal_server.py").read_text(encoding="utf-8-sig"))
    execution = next(
        node for node in ast.walk(server) if isinstance(node, ast.FunctionDef) and node.name == "execute_operations"
    )
    assert not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"require_regional_readiness", "validate_regional_readiness"}
        for node in ast.walk(execution)
    ), "Controller review path changed; inspect it before presenting staged consent."
    write("controller-review-check", {
        "scope": SCOPE, "checkedAtUtc": now,
        "infrastructureFingerprint": fingerprint, "actualGuardRejection": rejection,
        "result": "Historical mandatory pre-review gate claim is not current.",
        "evidence": [
            "AST inspection: portal_server.execute_operations contains no require_regional_readiness or "
            "validate_regional_readiness call; it runs the canonical agent through the authorized flow.",
            "portal_workflow.Store.report accepts explicit exact-scope deployment decisions after preparation "
            "without requiring an all-passed regional receipt. Recording a decision grants no consent.",
            "The standalone readiness validator still rejects these retained incomplete/stale observations. "
            "No deployment readiness or runtime acceptance is claimed.",
        ],
        "notPerformed": ["Canonical/backend code edits", "Provider registration", "Directory/resource mutations",
                         "Generated-value questionnaire", "Deployment authorization"],
    })
    write("readiness-guard", {"expectedRejected": True, "reason": rejection, "checkedAtUtc": now})
    write("scope-and-fingerprint-final", {
        "scope": SCOPE, "checkedAtUtc": now, "infrastructureFingerprint": fingerprint,
        "note": "Computed after final main.bicep and azure.yaml edits; compiled preview template equals production.",
    })
    metadata = json.loads((SCENARIO / "reviewed-metadata.json").read_text())
    metadata["summary"] = (
        "Generic Hospitality & Travel 250-seat restaurant reference with scoped Foundry agents and durable kitchen "
        "handoffs. Central US naming repaired; independent previews passed. Installation-dependent readiness "
        "remains pending explicit staged foundation consent; not deployed or live-validated."
    )
    (SCENARIO / "reviewed-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    refresh(SCENARIO, metadata=metadata)
    write("preparation-completed", {
        "stage": "deployment", "operation": "deployment-preparation", "scope": SCOPE, "status": "completed",
        "summary": "Central US Foundry naming repaired and available; full what-if 33 creates/13 dependent "
        "Unsupported expansions, no modifies/deletes. Independent previews passed. ACA Consumption quota "
        "still unknown: Microsoft.Quota NotRegistered, direct supported APIs omit core quota. Idempotent "
        "directory installer/output consumption prepared and tested offline. Current controller permits staged "
        "consent review. Preparation finalized, not deployment-ready: refresh retained eligibility before any "
        "authorized foundation provision; runtime remains locked. No cloud mutations.",
        "evidence": [
            "06-deployment-summary.md: consolidated Central US preparation, exact commands/results/cost/limitations.",
            "evidence\\centralus-189819a8\\installation-plan.json and scripts\\setup_identity.py: exact directory "
            "changes/permissions, ownership-safe retry, generated output capture; no Graph operation executed.",
            "evidence\\centralus-189819a8\\controller-review-check.json: actual current controller inspection; "
            "historical mandatory pre-review gate claim corrected without backend edits.",
            fact("foundry-domain-availability", f"{FOUNDRY_NAME} available before preview"),
            preview, validated, *quota_evidence[:5],
            "00-region-availability.json: 26-resource/SKU/feature checks with final current infrastructure hash; "
            "prior rejected-region evidence preserved. Original observation timestamps retained; unknowns stay unknown.",
            "python -m unittest discover -s generated-scenarios\\resto-scale-agent\\validation -p test_*.py: "
            "see local-checks.json for final exact results.",
            "local-checks.json: Python wiring 15 passed; application 26 passed; main/runtime builds and main lint "
            "passed. Original runtime lint failed without diagnostics; exact-command retry exited 0 as recorded "
            "in evidence\\resume-cbd218af-verification.json. No previous failure erased.",
            "evidence\\centralus-189819a8\\cost-review.json: exact Central US rates refreshed; USD 745-1150 shared, "
            "900-1650 typical full/month planning allowance; not quote/cap; usage/burst/taxes additional.",
            fact("group-exists-final", "false; no owned account reused/adopted or cloud resource provisioned"),
        ],
    })
    print(json.dumps({"checks": dict(Counter(item["status"] for item in checks)),
                      "fingerprint": fingerprint, "guard": rejection, "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
