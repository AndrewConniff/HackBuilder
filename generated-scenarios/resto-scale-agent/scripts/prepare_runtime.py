"""Generate runtime deployment parameters locally; never query or deploy Azure."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID


def parameters(outputs: dict, versions: dict, environment: str, location: str, image: str,
               endpoint: str, tenant: str, identity: dict, subscription: str) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,31}", environment):
        raise ValueError("Use a distinct 3-32 character lowercase environment.")
    UUID(tenant)
    UUID(subscription)
    if not location:
        raise ValueError("Confirmed location is required.")
    from setup_identity import consume
    staff = consume(identity, tenant, subscription, environment, location)

    def value(name: str):
        result = outputs[name]["value"]
        if result is None or result == "" or result == []:
            raise ValueError(f"Infrastructure output {name} is empty.")
        return result

    if value("AZURE_RESOURCE_GROUP") != f"rg-{environment}":
        raise ValueError("Infrastructure resource group does not match the confirmed environment.")
    for name, expected in (
        ("AZURE_LOCATION", location), ("AZURE_ENV_NAME", environment),
        ("AZURE_SUBSCRIPTION_ID", subscription), ("AZURE_TENANT_ID", tenant),
    ):
        if value(name).lower() != expected.lower():
            raise ValueError(f"Infrastructure {name} differs from the exact confirmed deployment target.")
    resource_id = value("AZURE_CONTAINER_APPS_ENVIRONMENT_ID")
    scope = f"/subscriptions/{subscription}/resourceGroups/rg-{environment}/".lower()
    if not resource_id.lower().startswith(scope):
        raise ValueError("Container environment belongs to a different resource group.")
    if not re.fullmatch(
        re.escape(value("AZURE_CONTAINER_REGISTRY_ENDPOINT")) + r"/[a-z0-9._/-]+@sha256:[a-f0-9]{64}", image
    ):
        raise ValueError("Use an immutable image digest in this scenario's registry.")
    uri = urlparse(endpoint)
    account = value("FOUNDRY_ACCOUNT_NAME")
    project = value("FOUNDRY_PROJECT_NAME").rsplit("/", 1)[-1]
    if (uri.scheme != "https" or uri.hostname != f"{account}.services.ai.azure.com"
            or uri.path.rstrip("/") != f"/api/projects/{project}"
            or uri.query or uri.fragment or uri.username or uri.password or uri.port not in (None, 443)):
        raise ValueError("Supply the discovered HTTPS endpoint for this exact Foundry project.")
    if versions.get("Initialized") is not True:
        raise ValueError("Initializer did not report successful catalog and agent installation.")
    agents = versions["AgentVersions"]
    if set(agents) != {"guest", "staff", "kitchen"} or any(
        not isinstance(version, str) or not version.strip() for version in agents.values()
    ):
        raise ValueError("All three installed immutable agent versions are required.")
    identities = value("RUNTIME_IDENTITIES")
    if [identity["role"] for identity in identities] != ["web", "chat", "worker", "scaler"]:
        raise ValueError("Unexpected runtime identity ordering.")
    for name in ("RESOURCE_SUFFIX", "AZURE_CONTAINER_APPS_ENVIRONMENT_DOMAIN", "COSMOS_ENDPOINT",
                 "KEY_VAULT_URI", "SERVICE_BUS_NAMESPACE", "APPLICATIONINSIGHTS_CONNECTION_STRING"):
        value(name)
    for identity in identities:
        UUID(identity["clientId"])
        if not identity["resourceId"].lower().startswith(scope):
            raise ValueError("Runtime identity belongs to a different deployment target.")
    values = {
        "environment": environment, "location": location, "infrastructure": outputs,
        "image": image, "foundryProjectEndpoint": endpoint, "agentVersions": agents,
        **staff,
    }
    return {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {name: {"value": item} for name, item in values.items()},
    }


def main() -> None:
    from setup_staff import private_directory, private_write

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("outputs", "versions", "environment", "location", "image", "endpoint", "tenant",
                 "subscription", "out"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--identity-receipt", required=True, help="Non-secret installed identity output; never user-entered IDs.")
    args = parser.parse_args()
    result = parameters(
        json.loads(Path(args.outputs).read_text(encoding="utf-8")),
        json.loads(Path(args.versions).read_text(encoding="utf-8")),
        args.environment, args.location, args.image, args.endpoint, args.tenant,
        json.loads(Path(args.identity_receipt).read_text(encoding="utf-8")), args.subscription,
    )
    output = Path(args.out)
    private_directory(output.parent)
    private_write(output, result)
    print("Private local runtime parameters written. No secrets printed; no Azure operations performed.")


if __name__ == "__main__":
    main()
