"""Collect authorized read-only Azure observations without allocating or changing resources."""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def has_exact_model_quota(data: object) -> bool:
    return (
        isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict)
        and data[0].get("name") == "OpenAI.GlobalStandard.gpt4.1"
        and all(isinstance(data[0].get(key), (int, float)) and not isinstance(data[0][key], bool)
                for key in ("used", "limit"))
    )


def azure_query(root: Path, arguments: list[str], environment: dict[str, str]) -> str:
    executable = shutil.which("az", path=environment.get("PATH", ""))
    if executable is None:
        raise ValueError("Azure CLI is unavailable in the configured execution environment.")
    invocation = [executable]
    if executable.lower().endswith(".cmd"):
        runtime = Path(executable).parent.parent / "python.exe"
        if not runtime.is_file():
            raise ValueError("The installed Azure CLI Python runtime could not be located.")
        # Bypass cmd.exe interpretation of parentheses and operators in JMESPath arguments.
        invocation = [str(runtime), "-m", "azure.cli"]
    try:
        result = subprocess.run(
            [*invocation, *arguments], cwd=root, env=environment, capture_output=True,
            text=True, encoding="utf-8", timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Read-only Azure query could not complete: {error}") from error
    if result.returncode:
        raise ValueError(f"Read-only Azure query failed: {(result.stderr or result.stdout)[-1200:]}")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builder-root", type=Path, required=True)
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--regions", nargs="+", choices=["eastus2", "swedencentral"], required=True)
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(args.builder_root / "scripts"))
    from azure_context import execution_environment, identity

    identity_result = identity(args.builder_root)
    scope = identity_result["scope"]
    if scope["subscriptionId"] != args.subscription or scope["tenantId"] != args.tenant:
        raise ValueError("Current Azure target differs from the authorized target; no readiness queries executed.")
    output = Path(__file__).resolve().parents[1] / "azure-readiness.json"
    observations = []
    if args.retry_failed:
        previous = json.loads(output.read_text(encoding="utf-8"))
        if previous["scope"] != scope:
            raise ValueError("Saved observations do not match the currently authorized Azure identity.")
        observations = previous["observations"]
    environment = execution_environment(args.builder_root)

    def collect(name: str, arguments: list[str], region: str | None = None) -> None:
        existing = next((item for item in observations if item["name"] == name and item["region"] == region), None)
        if args.retry_failed and existing and existing["queryStatus"] == "succeeded" and (
            name != "modelUsage" or has_exact_model_quota(existing.get("data"))
        ):
            return
        try:
            data = json.loads(azure_query(args.builder_root, [
                *arguments, "--subscription", args.subscription, "--output", "json"
            ], environment))
            if name == "modelUsage" and not has_exact_model_quota(data):
                raise ValueError("No exact GlobalStandard gpt-4.1 quota returned; eligibility remains unknown.")
            result = {"name": name, "region": region, "queryStatus": "succeeded", "data": data}
        except (ValueError, json.JSONDecodeError) as error:
            print(f"Read failed: {name} / {region}: {error}", file=sys.stderr)
            result = {"name": name, "region": region, "queryStatus": "failed", "error": str(error)}
        result["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
        if existing:
            result["previousAttempts"] = [
                *existing.get("previousAttempts", []),
                {key: value for key, value in existing.items() if key != "previousAttempts"},
            ]
            observations[observations.index(existing)] = result
        else:
            observations.append(result)
        print(f"{name} / {region or 'subscription'}: {result['queryStatus']}", flush=True)

    collect("providers", ["provider", "list", "--query",
            "[?namespace=='Microsoft.CognitiveServices' || namespace=='Microsoft.Web' || "
            "namespace=='Microsoft.Storage' || namespace=='Microsoft.Compute' || namespace=='Microsoft.Network' || "
            "namespace=='Microsoft.OperationalInsights' || namespace=='Microsoft.Insights' || "
            "namespace=='microsoft.insights' || "
            "namespace=='Microsoft.Authorization'].{namespace:namespace,state:registrationState}"])
    base = f"https://management.azure.com/subscriptions/{args.subscription}"
    collect("effectivePermissions", ["rest", "--method", "get", "--url",
            base + "/providers/Microsoft.Authorization/permissions?api-version=2022-04-01"])
    collect("policies", ["policy", "assignment", "list", "--scope", f"/subscriptions/{args.subscription}",
            "--disable-scope-strict-match", "--query",
            "[].{id:id,name:displayName,scope:scope,enforcementMode:enforcementMode,definition:policyDefinitionId}"])
    collect("foundryRoles", ["role", "definition", "list", "--query",
            "[?contains(roleName,'Foundry') || contains(roleName,'Azure AI')]."
            "{name:roleName,id:name,permissions:permissions}"])
    for region in args.regions:
        collect("vmSku", ["vm", "list-skus", "--location", region, "--size", "Standard_D2s_v5",
                "--resource-type", "virtualMachines", "--all", "--query",
                "[?name=='Standard_D2s_v5' && resourceType=='virtualMachines']."
                "{name:name,family:family,restrictions:restrictions,"
                "locations:locations,locationInfo:locationInfo}"], region)
        collect("computeUsage", ["vm", "list-usage", "--location", region, "--query",
                "[?name.value=='cores' || name.value=='standardDSv5Family' || name.value=='virtualMachines']."
                "{name:name.value,used:currentValue,limit:limit}"], region)
        collect("models", ["cognitiveservices", "model", "list", "--location", region, "--query",
                "[?model.name=='gpt-4.1' && model.version=='2025-04-14']"], region)
        collect("modelUsage", ["cognitiveservices", "usage", "list", "--location", region, "--query",
                "[?name.value=='OpenAI.GlobalStandard.gpt4.1']."
                "{name:name.value,used:currentValue,limit:limit}"], region)
        collect("webUsage", ["rest", "--method", "get", "--url",
                base + f"/providers/Microsoft.Web/locations/{region}/usages?api-version=2025-03-01"], region)
    output.write_text(json.dumps({
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "scope": scope, "authentication": identity_result["authentication"],
        "observations": observations,
        "limitations": [
            "Successful query is not proof of whole-design eligibility or runtime access.",
            "No resources allocated, providers registered, grants made or defaults changed.",
            "Role definitions/permissions do not prove future private data-plane access.",
            "No Bicep what-if or private management acceptance has been performed."
        ]
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Saved sanitized observations: {output}", flush=True)
    return 1 if any(item["queryStatus"] == "failed" for item in observations) else 0


if __name__ == "__main__":
    raise SystemExit(main())
