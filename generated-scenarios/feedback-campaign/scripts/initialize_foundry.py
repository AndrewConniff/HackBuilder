"""Initialize a real versioned Foundry prompt agent and initial durable rules after authorized deployment."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from cloud_io import ROOT, cli, environment, receipt, request, verify_target


def main() -> None:
    verify_target()
    env = environment()
    endpoint = env["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
    instructions = (ROOT / "src/FeedbackCampaign.Web/Policy/agent-instructions.txt").read_text(encoding="utf-8")
    digest = hashlib.sha256(instructions.encode()).hexdigest()
    url = endpoint + "/agents/campaign-listener?api-version=v1"
    existing = request("GET", url, "https://ai.azure.com", missing_ok=True)
    definition = {"kind": "prompt", "model": env["FOUNDRY_MODEL_DEPLOYMENT"], "instructions": instructions}
    # Agents GET returns the latest version; unchanged definition is reused.
    latest = (existing or {}).get("versions", {}).get("latest", existing or {})
    if latest.get("definition") != definition:
        created = request("POST", endpoint + "/agents/campaign-listener/versions?api-version=v1", "https://ai.azure.com",
                          {"definition": definition})
        latest = created.get("versions", {}).get("latest", created)
    if not latest.get("id") or not latest.get("version"):
        raise RuntimeError("Foundry did not return a real agent ID/version; initialization is not complete.")

    # Storage Table insert-if-absent; never overwrite a human-promoted active pointer.
    base = env["TABLE_ENDPOINT"].rstrip("/") + "/campaignstate"
    headers = {"x-ms-version": "2019-02-02", "DataServiceVersion": "3.0", "Accept": "application/json;odata=nometadata"}
    import json
    rules = {"version": "v1", "positiveThreshold": .8, "negativeThreshold": .89, "productRouting": False,
             "productNegativeThreshold": .8, "author": "installation",
             "reason": "Original intake rule; illustrative 80% negative is not active."}
    for partition, key, value in [
        ("rules", "v1", rules),
        ("config", "active", {"version": "v1", "promotedBy": "installation", "reason": "Original rules"}),
    ]:
        entity = request("GET", f"{base}(PartitionKey='{partition}',RowKey='{key}')",
                         "https://storage.azure.com/", headers=headers, missing_ok=True)
        if entity is None:
            request("POST", base, "https://storage.azure.com/",
                    {"PartitionKey": partition, "RowKey": key, "Payload": json.dumps(value)}, headers)
    receipt("agent-installation.json", {"checkedAtUtc": datetime.now(timezone.utc).isoformat(),
            "agentId": latest["id"], "version": latest["version"], "name": "campaign-listener",
            "instructionsSha256": digest, "projectEndpoint": endpoint})
    cli("azd", "env", "set", "FOUNDRY_AGENT_VERSION", str(latest["version"]))
    cli("az", "webapp", "config", "appsettings", "set", "--subscription", env["AZURE_SUBSCRIPTION_ID"],
        "--resource-group", env["AZURE_RESOURCE_GROUP"], "--name", env["AZURE_WEBAPP_NAME"],
        "--settings", f"FOUNDRY_AGENT_VERSION={latest['version']}", "--output", "none")
    print("Real Foundry agent and durable initial rules initialized; inference acceptance remains separate.")


if __name__ == "__main__":
    main()
