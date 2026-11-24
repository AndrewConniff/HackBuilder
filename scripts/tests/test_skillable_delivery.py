"""Verify the single-template, dual-mode Skillable release archive."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skillable_delivery as delivery


def delivery_content(packages: Path) -> Path:
    content = packages / delivery.DELIVERY_FOLDER / "content"
    content.mkdir(parents=True)
    template = {
        "$schema": delivery.TEMPLATE_SCHEMA,
        "contentVersion": "1.0.0.0",
        "parameters": {
            "deploymentMode": {
                "type": "string", "allowedValues": ["learner", "reference"], "defaultValue": "learner",
            },
        },
        "resources": [{
            "condition": "[equals(parameters('deploymentMode'), 'reference')]",
            "type": "Microsoft.Storage/storageAccounts/queueServices/queues", "apiVersion": "2023-05-01",
            "name": "fixture/default/events",
        }],
    }
    (content / delivery.TEMPLATE_NAME).write_text(json.dumps(template), encoding="utf-8")
    for mode in delivery.MODES:
        (content / f"azuredeploy.parameters.{mode}.json").write_text(
            json.dumps({"parameters": {"deploymentMode": {"value": mode}}}), encoding="utf-8",
        )
    (content / "README.md").write_text("Private lab delivery; not deployed.\n", encoding="utf-8")
    (content / "scripts").mkdir()
    (content / "scripts" / "Deploy.ps1").write_text("throw 'Fixture only; never deploy'\n", encoding="utf-8")
    manifest = {"schemaVersion": 1, "modes": {
        mode: {"requiredFiles": [], "postDeployScripts": []} for mode in delivery.MODES
    }}
    (content / "deployment-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return content


class SkillableDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.packages = Path(temporary.name) / "packages"
        self.content = delivery_content(self.packages)
        self.template_path = self.content / delivery.TEMPLATE_NAME
        self.template = delivery.read_object(self.template_path)

    def write_template(self, value: dict) -> None:
        self.template_path.write_text(json.dumps(value), encoding="utf-8")

    def test_builds_one_root_template_with_both_modes_and_all_declared_dependencies(self) -> None:
        (self.content / "data").mkdir()
        (self.content / "data" / "seed.csv").write_text("id\nsynthetic-1\n", encoding="utf-8")
        manifest_path = self.content / "deployment-manifest.json"
        manifest = delivery.read_object(manifest_path)
        manifest["modes"]["reference"]["requiredFiles"] = ["data/seed.csv"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        archive = delivery.build_delivery(self.packages)
        self.assertEqual(archive, delivery.validate_delivery(self.packages))
        with zipfile.ZipFile(archive) as packed:
            self.assertIn("data/seed.csv", packed.namelist())
            self.assertEqual(
                self.template, json.loads(packed.read("azuredeploy.json")),
            )
            self.assertNotIn(delivery.DELIVERY_FOLDER, packed.namelist())

    def test_rejects_external_templates_and_non_resource_group_scope(self) -> None:
        for properties in (
            {"templateLink": {"uri": "https://example.invalid/template.json"}},
            {"template": self.template, "parametersLink": {"uri": "https://example.invalid/parameters.json"}},
        ):
            with self.subTest(properties=properties):
                template = copy.deepcopy(self.template)
                template["resources"] = [{
                    "type": "Microsoft.Resources/deployments", "properties": properties,
                }]
                self.write_template(template)
                with self.assertRaisesRegex(ValueError, "templateLink/parametersLink"):
                    delivery.build_delivery(self.packages)
        template = copy.deepcopy(self.template)
        template["$schema"] = (
            "https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#"
        )
        self.write_template(template)
        with self.assertRaisesRegex(ValueError, "resource-group"):
            delivery.build_delivery(self.packages)

    def test_inline_nested_templates_remain_in_one_file(self) -> None:
        self.template["resources"] = [{
            "type": "Microsoft.Resources/deployments",
            "condition": "[equals(parameters('deploymentMode'), 'reference')]",
            "properties": {"mode": "Incremental", "template": {
                "$schema": delivery.TEMPLATE_SCHEMA, "contentVersion": "1.0.0.0", "resources": [],
            }},
        }]
        self.write_template(self.template)
        delivery.build_delivery(self.packages)
        self.template["resources"][0]["resourceGroup"] = "another-group"
        self.write_template(self.template)
        with self.assertRaisesRegex(ValueError, "inside the Skillable resource group"):
            delivery.build_delivery(self.packages)

    def test_resource_policy_cannot_be_bypassed_by_mode_or_nested_deployment(self) -> None:
        forbidden = {"type": "Microsoft.Sql/servers", "condition": False}
        for resource in (
            forbidden,
            {"type": "Microsoft.Resources/deployments", "properties": {"template": {
                "$schema": delivery.TEMPLATE_SCHEMA, "resources": [forbidden],
            }}},
        ):
            with self.subTest(resource=resource):
                self.template["resources"].append(resource)
                self.write_template(self.template)
                with self.assertRaisesRegex(ValueError, "not allowed by repository policy"):
                    delivery.build_delivery(self.packages)
                self.template["resources"].pop()

    def test_requires_safe_default_and_actual_mode_selection(self) -> None:
        for change in ("default", "unused", "wrong-parameters"):
            with self.subTest(change=change):
                template = copy.deepcopy(self.template)
                if change == "default":
                    template["parameters"]["deploymentMode"]["defaultValue"] = "reference"
                elif change == "unused":
                    template["resources"] = []
                else:
                    path = self.content / "azuredeploy.parameters.reference.json"
                    path.write_text('{"parameters":{"deploymentMode":{"value":"learner"}}}', encoding="utf-8")
                self.write_template(template)
                with self.assertRaisesRegex(ValueError, "deploymentMode"):
                    delivery.build_delivery(self.packages)

    def test_rejects_extra_templates_missing_dependencies_and_unassigned_payloads(self) -> None:
        extra = self.content / "extra.json"
        extra.write_text(json.dumps(self.template), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Only one ARM template"):
            delivery.build_delivery(self.packages)
        extra.write_text('{"synthetic": true}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Assign every supporting file"):
            delivery.build_delivery(self.packages)
        extra.unlink()
        manifest_path = self.content / "deployment-manifest.json"
        manifest = delivery.read_object(manifest_path)
        manifest["modes"]["learner"]["requiredFiles"] = ["missing.csv"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Missing or unsafe manifest dependency"):
            delivery.build_delivery(self.packages)

    def test_rejects_cached_files_credentials_and_alternative_iac(self) -> None:
        for name in (".env", "cacert.pem", "main.bicep", "main.tf", "credentials.json"):
            with self.subTest(name=name):
                path = self.content / name
                path.write_text("not deliverable", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Unsafe or non-deliverable"):
                    delivery.build_delivery(self.packages)
                path.unlink()
        self.template["parameters"]["password"] = {"type": "secureString", "defaultValue": "do-not-ship"}
        self.write_template(self.template)
        with self.assertRaisesRegex(ValueError, "secure parameter default"):
            delivery.build_delivery(self.packages)

    def test_detects_stale_and_incomplete_archive_entries(self) -> None:
        archive = delivery.build_delivery(self.packages)
        (self.content / "README.md").write_text("changed after packaging", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale"):
            delivery.validate_delivery(self.packages)
        delivery.build_delivery(self.packages)
        with zipfile.ZipFile(archive, "w") as packed:
            packed.writestr("azuredeploy.json", "{}")
        with self.assertRaisesRegex(ValueError, "exactly the content files"):
            delivery.validate_delivery(self.packages)


if __name__ == "__main__":
    unittest.main()
