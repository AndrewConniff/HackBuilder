"""Read-only, target-checked Entra discovery; never logs or persists bearer tokens."""

import base64
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "efd64343-6ef4-4926-951f-d3229f38bd76"
TENANT = "16b3c013-d300-468d-ac64-7eda0820b6d3"
FILTER = (
    "startswith(displayName,'hospitality') or startswith(displayName,'hotel') "
    "or startswith(displayName,'Margie') or startswith(displayName,'feedback')"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def query(tool: str, args: list[str], secret: bool = False) -> dict:
    started = now()
    result = subprocess.run(
        [shutil.which(tool) or tool, *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120, cwd=ROOT,
    )
    record = {
        "startedAtUtc": started, "completedAtUtc": now(),
        "command": [tool, *args], "exitCode": result.returncode,
    }
    if secret:
        if result.returncode:
            record["error"] = "Token query failed; raw token output and stderr intentionally withheld."
            return record
        token = json.loads(result.stdout)["token"]
        segment = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
        record["identityClaims"] = {key: claims.get(key) for key in ("tid", "oid", "aud", "exp")}
        record["note"] = "Decoded identity alignment only, not signature validation or API token acceptance."
    elif result.returncode:
        record["error"] = result.stderr.strip()
    else:
        record["result"] = json.loads(result.stdout)
    return record


def main() -> None:
    records = []
    account = query("az", ["account", "show", "--query",
                          "{subscription:id,name:name,tenant:tenantId,user:user,state:state}", "-o", "json"])
    records.append(account)
    context = account.get("result", {})
    if context.get("subscription") != SUBSCRIPTION or context.get("tenant") != TENANT:
        raise SystemExit("Target mismatch or unavailable; no discovery executed.")
    records.append(query("az", ["ad", "signed-in-user", "show", "--query",
                                "{id:id,userPrincipalName:userPrincipalName}", "-o", "json"]))
    records.append(query("azd", ["auth", "token", "--tenant-id", TENANT, "--scope",
                                 "https://management.azure.com/.default", "--no-prompt", "-o", "json"], secret=True))
    for kind in ("app", "sp"):
        projection = (
            "[].{id:id,appId:appId,displayName:displayName,identifierUris:identifierUris,"
            "signInAudience:signInAudience,api:api,appRoles:appRoles}"
            if kind == "app" else
            "[].{id:id,appId:appId,displayName:displayName,appOwnerOrganizationId:appOwnerOrganizationId,"
            "accountEnabled:accountEnabled,servicePrincipalNames:servicePrincipalNames,"
            "oauth2PermissionScopes:oauth2PermissionScopes,appRoles:appRoles}"
        )
        records.append(query("az", ["ad", kind, "list", "--filter", FILTER, "--query", projection, "-o", "json"]))
    records.append(query("az", ["group", "exists", "--name", "rg-hospitality-feedback",
                                "--subscription", SUBSCRIPTION, "-o", "json"]))
    evidence = {
        "checkedAtUtc": now(), "status": "decision_required", "scope": "read-only",
        "queries": records,
        "limitations": [
            "Prefix-filtered discovery only; not proof that no suitable registration exists elsewhere in the tenant.",
            "Display names are not evidence of intended reuse or consent.",
            "No suitable scenario-intended registration established; no consent or API token readiness asserted.",
            "No API token requested, no Entra/RBAC/resource writes, no refreshed model capacity claim.",
        ],
    }
    path = ROOT / "evidence" / "auth-discovery-2026-10-22.json"
    path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "evidence": str(path), "status": evidence["status"],
        "queryExitCodes": [row["exitCode"] for row in records],
        "applicationCount": len(records[3].get("result", [])),
        "servicePrincipalCount": len(records[4].get("result", [])),
        "resourceGroupExists": records[5].get("result"),
        "deployerObjectId": records[1].get("result", {}).get("id"),
        "azdIdentityClaims": records[2].get("identityClaims"),
    }, indent=2))


if __name__ == "__main__":
    main()
