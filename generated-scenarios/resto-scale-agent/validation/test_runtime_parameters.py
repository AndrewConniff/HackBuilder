"""Local parameter wiring tests; synthetic deployment outputs are not Azure evidence."""

import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from setup_identity import ownership, role_id, ROLES
SPEC = importlib.util.spec_from_file_location(
    "prepare_runtime", Path(__file__).resolve().parents[1] / "scripts" / "prepare_runtime.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeParametersTests(unittest.TestCase):
    def setUp(self):
        self.scope = (
            "/subscriptions/00000000-0000-0000-0000-000000000001"
            "/resourceGroups/rg-resto-test/providers/"
        )
        values = {
            "AZURE_RESOURCE_GROUP": "rg-resto-test",
            "AZURE_LOCATION": "eastus2",
            "AZURE_ENV_NAME": "resto-test",
            "AZURE_SUBSCRIPTION_ID": "00000000-0000-0000-0000-000000000001",
            "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000003",
            "AZURE_CONTAINER_APPS_ENVIRONMENT_ID": self.scope + "Microsoft.App/managedEnvironments/test",
            "AZURE_CONTAINER_APPS_ENVIRONMENT_DOMAIN": "example.internal",
            "AZURE_CONTAINER_REGISTRY_ENDPOINT": "test.azurecr.io",
            "FOUNDRY_ACCOUNT_NAME": "test",
            "FOUNDRY_PROJECT_NAME": "test/restaurant",
            "RESOURCE_SUFFIX": "test",
            "COSMOS_ENDPOINT": "https://test.documents.azure.com",
            "KEY_VAULT_URI": "https://test.vault.azure.net",
            "SERVICE_BUS_NAMESPACE": "test.servicebus.windows.net",
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=synthetic",
            "RUNTIME_IDENTITIES": [
                {"role": role, "resourceId": self.scope + f"Microsoft.ManagedIdentity/userAssignedIdentities/{role}",
                 "clientId": "00000000-0000-0000-0000-000000000002"}
                for role in ("web", "chat", "worker", "scaler")
            ],
        }
        self.outputs = {key: {"value": value} for key, value in values.items()}
        self.versions = {"Initialized": True, "AgentVersions": {"guest": "1", "staff": "2", "kitchen": "3"}}
        self.options = {
            "environment": "resto-test", "location": "eastus2",
            "image": "test.azurecr.io/restaurant@sha256:" + "a" * 64,
            "endpoint": "https://test.services.ai.azure.com/api/projects/restaurant",
            "tenant": "00000000-0000-0000-0000-000000000003",
            "subscription": "00000000-0000-0000-0000-000000000001",
        }
        scope = {"account": "synthetic@example.invalid", "environment": "resto-test", "resourceGroup": "rg-resto-test",
                 "region": "eastus2", "tenantId": self.options["tenant"], "subscriptionId": self.options["subscription"]}
        self.options["identity"] = {
            "installed": True, "scope": scope, "ownershipMarker": ownership(scope),
            "staffTenantId": scope["tenantId"], "staffAudience": "00000000-0000-0000-0000-000000000004",
            "roleIds": {role: role_id(ownership(scope), role) for role in ROLES},
            "api": {"clientId": "00000000-0000-0000-0000-000000000004",
                    "objectId": "00000000-0000-0000-0000-000000000005",
                    "servicePrincipalId": "00000000-0000-0000-0000-000000000006"},
            "client": {"clientId": "00000000-0000-0000-0000-000000000007",
                       "objectId": "00000000-0000-0000-0000-000000000008",
                       "servicePrincipalId": "00000000-0000-0000-0000-000000000009"}
        }

    def test_retains_pinned_versions_and_all_infrastructure_outputs(self):
        result = MODULE.parameters(self.outputs, self.versions, **self.options)["parameters"]
        self.assertEqual(self.versions["AgentVersions"], result["agentVersions"]["value"])
        self.assertEqual(self.outputs, result["infrastructure"]["value"])
        self.assertNotIn("staffAuthenticationJson", result)
        self.assertEqual(self.options["identity"]["staffAudience"], result["staffAudience"]["value"])
        self.assertEqual(self.options["tenant"], result["staffTenantId"]["value"])
        self.assertEqual(self.options["identity"]["client"]["clientId"], result["staffClientId"]["value"])

    def test_rejects_another_scenario_resource_group(self):
        self.outputs["AZURE_RESOURCE_GROUP"]["value"] = "rg-another-scenario"
        with self.assertRaisesRegex(ValueError, "resource group"):
            MODULE.parameters(self.outputs, self.versions, **self.options)

    def test_rejects_mutable_and_foreign_registry_images(self):
        for image in ("test.azurecr.io/restaurant:latest", "other.azurecr.io/restaurant@sha256:" + "a" * 64):
            with self.subTest(image=image), self.assertRaisesRegex(ValueError, "immutable image"):
                MODULE.parameters(self.outputs, self.versions, **(self.options | {"image": image}))

    def test_rejects_foreign_classic_and_credential_bearing_endpoints(self):
        for endpoint in (
            "https://other.services.ai.azure.com/api/projects/restaurant",
            "https://test.services.ai.azure.com/api/projects/other",
            "https://test.openai.azure.com",
            "https://user:password@test.services.ai.azure.com/api/projects/restaurant",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(ValueError, "exact Foundry project"):
                MODULE.parameters(self.outputs, self.versions, **(self.options | {"endpoint": endpoint}))

    def test_rejects_incomplete_initializer_results(self):
        for versions in ({"Initialized": False}, {"Initialized": True, "AgentVersions": {"guest": "1"}}):
            with self.subTest(versions=versions), self.assertRaises(ValueError):
                MODULE.parameters(self.outputs, versions, **self.options)

    def test_rejects_different_region_subscription_tenant_and_identity_scope(self):
        for name, replacement in (
            ("AZURE_LOCATION", "westus3"),
            ("AZURE_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000004"),
            ("AZURE_TENANT_ID", "00000000-0000-0000-0000-000000000004"),
        ):
            with self.subTest(name=name):
                original = self.outputs[name]["value"]
                self.outputs[name]["value"] = replacement
                with self.assertRaisesRegex(ValueError, "exact confirmed deployment target"):
                    MODULE.parameters(self.outputs, self.versions, **self.options)
                self.outputs[name]["value"] = original
        self.outputs["RUNTIME_IDENTITIES"]["value"][0]["resourceId"] = "/subscriptions/other/resourceGroups/rg-resto-test/id"
        with self.assertRaisesRegex(ValueError, "identity belongs"):
            MODULE.parameters(self.outputs, self.versions, **self.options)


if __name__ == "__main__":
    unittest.main()
