"""Regression checks for the actual compiled Cosmos grants and vault naming repair."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InfrastructureRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        az = shutil.which("az")
        if az is None:
            raise RuntimeError("Azure CLI Bicep component is required for infrastructure regression tests.")
        result = subprocess.run(
            [az, "bicep", "build", "--file", str(ROOT / "infra" / "main.bicep"), "--stdout"],
            capture_output=True, text=True, encoding="utf-8", timeout=120, check=True,
        )
        cls.compiled = json.loads(result.stdout)
        cls.previous = json.loads(
            (ROOT / "evidence" / "foundation-47a34228" / "main.arm.json").read_text(encoding="utf-8-sig")
        )

    def test_all_three_database_grants_use_fully_qualified_scope_without_chat_access(self) -> None:
        variables = self.compiled["variables"]
        self.assertEqual(
            "[format('{0}/dbs/restaurant', "
            "resourceId('Microsoft.DocumentDB/databaseAccounts', variables('cosmosAccountName')))]",
            variables["cosmosDatabaseScope"],
        )
        params = self.compiled["resources"]["cosmos"]["properties"]["parameters"]
        grants = params["sqlRoleAssignments"]["value"]
        self.assertEqual(3, grants.count("'scope', variables('cosmosDatabaseScope')"))
        self.assertIn("format('identities[{0}]', 0)", grants)
        self.assertIn("format('identities[{0}]', 2)", grants)
        self.assertNotIn("format('identities[{0}]', 1)", grants)
        self.assertNotIn("'scope', '/dbs/restaurant'", grants)
        self.assertNotIn("reference('cosmos')", variables["cosmosDatabaseScope"])

    def test_vault_name_is_scope_bound_and_all_other_vault_controls_are_unchanged(self) -> None:
        expression = self.compiled["variables"]["vaultName"]
        self.assertIn("guid(subscription().subscriptionId, parameters('environment'),", expression)
        self.assertIn("'resto-scale-agent', 'vault-v2'", expression)
        self.assertIn("15", expression)
        current = dict(self.compiled["resources"]["vault"]["properties"]["parameters"])
        previous = dict(self.previous["resources"]["vault"]["properties"]["parameters"])
        self.assertEqual({"value": "[variables('vaultName')]"}, current.pop("name"))
        previous.pop("name")
        self.assertEqual(previous, current)

    def test_existing_resource_names_and_security_inputs_are_preserved(self) -> None:
        self.assertEqual(self.previous["variables"]["uniqueSuffix"], self.compiled["variables"]["uniqueSuffix"])
        self.assertEqual(
            self.previous["variables"]["foundryAccountName"], self.compiled["variables"]["foundryAccountName"]
        )
        for name, module in self.compiled["resources"].items():
            if name not in {"cosmos", "vault"}:
                with self.subTest(module=name):
                    previous_module = dict(self.previous["resources"][name])
                    current_module = dict(module)
                    if "dependsOn" in previous_module:
                        self.assertEqual(
                            sorted(previous_module.pop("dependsOn")), sorted(current_module.pop("dependsOn"))
                        )
                    self.assertEqual(previous_module, current_module)
        current = dict(self.compiled["resources"]["cosmos"]["properties"]["parameters"])
        previous = dict(self.previous["resources"]["cosmos"]["properties"]["parameters"])
        self.assertEqual(previous.pop("name")["value"], self.compiled["variables"]["cosmosAccountName"])
        self.assertEqual({"value": "[variables('cosmosAccountName')]"}, current.pop("name"))
        previous.pop("sqlRoleAssignments")
        current.pop("sqlRoleAssignments")
        self.assertEqual(previous, current)


if __name__ == "__main__":
    unittest.main()
