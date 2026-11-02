"""Wrap the unchanged group template for read-only preview of an absent target group."""

import json
from pathlib import Path

directory = Path(__file__).resolve().parent
template = json.loads((directory / "what-if-main-c3e1750f.arm.json").read_text(encoding="utf-8-sig"))
parameters = json.loads((directory / "main-preflight.parameters.json").read_text(encoding="utf-8"))
assert parameters["parameters"]["environment"]["value"] == "resto-scale-agent"
assert parameters["parameters"]["location"]["value"] == "eastus2"
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
            "name": "reference-preflight-c3e1750f",
            "resourceGroup": "rg-resto-scale-agent",
            "dependsOn": [
                "[subscriptionResourceId('Microsoft.Resources/resourceGroups', 'rg-resto-scale-agent')]"
            ],
            "properties": {
                "mode": "Incremental",
                "expressionEvaluationOptions": {"scope": "inner"},
                "parameters": parameters["parameters"],
                "template": template,
            },
        },
    ],
}
output = directory / "what-if-subscription-c3e1750f.arm.json"
output.write_text(json.dumps(wrapper, indent=2) + "\n", encoding="utf-8")
print(f"Generated {output.name}: only rg-resto-scale-agent and its unchanged main template.")
print("No Azure call, resource-group creation or deployment was executed by this generator.")
