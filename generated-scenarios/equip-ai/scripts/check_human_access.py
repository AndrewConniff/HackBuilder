"""Check only the approved equip-ai human-access scope; never provision resources."""

from datetime import datetime, timezone
import ipaddress
import json
import re
import urllib.parse
import urllib.request

from install_identity import command, save
from private_runner import GROUP, ROOT, SUBSCRIPTION
from validate_live import values

EVIDENCE = ROOT / "local-evidence" / "resume-20261028"


def rate(service: str, meter: str) -> dict:
    query = (f"serviceName eq '{service}' and armRegionName eq 'centralus' "
             f"and priceType eq 'Consumption' and meterName eq '{meter}'")
    url = "https://prices.azure.com/api/retail/prices?" + urllib.parse.urlencode({"$filter": query})
    with urllib.request.urlopen(url, timeout=90) as response:
        items = json.load(response)["Items"]
    if len(items) != 1 or items[0]["unitOfMeasure"] != "1 Hour":
        raise ValueError(f"Expected one hourly Central US meter: {meter}")
    return items[0]


def main() -> None:
    config = values()
    if config.get("EQUIP_ENABLE_HUMAN_MANAGEMENT") != "true":
        raise ValueError("Human access must be explicitly enabled after the scope/cost approval.")
    if config.get("EQUIP_ENABLE_MANAGEMENT") != "true":
        raise ValueError("Human access requires the existing management host.")
    target = ["--subscription", SUBSCRIPTION, "--resource-group", GROUP]
    network = command(["az", "network", "vnet", "show", *target, "--name", "vnet-equip-equip-ai"])
    candidate = ipaddress.ip_network("10.247.0.192/26")
    if not any(candidate.subnet_of(ipaddress.ip_network(prefix))
               for prefix in network["addressSpace"]["addressPrefixes"]):
        raise ValueError("Bastion subnet must remain inside the approved existing address space.")
    for subnet in network["subnets"]:
        prefixes = [subnet["addressPrefix"]] if subnet.get("addressPrefix") else subnet["addressPrefixes"]
        for prefix in prefixes:
            if candidate.overlaps(ipaddress.ip_network(prefix)) and not (
                subnet["name"] == "AzureBastionSubnet" and candidate == ipaddress.ip_network(prefix)
            ):
                raise ValueError("Bastion subnet overlaps an existing workload subnet.")
    provider = command(["az", "provider", "show", "--subscription", SUBSCRIPTION, "--namespace", "Microsoft.Network"])
    locations = next(item["locations"] for item in provider["resourceTypes"] if item["resourceType"] == "bastionHosts")
    if provider["registrationState"] != "Registered" or "Central US" not in locations:
        raise ValueError("Bastion provider/region readiness failed.")
    meters = [rate("Azure Bastion", "Standard Gateway"), rate("Virtual Network", "Standard Static IP Addresses")]
    incremental = round(sum(item["retailPrice"] for item in meters) * 730, 2)
    if incremental > 216.08:
        raise ValueError("Human-access prices exceed the reviewed incremental illustration; review before allocation.")
    template = json.loads((ROOT / "infra" / "main.parameters.json").read_text())
    for parameter in template["parameters"].values():
        match = re.fullmatch(r"\$\{([A-Z_]+)}", str(parameter["value"]))
        if match:
            parameter["value"] = config[match[1]]
    for name in ("enableManagement", "enableHumanManagement", "restoreFoundry"):
        if template["parameters"][name]["value"] not in ("true", "false"):
            raise ValueError(f"Invalid explicit Boolean value: {name}")
        template["parameters"][name]["value"] = template["parameters"][name]["value"] == "true"
    parameters = EVIDENCE / "human-access.parameters.json"
    save(parameters, template)
    repair_parameters = EVIDENCE / "human-access-repair.parameters.json"
    save(repair_parameters, {
        "$schema": template["$schema"], "contentVersion": "1.0.0.0",
        "parameters": {key: template["parameters"][key] for key in ("environment", "location", "principalId")},
    })
    args = [*target, "--template-file", str(ROOT / "infra" / "human-access-repair.bicep"),
            "--parameters", str(repair_parameters)]
    validation = command(["az", "deployment", "group", "validate", *args], timeout=600)
    save(EVIDENCE / "human-access-repair-arm-validation.json", validation)
    preview = command(["az", "deployment", "group", "what-if", *args, "--no-pretty-print"], timeout=600)
    save(EVIDENCE / "human-access-repair-whatif.json", preview)
    changes = preview.get("changes", [])
    deletions = [item["resourceId"] for item in changes if item["changeType"] == "Delete"]
    allowed = (
        "/microsoft.network/virtualnetworks/vnet-equip-equip-ai/subnets/azurebastionsubnet",
        "/microsoft.network/networksecuritygroups/nsg-equip-management-equip-ai/securityrules/deny-all-inbound",
        "/microsoft.network/networksecuritygroups/nsg-equip-management-equip-ai/securityrules/allow-bastion-rdp",
        "/microsoft.network/publicipaddresses/pip-equip-bastion-equip-ai",
        "/microsoft.network/bastionhosts/bas-equip-equip-ai",
        "/microsoft.devices/iothubs/iot-equip-equipai-kex72v/providers/microsoft.authorization/roleassignments/",
    )
    unexpected = [item["resourceId"] for item in changes if item["changeType"] not in ("Ignore", "NoChange")
                  and not any(fragment in item["resourceId"].lower() for fragment in allowed)]
    summary = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "subscriptionId": SUBSCRIPTION, "resourceGroup": GROUP, "region": "centralus",
        "bastionSubnet": str(candidate), "subnetOverlap": False, "vnetExpansionRequired": False,
        "providerRegistered": True, "regionListed": True,
        "incrementalMonthlyUsd": incremental, "combinedIllustrativeMonthlyUsd": round(249.42 + incremental, 2),
        "meters": meters, "armValidation": validation.get("properties", {}).get("provisioningState"),
        "changes": [{"type": item["changeType"], "resource": item["resourceId"]} for item in changes],
        "deletions": deletions, "unexpectedChanges": unexpected, "provisionedByThisCheck": False,
        "template": "infra/human-access-repair.bicep",
        "coreRedeploymentDeferred": "Full-source preview includes unrelated read-only/default property deltas; deploy only approved additions.",
        "readinessIsNotAllocationGuarantee": True,
    }
    save(EVIDENCE / "human-access-readiness.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "meters"}, indent=2))
    if deletions or unexpected:
        raise ValueError("Unexpected what-if deletion or resource change; do not deploy.")


if __name__ == "__main__":
    main()
