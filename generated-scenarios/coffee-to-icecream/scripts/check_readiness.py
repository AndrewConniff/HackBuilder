"""Collect explicitly authorized read-only target metadata; never register providers, provision or change defaults."""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "efd64343-6ef4-4926-951f-d3229f38bd76"
TENANT = "16b3c013-d300-468d-ac64-7eda0820b6d3"
REGIONS = ("swedencentral", "westeurope", "uksouth")
PROVIDERS = (
    "Microsoft.CognitiveServices", "Microsoft.Web", "Microsoft.Storage",
    "Microsoft.OperationalInsights", "Microsoft.Insights", "Microsoft.Authorization",
)


def collect(repository: Path) -> None:
    """Verify the authorized identity and save actual provider, SKU, model, quota and role observations."""
    sys.path.insert(0, str(repository / "scripts"))
    import azure_context

    identity = azure_context.identity(repository)
    if identity["scope"] != {
        "account": "petender@microsoft.com", "subscriptionId": SUBSCRIPTION, "tenantId": TENANT
    }:
        raise ValueError("Current identity differs from authorized target; no subscription discovery performed.")
    az = shutil.which("az")
    if az is None:
        raise ValueError("Azure CLI is missing.")
    cli = [az]
    if Path(az).suffix.lower() == ".cmd":
        cli = [str(Path(az).parent.parent / "python.exe"), "-m", "azure.cli"]
    evidence = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "scope": identity["scope"],
        "authority": {
            "designReview": "Accept this design for readiness preparation",
            "authorizePreparation": True,
            "operations": "Read-only exact-target readiness and ARM what-if; no writes or deployment consent",
        },
        "observations": {},
    }
    output = ROOT / "evidence" / "readiness.json"
    output.parent.mkdir(exist_ok=True)

    def query(key: str, arguments: list[str]) -> object:
        result = subprocess.run([*cli, *arguments, "--output", "json"], capture_output=True,
                                text=True, encoding="utf-8", timeout=120, check=False)
        observation = {"command": ["az", *arguments, "--output", "json"], "exitCode": result.returncode}
        if result.returncode:
            observation["error"] = result.stderr[-2000:]
            value = None
            print(f"FAILED {key}: {result.stderr[-300:]}", file=sys.stderr)
        else:
            value = json.loads(result.stdout)
            observation["result"] = value
            print(f"READ {key}")
        evidence["observations"][key] = observation
        output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        return value

    query("deployer", ["ad", "signed-in-user", "show", "--query", "{objectId:id,userPrincipalName:userPrincipalName}"])
    query("effectiveSubscriptionGrants", [
        "role", "assignment", "list", "--subscription", SUBSCRIPTION,
        "--assignee-object-id", "214d672b-df87-4f3b-94fd-7863032546c1", "--include-inherited", "--all",
        "--query", f"[?scope=='/subscriptions/{SUBSCRIPTION}'].{{role:roleDefinitionName,scope:scope}}",
    ])
    query("agentConsumerRole", ["role", "definition", "list", "--subscription", SUBSCRIPTION,
                              "--name", "Foundry Agent Consumer"])
    query("policyAssignments", ["policy", "assignment", "list", "--subscription", SUBSCRIPTION,
                               "--scope", f"/subscriptions/{SUBSCRIPTION}"])
    query("effectivePolicies", ["rest", "--method", "get", "--url",
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
        "Microsoft.Authorization/policyAssignments",
        "--url-parameters", "api-version=2024-04-01", "$filter=atScope()"])
    query("modelCapacity", ["rest", "--method", "get", "--url",
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
        "Microsoft.CognitiveServices/modelCapacities",
        "--url-parameters", "api-version=2024-10-01", "modelFormat=OpenAI",
        "modelName=gpt-4.1-mini", "modelVersion=2025-04-14",
        "--query", "value[?properties.skuName=='GlobalStandard' && "
        "(location=='swedencentral' || location=='westeurope' || location=='uksouth')]"])
    for provider in PROVIDERS:
        query(provider, ["provider", "show", "--subscription", SUBSCRIPTION, "--namespace", provider])
    query("storageSkus", ["rest", "--method", "get", "--url",
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
        "Microsoft.Storage/skus?api-version=2025-01-01",
        "--query", "value[?name=='Standard_LRS']"])
    query("webSkuRegions", ["appservice", "list-locations", "--subscription", SUBSCRIPTION,
                            "--sku", "P0V3", "--linux-workers-enabled"])
    for region in REGIONS:
        query(f"{region}/model", ["rest", "--method", "get", "--url",
            f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
            f"Microsoft.CognitiveServices/locations/{region}/models?api-version=2025-06-01",
            "--query", "value[?model.name=='gpt-4.1-mini' && model.version=='2025-04-14'].model"])
        query(f"{region}/modelQuota", ["cognitiveservices", "usage", "list",
            "--subscription", SUBSCRIPTION, "--location", region,
            "--query", "[?name.value=='OpenAI.GlobalStandard.gpt4.1-mini']"])
        query(f"{region}/webUsage", ["rest", "--method", "get", "--url",
            f"https://management.azure.com/subscriptions/{SUBSCRIPTION}/providers/"
            f"Microsoft.Web/locations/{region}/usages?api-version=2024-11-01"])
    print(f"Saved metadata only: {output}")
    failures = [key for key, value in evidence["observations"].items() if value["exitCode"] != 0]
    if failures:
        raise RuntimeError(f"Readiness collection failed for: {', '.join(failures)}; inspect recorded errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    collect(parser.parse_args().repository)
