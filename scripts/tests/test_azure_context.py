"""Test private target discovery without tokens, mutations or Azure resource queries."""

from __future__ import annotations

import json
import sys
import tempfile
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import azure_context


class AzureContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scenario = self.root / "generated-scenarios" / "example"
        self.scenario.mkdir(parents=True)
        (self.scenario / "00-region-availability.json").write_text(
            '{"provisionalRegion":"eastus2"}', encoding="utf-8",
        )
        self.project = {"projectSlug": "example", "authorizations": []}
        self.identity = {"account": "operator@example.test", "subscriptionId": "sub-id", "tenantId": "tenant-id"}

    def responses(self, azd: str = "operator@example.test") -> list[str]:
        return [
            json.dumps(self.identity),
            '{"expiresOn":"future","subscription":"sub-id","tenant":"tenant-id"}',
            f"Logged in to Azure as {azd}",
        ]

    def test_command_resolves_windows_cli_entrypoint_and_does_not_use_shell(self) -> None:
        with (
            patch.object(azure_context.shutil, "which", return_value=r"C:\Tools\az.cmd"),
            patch.object(azure_context.subprocess, "run", return_value=
                         subprocess.CompletedProcess([], 0, stdout="{}", stderr="")) as run,
        ):
            self.assertEqual("{}", azure_context.command(self.root, ["az", "account", "show"]))
        self.assertEqual(r"C:\Tools\az.cmd", run.call_args.args[0][0])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_discovery_reuses_architecture_and_conventions_without_resource_queries(self) -> None:
        with patch.object(azure_context, "command", side_effect=self.responses()) as command:
            result = azure_context.discover(self.root, self.scenario, self.project)
        self.assertEqual("eastus2", result["scope"]["region"])
        self.assertEqual("example", result["scope"]["environment"])
        self.assertEqual("rg-example", result["scope"]["resourceGroup"])
        self.assertNotIn("accessToken", json.dumps(result))
        self.assertEqual(3, command.call_count)
        self.assertIn("--check-status", command.call_args_list[-1].args[1])
        self.assertIn("metadata", result["authentication"]["azureCli"])

    def test_identity_mismatch_and_local_environment_conflicts_block_proposal(self) -> None:
        with (
            patch.object(azure_context, "command", side_effect=self.responses("other@example.test")),
            self.assertRaisesRegex(ValueError, "names differ"),
        ):
            azure_context.discover(self.root, self.scenario, self.project)
        env = self.scenario / ".azure" / "existing"
        env.mkdir(parents=True)
        (env / ".env").write_text('AZURE_SUBSCRIPTION_ID="wrong"\n', encoding="utf-8")
        with (
            patch.object(azure_context, "command", side_effect=self.responses()),
            self.assertRaisesRegex(ValueError, "conflicts"),
        ):
            azure_context.discover(self.root, self.scenario, self.project)

    def test_first_discovery_accepts_explicit_null_saved_context(self) -> None:
        self.project["deploymentContext"] = None
        with patch.object(azure_context, "command", side_effect=self.responses()):
            result = azure_context.discover(self.root, self.scenario, self.project)
        self.assertEqual(self.identity["subscriptionId"], result["scope"]["subscriptionId"])
        self.assertEqual("eastus2", result["scope"]["region"])

    def test_scenario_target_proposal_reuses_already_validated_tool_identity(self) -> None:
        identified = {"scope": self.identity, "authentication": {"azureCli": "Verified", "azd": "Verified"}}
        with patch.object(azure_context, "identity") as identity:
            result = azure_context.discover(self.root, self.scenario, self.project, identified=identified)
        identity.assert_not_called()
        self.assertEqual(self.identity["subscriptionId"], result["scope"]["subscriptionId"])
        self.assertEqual("rg-example", result["scope"]["resourceGroup"])

    def test_existing_azd_environment_and_explicit_edits(self) -> None:
        env = self.scenario / ".azure" / "existing"
        env.mkdir(parents=True)
        (env / ".env").write_text('AZURE_RESOURCE_GROUP="rg-existing"\n', encoding="utf-8")
        with patch.object(azure_context, "command", side_effect=self.responses()):
            result = azure_context.discover(self.root, self.scenario, self.project, {"region": "westus3"})
        self.assertEqual("existing", result["scope"]["environment"])
        self.assertEqual("rg-existing", result["scope"]["resourceGroup"])
        self.assertEqual("westus3", result["scope"]["region"])
        self.assertEqual("User-edited proposed target", result["sources"]["region"])

class RegionalReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.scenario = Path(self.temp.name)
        (self.scenario / "infra").mkdir()
        (self.scenario / "infra" / "main.bicep").write_text("param location string", encoding="utf-8")
        (self.scenario / "azure.yaml").write_text("name: example", encoding="utf-8")
        self.scope = {
            "account": "operator", "subscriptionId": "sub", "tenantId": "tenant",
            "environment": "example", "resourceGroup": "rg-example", "region": "eastus2",
        }
        self.project = {"authorizations": [{"kind": "deployment-preparation", "scope": self.scope}]}
        self.readiness = {
            "scope": self.scope, "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
            "infrastructureFingerprint": azure_context.infrastructure_fingerprint(self.scenario),
            "checks": [{
                "service": "cosmos-db", "resourceType": "Microsoft.DocumentDB/databaseAccounts",
                "sku": "Standard", "region": "eastus2", "status": "passed",
                "evidence": ["Actual az cosmosdb locations list results; East US 2."],
                "zoneRedundant": True, "properties": {
                    "supportsAvailabilityZone": True, "isSubscriptionRegionAccessAllowedForAz": True,
                    "isSubscriptionRegionAccessAllowedForRegular": False, "status": "Online",
                },
            }],
        }

    def validate(self, services: list[str] | None = None) -> list[str]:
        (self.scenario / "00-region-availability.json").write_text(
            json.dumps({"regionalReadiness": self.readiness}), encoding="utf-8",
        )
        return azure_context.validate_regional_readiness(
            self.scenario, self.project, self.scope, services or ["cosmos-db"],
        )

    def test_cosmos_public_zone_support_does_not_override_subscription_access(self) -> None:
        self.assertTrue(self.validate())
        properties = self.readiness["checks"][0]["properties"]
        for value in (False, None, "true"):
            properties["isSubscriptionRegionAccessAllowedForAz"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "not eligible"):
                self.validate()
        properties["isSubscriptionRegionAccessAllowedForAz"] = True
        properties["supportsAvailabilityZone"] = False
        with self.assertRaisesRegex(ValueError, "not eligible"):
            self.validate()

    def test_nonzone_cosmos_uses_regular_subscription_access_flag(self) -> None:
        self.readiness["checks"][0]["zoneRedundant"] = False
        with self.assertRaisesRegex(ValueError, "AllowedForRegular"):
            self.validate()
        self.readiness["checks"][0]["properties"]["isSubscriptionRegionAccessAllowedForRegular"] = True
        self.assertTrue(self.validate())

    def test_scope_freshness_infrastructure_and_complete_service_coverage(self) -> None:
        with self.assertRaisesRegex(ValueError, "omits selected"):
            self.validate(["cosmos-db", "foundry"])
        self.readiness["checkedAtUtc"] = (datetime.now(timezone.utc) - timedelta(minutes=16)).isoformat()
        with self.assertRaisesRegex(ValueError, "15 minutes"):
            self.validate()
        self.readiness["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
        (self.scenario / "infra" / "main.bicep").write_text("param other string", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "infrastructure changes"):
            self.validate()
        self.readiness["infrastructureFingerprint"] = azure_context.infrastructure_fingerprint(self.scenario)
        self.readiness["scope"] = {**self.scope, "subscriptionId": "another-scenario-subscription"}
        with self.assertRaisesRegex(ValueError, "exact preparation scope"):
            self.validate()
        self.project["authorizations"] = []
        with self.assertRaisesRegex(ValueError, "authorization"):
            self.validate()

    def vm(self) -> dict:
        check = {
            "service": "compute", "resourceType": "Microsoft.Compute/virtualMachines",
            "sku": "Standard_B2s", "region": "eastus2", "status": "passed",
            "evidence": ["Actual SKU restrictions and usage responses."], "vmFamily": "standardBSFamily",
            "restrictions": [], "zonesSupported": True, "demand": {"vcpus": 8, "instances": 4},
            "quotas": [
                {"name": "standardBSFamily", "limit": 10, "currentValue": 2, "required": 8},
                {"name": "cores", "limit": 20, "currentValue": 10, "required": 8},
                {"name": "virtualMachines", "limit": 10, "currentValue": 4, "required": 4},
            ],
        }
        self.readiness["checks"] = [check]
        return check

    def test_vm_family_total_and_count_quota_all_include_scale_demand(self) -> None:
        check = self.vm()
        self.assertTrue(self.validate(["compute"]))
        for index in range(3):
            quota = check["quotas"][index]
            original = quota["limit"]
            quota["limit"] = quota["currentValue"] + quota["required"] - 1
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "Insufficient"):
                self.validate(["compute"])
            quota["limit"] = original
        check["quotas"][0]["limit"] = 0
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            self.validate(["compute"])

    def test_vm_restrictions_unknown_zones_and_underreported_demand_are_not_available(self) -> None:
        check = self.vm()
        check["restrictions"] = [{"reasonCode": "NotAvailableForSubscription"}]
        with self.assertRaisesRegex(ValueError, "restrictions"):
            self.validate(["compute"])
        check["restrictions"] = []
        check["zonesSupported"] = None
        with self.assertRaisesRegex(ValueError, "requested-zone"):
            self.validate(["compute"])
        check["zonesSupported"] = True
        check["quotas"][0]["required"] = 1
        with self.assertRaisesRegex(ValueError, "headroom"):
            self.validate(["compute"])

    def test_multiple_resources_share_regional_and_family_quota(self) -> None:
        check = self.vm()
        self.readiness["checks"].append(json.loads(json.dumps(check)))
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            self.validate(["compute"])

    def test_app_service_quota_is_not_inferred_from_a_vm_size_label(self) -> None:
        self.readiness["checks"] = [{
            "service": "app-service", "resourceType": "Microsoft.Web/serverfarms", "sku": "B2",
            "region": "eastus2", "status": "passed", "evidence": ["Actual Microsoft.Web usage response"],
            "quotas": [{"name": "B2 workers", "currentValue": 0, "limit": 0, "required": 1}],
        }]
        with self.assertRaisesRegex(ValueError, "Microsoft.Web/serverfarms"):
            self.validate(["app-service"])
        self.readiness["checks"][0]["quotas"] = []
        with self.assertRaisesRegex(ValueError, "Microsoft.Web SKU/worker"):
            self.validate(["app-service"])

    def test_unknown_missing_or_nonnumeric_evidence_is_rejected(self) -> None:
        check = self.vm()
        check["status"] = "unknown"
        with self.assertRaisesRegex(ValueError, "blocked or unknown"):
            self.validate(["compute"])
        check["status"] = "passed"
        check["quotas"][0]["limit"] = True
        with self.assertRaisesRegex(ValueError, "numeric"):
            self.validate(["compute"])
        check["quotas"][0]["limit"] = 10
        check["evidence"] = []
        with self.assertRaisesRegex(ValueError, "real command"):
            self.validate(["compute"])
