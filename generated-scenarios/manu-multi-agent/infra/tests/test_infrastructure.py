"""Check the compiled infrastructure and later application integration contract without Azure access."""

import json
import os
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCENARIO = Path(__file__).resolve().parents[2]
APPLICATION_TEMPLATE = Path(
    os.environ.get("ABCBUILDER_APPLICATION_EVIDENCE", SCENARIO / ".application-evidence")
) / "main.arm.json"
TEMPLATE = json.loads(
    (APPLICATION_TEMPLATE if APPLICATION_TEMPLATE.exists() else SCENARIO / ".infra-evidence" / "main.arm.json")
    .read_text(encoding="utf-8")
)


def resources(template: dict) -> list[dict]:
    value = template.get("resources", {})
    return list(value.values()) if isinstance(value, dict) else value


def nested(template: dict, name: str) -> dict:
    return resource(template, name)["properties"]["template"]


def resource(template: dict, name: str) -> dict:
    value = template["resources"]
    if isinstance(value, dict):
        return value[name]
    prefix = {"vnet": "network", "app": "application"}.get(name, name)
    matches = [
        item for item in value
        if item["name"].startswith(f"[format('{prefix}-")
        or (name == "consumer" and item["type"] == "Microsoft.Authorization/roleAssignments")
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected exactly one compiled resource for {name}, found {len(matches)}")
    return matches[0]


def descendants(template: dict) -> list[dict]:
    result = []
    for resource in resources(template):
        result.append(resource)
        properties = resource.get("properties", {})
        child = properties.get("template") if isinstance(properties, dict) else None
        if child:
            result.extend(descendants(child))
    return result


class InfrastructureTests(unittest.TestCase):
    def test_foundation_has_no_workload_or_fake_url(self) -> None:
        self.assertEqual("foundation", TEMPLATE["parameters"]["deploymentPhase"]["defaultValue"])
        self.assertIn("workload", TEMPLATE["resources"]["workload"]["condition"])
        self.assertIn("null()", TEMPLATE["outputs"]["APP_PUBLIC_URL"]["value"])
        self.assertIn("project: src/MobilityCommercial.Web", (SCENARIO / "azure.yaml").read_text())

    def test_model_and_region_defaults_use_persisted_evidence(self) -> None:
        evidence = json.loads((SCENARIO / "00-region-availability.json").read_text())
        for key in ("location", "modelName", "modelVersion", "modelSku"):
            self.assertIn("variables(", TEMPLATE["parameters"][key]["defaultValue"])
        self.assertIsNone(evidence["selectedRegion"])
        self.assertFalse(evidence["liveChecksPerformed"])
        self.assertEqual("eastus2", evidence["provisionalRegion"])

    def test_private_services_are_keyless_and_not_public(self) -> None:
        data = nested(TEMPLATE, "dependencies")
        for module in ("platformStorage", "businessStorage", "cosmos", "search", "vault", "registry"):
            with self.subTest(module=module):
                wrapper = data["resources"][module]["properties"]
                parameters = wrapper["parameters"]
                if module == "cosmos":
                    self.assertEqual("Disabled", parameters["networkRestrictions"]["value"]["publicNetworkAccess"])
                    account = wrapper["template"]["resources"]["databaseAccount"]
                    self.assertIn("networkRestrictions", json.dumps(account))
                else:
                    self.assertEqual("Disabled", parameters["publicNetworkAccess"]["value"])
                    self.assertIn("publicNetworkAccess", json.dumps(wrapper["template"]["resources"]))
        for name in ("platformStorage", "businessStorage"):
            self.assertFalse(data["resources"][name]["properties"]["parameters"]["allowSharedKeyAccess"]["value"])
        self.assertTrue(data["resources"]["cosmos"]["properties"]["parameters"]["disableLocalAuthentication"]["value"])
        self.assertTrue(data["resources"]["search"]["properties"]["parameters"]["disableLocalAuth"]["value"])

    def test_fixture_storage_is_separate_and_runtime_read_only(self) -> None:
        data = nested(TEMPLATE, "dependencies")["resources"]
        platform = data["platformStorage"]["properties"]["parameters"]
        business = data["businessStorage"]["properties"]["parameters"]
        self.assertNotEqual(platform["name"]["value"], business["name"]["value"])
        container = business["blobServices"]["value"]["containers"][0]
        self.assertEqual("synthetic-fixtures", container["name"])
        roles = container["roleAssignments"]
        app_role = next(role for role in roles if role["principalType"] == "ServicePrincipal")
        self.assertEqual("Storage Blob Data Reader", app_role["roleDefinitionIdOrName"])
        access = json.dumps(nested(TEMPLATE, "access"))
        self.assertNotIn("businessStorageName", access)

    def test_internal_environment_and_all_four_subnets(self) -> None:
        environment = TEMPLATE["resources"]["appEnvironment"]["properties"]["parameters"]
        self.assertTrue(environment["internal"]["value"])
        self.assertEqual("Disabled", environment["publicNetworkAccess"]["value"])
        network = resource(nested(TEMPLATE, "network"), "vnet")["properties"]["parameters"]
        subnets = network["subnets"]["value"]
        self.assertEqual(["apps", "agents", "apim", "endpoints"], [value["name"] for value in subnets])
        self.assertEqual("Microsoft.App/environments", subnets[0]["delegation"])
        self.assertEqual("Microsoft.App/environments", subnets[1]["delegation"])
        self.assertEqual("Microsoft.Web/serverFarms", subnets[2]["delegation"])
        self.assertTrue(all("networkSecurityGroupResourceId" in value for value in subnets))

    def test_private_links_and_internal_dns(self) -> None:
        private = nested(TEMPLATE, "privateLinks")
        self.assertEqual(8, len(private["variables"]["zoneNames"]))
        self.assertEqual(7, len(private["variables"]["targets"]))
        foundry = private["variables"]["targets"][0]
        self.assertEqual([0, 1, 2], foundry["zones"])
        dns = TEMPLATE["resources"]["appDns"]["properties"]["parameters"]["a"]["value"]
        self.assertEqual(["@", "*"], [value["name"] for value in dns])

    def test_direct_project_and_single_capability_host(self) -> None:
        foundry = nested(TEMPLATE, "foundry")
        project = foundry["resources"]["project"]
        self.assertEqual("Microsoft.CognitiveServices/accounts/projects", project["type"])
        self.assertEqual("SystemAssigned", project["identity"]["type"])
        for name in ("storageConnection", "cosmosConnection", "searchConnection"):
            self.assertEqual("AAD", foundry["resources"][name]["properties"]["authType"])
        hosts = [
            value for value in descendants(TEMPLATE)
            if value["type"].lower().endswith("/capabilityhosts")
        ]
        self.assertEqual(1, len(hosts))
        self.assertEqual("Agents", hosts[0]["properties"]["capabilityHostKind"])
        self.assertFalse(any("MachineLearningServices" in value["type"] for value in descendants(TEMPLATE)))
        self.assertEqual(
            ["access", "privateLinks"],
            [name for name in TEMPLATE["resources"]["capability"]["dependsOn"] if name in ("access", "privateLinks")],
        )

    def test_workload_requires_real_installation_values(self) -> None:
        workload = nested(TEMPLATE, "workload")
        for name in ("imageDigest", "fixtureManifestHash"):
            self.assertEqual(64, workload["parameters"][name]["minLength"])
            self.assertEqual(64, workload["parameters"][name]["maxLength"])
        for name in ("salesAgentVersion", "marketingAgentVersion", "coordinatorAgentVersion"):
            self.assertEqual(1, workload["parameters"][name]["minLength"])
        self.assertEqual(36, workload["parameters"]["consumerRoleDefinitionId"]["minLength"])
        self.assertEqual(32, workload["parameters"]["signingKeyVersion"]["minLength"])
        self.assertIn("signingKeyVersion", workload["variables"]["settings"]["Signing__KeyUri"])
        role = resource(workload, "consumer")["properties"]["roleDefinitionId"]
        self.assertIn("parameters('consumerRoleDefinitionId')", role)
        self.assertNotIn("53ca6127", role)

    def test_runtime_bounds_and_three_agent_versions(self) -> None:
        workload = nested(TEMPLATE, "workload")
        settings = workload["variables"]["settings"]
        expected = {
            "Limits__MaxInputCharacters": "4000",
            "Limits__MaxOutputTokens": "800",
            "Limits__MaxResponsesRequests": "7",
            "Limits__MaxCumulativeTokens": "30000",
            "Limits__DeadlineSeconds": "90",
            "Limits__MaxConcurrentHandoffs": "4",
            "Foundry__SalesAgentName": "sales-fit",
            "Foundry__MarketingAgentName": "marketing-claims",
            "Foundry__CoordinatorAgentName": "handoff-coordinator",
        }
        for name, value in expected.items():
            self.assertEqual(value, settings[name])
        app = resource(workload, "app")["properties"]["parameters"]
        self.assertEqual(1, app["scaleSettings"]["value"]["minReplicas"])
        self.assertEqual(3, app["scaleSettings"]["value"]["maxReplicas"])
        self.assertIn("@sha256:", app["containers"]["value"][0]["image"])
        self.assertFalse(app["ingressAllowInsecure"]["value"])

    def test_gateway_has_explicit_routes_and_identity_replacement(self) -> None:
        workload = nested(TEMPLATE, "workload")
        routes = workload["variables"]["operations"]
        self.assertEqual(8, len(routes))
        self.assertFalse(any("*" in route["urlTemplate"] for route in routes))
        self.assertIn("/api/handoffs", [route["urlTemplate"] for route in routes])
        gateway = resource(workload, "gateway")["properties"]["parameters"]
        self.assertEqual("StandardV2", gateway["sku"]["value"])
        self.assertEqual(1, gateway["skuCapacity"]["value"])
        self.assertEqual("External", gateway["virtualNetworkType"]["value"])
        policy = ET.parse(SCENARIO / "infra" / "modules" / "gateway-policy.xml").getroot()
        auth = policy.find("inbound/authentication-managed-identity")
        self.assertEqual("__GATEWAY_CLIENT_ID__", auth.attrib["client-id"])
        self.assertEqual("__BACKEND_RESOURCE__", auth.attrib["resource"])
        deletion = policy.find("inbound/set-header[@name='Authorization']")
        self.assertEqual("delete", deletion.attrib["exists-action"])
        self.assertEqual(2, len(policy.findall("inbound/rate-limit-by-key")))
        self.assertIsNone(policy.find(".//trace"))
        self.assertIsNone(policy.find(".//retry"))
        error_responses = policy.findall("on-error/choose/when/return-response")
        error_responses += policy.findall("on-error/choose/otherwise/return-response")
        self.assertEqual(
            ["429", "404", "503"],
            [response.find("set-status").attrib["code"] for response in error_responses],
        )
        for response in error_responses:
            self.assertIsNotNone(response.find("set-header[@name='X-Correlation-ID']"))
            self.assertIsNotNone(response.find("set-header[@name='Cache-Control']"))

    def test_signing_key_and_cosmos_planning_ceiling(self) -> None:
        data = nested(TEMPLATE, "dependencies")["resources"]
        vault = data["vault"]["properties"]["parameters"]
        self.assertTrue(vault["enablePurgeProtection"]["value"])
        key = vault["keys"]["value"][0]
        self.assertEqual("RSA", key["kty"])
        self.assertEqual(2048, key["keySize"])
        self.assertEqual(["sign", "verify"], key["keyOps"])
        self.assertEqual("Key Vault Crypto User", key["roleAssignments"][0]["roleDefinitionIdOrName"])
        cosmos = data["cosmos"]["properties"]["parameters"]
        self.assertEqual(5000, cosmos["totalThroughputLimit"]["value"])
        self.assertNotIn("sqlDatabases", cosmos)

    def test_naming_tags_docs_and_guarded_cloud_hooks(self) -> None:
        tags = TEMPLATE["variables"]["tags"]
        self.assertEqual("manu-multi-agent", tags["Project"])
        self.assertEqual("Ignore", tags["SecurityControl"])
        self.assertIn("fail(", tags["Environment"])
        self.assertIn("rg-", tags["Environment"])
        source = (SCENARIO / "infra" / "main.bicep").read_text()
        self.assertEqual(1, source.count("uniqueString(resourceGroup().id)"))
        wiring = (SCENARIO / "azure.yaml").read_text()
        self.assertIn("preprovision:", wiring)
        self.assertIn("postprovision:", wiring)
        self.assertIn("prepublish:", wiring)
        self.assertIn("deployment_lifecycle.py before", wiring)
        self.assertIn("deployment_lifecycle.py after", wiring)
        headings = re.findall(r"^## (.+)$", (SCENARIO / "04-implementation-plan.md").read_text(), re.MULTILINE)
        self.assertEqual(
            [
                "Overview", "Resource Inventory", "Module Structure", "Implementation Tasks",
                "Dependency Graph", "Runtime Flow Diagram", "Naming Conventions", "Execution Handoff",
            ],
            headings,
        )
        for name in ("04-implementation-plan.md", "05-implementation-reference.md"):
            for number, line in enumerate((SCENARIO / name).read_text().splitlines(), 1):
                self.assertLessEqual(len(line), 120, f"{name}:{number}")


if __name__ == "__main__":
    unittest.main()
