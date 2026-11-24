"""Check compiled ARM resource types and bounded configurations against FBC policy."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

POLICY_PATH = (
    Path(__file__).resolve().parents[1] / ".github" / "skills" / "hack-builder-workflow"
    / "assets" / "allowed-azure-resources.json"
)
REFERENCE = re.compile(r"\[(parameters|variables)\('([^']+)'\)\]", re.IGNORECASE)
GLOBAL_TYPES = {
    "microsoft.communication/communicationservices",
    "microsoft.communication/emailservices",
    "microsoft.communication/emailservices/domains",
}
UNLOCATED_TYPES = {"microsoft.authorization/roleassignments", "microsoft.eventgrid/eventsubscriptions"}


def load_policy() -> dict:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(policy, dict) or policy.get("schemaVersion") != 1:
        raise ValueError("Missing or unsupported repository resource policy.")
    if not isinstance(policy.get("resourceTypes"), dict) or not policy["resourceTypes"]:
        raise ValueError("Repository resource policy must explicitly list allowed resource types.")
    return policy


def policy_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in (POLICY_PATH, POLICY_PATH.parent.parent / "references" / "allowed-azure-resources.md"):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def values(value: object, template: dict, seen: tuple[str, ...] = ()) -> list:
    if not isinstance(value, str) or not value.startswith("["):
        return [value]
    match = REFERENCE.fullmatch(value)
    if not match:
        raise ValueError(f"Cannot prove constrained ARM expression is policy-safe: {value}")
    kind, name = match.groups()
    key = f"{kind.lower()}:{name}"
    if key in seen:
        raise ValueError(f"Circular policy-constrained ARM reference: {name}")
    if kind.lower() == "variables":
        if name not in template.get("variables", {}):
            raise ValueError(f"Missing constrained ARM variable: {name}")
        return values(template["variables"][name], template, (*seen, key))
    parameter = template.get("parameters", {}).get(name)
    if not isinstance(parameter, dict) or not parameter.get("allowedValues"):
        raise ValueError(f"Constrained parameter {name} needs bounded allowedValues, not just a default.")
    result = []
    for option in parameter["allowedValues"]:
        result.extend(values(option, template, (*seen, key)))
    if "defaultValue" in parameter and parameter["defaultValue"] not in parameter["allowedValues"]:
        raise ValueError(f"Constrained parameter {name} has a default outside allowedValues.")
    return result


def field_values(resource: object, path: str, template: dict, optional: bool = False) -> list:
    current = [resource]
    for part in path.split("."):
        following = []
        for item in current:
            for candidate in values(item, template):
                if part == "*" and isinstance(candidate, list) and candidate:
                    following.extend(candidate)
                elif isinstance(candidate, dict) and part in candidate:
                    following.append(candidate[part])
                elif not optional:
                    raise ValueError(f"Missing required policy field: {path}")
        current = following
    return current


def check_fields(resource: dict, template: dict, rules: dict) -> None:
    for path, rule in rules.items():
        for raw in field_values(resource, path, template, rule.get("optional", False)):
            if rule.get("nonempty"):
                if isinstance(raw, str) and re.fullmatch(r"\[resourceId\(.+\)\]", raw, re.IGNORECASE):
                    continue
            for value in values(raw, template):
                if rule.get("nonempty") and (not isinstance(value, str) or not value.strip()):
                    raise ValueError(f"{path} must reference a nonempty workspace.")
                if "in" in rule and not any(type(value) is type(item) and value == item for item in rule["in"]):
                    raise ValueError(f"{path}={value!r} is outside allowed values {rule['in']}.")
                if "length" in rule and (not isinstance(value, list) or len(value) != rule["length"]):
                    raise ValueError(f"{path} must contain exactly {rule['length']} entry.")
                if "min" in rule or "max" in rule:
                    if type(value) not in (int, float) or not math.isfinite(value):
                        raise ValueError(f"{path} must be a bounded number.")
                    if value < rule.get("min", value) or value > rule.get("max", value):
                        raise ValueError(f"{path}={value} exceeds its allowed policy bounds.")


def validate_template(template: dict) -> None:
    if "resources" not in template:
        raise ValueError("A compiled ARM template must declare resources, even when the array is empty.")
    policy = load_policy()
    allowed = {name.lower(): rules for name, rules in policy["resourceTypes"].items()}
    storage_count = 0
    workload_region: str | None = None

    def inspect(document: dict, parent_type: str = "") -> None:
        nonlocal storage_count, workload_region
        resources = document.get("resources", [])
        if isinstance(resources, dict):
            resources = list(resources.values())
        if not isinstance(resources, list):
            raise ValueError("Policy checking requires an ARM resource array or symbolic-name object.")
        for resource in resources:
            if not isinstance(resource, dict) or not isinstance(resource.get("type"), str):
                raise ValueError("Each policy-checked ARM resource must declare its type.")
            if "copy" in resource:
                raise ValueError("Expand resource copy loops before policy validation; scale cannot be assumed safe.")
            type_options = values(resource["type"], document)
            if len(type_options) != 1 or not isinstance(type_options[0], str):
                raise ValueError("ARM resource types must resolve to one explicit allowed type.")
            resource_type = type_options[0]
            if parent_type and "." not in resource_type.split("/")[0]:
                resource_type = f"{parent_type}/{resource_type}"
            resource_type = resource_type.lower()
            if resource_type == "microsoft.resources/deployments":
                properties = resource.get("properties", {})
                if (
                    not isinstance(properties, dict) or not isinstance(properties.get("template"), dict)
                    or any(key in properties for key in ("templateLink", "parametersLink"))
                    or any(key in resource for key in ("scope", "subscriptionId", "resourceGroup"))
                ):
                    raise ValueError("Policy checking requires same-scope inline deployments, not external templates.")
                inspect(properties["template"])
                continue
            if resource_type not in allowed:
                raise ValueError(f"Resource type is not allowed by repository policy: {resource_type}")
            try:
                check_fields(resource, document, allowed[resource_type])
                regional = resource_type.count("/") == 1 and resource_type not in UNLOCATED_TYPES
                locations = field_values(resource, "location", document, optional=not regional)
                for location in locations:
                    if resource_type in GLOBAL_TYPES and location == "global":
                        continue
                    if not policy["approvedRegions"]:
                        raise ValueError("Approved regions are unresolved; an explicit repository policy edit is required.")
                    regions = values(location, document)
                    if len(regions) != 1 or regions[0] not in policy["approvedRegions"]:
                        raise ValueError("Resource location is outside the approved region list.")
                    if workload_region is not None and workload_region != regions[0]:
                        raise ValueError("Every regional resource must use one common approved region.")
                    workload_region = regions[0]
                if resource_type == "microsoft.storage/storageaccounts":
                    storage_count += 1
                    if storage_count > 1:
                        raise ValueError("Blob and Queues must share one StorageV2 account; a second account is denied.")
                if resource_type == "microsoft.documentdb/databaseaccounts":
                    capabilities = field_values(resource, "properties.capabilities", document, optional=True)
                    serverless = capabilities == [[{"name": "EnableServerless"}]]
                    if not serverless:
                        cap = policy["cosmosAutoscaleMaxThroughput"]
                        if cap is None:
                            raise ValueError("Cosmos provisioned autoscale cap is unresolved in repository policy.")
                        if capabilities not in ([], [[]]):
                            raise ValueError("Only NoSQL serverless or provisioned autoscale is allowed.")
                        check_fields(resource, document, {
                            "properties.capacity.totalThroughputLimit": {"min": 1, "max": cap},
                        })
                    for regions in field_values(resource, "properties.locations", document):
                        if any(region.get("locationName") != workload_region for region in regions):
                            raise ValueError("The Cosmos data region must match the common approved region.")
                if resource_type in {
                    "microsoft.documentdb/databaseaccounts/sqldatabases",
                    "microsoft.documentdb/databaseaccounts/sqldatabases/containers",
                }:
                    for options in field_values(resource, "properties.options", document, optional=True):
                        if options.get("throughput") is not None:
                            raise ValueError("Manual provisioned Cosmos throughput is not allowed.")
                        if "autoscaleSettings" in options:
                            cap = policy["cosmosAutoscaleMaxThroughput"]
                            if cap is None:
                                raise ValueError("Cosmos provisioned autoscale cap is unresolved in repository policy.")
                            check_fields(options, document, {"autoscaleSettings.maxThroughput": {"min": 1, "max": cap}})
                if resource_type == "microsoft.cognitiveservices/accounts/deployments":
                    names = field_values(resource, "properties.model.name", document)
                    versions = field_values(resource, "properties.model.version", document)
                    for name, version in itertools.product(
                        *(values(item, document) for item in (names[0], versions[0])),
                    ):
                        if name not in policy["models"] or version not in policy["models"][name]:
                            raise ValueError(f"Model name/version is not explicitly approved: {name}/{version}")
                        rate = policy["modelCapacityTpm"].get(f"{name}/{version}")
                        if type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0:
                            raise ValueError(f"Verified tokens per capacity unit are unresolved: {name}/{version}")
                        capacity = field_values(resource, "sku.capacity", document)
                        if any(units * rate > policy["maxModelTpm"] for units in values(capacity[0], document)):
                            raise ValueError("Model deployment TPM exceeds its repository policy bounds.")
                if resource_type in {"microsoft.app/containerapps", "microsoft.app/jobs"}:
                    for path in ("properties.template.containers", "properties.template.initContainers"):
                        for raw in field_values(resource, path, document, optional="initContainers" in path):
                            for containers in values(raw, document):
                                for container in containers:
                                    check_fields(container, document, {
                                        "resources.cpu": {"in": [0.25, 0.5]},
                                        "resources.memory": {"in": ["0.5Gi", "1Gi"]},
                                    })
                                    if "gpu" in container["resources"]:
                                        raise ValueError("Container GPUs are not allowed.")
                                    cpus = field_values(container, "resources.cpu", document)
                                    memory = field_values(container, "resources.memory", document)
                                    for cpu, size in itertools.product(
                                        values(cpus[0], document), values(memory[0], document),
                                    ):
                                        if (cpu, size) not in {(0.25, "0.5Gi"), (0.5, "1Gi")}:
                                            raise ValueError("Container CPU/memory must match an allowed configuration.")
                if resource_type == "microsoft.app/jobs":
                    triggers = field_values(resource, "properties.configuration.triggerType", document)
                    for trigger in values(triggers[0], document):
                        if trigger not in {"Manual", "Schedule", "Event"}:
                            raise ValueError("Container job trigger type must be explicit.")
                        config = f"properties.configuration.{trigger.lower()}TriggerConfig"
                        check_fields(resource, document, {f"{config}.parallelism": {"min": 1, "max": 3}})
                        if trigger == "Event":
                            check_fields(resource, document, {
                                f"{config}.scale.maxExecutions": {"min": 0, "max": 3},
                            })
                            parallelism = field_values(resource, f"{config}.parallelism", document)
                            executions = field_values(resource, f"{config}.scale.maxExecutions", document)
                            if any(
                                workers * runs > 3 for workers, runs in itertools.product(
                                    values(parallelism[0], document), values(executions[0], document),
                                )
                            ):
                                raise ValueError("Container job concurrent replica count must not exceed 3.")
            except ValueError as error:
                raise ValueError(f"{resource_type}: {error}") from error
            inspect({**document, "resources": resource.get("resources", [])}, resource_type)

    inspect(template)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Compiled ARM JSON, including inline modules.")
    args = parser.parse_args()
    try:
        template = json.loads(args.template.read_text(encoding="utf-8-sig"))
        if not isinstance(template, dict):
            raise ValueError("The compiled ARM template must be an object.")
        validate_template(template)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Resource policy blocked: {error}\n")
    print("Resource policy: passed for the checked ARM types, SKUs and configuration bounds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
