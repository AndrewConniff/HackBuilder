"""Create only a read-only subscription preview wrapper for the saved exact scope."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent


def main() -> None:
    template_path = DIRECTORY / "what-if-main-19f3d63e.arm.json"
    template = json.loads(template_path.read_text(encoding="utf-8-sig"))
    resources = template["resources"]
    modules = list(resources.values()) if isinstance(resources, dict) else resources
    registry = next(item for item in modules if item["name"] == "registry")
    parameters = registry["properties"]["parameters"]
    expected = {
        "acrSku": "Basic",
        "publicNetworkAccess": "Enabled",
        "networkRuleSetDefaultAction": "Allow",
        "acrAdminUserEnabled": False,
        "anonymousPullEnabled": False,
    }
    for name, value in expected.items():
        assert parameters[name]["value"] == value, name
    assert "networkRuleSetIpRules" not in parameters
    assert "privateEndpoints" not in parameters
    registry_template = registry["properties"]["template"]
    assert registry_template["parameters"]["networkRuleSetIpRules"].get("defaultValue") is None
    assert registry_template["variables"]["shouldConfigureNetworkRuleSet"] == (
        "[or(not(equals(parameters('networkRuleSetIpRules'), null())), "
        "and(equals(variables('publicNetworkAccessMode'), 'Enabled'), "
        "equals(parameters('networkRuleSetDefaultAction'), 'Deny')))]"
    )
    cosmos = next(item for item in modules if item["name"] == "cosmos")
    assert cosmos["properties"]["parameters"]["zoneRedundant"]["value"] is True
    environment = next(item for item in modules if item["name"] == "environment")
    assert environment["properties"]["parameters"]["zoneRedundant"]["value"] is True

    saved = json.loads((DIRECTORY / "main-preflight.parameters.json").read_text(encoding="utf-8-sig"))
    assert saved["parameters"]["environment"]["value"] == "resto-scale-agent"
    assert saved["parameters"]["location"]["value"] == "eastus2"
    saved["parameters"]["guestSigningKeyExpiration"]["value"] = (
        datetime.now(timezone.utc) + timedelta(days=180)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    parameter_path = DIRECTORY / "main-preflight-19f3d63e.parameters.json"
    parameter_path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
    wrapper = {
        "$schema": "https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "resources": [
            {
                "type": "Microsoft.Resources/resourceGroups",
                "apiVersion": "2024-03-01",
                "name": "rg-resto-scale-agent",
                "location": "eastus2",
                "tags": {
                    "Environment": "resto-scale-agent",
                    "ManagedBy": "Bicep",
                    "Project": "resto-scale-agent",
                    "SecurityControl": "Ignore",
                },
            },
            {
                "type": "Microsoft.Resources/deployments",
                "apiVersion": "2022-09-01",
                "name": "reference-preflight-19f3d63e",
                "resourceGroup": "rg-resto-scale-agent",
                "dependsOn": [
                    "[subscriptionResourceId('Microsoft.Resources/resourceGroups', 'rg-resto-scale-agent')]"
                ],
                "properties": {
                    "mode": "Incremental",
                    "expressionEvaluationOptions": {"scope": "inner"},
                    "parameters": saved["parameters"],
                    "template": template,
                },
            },
        ],
    }
    wrapper_path = DIRECTORY / "what-if-subscription-19f3d63e.arm.json"
    wrapper_path.write_text(json.dumps(wrapper, indent=2) + "\n", encoding="utf-8")
    result = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "templateSha256": hashlib.sha256(template_path.read_bytes()).hexdigest(),
        "wrapperSha256": hashlib.sha256(wrapper_path.read_bytes()).hexdigest(),
        "checks": {
            "basicRegistryAuthenticatedPublicAccess": True,
            "premiumNetworkRuleSetConditionFalse": True,
            "adminAndAnonymousAccessDisabled": True,
            "cosmosAndEnvironmentZoneRedundancyRetained": True,
            "sameSavedEnvironmentAndRegion": True,
        },
        "scope": "Compiled-input regression checks and wrapper generation only; no Azure operation.",
    }
    (DIRECTORY / "registry-regression-19f3d63e.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
