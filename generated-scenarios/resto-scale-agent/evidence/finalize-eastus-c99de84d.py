"""Persist observed East US preparation failures and bounded partial checks for this reference only."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
SCENARIO = DIRECTORY.parent
RUN = DIRECTORY / "eastus-c99de84d"
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts"))

from azure_context import infrastructure_fingerprint, validate_regional_readiness
from scenario_catalog import refresh


def read(name: str) -> dict:
    return json.loads((RUN / f"{name}.json").read_text(encoding="utf-8-sig"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def facts(name: str, observation: str) -> str:
    record = read(name)
    return (
        f"{record['command']}: exit {record['exitCode']}; {observation}. "
        f"Observed {record['checkedAtUtc']}; evidence/eastus-c99de84d/{name}.json"
    )


def main() -> None:
    scope = {
        "account": "petender@microsoft.com",
        "subscriptionId": "efd64343-6ef4-4926-951f-d3229f38bd76",
        "tenantId": "16b3c013-d300-468d-ac64-7eda0820b6d3",
        "environment": "resto-scale-agent",
        "resourceGroup": "rg-resto-scale-agent",
        "region": "eastus",
    }
    identity = read("identity")["result"]
    assert all(identity[key] == scope[key] for key in ("account", "subscriptionId", "tenantId"))
    assert identity["state"] == "Enabled"
    assert read("group-exists")["result"] is False
    assert read("group-exists-final")["result"] is False
    compiled = json.loads((DIRECTORY / "main-c99de84d.arm.json").read_text(encoding="utf-8-sig"))
    assert "defaultValue" not in compiled["parameters"]["location"]
    production_parameters = json.loads((SCENARIO / "infra" / "main.parameters.json").read_text(encoding="utf-8"))
    assert production_parameters["parameters"]["location"]["value"] == "${AZURE_LOCATION}"
    providers = {item["namespace"].casefold(): item for item in read("providers")["result"]}
    checks = []

    def check(service: str, resource_type: str, sku: str, status: str, evidence: list[str], **extra: object) -> None:
        provider = resource_type.split("/")[0].casefold()
        if provider in providers:
            assert providers[provider]["registrationState"] == "Registered", provider
            evidence = [facts("providers", f"{resource_type.split('/')[0]} Registered"), *evidence]
        checks.append({
            "service": service, "resourceType": resource_type, "sku": sku, "region": "eastus",
            "status": status, "evidence": evidence, "quotas": [], **extra,
        })

    full = read("what-if-full")["result"]
    assert full["status"] == "Succeeded" and full["error"] is None
    full_counts = {}
    for change in full["changes"]:
        full_counts[change["changeType"]] = full_counts.get(change["changeType"], 0) + 1
    assert full_counts == {"Create": 9}
    skipped = [item["target"].rsplit("/", 1)[-1] for item in full["diagnostics"]]
    assert len(skipped) == 8
    preview_fact = facts("what-if-full", "Succeeded; 9 evaluated creates, 0 modifies/deletes; 8 skipped modules")
    cosmos = next(item for item in read("cosmos-locations")["result"] if item["name"] == "East US")
    properties = cosmos["properties"]
    assert properties["isSubscriptionRegionAccessAllowedForAz"] is False
    assert properties["isSubscriptionRegionAccessAllowedForRegular"] is False
    cosmos_fact = facts(
        "cosmos-locations",
        "East US Online, zones supported, subscription AZ access FALSE and regular access FALSE",
    )
    check(
        "cosmos-db", "Microsoft.DocumentDB/databaseAccounts",
        "Standard/NoSQL; autoscale max 4000 RU/s; Continuous7Days", "blocked",
        [cosmos_fact, facts("what-if-cosmos", "partial independent preview Succeeded; eligibility denial still blocks")],
        zoneRedundant=True, properties=properties,
        features={"serverless": False, "autoscaleMaxRU": 4000, "backupPolicy": "Continuous7Days"},
    )
    for resource_type, sku in (
        ("Microsoft.DocumentDB/databaseAccounts/sqlDatabases", "shared autoscale 400-4000 RU/s"),
        ("Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers", "3 NoSQL containers; /aggregateKey"),
    ):
        check("cosmos-db", resource_type, sku, "blocked", [cosmos_fact, "Parent account regional access denied."])
    check(
        "foundry", "Microsoft.CognitiveServices/accounts", "AIServices/S0", "blocked",
        [
            facts("foundry-skus", "AIServices S0 East US listed, restrictions empty"),
            facts("what-if-foundry", "CustomDomainInUse: ai-resto-4tvlzr5zf2rxi"),
            "No purge, adoption, alternate name, lookup outside target scope or resource creation attempted.",
        ],
    )
    quota = next(
        item for item in read("model-quota")["result"]
        if item["name"]["value"] == "OpenAI.GlobalStandard.gpt-5.4-mini"
    )
    capacity = next(
        item for item in read("model-capacity-regional-corrected")["result"]["value"]
        if item["name"] == "GlobalStandard"
    )
    model = next(
        item for item in read("model-eligibility")["result"]
        if item["kind"] == "AIServices" and item["model"]["name"] == "gpt-5.4-mini"
        and item["model"]["version"] == "2026-03-17"
    )
    assert model["model"]["capabilities"]["agentsV2"] == "true"
    assert model["model"]["capabilities"]["responses"] == "true"
    assert quota["limit"] - quota["currentValue"] >= 100
    assert capacity["properties"]["availableCapacity"] >= 100
    check(
        "foundry", "Microsoft.CognitiveServices/accounts/deployments",
        "gpt-5.4-mini/2026-03-17/GlobalStandard; capacity 100", "passed",
        [
            facts("model-eligibility", "exact AIServices/S0 model/version GA, agentsV2/responses true"),
            facts("model-quota", f"global quota limit {quota['limit']}, used {quota['currentValue']}, additional 100"),
            facts("model-capacity-regional-corrected", f"East US availableCapacity {capacity['properties']['availableCapacity']}"),
            "Model metadata eligibility only; no capacity reservation, provisioning or inference proof.",
        ],
        quotas=[{
            "name": quota["name"]["value"], "limit": quota["limit"],
            "currentValue": quota["currentValue"], "required": 100,
        }],
    )
    check(
        "foundry", "Microsoft.CognitiveServices/accounts/projects", "not-applicable; direct child restaurant",
        "unknown", [preview_fact, "Project skipped; parent account blocked; new identity outputs not fabricated."],
    )
    check(
        "foundry", "Microsoft.CognitiveServices/accounts/projects/agents",
        "not-applicable; Basic setup, prompt agents, Responses and app-executed Functions", "unknown",
        [
            facts("model-eligibility", "selected exact model exposes agentsV2/responses"),
            "Microsoft Learn limits-quotas-regions: East US Agents/Responses/Function supported (read 2026-10-23).",
            "No installed project exists; subscription-specific agent/tool runtime acceptance remains pending.",
        ],
    )
    usage = next(item for item in read("aca-usage")["result"]["value"]
                 if item["name"]["value"] == "ManagedEnvironmentCount")
    check(
        "container-apps", "Microsoft.App/managedEnvironments", "workload profiles/Consumption; zoneRedundant=true",
        "unknown",
        [
            facts("aca-profiles", "Consumption explicitly listed for East US"),
            facts("aca-usage", f"ManagedEnvironmentCount {usage['currentValue']}/{usage['limit']}; demand 1"),
            facts("region-zones-corrected", "East US has subscription logical zones 1, 2, 3"),
            preview_fact,
            "Environment skipped; managed-environment-specific Consumption core quota unavailable before creation.",
        ],
        quotas=[{
            "name": "ManagedEnvironmentCount", "limit": usage["limit"],
            "currentValue": usage["currentValue"], "required": 1,
        }],
        zoneRedundant=True,
    )
    check(
        "container-apps", "Microsoft.App/containerApps",
        "Consumption; each 0.5 vCPU/1 GiB; web max12, chat max6, worker max10", "unknown",
        [
            facts("aca-profiles", "Consumption available; profile description is not environment quota"),
            "28 max replicas = 14 vCPU/28 GiB; conservative old/new revision overlap 56 replicas = 28 vCPU/56 GiB.",
            "Single revision mode retained; no observed core quota for nonexistent environment. Unknown, not passing.",
            "Runtime what-if pending actual environment outputs, agent versions, staff audience and image digest.",
            "No Microsoft.Compute VM/VMSS or Microsoft.Web plan is planned; their quotas cannot prove ACA readiness.",
        ],
        demand={"vcpus": 28, "instances": 56, "steadyMaxVcpus": 14, "steadyMaxInstances": 28},
    )
    for name, service, resource_type, sku in (
        ("registry", "container-registry", "Microsoft.ContainerRegistry/registries", "Basic"),
        ("broker", "service-bus", "Microsoft.ServiceBus/namespaces", "Premium/1 MU/1 partition; zones enabled"),
        ("vault", "key-vault", "Microsoft.KeyVault/vaults", "standard; RBAC, purge protection, soft delete"),
    ):
        record = read(f"what-if-{name}")
        assert record["exitCode"] == 0 and record["result"]["status"] == "Succeeded"
        additional = []
        if name == "broker":
            additional = [facts("servicebus-skus", "Premium East US supportsSKU/zones/partitions all true")]
        check(
            service, resource_type, sku, "passed",
            [facts(f"what-if-{name}", "independent partial provider preview Succeeded; grants/diagnostics excluded"),
             *additional, "Configuration eligibility only; not reserved capacity or deployed acceptance."],
        )
    check(
        "service-bus", "Microsoft.ServiceBus/namespaces/queues",
        "Premium kitchen; sessions + duplicate detection; 1 queue", "passed",
        [facts("what-if-broker", "namespace and kitchen queue evaluated; grants excluded, unchanged session/dedup settings")],
    )
    check(
        "key-vault", "Microsoft.KeyVault/vaults/keys", "software RSA/3072; sign/verify; 180-day expiry/90-day rotation",
        "passed", [facts("what-if-vault", "vault and key evaluated; Crypto User grant excluded, not validated")],
    )
    check(
        "managed-identity", "Microsoft.ManagedIdentity/userAssignedIdentities", "not-applicable; 4 distinct identities",
        "passed", [preview_fact, "Four exact planned identities evaluated; no principal/client IDs fabricated."],
    )
    network_usage = next(item for item in read("network-usage")["result"]
                         if item["name"]["value"] == "VirtualNetworks")
    check(
        "virtual-network", "Microsoft.Network/virtualNetworks", "not-applicable; 10.74.0.0/22", "passed",
        [facts("network-usage", "VirtualNetworks 0/1000; additional 1"), preview_fact],
        quotas=[{
            "name": "VirtualNetworks", "limit": int(network_usage["limit"]),
            "currentValue": int(network_usage["currentValue"]), "required": 1,
        }],
    )
    check(
        "virtual-network", "Microsoft.Network/virtualNetworks/subnets",
        "not-applicable; /23; Microsoft.App/environments delegation", "passed", [preview_fact],
    )
    check(
        "log-analytics", "Microsoft.OperationalInsights/workspaces", "PerGB2018; retention 30 days", "passed",
        [preview_fact, "Workspace evaluated in full preview; ingestion volume and runtime acceptance not tested."],
    )
    check(
        "application-insights", "Microsoft.Insights/components",
        "workspace-based; local auth disabled; 20% sampling", "unknown",
        [preview_fact, "insights skipped because workspace/identity outputs are unresolved; not claimed validated."],
    )
    for service, resource_type, sku in (
        ("azure-rbac", "Microsoft.Authorization/roleAssignments", "not-applicable; global extension resource"),
        ("cosmos-db", "Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments", "not-applicable; scoped data roles"),
        ("diagnostics", "Microsoft.Insights/diagnosticSettings", "not-applicable; workspace diagnostic routing"),
    ):
        check(
            service, resource_type, sku, "unknown",
            [
                preview_fact, "Nonregional extension bound to East US target resources; no independent deployment region.",
                "New-resource identity/output-dependent checks pending; independent previews exclude these, not validate them.",
            ],
        )
    check(
        "resource-group", "Microsoft.Resources/resourceGroups", "not-applicable", "passed",
        [facts("group-exists-final", "false; exact group remains absent"), preview_fact],
    )
    check(
        "resource-tags", "Microsoft.Resources/tags", "not-applicable; global extension resource", "passed",
        [preview_fact, "Nonregional tags extension inherits target resource scope; exact approved tags retained."],
    )
    check(
        "arm-deployments", "Microsoft.Resources/deployments", "not-applicable; ARM control-plane wrappers", "unknown",
        [preview_fact, "Nonregional group-level deployment records; eight nested module evaluations skipped."],
    )
    check(
        "azure-policy", "Microsoft.Authorization/policyAssignments", "not-applicable; global inherited policy",
        "unknown",
        [
            facts("policy", "3 assignments enumerated; actual full preview skips 8 modules"),
            "No claim that skipped modules passed policy; independent previews accepted only their reduced scope.",
        ],
    )
    b2 = next(item for item in read("web-usage")["result"]["value"] if item["name"]["value"] == "B2")
    assert b2["limit"] == 0 and b2["currentValue"] == 0
    now = datetime.now(timezone.utc).isoformat()
    readiness = {
        "scope": scope, "checkedAtUtc": now, "infrastructureFingerprint": infrastructure_fingerprint(SCENARIO),
        "checks": checks, "deploymentReady": False,
        "limitations": [
            "Prior East US 2 blocker superseded by target change, never verified resolved.",
            "No other scenario workspace inspected or changed; no outside-scope regional capacity queries.",
            "All checks are observations, not capacity reservations; passing partial previews do not override failures.",
        ],
    }
    region_path = SCENARIO / "00-region-availability.json"
    region = json.loads(region_path.read_text(encoding="utf-8-sig"))
    region.update({
        "evidenceStatus": "eastus_preparation_failed_regional_access_and_foundry_name",
        "checkedAtUtc": now, "subscriptionName": identity["name"], "requestedRegions": ["eastus"],
        "candidateRegions": list(dict.fromkeys([*region["candidateRegions"], "eastus"])),
        "selectedRegion": None, "validationTargetRegion": "eastus", "regionalReadiness": readiness,
        "eastusPreparation": {
            "scope": scope, "checkedAtUtc": now, "mutationsPerformed": False,
            "fullWhatIf": {"status": "Succeeded", "counts": full_counts, "skippedModules": skipped},
            "foundryConflict": read("what-if-foundry")["stderr"],
            "evidenceDirectory": "evidence/eastus-c99de84d",
            "priorEvidence": "preparation/recoveryPreparation/results retained as historical East US 2 evidence",
            "appServiceDiagnostic": {
                "resourceType": "Microsoft.Web/serverfarms", "region": "eastus", "sku": "B2",
                "applicableToThisScenario": False, "plannedDemand": 0,
                "quota": {"name": "B2", "limit": b2["limit"], "currentValue": b2["currentValue"]},
                "evidence": facts("web-usage", "Microsoft.Web B2 VMs worker quota limit 0, current 0"),
                "conclusion": "Zero permits no positive worker demand; not a Compute B-family quota or an ACA quota. "
                              "No equip-ai workspace inspected or changed and no readiness claimed for it.",
            },
        },
        "recommendation": "East US is not deployable for the unchanged reference: Cosmos subscription AZ and regular "
                          "access both false; exact Foundry custom domain unavailable. Preserve zones, SKUs and identity. "
                          "No allocation, purge, quota request, rename or deployment retry authorized. "
                          "Additional ACA environment-core and dependent identity/policy checks remain unknown. "
                          "Resolve target/name eligibility through the portal, then refresh read-only checks/what-if/cost "
                          "before any later separate exact-target deployment consent.",
        "outstandingLiveChecks": [
            "Cosmos East US subscription eligibility is false for both AZ and regular access; retain zone redundancy.",
            "Foundry exact custom domain conflicts; ownership/retention unresolved. No purge or silent rename.",
            "ACA Consumption environment-core quota must cover max scale and transient rollout demand; currently unknown.",
            "Dependent project/identity/telemetry/policy preview pending real outputs; no fabricated IDs.",
            "Runtime deployment, image publication and Entra setup remain separately unauthorized and unperformed.",
            "Inference, agents, application, load and recovery acceptance remain unperformed.",
        ],
    })
    region["candidateEvaluations"].append({
        "region": "eastus", "checkedAtUtc": now, "result": "blocked",
        "rejectionReasons": [
            "Cosmos isSubscriptionRegionAccessAllowedForAz=false and isSubscriptionRegionAccessAllowedForRegular=false.",
            "Foundry independent provider preview: CustomDomainInUse for the exact proposed name.",
        ],
        "limitations": ["ACA environment Consumption-core quota and output-dependent validation unknown."],
    })
    region["model"]["quota"] = {
        "unit": "thousands of tokens per minute", "limit": quota["limit"], "currentValue": quota["currentValue"],
        "available": quota["limit"] - quota["currentValue"], "requested": 100,
        "evidence": "evidence/eastus-c99de84d/model-quota.json",
    }
    region["model"]["capacity"] = {
        "region": "eastus", "availableCapacity": capacity["properties"]["availableCapacity"],
        "requested": 100, "reservation": False,
        "evidence": "evidence/eastus-c99de84d/model-capacity-regional-corrected.json",
    }
    region["model"]["inferenceResidency"] = "Global processing; East US resource location does not constrain inference."
    region["historicalEvidenceNote"] = (
        "results, preparation and recoveryPreparation preserve dated East US 2 findings. "
        "regionalReadiness and eastusPreparation are the current exact-target observations."
    )
    cost = cost_review()
    write(region_path, region)
    write(RUN / "cost-review.json", cost)
    try:
        validate_regional_readiness(
            SCENARIO, {"authorizations": [{"kind": "deployment-preparation", "scope": scope}]},
            scope, json.loads((SCENARIO / "scenario-manifest.json").read_text())["services"],
        )
    except ValueError as error:
        assert "Cosmos" in str(error) or "Microsoft.DocumentDB/databaseAccounts" in str(error)
        guard = {"expectedRejected": True, "reason": str(error), "checkedAtUtc": now}
    else:
        raise AssertionError("Regional gate unexpectedly accepted blocked evidence.")
    write(RUN / "readiness-guard.json", guard)
    metadata = json.loads((SCENARIO / "reviewed-metadata.json").read_text())
    metadata["summary"] = (
        "Generic Hospitality & Travel reference for a 250-seat restaurant with scoped Foundry agents, deterministic "
        "transactions and durable kitchen handoffs. Local implementation retained; current read-only preparation "
        "failed regional eligibility and a resource-name conflict. Not deployed or live-validated."
    )
    write(SCENARIO / "reviewed-metadata.json", metadata)
    refresh(SCENARIO, metadata=metadata)
    write(DIRECTORY / "preparation-failed-c99de84d.json", {
        "stage": "deployment", "operation": "deployment-preparation", "scope": scope, "status": "failed",
        "summary": "East US preparation failed: Cosmos AZ and regular subscription regional access both false; "
                   "Foundry exact subdomain CustomDomainInUse. ACA Consumption core quota and dependent checks unknown. "
                   "B2 rechecked under Microsoft.Web: limit 0, used 0; not an ACA/Compute quota. "
                   "Full preview has 9 creates, 8 skipped modules; independent previews are partial. "
                   "No cloud mutations, quota requests, directory writes or deployment retry.",
        "evidence": [
            "06-deployment-summary.md: East US current findings, full/partial what-if boundaries and refreshed USD cost.",
            f"00-region-availability.json: {len(checks)} per-resource/SKU/features checks, exact current scope/fingerprint, "
            "blocked/unknown findings; prior region evidence retained. evidence/eastus-c99de84d/readiness-guard.json "
            "verifies deployment guard rejects this evidence.",
            cosmos_fact, facts("what-if-foundry", "CustomDomainInUse; ownership not inferred"),
            preview_fact,
            facts("model-quota", "GlobalStandard gpt-5.4-mini quota 100/1000; additional demand 100"),
            facts("model-capacity-regional-corrected", "exact East US model/version capacity 900, not reserved"),
            facts("web-usage", "actual Microsoft.Web B2 worker quota current 0/limit 0; no positive demand eligible"),
            facts("aca-usage", "environment count 0/50 does NOT establish Consumption core quota"),
            facts("group-exists-final", "false; no resources provisioned"),
            "evidence/eastus-c99de84d/cost-review.json: exact East US public meters; shared estimate "
            "USD 745-1150/month, full reference USD 900-1650/month, not quote/cap; no authorization implied.",
            "Production main.bicep location remains required; infra/main.parameters.json uses ${AZURE_LOCATION}. "
            "Only scenario-local preparation configuration set eastus; no azd environment initialized or defaults changed.",
            "Scenario-only scenario_catalog.refresh used directly to avoid CLI export_index writing shared catalog. "
            "No packages, future hack targets or other scenario files touched.",
        ],
    })
    print(json.dumps({
        "checks": len(checks), "statuses": {status: sum(item["status"] == status for item in checks)
                                         for status in ("passed", "blocked", "unknown")},
        "fingerprint": readiness["infrastructureFingerprint"], "guard": guard,
        "cost": cost["monthlyExamples"],
    }, indent=2))


def cost_review() -> dict:
    def meter(file_name: str, product: str, name: str, sku: str | None = None) -> dict:
        items = [item for page in read(file_name)["pages"] for item in page["response"]["Items"]
                 if item["productName"] == product and item["meterName"] == name
                 and item["type"] == "Consumption" and item["tierMinimumUnits"] == 0
                 and (sku is None or item["skuName"] == sku)]
        assert len(items) == 1, (file_name, product, name, len(items))
        item = items[0]
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
        "input": meter("prices-model-corrected", "Azure OpenAI GPT5", "5.4 mini Inp Gl 1M Tokens"),
        "output": meter("prices-model-corrected", "Azure OpenAI GPT5", "5.4 mini Opt Gl 1M Tokens"),
    }
    rate = {name: item["retailPrice"] for name, item in rates.items()}
    seconds = 730 * 3600
    return {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "region": "eastus", "currency": "USD",
        "rates": rates,
        "monthlyExamples": {
            "hours": 730, "brokerOneMU": round(730 * rate["broker"], 2),
            "cosmos400RU": round(730 * 4 * rate["cosmosAutoscale"], 2),
            "cosmos4000RU": round(730 * 40 * rate["cosmosAutoscale"], 2),
            "nineReplicasIdle": round(seconds * (4.5 * rate["cpuIdle"] + 9 * rate["memoryIdle"]), 2),
            "nineReplicasActive": round(seconds * (4.5 * rate["cpuActive"] + 9 * rate["memoryActive"]), 2),
            "model24MInput7_2MOutput": round(24 * rate["input"] + 7.2 * rate["output"], 2),
            "max28ReplicasActive": round(seconds * (14 * rate["cpuActive"] + 28 * rate["memoryActive"]), 2),
        },
        "planningAllowancesMonthly": {"shared": [745, 1150], "fullReference": [900, 1650], "ancillary": [30, 120]},
        "limitations": [
            "Planning ranges retained after checking actual East US base rates; not a quote, budget approval or cap.",
            "Nine warm replicas and 200 turns/day; max scale and temporary old/new overlap can exceed normal allowance.",
            "Ancillary ACR, logs, insights, vault and network retain unquoted USD 30-120/month allowance.",
            "Requests, storage, restore, zone-related billing, telemetry, egress and taxes can add costs; grants/discounts excluded.",
            "No pricing or preview result overrides Cosmos regional denial, Foundry conflict or unknown environment quota.",
            "East US 2 meter IDs and the old serviceName Azure OpenAI query returned no East US model rates; corrected "
            "product Azure OpenAI GPT5 / service Foundry Models used without substituting old-region prices.",
        ],
    }


if __name__ == "__main__":
    main()
