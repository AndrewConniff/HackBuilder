"""Collect approved management eligibility and full exact ARM preview without provisioning."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = Path.cwd()
EVIDENCE = ROOT / "local-evidence" / "management-repair-20261024"
SUB = "efd64343-6ef4-4926-951f-d3229f38bd76"
BASE = f"https://management.azure.com/subscriptions/{SUB}"
MANAGEMENT_VM_SIZE = "Standard_D2als_v7"


def save(name: str, value: object) -> None:
    (EVIDENCE / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(name: str, arguments: list[str], timeout: int = 600):
    start = datetime.now(timezone.utc).isoformat()
    result = subprocess.run([shutil.which(arguments[0]), *arguments[1:]], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=timeout, check=False)
    save(name + ".command", {"command": arguments, "startedAtUtc": start,
                             "finishedAtUtc": datetime.now(timezone.utc).isoformat(),
                             "exitCode": result.returncode, "stderr": result.stderr})
    if result.returncode:
        save(name, {"rawOutput": result.stdout, "error": result.stderr})
        raise RuntimeError(f"{name}: {result.stderr[-2500:]}")
    value = json.loads(result.stdout) if result.stdout.strip() else {}
    save(name, value)
    print(f"{name}: exit 0", flush=True)
    return value


def az(name: str, *arguments: str):
    return run(name, ["az", *arguments, "--subscription", SUB, "--output", "json"])


def main() -> None:
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-skus", action="store_true")
    parser.add_argument("--eligibility-only", action="store_true")
    parser.add_argument("--evidence-directory", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    EVIDENCE = args.evidence_directory.resolve()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(REPO / "scripts"))
    from azure_context import discover
    project = json.loads((REPO / ".abcbuilder-portal/projects/equip-ai.json").read_text(encoding="utf-8-sig"))
    observed = discover(REPO, ROOT, project, overrides={"region": "centralus"})
    approval = json.loads(
        (ROOT / "local-evidence" / "management-repair-20261024" / "user-approval.json").read_text())
    if observed["scope"] != approval["scope"] or observed["conflicts"]:
        raise ValueError("Actual CLI target differs from approved target.")
    observed["legacyRegionReconciliation"] = (
        "Legacy project retained East US; explicit current user approval and existing scenario azd "
        "environment select Central US. Per-call override only; no shared Azure defaults changed.")
    save("current-identity", observed)
    # Reuse this invocation's expensive SKU enumeration after a local parser repair.
    skus = (json.loads((EVIDENCE / "compute-skus.json").read_text())
            if args.reuse_skus else
            az("compute-skus", "vm", "list-skus", "--location", "centralus",
               "--size", MANAGEMENT_VM_SIZE, "--all"))
    sku = next(x for x in skus if x["name"] == MANAGEMENT_VM_SIZE and x["resourceType"] == "virtualMachines")
    usage = az("compute-usage", "vm", "list-usage", "--location", "centralus")
    quotas = []
    for name, required in ((sku["family"], 2), ("cores", 2), ("virtualMachines", 1)):
        item = next(x for x in usage if x["name"]["value"].casefold() == name.casefold())
        current, limit = int(item["currentValue"]), int(item["limit"])
        quotas.append({"name": name, "currentValue": current, "limit": limit,
                       "required": required, "passed": current + required <= limit})
    capabilities = {x["name"]: x["value"] for x in sku["capabilities"]}
    image = az("ubuntu-image", "vm", "image", "show", "--location", "centralus", "--urn",
               "Canonical:ubuntu-24_04-lts:server:latest")
    provider = az("compute-provider", "provider", "show", "--namespace", "Microsoft.Compute")
    network = az("management-network-usage", "network", "list-usages", "--location", "centralus")
    relevant = []
    for item in network:
        if item["name"]["value"] in {"NatGateways", "PublicIPAddresses", "NetworkSecurityGroups",
                                      "NetworkInterfaces", "VirtualNetworks", "StandardSkuPublicIpAddresses"}:
            relevant.append({**item, "required": 1,
                             "passed": int(item["currentValue"]) + 1 <= int(item["limit"])})
    summary = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "scope": observed["scope"],
        "sku": sku["name"], "restrictions": sku["restrictions"], "capabilities": capabilities,
        "quotas": quotas, "image": image, "computeProvider": provider["registrationState"],
        "networkQuotas": relevant, "allocationReserved": False,
    }
    image_features = {item["name"]: item["value"] for item in image.get("features", [])}
    summary["diskControllerCompatible"] = bool(
        set(capabilities.get("DiskControllerTypes", "").replace(" ", "").split(","))
        & set(image_features.get("DiskControllerTypes", "").replace(" ", "").split(","))
        - {""}
    )
    summary["passed"] = (not sku["restrictions"] and all(x["passed"] for x in quotas)
                         and provider["registrationState"] == "Registered"
                         and capabilities.get("HyperVGenerations", "").find("V2") >= 0
                         and capabilities.get("TrustedLaunchDisabled", "False") == "False"
                         and image.get("hyperVGeneration") == "V2"
                         and image_features.get("SecurityType") == "TrustedLaunchSupported"
                         and summary["diskControllerCompatible"]
                         and all(x["passed"] for x in relevant))
    save("management-readiness", summary)
    if not summary["passed"]:
        raise ValueError("Management eligibility failed; see management-readiness.json")
    if args.eligibility_only:
        print("Management eligibility passed; exact ARM what-if and provisioning not executed.", flush=True)
        return
    # Public key is local installation material, not a cloud change or public access exception.
    key = ROOT / ".installation/equip-ai/management-ssh"
    if not key.with_suffix(".pub").exists():
        result = subprocess.run([shutil.which("ssh-keygen"), "-t", "ed25519", "-f", str(key),
                                 "-N", "", "-C", "equip-ai-management"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
    values = {}
    for line in (ROOT / ".azure/equip-ai/.env").read_text().splitlines():
        name, sep, value = line.partition("=")
        if sep:
            values[name] = value.strip().strip('"')
    parameters = json.loads((ROOT / "infra/main.parameters.json").read_text())
    values["EQUIP_ENABLE_MANAGEMENT"] = True
    values["EQUIP_MANAGEMENT_PUBLIC_KEY"] = key.with_suffix(".pub").read_text().strip()
    for name, item in parameters["parameters"].items():
        item["value"] = values[item["value"][2:-1]]
    save("exact-parameters", parameters)
    # Preserve every module and output; unlike the earlier partial preview this is the full source.
    template = run("full-bicep", ["az", "bicep", "build", "--file", str(ROOT / "infra/main.bicep"), "--stdout"])
    exists = az("target-group-exists", "group", "exists", "--name", "rg-equip-ai")
    if exists:
        result = az("full-whatif", "deployment", "group", "what-if", "--resource-group", "rg-equip-ai",
                    "--template-file", str(EVIDENCE / "full-bicep.json"),
                    "--parameters", "@" + str(EVIDENCE / "exact-parameters.json"), "--no-pretty-print")
    else:
        wrapper = {
            "$schema": "https://schema.management.azure.com/schemas/2018-05-01/subscriptionDeploymentTemplate.json#",
            "contentVersion": "1.0.0.0", "resources": [
                {"type": "Microsoft.Resources/resourceGroups", "apiVersion": "2024-03-01",
                 "name": "rg-equip-ai", "location": "centralus"},
                {"type": "Microsoft.Resources/deployments", "apiVersion": "2022-09-01",
                 "name": "equip-ai-full-reviewed", "resourceGroup": "rg-equip-ai",
                 "dependsOn": ["rg-equip-ai"], "properties": {
                     "mode": "Incremental", "expressionEvaluationOptions": {"scope": "inner"},
                     "template": template, "parameters": parameters["parameters"]}},
            ],
        }
        save("full-subscription-preview", wrapper)
        result = az("full-whatif", "deployment", "sub", "what-if", "--location", "centralus",
                    "--template-file", str(EVIDENCE / "full-subscription-preview.json"), "--no-pretty-print")
    print(json.dumps({"status": result.get("status"), "error": result.get("error"),
                      "changes": len(result.get("changes", []))}, indent=2))


if __name__ == "__main__":
    main()
