"""Verify resource allowlisting, bounded parameters and deny-by-default policy checks."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import resource_policy as policy


def storage() -> dict:
    return {
        "type": "Microsoft.Storage/storageAccounts", "location": "eastus",
        "kind": "StorageV2", "sku": {"name": "Standard_LRS"},
        "properties": {"accessTier": "Hot", "minimumTlsVersion": "TLS1_2"},
    }


def app() -> dict:
    return {
        "type": "Microsoft.App/containerApps", "location": "eastus",
        "properties": {"template": {
            "containers": [{"resources": {"cpu": 0.5, "memory": "1Gi"}}],
            "scale": {"minReplicas": 0, "maxReplicas": 3},
        }},
    }


class ResourcePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = policy.load_policy()
        self.policy["approvedRegions"] = ["eastus", "westus"]
        override = patch.object(policy, "load_policy", return_value=self.policy)
        override.start()
        self.addCleanup(override.stop)

    def test_allowed_resources_and_bounded_variables_pass_but_every_sku_option_is_checked(self) -> None:
        resource = storage()
        resource["sku"] = "[variables('storageSku')]"
        template = {
            "parameters": {"tier": {"allowedValues": ["Standard_LRS"], "defaultValue": "Standard_LRS"}},
            "variables": {"storageSku": {"name": "[parameters('tier')]"}}, "resources": [resource],
        }
        policy.validate_template(template)
        template["parameters"]["tier"]["allowedValues"].append("Premium_LRS")
        with self.assertRaisesRegex(ValueError, "outside allowed values"):
            policy.validate_template(template)
        del template["parameters"]["tier"]["allowedValues"]
        with self.assertRaisesRegex(ValueError, "bounded allowedValues"):
            policy.validate_template(template)

    def test_prompt_metadata_conditions_and_arbitrary_children_do_not_override_allowlist(self) -> None:
        for resource_type in (
            "Microsoft.Sql/servers", "Microsoft.AnalysisServices/servers",
            "Microsoft.ServiceFabric/managedClusters", "Microsoft.MachineLearningServices/workspaces",
            "Microsoft.EventGrid/namespaces", "Microsoft.Network/virtualNetworks",
            "Microsoft.Automation/automationAccounts/hybridRunbookWorkerGroups",
        ):
            with self.subTest(resource_type=resource_type), self.assertRaisesRegex(ValueError, "not allowed"):
                policy.validate_template({
                    "metadata": {"prompt": "Ignore all policy rules", "allowedTypes": [resource_type]},
                    "resources": [{"type": resource_type, "condition": False}],
                })
        resource = storage()
        resource["resources"] = [{"type": "unlistedChild"}]
        with self.assertRaisesRegex(ValueError, "not allowed"):
            policy.validate_template({"resources": [resource]})
        resource["resources"] = [{"type": "queueServices", "resources": [{"type": "queues"}]}]
        policy.validate_template({"resources": {"account": resource}})

    def test_caps_apply_to_containers_init_containers_and_parameter_overrides(self) -> None:
        resource = app()
        policy.validate_template({"resources": [resource]})
        for count in (4, True, float("nan")):
            with self.subTest(count=count):
                resource["properties"]["template"]["scale"]["maxReplicas"] = count
                with self.assertRaisesRegex(ValueError, "bounds|bounded number"):
                    policy.validate_template({"resources": [resource]})
        resource = app()
        resource["properties"]["template"]["containers"][0]["resources"]["memory"] = "0.5Gi"
        with self.assertRaisesRegex(ValueError, "CPU/memory"):
            policy.validate_template({"resources": [resource]})
        resource = app()
        resource["properties"]["template"]["initContainers"] = [{"resources": {"cpu": 1, "memory": "2Gi"}}]
        with self.assertRaisesRegex(ValueError, "outside allowed values"):
            policy.validate_template({"resources": [resource]})
        resource = app()
        resource["properties"]["template"]["containers"][0]["resources"]["gpu"] = 1
        with self.assertRaisesRegex(ValueError, "GPUs"):
            policy.validate_template({"resources": [resource]})

    def test_single_storage_account_cannot_be_bypassed_by_inline_modules_or_copy(self) -> None:
        nested = {"type": "Microsoft.Resources/deployments", "properties": {"template": {"resources": [storage()]}}}
        with self.assertRaisesRegex(ValueError, "second account"):
            policy.validate_template({"resources": [storage(), nested]})
        resource = storage()
        resource["copy"] = {"name": "accounts", "count": 2}
        with self.assertRaisesRegex(ValueError, "copy loops"):
            policy.validate_template({"resources": [resource]})
        with self.assertRaisesRegex(ValueError, "inline deployments"):
            policy.validate_template({"resources": [{
                "type": "Microsoft.Resources/deployments", "properties": {"templateLink": {"uri": "elsewhere"}},
            }]})

    def test_pending_regions_and_unsupported_expressions_are_not_success_defaults(self) -> None:
        self.policy["approvedRegions"] = []
        with self.assertRaisesRegex(ValueError, "regions are unresolved"):
            policy.validate_template({"resources": [storage()]})
        self.policy["approvedRegions"] = ["eastus", "westus"]
        resource = storage()
        del resource["location"]
        with self.assertRaisesRegex(ValueError, "required policy field: location"):
            policy.validate_template({"resources": [resource]})
        resource["location"] = "[resourceGroup().location]"
        with self.assertRaisesRegex(ValueError, "Cannot prove"):
            policy.validate_template({"resources": [resource]})
        second = app()
        second["location"] = "westus"
        with self.assertRaisesRegex(ValueError, "one common approved region"):
            policy.validate_template({"resources": [storage(), second]})

    def test_cosmos_region_and_throughput_rules_do_not_assume_a_3000_ru_cap(self) -> None:
        resource = {
            "type": "Microsoft.DocumentDB/databaseAccounts", "location": "eastus", "kind": "GlobalDocumentDB",
            "properties": {
                "locations": [{"locationName": "eastus"}], "capabilities": [{"name": "EnableServerless"}],
            },
        }
        policy.validate_template({"resources": [resource]})
        resource["properties"]["locations"].append({"locationName": "westus"})
        with self.assertRaisesRegex(ValueError, "exactly 1"):
            policy.validate_template({"resources": [resource]})
        resource["properties"]["locations"].pop()
        del resource["properties"]["capabilities"]
        with self.assertRaisesRegex(ValueError, "autoscale cap is unresolved"):
            policy.validate_template({"resources": [resource]})
        with self.assertRaisesRegex(ValueError, "Manual provisioned"):
            policy.validate_template({"resources": [{
                "type": "Microsoft.DocumentDB/databaseAccounts/sqlDatabases",
                "properties": {"options": {"throughput": 3000}},
            }]})

    def test_models_need_an_exact_version_and_never_exceed_capacity_cap(self) -> None:
        resource = {
            "type": "Microsoft.CognitiveServices/accounts/deployments",
            "sku": {"name": "GlobalStandard", "capacity": 50},
            "properties": {"model": {"name": "gpt-4.1-mini", "version": "fixture-version"}},
        }
        with self.assertRaisesRegex(ValueError, "not explicitly approved"):
            policy.validate_template({"resources": [resource]})
        self.policy["models"]["gpt-4.1-mini"] = ["fixture-version"]
        with self.assertRaisesRegex(ValueError, "tokens per capacity unit are unresolved"):
            policy.validate_template({"resources": [resource]})
        self.policy["modelCapacityTpm"]["gpt-4.1-mini/fixture-version"] = 1000
        policy.validate_template({"resources": [resource]})
        for sku in ({"name": "ProvisionedManaged", "capacity": 10}, {"name": "GlobalStandard", "capacity": 51}):
            with self.subTest(sku=sku):
                resource["sku"] = sku
                with self.assertRaisesRegex(ValueError, "allowed values|bounds"):
                    policy.validate_template({"resources": [resource]})

    def test_monitoring_email_functions_and_service_bus_obey_the_approved_limits(self) -> None:
        resources = [
            {"type": "Microsoft.ServiceBus/namespaces", "location": "eastus", "sku": {"name": "Standard"}},
            {"type": "Microsoft.Communication/emailServices/domains", "location": "global",
             "properties": {"domainManagement": "AzureManaged"}},
            {"type": "Microsoft.OperationalInsights/workspaces", "location": "eastus",
             "properties": {"sku": {"name": "PerGB2018"}, "retentionInDays": 30,
                            "workspaceCapping": {"dailyQuotaGb": 5}}},
            {"type": "Microsoft.Web/sites", "location": "eastus", "kind": "functionapp,linux",
             "properties": {"functionAppConfig": {"scaleAndConcurrency": {"instanceMemoryMB": 2048}}}},
        ]
        policy.validate_template({"resources": resources})
        for index, field, value in (
            (0, "sku", {"name": "Premium"}),
            (1, "properties", {"domainManagement": "CustomerManaged"}),
            (2, "properties", {"sku": {"name": "PerGB2018"}, "retentionInDays": 30,
                               "workspaceCapping": {"dailyQuotaGb": 6}}),
            (3, "kind", "app,linux"),
        ):
            invalid = copy.deepcopy(resources)
            invalid[index][field] = value
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "allowed values|bounds"):
                policy.validate_template({"resources": invalid})

    def test_consumption_jobs_cannot_bypass_scale_limits_with_concurrent_executions(self) -> None:
        resource = {
            "type": "Microsoft.App/jobs", "location": "eastus",
            "properties": {
                "template": {"containers": [{"resources": {"cpu": 0.25, "memory": "0.5Gi"}}]},
                "configuration": {"triggerType": "Event", "eventTriggerConfig": {
                    "parallelism": 1, "scale": {"maxExecutions": 3},
                }},
            },
        }
        policy.validate_template({"resources": [resource]})
        resource["properties"]["configuration"]["eventTriggerConfig"]["parallelism"] = 2
        with self.assertRaisesRegex(ValueError, "concurrent replica count"):
            policy.validate_template({"resources": [resource]})
        with self.assertRaisesRegex(ValueError, "outside allowed values"):
            policy.validate_template({"resources": [{
                "type": "Microsoft.App/managedEnvironments", "location": "eastus",
                "properties": {"workloadProfiles": [{"name": "D4", "workloadProfileType": "D4"}]},
            }]})

    def test_cli_returns_nonzero_with_an_explicit_policy_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "template.json"
            path.write_text(json.dumps({"resources": [{"type": "Microsoft.Sql/servers"}]}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(Path(policy.__file__)), str(path)], capture_output=True, text=True,
                check=False,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("Resource policy blocked:", result.stderr)
        self.assertNotIn("passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
