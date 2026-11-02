"""Persist actual West US 2 findings and preserve all previous regional rejection evidence."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from prepare import REGION, RUN, SCENARIO, SCOPE, read, write

sys.path.insert(0, str(Path.cwd() / "scripts"))

from azure_context import infrastructure_fingerprint, validate_regional_readiness
from scenario_catalog import refresh


def facts(name: str, observation: str) -> str:
    record = read(name)
    return (
        f"{record['command']}: exit {record['exitCode']}; {observation}. "
        f"Observed {record['checkedAtUtc']}; evidence\\{RUN.name}\\{name}.json"
    )


def costs() -> dict:
    def meter(file_name: str, product: str, name: str, sku: str | None = None) -> dict:
        matches = [
            item for page in read(file_name)["pages"] for item in page["response"]["Items"]
            if item["productName"] == product and item["meterName"] == name
            and item["type"] == "Consumption" and item["tierMinimumUnits"] == 0
            and (sku is None or item["skuName"] == sku)
        ]
        assert len(matches) == 1, f"Exact regional meter ambiguous/missing: {name}"
        item = matches[0]
        assert item["armRegionName"] == REGION and item["currencyCode"] == "USD"
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
    }
    model_meters = [
        item for page in read("prices-model")["pages"] for item in page["response"]["Items"]
        if item["meterName"] in ("5.4 mini Inp Gl 1M Tokens", "5.4 mini Opt Gl 1M Tokens")
    ]
    assert model_meters == [], "Reevaluate model pricing; do not reuse the observed missing-meter result."
    rate = {name: item["retailPrice"] for name, item in rates.items()}
    seconds = 730 * 3600
    return {
        "region": REGION, "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "currency": "USD",
        "rates": rates, "modelRates": None,
        "modelPricingStatus": "Exact gpt-5.4-mini GlobalStandard meters absent; GPT 5 Chat rates not substituted.",
        "monthlyExamples": {
            "hours": 730, "brokerOneMU": round(730 * rate["broker"], 2),
            "cosmos400RU": round(730 * 4 * rate["cosmosAutoscale"], 2),
            "cosmos4000RU": round(730 * 40 * rate["cosmosAutoscale"], 2),
            "nineReplicasIdle": round(seconds * (4.5 * rate["cpuIdle"] + 9 * rate["memoryIdle"]), 2),
            "nineReplicasActive": round(seconds * (4.5 * rate["cpuActive"] + 9 * rate["memoryActive"]), 2),
            "max28ReplicasActive": round(seconds * (14 * rate["cpuActive"] + 28 * rate["memoryActive"]), 2),
            "rollout56ReplicasActive": round(seconds * (28 * rate["cpuActive"] + 56 * rate["memoryActive"]), 2),
            "model24MInput7_2MOutput": None,
        },
        "priorPlanningAllowancesNotRequoted": {"shared": [745, 1150], "fullReference": [900, 1650]},
        "limitations": [
            "Exact current-region base meters only; no complete current-region model/full-reference quote.",
            "Ancillary ACR/vault/network/telemetry not individually requoted; storage/requests/egress/tax may add cost.",
            "Maximum scale and temporary overlap can exceed prior allowances; pricing does not prove eligibility.",
        ],
    }


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    identity = read("identity")["result"]
    assert all(identity[key] == SCOPE[key] for key in ("account", "subscriptionId", "tenantId"))
    assert identity["state"] == "Enabled"
    assert read("group-exists")["result"] is False and read("group-exists-final")["result"] is False
    fingerprint = infrastructure_fingerprint(SCENARIO)
    assert read("scope-and-fingerprint")["infrastructureFingerprint"] == fingerprint
    assert "defaultValue" not in read("main.arm")["parameters"]["location"]
    parameters = json.loads((SCENARIO / "infra" / "main.parameters.json").read_text())
    assert parameters["parameters"]["location"]["value"] == "${AZURE_LOCATION}"
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
    assert "ResourceGroupNotFound" in read("aca-environment-usage")["stderr"]
    for name in ("registry", "cosmos", "broker", "vault"):
        result = read(f"what-if-{name}")["result"]
        assert result["status"] == "Succeeded" and not result.get("diagnostics")
        assert all(item["changeType"] == "Create" for item in result["changes"])
    checks = []

    def check(service: str, resource_type: str, sku: str, status: str, evidence: list[str], **extra: object) -> None:
        provider = providers.get(resource_type.split("/")[0].casefold())
        if provider:
            assert provider["registrationState"] == "Registered"
            evidence = [facts("providers", f"{provider['namespace']} Registered"), *evidence]
        checks.append({
            "service": service, "resourceType": resource_type, "sku": sku, "region": REGION,
            "status": status, "evidence": evidence, "quotas": [], **extra,
        })

    preview = facts("what-if-full", "9 creates, no modifies/deletes; eight modules skipped, not full acceptance")
    properties = next(item for item in read("cosmos-locations")["result"] if item["name"] == "West US 2")["properties"]
    assert properties["status"] == "Online" and properties["supportsAvailabilityZone"] is True
    assert properties["isSubscriptionRegionAccessAllowedForAz"] is False
    assert properties["isSubscriptionRegionAccessAllowedForRegular"] is True
    cosmos = facts("cosmos-locations", "West US 2 Online; zones supported; subscription AZ FALSE, regular TRUE")
    check("cosmos-db", "Microsoft.DocumentDB/databaseAccounts",
          "Standard/NoSQL; provisioned autoscale max 4000 RU/s; Continuous7Days", "blocked",
          [cosmos, facts("what-if-cosmos", "exact feature preview succeeds but does NOT override AZ access FALSE"),
           "Required zones retained; regular access cannot validate this zonal design; not serverless."],
          zoneRedundant=True, properties=properties,
          features={"serverless": False, "autoscaleMaxRU": 4000, "backupPolicy": "Continuous7Days"})
    for resource_type, sku in (
        ("Microsoft.DocumentDB/databaseAccounts/sqlDatabases", "shared autoscale 400-4000 RU/s"),
        ("Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers", "3 NoSQL containers; /aggregateKey"),
    ):
        check("cosmos-db", resource_type, sku, "blocked",
              [cosmos, facts("what-if-cosmos", "partial preview accepted shape; parent subscription AZ access denied")])
    check("foundry", "Microsoft.CognitiveServices/accounts", "AIServices/S0", "blocked",
          [facts("foundry-skus", "West US 2 AIServices S0 listed without restrictions"),
           facts("what-if-foundry", "CustomDomainInUse for exact ai-resto-4tvlzr5zf2rxi"),
           "No purge, adoption, rename or resource mutation attempted; conflict not a regional quota diagnosis."])
    quota = next(item for item in read("model-quota")["result"]
                 if item["name"]["value"] == "OpenAI.GlobalStandard.gpt-5.4-mini")
    models = [item for item in read("model-eligibility")["result"] if item["kind"] == "AIServices"
              and item["model"]["name"] == "gpt-5.4-mini" and item["model"]["version"] == "2026-03-17"]
    assert models == [] and read("model-capacity")["result"]["value"] == []
    check("foundry", "Microsoft.CognitiveServices/accounts/deployments",
          "gpt-5.4-mini/2026-03-17/GlobalStandard; capacity 100", "blocked",
          [facts("model-eligibility", "exact AIServices model/version absent from West US 2 list"),
           facts("model-capacity", "West US 2 exact model/version query returned value=[]; usable capacity unknown"),
           facts("model-quota", f"GLOBAL scope quota {quota['currentValue']}/{quota['limit']}; demand 100"),
           "Global quota headroom is not regional eligibility/capacity or a reservation; no model substitution."],
          quotas=[{"name": quota["name"]["value"], "limit": quota["limit"],
                   "currentValue": quota["currentValue"], "required": 100}])
    check("foundry", "Microsoft.CognitiveServices/accounts/projects", "not-applicable; direct child restaurant",
          "unknown", [preview, "Project skipped and parent account blocked; no output/identity IDs invented."])
    check("foundry", "Microsoft.CognitiveServices/accounts/projects",
          "not-applicable; Basic setup; three prompt agents; Responses/app-executed Functions", "unknown",
          [facts("model-eligibility", "exact required model/version absent"),
           f"evidence\\{RUN.name}\\public-feature-evidence.json: West US 2 absent from current Learn Agents/"
           "Responses and Function region tables; support NOT established.",
           "Bing-specific region mention is not support for this configuration; no live invocation in read-only scope."],
          feature="Foundry Agent Service data-plane prompt agents and function tools")
    usage = next(item for item in read("aca-usage")["result"]["value"]
                 if item["name"]["value"] == "ManagedEnvironmentCount")
    assert usage["currentValue"] + 1 <= usage["limit"]
    assert any(item["name"] == "Consumption" for item in read("aca-profiles")["result"]["value"])
    assert {item["logicalZone"] for item in read("region-zones")["result"][0]["availabilityZoneMappings"]} == {
        "1", "2", "3",
    }
    check("container-apps", "Microsoft.App/managedEnvironments", "workload profiles/Consumption; zones enabled",
          "unknown", [facts("aca-profiles", "Consumption listed; profile cores are not environment core quota"),
                      facts("aca-usage", f"ManagedEnvironmentCount {usage['currentValue']}/{usage['limit']}; demand 1"),
                      facts("region-zones", "subscription logical zones 1/2/3"),
                      facts("aca-environment-usage", "ResourceGroupNotFound; Consumption core quota UNKNOWN"), preview],
          zoneRedundant=True, quotas=[{"name": "ManagedEnvironmentCount", "limit": usage["limit"],
                                      "currentValue": usage["currentValue"], "required": 1}])
    check("container-apps", "Microsoft.App/containerApps",
          "Consumption; each 0.5 vCPU/1 GiB; web 3-12/chat 3-6/worker 3-10", "unknown",
          [facts("aca-environment-usage", "actual Consumption core limit unavailable"),
           "28 max replicas/14 vCPU; conservative rollout overlap 56 replicas/28 vCPU/56 GiB.",
           "Private chat ingress, no worker ingress, managed identities and network encryption unchanged.",
           "Runtime preview awaits actual outputs/image/agent versions/staff audience; no placeholders invented.",
           "No Compute VM/VMSS or Microsoft.Web plan in IaC; their quotas cannot establish ACA eligibility."],
          demand={"vcpus": 28, "instances": 56, "steadyMaxVcpus": 14, "steadyMaxInstances": 28})
    broker = next(item["properties"] for item in read("servicebus-skus")["result"]["value"]
                  if item["name"] == REGION and item["properties"]["skuName"] == "Premium")
    assert broker["supportsSKU"] and broker["features"]["supportsZoneRedundancy"]
    assert broker["features"]["supportsPartitionedSBNamespace"]
    for name, service, resource_type, sku in (
        ("registry", "container-registry", "Microsoft.ContainerRegistry/registries",
         "Basic; authenticated public TLS; admin/anonymous disabled"),
        ("broker", "service-bus", "Microsoft.ServiceBus/namespaces", "Premium/1 MU/1 partition; zones enabled"),
        ("vault", "key-vault", "Microsoft.KeyVault/vaults", "standard; RBAC/purge protection/soft delete"),
    ):
        evidence = [facts(f"what-if-{name}", "exact configuration partial provider preflight passed; grants excluded"),
                    "Limited provider eligibility observation, not a capacity reservation or whole-reference pass."]
        if name == "broker":
            evidence.append(facts("servicebus-skus", "West US 2 Premium supports SKU/zones/partitions"))
        check(service, resource_type, sku, "passed", evidence)
    check("service-bus", "Microsoft.ServiceBus/namespaces/queues", "Premium kitchen; sessions/dedup; one queue",
          "passed", [facts("what-if-broker", "exact queue shape accepted; identity grants excluded")])
    check("key-vault", "Microsoft.KeyVault/vaults/keys", "software RSA/3072; expiry 180d/rotation 90d",
          "passed", [facts("what-if-vault", "exact key shape accepted; Crypto User grant excluded")])
    check("managed-identity", "Microsoft.ManagedIdentity/userAssignedIdentities", "not-applicable; four identities",
          "passed", [preview, "Four identity resources evaluated; real generated IDs remain deployment outputs."])
    network = next(item for item in read("network-usage")["result"] if item["name"]["value"] == "VirtualNetworks")
    assert int(network["currentValue"]) + 1 <= int(network["limit"])
    check("virtual-network", "Microsoft.Network/virtualNetworks", "not-applicable; 10.74.0.0/22", "passed",
          [facts("network-usage", f"VirtualNetworks {network['currentValue']}/{network['limit']}; demand 1"), preview],
          quotas=[{"name": "VirtualNetworks", "limit": int(network["limit"]),
                   "currentValue": int(network["currentValue"]), "required": 1}])
    check("virtual-network", "Microsoft.Network/virtualNetworks/subnets",
          "not-applicable; delegated Microsoft.App/environments /23", "passed", [preview])
    check("log-analytics", "Microsoft.OperationalInsights/workspaces", "PerGB2018; retention 30 days",
          "passed", [preview, "Workspace evaluated; no telemetry ingest or load acceptance claimed."])
    check("application-insights", "Microsoft.Insights/components", "workspace-based; local auth disabled; sample 20%",
          "unknown", [preview, "Skipped workspace/identity-dependent component not certified."])
    for service, resource_type, sku in (
        ("azure-rbac", "Microsoft.Authorization/roleAssignments", "not-applicable; global extension"),
        ("cosmos-db", "Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments", "not-applicable; data roles"),
        ("diagnostics", "Microsoft.Insights/diagnosticSettings", "not-applicable; diagnostic routing"),
    ):
        check(service, resource_type, sku, "unknown",
              [preview, "Nonregional extension inherits West US 2 parent scope; no separate deployment region.",
               "Output-dependent checks excluded from independent previews; not validated; no fabricated IDs."])
    check("resource-group", "Microsoft.Resources/resourceGroups", "not-applicable", "passed",
          [facts("group-exists-final", "false; exact group absent before and after previews"), preview])
    check("resource-tags", "Microsoft.Resources/tags", "not-applicable; global extension", "passed",
          [preview, "Nonregional tags extension inherits parent scope; exact tags unchanged."])
    check("arm-deployments", "Microsoft.Resources/deployments", "not-applicable; ARM control-plane wrappers",
          "unknown", [preview, "Nonregional group wrappers; eight skipped modules prevent whole-reference acceptance."])
    check("azure-policy", "Microsoft.Authorization/policyAssignments", "not-applicable; global inherited policy",
          "unknown", [facts("policy", f"{len(read('policy')['result'])} inherited assignments enumerated"),
                      facts("rbac", "current inherited assignments inspected; no role/directory mutation"),
                      "Nonregional policies apply to West US 2; skipped modules not certified compliant.", preview])
    assert len(checks) == 26
    cost = costs()
    write("cost-review", cost)
    path = SCENARIO / "00-region-availability.json"
    region = json.loads(path.read_text(encoding="utf-8-sig"))
    prior = region.get("regionalReadiness")
    history = region.setdefault("regionalReadinessHistory", [])
    if prior and prior["scope"] != SCOPE and prior not in history:
        history.append(prior)
    summary = (
        "West US 2 preparation failed: required Cosmos AZ subscription access is false; exact Foundry subdomain "
        "returns CustomDomainInUse; required gpt-5.4-mini/2026-03-17 absent from regional model list and capacity "
        "response empty. Global quota 100/1000 does not establish regional eligibility. Agent feature support "
        "unverified; ACA Consumption core quota unknown. Full what-if: 9 creates, 8 skipped modules; partial "
        "previews do not override failures. Exact model regional prices absent. No resources/defaults/targets changed."
    )
    rejection = [
        "Cosmos Online/supportsAvailabilityZone true, but required isSubscriptionRegionAccessAllowedForAz FALSE.",
        "Exact Foundry ai-resto-4tvlzr5zf2rxi preflight: CustomDomainInUse.",
        "Exact gpt-5.4-mini/2026-03-17 absent from AIServices model list; regional model capacity value empty.",
        "Agent/Responses/Function support unverified; West US 2 absent from current official region tables.",
        "ACA Consumption core quota and eight output-dependent modules unverified.",
    ]
    readiness = {
        "scope": SCOPE, "checkedAtUtc": now, "infrastructureFingerprint": fingerprint,
        "checks": checks, "deploymentReady": False,
        "limitations": ["Complete inventory considered; blocked/unknown entries prohibit preparation completion.",
                        "What-if and positive quota metadata cannot reserve allocation or prove runtime acceptance."],
    }
    region.update({
        "checkedAtUtc": now, "evidenceStatus": "westus2_preparation_failed_access_model_name_and_unknown_dependencies",
        "subscriptionName": identity["name"], "subscriptionId": SCOPE["subscriptionId"], "tenantId": SCOPE["tenantId"],
        "selectedRegion": None, "validationTargetRegion": REGION, "regionalReadiness": readiness,
        "westus2Preparation": {
            "scope": SCOPE, "checkedAtUtc": now, "mutationsPerformed": False, "summary": summary,
            "evidenceDirectory": f"evidence\\{RUN.name}", "rejectionReasons": rejection,
            "fullWhatIf": {"status": full["status"], "counts": counts, "skippedModules": skipped},
            "foundryConflict": read("what-if-foundry")["stderr"],
            "costEvidence": f"evidence\\{RUN.name}\\cost-review.json",
        },
        "recommendation": (
            "Neither newly requested candidate passes the complete unchanged reference: Central US has the "
            "exact-name conflict and unresolved checks; West US 2 additionally denies required Cosmos AZ access "
            "and does not list the required model/capacity or establish agent feature support. No deployment "
            "consent review. Retain regions/history, required services, identity, network and zones; no automatic "
            "purge, rename, quota request, service/model substitution, or out-of-scope candidate queries."
        ),
        "outstandingLiveChecks": rejection + [
            "Runtime preview requires genuine deployment outputs/image/agent versions; no invented production IDs.",
            "Exact West US 2 gpt-5.4-mini retail meters missing; no substitute-model or other-region price claimed.",
            "No mutations or runtime operations authorized; no current deployment/model/agent/load/recovery success.",
        ],
        "historicalEvidenceNote": (
            "Earlier results/preparation/recoveryPreparation, eastusPreparation, centralusPreparation and "
            "regionalReadinessHistory remain historical observations. Current attempt is westus2Preparation; "
            "no previous failure or approval is erased or inherited."
        ),
    })
    region["candidateEvaluations"].append({
        "region": REGION, "checkedAtUtc": now, "result": "blocked", "scope": SCOPE,
        "rejectionReasons": rejection, "evidenceDirectory": f"evidence\\{RUN.name}",
    })
    region["model"]["quota"] = {
        "unit": "thousands of tokens per minute", "scope": "Global", "limit": quota["limit"],
        "currentValue": quota["currentValue"], "available": quota["limit"] - quota["currentValue"], "requested": 100,
        "evidence": f"evidence\\{RUN.name}\\model-quota.json",
    }
    region["model"]["capacity"] = {
        "region": REGION, "availableCapacity": None, "requested": 100, "reservation": False,
        "status": "unknown_empty_regional_response", "evidence": f"evidence\\{RUN.name}\\model-capacity.json",
    }
    region["model"]["quotaCapacityStatus"] = "blocked_model_not_listed_regional_capacity_unknown"
    region["model"]["inferenceResidency"] = "Global processing; resource region does not constrain inference."
    path.write_text(json.dumps(region, indent=2) + "\n", encoding="utf-8")
    try:
        validate_regional_readiness(
            SCENARIO, {"authorizations": [{"kind": "deployment-preparation", "scope": SCOPE}]},
            SCOPE, json.loads((SCENARIO / "scenario-manifest.json").read_text())["services"],
        )
    except ValueError as error:
        assert "Microsoft.DocumentDB/databaseAccounts" in str(error)
        write("readiness-guard", {"expectedRejected": True, "reason": str(error), "checkedAtUtc": now})
    else:
        raise AssertionError("Readiness guard accepted blocked/unknown regional evidence.")
    metadata_path = SCENARIO / "reviewed-metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["summary"] = (
        "Generic Hospitality & Travel reference for a 250-seat restaurant with scoped Foundry agents, deterministic "
        "transactions and durable kitchen handoffs. Local implementation retained; read-only regional preparation "
        "failed access, exact model/name and unresolved dependency checks. Not deployed or live-validated."
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    refresh(SCENARIO, metadata=metadata)
    write("preparation-failed", {
        "stage": "deployment", "operation": "deployment-preparation", "scope": SCOPE, "status": "failed",
        "summary": summary, "evidence": [
            f"00-region-availability.json: 26 current checks, exact scope/fingerprint {fingerprint}; earlier history retained.",
            "06-deployment-summary.md: current West US 2 observations and historical rejections, exact preview limits.",
            cosmos, facts("what-if-foundry", "FAILED CustomDomainInUse; no purge/adoption/rename attempted"),
            facts("model-eligibility", "exact required model/version absent from regional AIServices list"),
            facts("model-capacity", "exact current-region model/version capacity returned value=[]; unknown"),
            facts("model-quota", "global quota 100/1000; demand 100; not regional capacity"),
            facts("aca-environment-usage", "FAILED ResourceGroupNotFound; core quota unknown for 28-vCPU rollout demand"),
            preview, facts("validate-full", "Succeeded with skipped-module warnings, not full validation"),
            *[facts(f"what-if-{name}", "Succeeded; exact configuration limited preview; excluded grants documented")
              for name in ("registry", "cosmos", "broker", "vault")],
            facts("group-exists-final", "false; no provisioning or target conflict"),
            f"evidence\\{RUN.name}\\public-feature-evidence.json: current Learn regional feature/quota findings.",
            f"evidence\\{RUN.name}\\cost-review.json: current-region exact base rates; required model meter missing.",
            f"evidence\\{RUN.name}\\readiness-guard.json: actual backend guard rejects failed Cosmos readiness.",
            "az bicep build --file generated-scenarios\\resto-scale-agent\\infra\\main.bicep --outfile "
            f"generated-scenarios\\resto-scale-agent\\evidence\\{RUN.name}\\main.arm.json && "
            "az bicep lint --file generated-scenarios\\resto-scale-agent\\infra\\main.bicep: exit 0; no diagnostics.",
            "scenario_catalog.refresh(scenario, metadata=reviewedMetadata): only scenario manifest refreshed; "
            "CLI index export omitted because this bounded worker cannot write canonical repository files.",
            "No resource/directory mutations, shared-default change, quota requests, other-region queries, "
            "deployment-consent review, suitability approval, packages or teams.",
        ],
    })
    print(json.dumps({"summary": summary, "statuses": dict(Counter(item["status"] for item in checks)),
                      "cost": cost["monthlyExamples"], "fingerprint": fingerprint}, indent=2))


if __name__ == "__main__":
    main()
