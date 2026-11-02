"""Persist current Central US preparation evidence without losing earlier regional rejection history."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(__file__).resolve().parent
SCENARIO = RUN.parent.parent
sys.path.insert(0, str(Path.cwd() / "scripts"))

from azure_context import infrastructure_fingerprint, validate_regional_readiness
from scenario_catalog import refresh

from prepare import SCOPE, read, write


def facts(name: str, observation: str) -> str:
    record = read(name)
    return (
        f"{record['command']}: exit {record['exitCode']}; {observation}. "
        f"Observed {record['checkedAtUtc']}; evidence\\centralus-91633e9e\\{name}.json"
    )


def costs() -> dict:
    def meter(file_name: str, product: str, name: str, sku: str | None = None) -> dict:
        matches = [
            item for page in read(file_name)["pages"] for item in page["response"]["Items"]
            if item["productName"] == product and item["meterName"] == name
            and item["type"] == "Consumption" and item["tierMinimumUnits"] == 0
            and (sku is None or item["skuName"] == sku)
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one exact Central US meter: {file_name}/{product}/{name}: {len(matches)}")
        item = matches[0]
        assert item["armRegionName"] == "centralus" and item["currencyCode"] == "USD"
        return {key: item[key] for key in ("meterId", "meterName", "retailPrice", "unitOfMeasure", "armRegionName")}

    rates = {
        "broker": meter("prices-broker", "Service Bus", "Premium Messaging Unit"),
        "cpuActive": meter("prices-aca", "Azure Container Apps", "Standard vCPU Active Usage"),
        "cpuIdle": meter("prices-aca", "Azure Container Apps", "Standard vCPU Idle Usage"),
        "memoryActive": meter("prices-aca", "Azure Container Apps", "Standard Memory Active Usage"),
        "memoryIdle": meter("prices-aca", "Azure Container Apps", "Standard Memory Idle Usage"),
        "cosmosAutoscale": meter("prices-cosmos", "Azure Cosmos DB autoscale", "AP1 100 RUs"),
        "cosmosStorage": meter("prices-cosmos", "Azure Cosmos DB", "Data Stored", "RUs"),
        "continuous7Days": meter("prices-cosmos", "Azure Cosmos DB - PITR", "Cont 7D Bkup Continuous Backup"),
        "input": meter("prices-model", "Azure OpenAI GPT5", "5.4 mini Inp Gl 1M Tokens"),
        "output": meter("prices-model", "Azure OpenAI GPT5", "5.4 mini Opt Gl 1M Tokens"),
    }
    rate = {name: item["retailPrice"] for name, item in rates.items()}
    seconds = 730 * 3600
    return {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "region": "centralus", "currency": "USD",
        "rates": rates,
        "monthlyExamples": {
            "hours": 730,
            "brokerOneMU": round(730 * rate["broker"], 2),
            "cosmos400RU": round(730 * 4 * rate["cosmosAutoscale"], 2),
            "cosmos4000RU": round(730 * 40 * rate["cosmosAutoscale"], 2),
            "nineReplicasIdle": round(seconds * (4.5 * rate["cpuIdle"] + 9 * rate["memoryIdle"]), 2),
            "nineReplicasActive": round(seconds * (4.5 * rate["cpuActive"] + 9 * rate["memoryActive"]), 2),
            "model24MInput7_2MOutput": round(24 * rate["input"] + 7.2 * rate["output"], 2),
            "max28ReplicasActive": round(seconds * (14 * rate["cpuActive"] + 28 * rate["memoryActive"]), 2),
            "rollout56ReplicasActive": round(seconds * (28 * rate["cpuActive"] + 56 * rate["memoryActive"]), 2),
        },
        "planningAllowancesMonthly": {"shared": [745, 1150], "fullReference": [900, 1650], "ancillary": [30, 120]},
        "limitations": [
            "Exact current-region public base meters refreshed; allowances are estimates, not a quote or cap.",
            "Nine warm replicas and 200 turns/day example; maximum scale and transient overlap can cost more.",
            "Ancillary ACR, telemetry, vault and network allowance not individually requoted.",
            "Requests, storage, restore, zone-related billing, egress and taxes may add costs.",
            "Pricing does not override failed name preflight, unknown core quota or incomplete policy evaluation.",
        ],
    }


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    identity = read("identity")["result"]
    assert all(identity[key] == SCOPE[key] for key in ("account", "subscriptionId", "tenantId"))
    assert identity["state"] == "Enabled"
    assert read("group-exists")["result"] is False and read("group-exists-final")["result"] is False
    assert read("scope-and-fingerprint")["infrastructureFingerprint"] == infrastructure_fingerprint(SCENARIO)
    parameters = json.loads((SCENARIO / "infra" / "main.parameters.json").read_text())
    assert parameters["parameters"]["location"]["value"] == "${AZURE_LOCATION}"
    compiled = json.loads((RUN / "main.arm.json").read_text(encoding="utf-8-sig"))
    assert "defaultValue" not in compiled["parameters"]["location"]
    providers = {item["namespace"].casefold(): item for item in read("providers")["result"]}
    full = read("what-if-full")["result"]
    assert full["status"] == "Succeeded" and full["error"] is None
    counts = dict(Counter(item["changeType"] for item in full["changes"]))
    assert counts == {"Create": 9}
    skipped = [item["target"].rsplit("/", 1)[-1] for item in full["diagnostics"]]
    assert len(skipped) == 8
    assert read("validate-full")["result"]["properties"]["provisioningState"] == "Succeeded"
    assert read("what-if-foundry")["exitCode"] == 1
    assert "CustomDomainInUse" in read("what-if-foundry")["stderr"]
    assert read("aca-environment-usage")["exitCode"] == 1
    assert "ResourceGroupNotFound" in read("aca-environment-usage")["stderr"]
    for name in ("registry", "cosmos", "broker", "vault"):
        result = read(f"what-if-{name}")["result"]
        assert result["status"] == "Succeeded" and not result.get("diagnostics")
        assert all(item["changeType"] == "Create" for item in result["changes"])
    checks = []

    def check(service: str, resource_type: str, sku: str, status: str, evidence: list[str], **extra: object) -> None:
        provider = providers.get(resource_type.split("/")[0].casefold())
        if provider is not None:
            assert provider["registrationState"] == "Registered"
            evidence = [facts("providers", f"{provider['namespace']} Registered"), *evidence]
        checks.append({
            "service": service, "resourceType": resource_type, "sku": sku, "region": "centralus",
            "status": status, "evidence": evidence, "quotas": [], **extra,
        })

    preview = facts("what-if-full", "Succeeded; 9 evaluated creates, 0 modifies/deletes; 8 skipped modules")
    properties = next(item for item in read("cosmos-locations")["result"]
                      if item["name"] == "Central US")["properties"]
    assert properties["status"] == "Online"
    assert properties["supportsAvailabilityZone"] is True
    assert properties["isSubscriptionRegionAccessAllowedForAz"] is True
    assert properties["isSubscriptionRegionAccessAllowedForRegular"] is True
    cosmos = facts("cosmos-locations", "Central US Online; zones supported; subscription AZ and regular access TRUE")
    check(
        "cosmos-db", "Microsoft.DocumentDB/databaseAccounts",
        "Standard/NoSQL; autoscale max 4000 RU/s; Continuous7Days", "passed",
        [cosmos, facts("what-if-cosmos", "exact zone/autoscale/Continuous7Days configuration accepted; grants excluded"),
         "Provisioned autoscale, not serverless. Region allows Zone backup redundancy; actual capacity not reserved."],
        zoneRedundant=True, properties=properties,
        features={"serverless": False, "autoscaleMaxRU": 4000, "backupPolicy": "Continuous7Days"},
    )
    for resource_type, sku in (
        ("Microsoft.DocumentDB/databaseAccounts/sqlDatabases", "shared autoscale 400-4000 RU/s"),
        ("Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers", "3 NoSQL containers; /aggregateKey"),
    ):
        check("cosmos-db", resource_type, sku, "passed",
              [cosmos, facts("what-if-cosmos", "exact database/three containers evaluated; data roles excluded")])
    check(
        "foundry", "Microsoft.CognitiveServices/accounts", "AIServices/S0", "blocked",
        [facts("foundry-skus", "AIServices S0 Central US listed; restrictions empty"),
         facts("what-if-foundry", "CustomDomainInUse for exact proposed ai-resto-4tvlzr5zf2rxi"),
         "Conflict is name-specific, not proof that Central US lacks Foundry support. No purge/adoption/rename attempted."],
    )
    quota = next(item for item in read("model-quota")["result"]
                 if item["name"]["value"] == "OpenAI.GlobalStandard.gpt-5.4-mini")
    capacity = next(item for item in read("model-capacity")["result"]["value"] if item["name"] == "GlobalStandard")
    model = next(item for item in read("model-eligibility")["result"]
                 if item["kind"] == "AIServices" and item["model"]["name"] == "gpt-5.4-mini"
                 and item["model"]["version"] == "2026-03-17")
    assert model["model"]["capabilities"]["agentsV2"] == "true"
    assert model["model"]["capabilities"]["responses"] == "true"
    assert quota["limit"] - quota["currentValue"] >= 100
    assert capacity["location"] == "centralus" and capacity["properties"]["availableCapacity"] >= 100
    check(
        "foundry", "Microsoft.CognitiveServices/accounts/deployments",
        "gpt-5.4-mini/2026-03-17/GlobalStandard; capacity 100", "passed",
        [facts("model-eligibility", "exact model/version GA; agentsV2/responses true; GlobalStandard listed"),
         facts("model-quota", f"quota current {quota['currentValue']}, limit {quota['limit']}, additional demand 100"),
         facts("model-capacity", f"Central US availableCapacity {capacity['properties']['availableCapacity']}; not reserved"),
         "Eligibility metadata only; blocked parent prevents deployment. Raw SKU rateLimits retained, no measured RPM claim."],
        quotas=[{"name": quota["name"]["value"], "limit": quota["limit"],
                 "currentValue": quota["currentValue"], "required": 100}],
    )
    check(
        "foundry", "Microsoft.CognitiveServices/accounts/projects", "not-applicable; direct child restaurant",
        "unknown", [preview, "Project skipped; parent account name blocked; real identity outputs not fabricated."],
    )
    check(
        "foundry", "Microsoft.CognitiveServices/accounts/projects",
        "not-applicable; Basic setup, three prompt agents; Responses/app-executed Functions", "unknown",
        [facts("model-eligibility", "exact model agentsV2/responses true"),
         "evidence\\centralus-91633e9e\\public-feature-evidence.json: current Learn Central US Agents/Responses/Function yes.",
         "Public feature support checked; installed-project quota/tool acceptance remains unverified, not passed.",
         "Agents are project data-plane objects, not an additional invented ARM resource type."],
        feature="Foundry Agent Service data-plane prompt agents and function tools",
    )
    usage = next(item for item in read("aca-usage")["result"]["value"]
                 if item["name"]["value"] == "ManagedEnvironmentCount")
    assert usage["currentValue"] + 1 <= usage["limit"]
    assert any(item["name"] == "Consumption" for item in read("aca-profiles")["result"]["value"])
    assert {item["logicalZone"] for item in read("region-zones")["result"][0]["availabilityZoneMappings"]} == {
        "1", "2", "3",
    }
    check(
        "container-apps", "Microsoft.App/managedEnvironments", "workload profiles/Consumption; zoneRedundant=true",
        "unknown",
        [facts("aca-profiles", "Consumption explicitly listed for Central US; profile cores are not environment quota"),
         facts("aca-usage", f"ManagedEnvironmentCount {usage['currentValue']}/{usage['limit']}, demand 1"),
         facts("region-zones", "Central US subscription logical zones 1, 2, 3"),
         facts("aca-environment-usage", "ResourceGroupNotFound; future environment Consumption core quota UNKNOWN"),
         preview, "No resource created to discover quota; documented per-environment limit cannot be assumed."],
        quotas=[{"name": "ManagedEnvironmentCount", "limit": usage["limit"],
                 "currentValue": usage["currentValue"], "required": 1}],
        zoneRedundant=True,
    )
    check(
        "container-apps", "Microsoft.App/containerApps",
        "Consumption; 0.5 vCPU/1 GiB each; web 3-12, chat 3-6, worker 3-10", "unknown",
        [facts("aca-environment-usage", "no actual Managed Environment Consumption Cores limit available"),
         "28 max replicas = 14 vCPU/28 GiB; conservative rollout overlap 56 replicas = 28 vCPU/56 GiB.",
         "Runtime exact what-if needs real environment outputs, image digest, installed agent versions and staff audience.",
         "No Microsoft.Web/serverfarms or Microsoft.Compute VM/VMSS planned; B2/VM-family quotas are not ACA quotas."],
        demand={"vcpus": 28, "instances": 56, "steadyMaxVcpus": 14, "steadyMaxInstances": 28},
    )
    broker = next(item["properties"] for item in read("servicebus-skus")["result"]["value"]
                  if item["name"] == "centralus" and item["properties"]["skuName"] == "Premium")
    assert broker["supportsSKU"] is True and broker["features"]["supportsZoneRedundancy"] is True
    assert broker["features"]["supportsPartitionedSBNamespace"] is True
    for name, service, resource_type, sku in (
        ("registry", "container-registry", "Microsoft.ContainerRegistry/registries",
         "Basic; authenticated public TLS/Entra; admin/anonymous disabled"),
        ("broker", "service-bus", "Microsoft.ServiceBus/namespaces",
         "Premium/1 MU/1 partition; zones enabled; local auth disabled"),
        ("vault", "key-vault", "Microsoft.KeyVault/vaults",
         "standard; RBAC, purge protection, soft delete; authenticated public endpoint"),
    ):
        evidence = [facts(f"what-if-{name}", "exact configuration provider preflight passed; grants/diagnostics excluded"),
                    "No capacity reservation or runtime acceptance claimed; no quota increase requested."]
        if name == "broker":
            evidence.append(facts("servicebus-skus", "Premium Central US supportsSKU/zones/partitions all true"))
        check(service, resource_type, sku, "passed", evidence)
    check(
        "service-bus", "Microsoft.ServiceBus/namespaces/queues",
        "Premium kitchen; sessions/duplicate detection; one queue", "passed",
        [facts("what-if-broker", "exact queue evaluated; data grants excluded")],
    )
    check(
        "key-vault", "Microsoft.KeyVault/vaults/keys",
        "software RSA/3072; sign/verify; expiry 180 days, rotation 90 days", "passed",
        [facts("what-if-vault", "vault/key evaluated; Crypto User identity grant excluded")],
    )
    check(
        "managed-identity", "Microsoft.ManagedIdentity/userAssignedIdentities", "not-applicable; 4 distinct identities",
        "passed", [preview, "Four exact identities evaluated; principal/client IDs remain deployment outputs."],
    )
    network = next(item for item in read("network-usage")["result"] if item["name"]["value"] == "VirtualNetworks")
    assert int(network["currentValue"]) + 1 <= int(network["limit"])
    check(
        "virtual-network", "Microsoft.Network/virtualNetworks", "not-applicable; 10.74.0.0/22", "passed",
        [facts("network-usage", f"VirtualNetworks {network['currentValue']}/{network['limit']}, demand 1"), preview],
        quotas=[{"name": "VirtualNetworks", "limit": int(network["limit"]),
                 "currentValue": int(network["currentValue"]), "required": 1}],
    )
    check(
        "virtual-network", "Microsoft.Network/virtualNetworks/subnets",
        "not-applicable; /23; Microsoft.App/environments delegation", "passed", [preview],
    )
    check(
        "log-analytics", "Microsoft.OperationalInsights/workspaces", "PerGB2018; retention 30 days", "passed",
        [preview, "Workspace evaluated; telemetry ingest volume is not load-tested."],
    )
    check(
        "application-insights", "Microsoft.Insights/components",
        "workspace-based; local auth disabled; sampling 20%", "unknown",
        [preview, "insights skipped because workspace/identity outputs unresolved; not certified."],
    )
    for service, resource_type, sku in (
        ("azure-rbac", "Microsoft.Authorization/roleAssignments", "not-applicable; global extension"),
        ("cosmos-db", "Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments", "not-applicable; data roles"),
        ("diagnostics", "Microsoft.Insights/diagnosticSettings", "not-applicable; diagnostic routing"),
    ):
        check(
            service, resource_type, sku, "unknown",
            [preview, "Nonregional extension bound to Central US parent scope; no independent resource region.",
             "Real identity/output-dependent preview pending; excluded from independent previews, not validated."],
        )
    check(
        "resource-group", "Microsoft.Resources/resourceGroups", "not-applicable", "passed",
        [facts("group-exists-final", "false; exact target absent, no provisioning"), preview],
    )
    check(
        "resource-tags", "Microsoft.Resources/tags", "not-applicable; global extension", "passed",
        [preview, "Nonregional tags extension inherits resource scope; unchanged tags evaluated."],
    )
    check(
        "arm-deployments", "Microsoft.Resources/deployments", "not-applicable; ARM control-plane wrappers", "unknown",
        [preview, "Group-level nonregional control-plane records; eight modules skipped, not whole-reference acceptance."],
    )
    check(
        "azure-policy", "Microsoft.Authorization/policyAssignments", "not-applicable; global inherited policy",
        "unknown",
        [facts("policy", f"{len(read('policy')['result'])} assignments inspected; full preview skipped eight modules"),
         "Nonregional subscription inheritance applies to Central US; skipped modules not certified compliant."],
    )
    cost = costs()
    write("cost-review", cost)
    region_path = SCENARIO / "00-region-availability.json"
    region = json.loads(region_path.read_text(encoding="utf-8-sig"))
    prior = region.get("regionalReadiness")
    history = region.setdefault("regionalReadinessHistory", [])
    if prior and prior.get("scope") != SCOPE and prior not in history:
        history.append(prior)
    readiness = {
        "scope": SCOPE, "checkedAtUtc": now, "infrastructureFingerprint": infrastructure_fingerprint(SCENARIO),
        "checks": checks, "deploymentReady": False,
        "limitations": [
            "Complete dependency inventory checked; blocked/unknown entries prevent preparation completion.",
            "Passing checks establish only their stated metadata/partial provider eligibility, not capacity reservation.",
            "No other scenario or candidate region validated in this bounded attempt.",
        ],
    }
    summary = (
        "Central US preparation failed: exact Foundry custom domain returns CustomDomainInUse. "
        "Cosmos subscription AZ/regular access both true; exact model GlobalStandard quota 100/1000, "
        "additional 100, available capacity 900. ACA Consumption core quota remains unknown for the absent "
        "environment. Full what-if: 9 creates, 8 skipped modules; independent previews partial. "
        "No provisioning, quota requests, directory writes, target/name changes or consent review started."
    )
    region.update({
        "evidenceStatus": "centralus_preparation_failed_foundry_name_and_unverified_dependencies",
        "checkedAtUtc": now, "subscriptionName": identity["name"],
        "requestedRegions": ["centralus", "westus2"],
        "candidateRegions": list(dict.fromkeys([*region["candidateRegions"], "centralus", "westus2"])),
        "selectedRegion": None, "validationTargetRegion": "centralus", "regionalReadiness": readiness,
        "centralusPreparation": {
            "scope": SCOPE, "checkedAtUtc": now, "mutationsPerformed": False,
            "fullWhatIf": {"status": "Succeeded", "counts": counts, "skippedModules": skipped},
            "foundryConflict": read("what-if-foundry")["stderr"],
            "evidenceDirectory": "evidence\\centralus-91633e9e",
            "summary": summary, "estimatedCost": cost["planningAllowancesMonthly"],
            "westus2": "User candidate retained; not queried or selected in this current-region-only attempt.",
        },
        "recommendation": (
            "Central US passes Cosmos AZ regional access and exact model eligibility but the unchanged reference "
            "does not pass complete preparation: Foundry proposed subdomain conflicts and ACA core/dependent checks "
            "remain unknown. Preserve target, name ownership, zones, identity, security and services. Backend may "
            "schedule separately scoped candidate evaluation or naming resolution; no automatic rename, purge, "
            "quota increase or deployment. No deployment-consent review until complete fresh checks pass."
        ),
        "outstandingLiveChecks": [
            "Foundry exact custom domain CustomDomainInUse; unresolved ownership/retention, no purge/adoption/rename.",
            "ACA per-environment Consumption core quota unknown; 14 steady-max/28 rollout-overlap vCPU required.",
            "Eight full-preview modules skipped; real identity, project, diagnostics and policy checks incomplete.",
            "Runtime preview awaits real outputs/image/agent versions/staff audience; no invented production IDs.",
            "No resource or directory writes authorized; no live model/agent/load/recovery acceptance performed.",
            "West US 2 candidate awaits a separately assigned exact saved region; no result inferred.",
        ],
        "historicalEvidenceNote": (
            "results/preparation/recoveryPreparation preserve East US 2 findings; eastusPreparation and "
            "regionalReadinessHistory preserve rejected East US observations. Current evidence is centralusPreparation "
            "and regionalReadiness, not proof of complete deployment readiness."
        ),
    })
    candidate = {
        "region": "centralus", "checkedAtUtc": now, "result": "blocked",
        "rejectionReasons": [
            "Exact Foundry subdomain ai-resto-4tvlzr5zf2rxi: CustomDomainInUse, independent current-region what-if.",
            "ACA Consumption core quota and output-dependent full validation unknown.",
        ],
        "passedFacts": ["Cosmos AZ/regular subscription access true; Online and supportsAvailabilityZone true.",
                        "Exact gpt-5.4-mini/2026-03-17/GlobalStandard quota and capacity sufficient for additional 100."],
        "scope": SCOPE, "evidenceDirectory": "evidence\\centralus-91633e9e",
    }
    region["candidateEvaluations"] = [
        item for item in region["candidateEvaluations"]
        if item.get("evidenceDirectory") != candidate["evidenceDirectory"]
    ]
    region["candidateEvaluations"].append(candidate)
    region["model"]["quota"] = {
        "unit": "thousands of tokens per minute", "limit": quota["limit"], "currentValue": quota["currentValue"],
        "available": quota["limit"] - quota["currentValue"], "requested": 100,
        "evidence": "evidence\\centralus-91633e9e\\model-quota.json",
    }
    region["model"]["capacity"] = {
        "region": "centralus", "availableCapacity": capacity["properties"]["availableCapacity"],
        "requested": 100, "reservation": False, "evidence": "evidence\\centralus-91633e9e\\model-capacity.json",
    }
    region["model"]["inferenceResidency"] = "Global processing; Central US location does not constrain inference."
    region_path.write_text(json.dumps(region, indent=2) + "\n", encoding="utf-8")
    try:
        validate_regional_readiness(
            SCENARIO, {"authorizations": [{"kind": "deployment-preparation", "scope": SCOPE}]},
            SCOPE, json.loads((SCENARIO / "scenario-manifest.json").read_text())["services"],
        )
    except ValueError as error:
        assert "Microsoft.CognitiveServices/accounts" in str(error), str(error)
        write("readiness-guard", {"expectedRejected": True, "reason": str(error), "checkedAtUtc": now})
    else:
        raise AssertionError("Readiness guard accepted blocked Central US evidence.")
    metadata = json.loads((SCENARIO / "reviewed-metadata.json").read_text())
    metadata["summary"] = (
        "Generic Hospitality & Travel reference for a 250-seat restaurant with scoped Foundry agents, deterministic "
        "transactions and durable kitchen handoffs. Local implementation retained; current read-only preparation "
        "failed a resource-name conflict and unverified dependencies. Not deployed or live-validated."
    )
    (SCENARIO / "reviewed-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    refresh(SCENARIO, metadata=metadata)
    write("preparation-failed", {
        "stage": "deployment", "operation": "deployment-preparation", "scope": SCOPE, "status": "failed",
        "summary": summary,
        "evidence": [
            "00-region-availability.json: complete 26-resource/feature readiness inventory with current exact "
            "scope/hash; earlier regional readiness archived, all rejection history retained.",
            "06-deployment-summary.md: Central US results, exact preview boundaries, costs and no-mutation record.",
            facts("what-if-foundry", "FAILED CustomDomainInUse; no name, ownership or security change attempted"),
            cosmos, facts("model-quota", "100 used of 1000; additional 100"),
            facts("model-capacity", "Central US exact model/version/GlobalStandard availableCapacity 900"),
            facts("aca-environment-usage", "FAILED ResourceGroupNotFound; Consumption core quota unknown"),
            facts("aca-usage", "managed environment count 0/50; not a Consumption-core quota"),
            preview, facts("validate-full", "Succeeded with same eight skipped nested modules"),
            facts("what-if-registry", "Succeeded; 2 creates; exact Basic public-authenticated controls retained"),
            facts("what-if-cosmos", "Succeeded; 6 creates; exact zone/autoscale/continuous-backup controls retained"),
            facts("what-if-broker", "Succeeded; 3 creates; Premium 1 MU/1 partition; sessions/dedup/zones retained"),
            facts("what-if-vault", "Succeeded; 3 creates; Standard RBAC/purge-protected RSA key retained"),
            facts("group-exists-final", "false; exact group remains absent"),
            "az bicep build --file generated-scenarios\\resto-scale-agent\\infra\\main.bicep --outfile "
            "generated-scenarios\\resto-scale-agent\\evidence\\centralus-91633e9e\\main.arm.json && "
            "az bicep lint --file generated-scenarios\\resto-scale-agent\\infra\\main.bicep: exit 0, no diagnostics.",
            "evidence\\centralus-91633e9e\\cost-review.json: current-region exact retail meters; shared USD "
            "745-1150/month, full USD 900-1650/month estimates, not quotes/caps; max/rollout can exceed them.",
            "evidence\\centralus-91633e9e\\readiness-guard.json: actual guard rejected blocked Foundry account.",
            "No provisioning, shared-default change, directory write, quota request, other-region validation, "
            "deployment-consent review, suitability approval, hack composition or event deployment.",
        ],
    })
    print(json.dumps({"summary": summary, "statuses": dict(Counter(item["status"] for item in checks)),
                      "cost": cost["monthlyExamples"], "fingerprint": readiness["infrastructureFingerprint"]}, indent=2))


if __name__ == "__main__":
    main()
