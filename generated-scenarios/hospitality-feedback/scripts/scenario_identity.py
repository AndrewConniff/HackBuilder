"""Install or verify dedicated scenario identities only within canonical deployment consent."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
GRAPH = "https://graph.microsoft.com/v1.0"
DIRECTORY_ACTIONS = ["scenario-owned-applications", "scenario-owned-service-principals"]
TARGETS = {
    "account": "DEPLOYMENT_ACCOUNT",
    "subscriptionId": "AZURE_SUBSCRIPTION_ID",
    "tenantId": "AZURE_TENANT_ID",
    "resourceGroup": "AZURE_RESOURCE_GROUP",
    "environment": "AZURE_ENV_NAME",
    "region": "AZURE_LOCATION",
}


def command(args: list[str], secret: bool = False) -> str:
    """Run a checked CLI operation without changing shared account defaults."""
    executable = shutil.which(args[0])
    if executable is None:
        raise RuntimeError(f"Required executable not found: {args[0]}")
    result = subprocess.run(
        [executable, *args[1:]], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120
    )
    if result.returncode:
        if secret:
            raise RuntimeError(f"{args[0]} token identity check failed; raw output intentionally withheld.")
        raise RuntimeError(f"{args[0]} {args[1]} failed ({result.returncode}): {result.stderr.strip()}")
    return result.stdout


def authorize(state: dict, values: dict[str, str]) -> dict:
    """Reject absent, stale, restricted or mismatched cloud/directory scope before queries."""
    if state.get("projectSlug") != ROOT.name or not state.get("designConfirmed"):
        raise ValueError("Confirmed same-scenario design is required.")
    scope = {field: values.get(variable, "") for field, variable in TARGETS.items()}
    if not all(scope.values()):
        raise ValueError("Resolve exact targets in the portal Azure context card before installation.")
    grants = [
        item["scope"] for item in state.get("authorizations", [])
        if item.get("kind") == "deployment"
        and all(item.get("scope", {}).get(field) == value for field, value in scope.items())
    ]
    if not any(set(DIRECTORY_ACTIONS).issubset(grant.get("directoryActions", [])) for grant in grants):
        raise ValueError("Exact deployment consent must explicitly include dedicated application and SP writes.")
    if state.get("setupBlocker") or any(
        item.get("status") in {"pending", "reviewing"} for item in state.get("decisions", [])
    ):
        raise ValueError("Resolve the current portal blocker/decision before installation.")
    return scope


def graph(method: str, path: str, body: dict | None = None) -> dict:
    """Call the documented Graph v1.0 surface; request files contain no credentials."""
    args = ["az", "rest", "--method", method, "--url", f"{GRAPH}/{path}", "--output", "json"]
    if body is not None:
        file = ROOT / ".local" / "identity-request.json"
        file.parent.mkdir(exist_ok=True)
        file.write_text(json.dumps(body), encoding="utf-8")
        args.extend(["--headers", "Content-Type=application/json", "--body", f"@{file}"])
        try:
            output = command(args)
        finally:
            file.unlink(missing_ok=True)
    else:
        output = command(args)
    return json.loads(output) if output.strip() else {}


def owned_application(name: str, marker: str, install: bool, properties: dict) -> dict:
    """Recover interrupted creation by marker and refuse similarly named unrelated applications."""
    query = quote(f"displayName eq '{name}'", safe="")
    response = graph("GET", f"applications?$filter={query}")
    if response.get("@odata.nextLink"):
        raise ValueError("Ambiguous application search; refuse truncated ownership discovery.")
    matches = response["value"]
    if len(matches) > 1 or any(marker not in app.get("tags", []) for app in matches):
        raise ValueError(f"Application ownership conflict: {name}. No adoption or duplicate creation.")
    if not matches:
        if not install:
            raise ValueError(f"Scenario-owned application is not installed: {name}")
        return graph("POST", "applications", {
            "displayName": name, "signInAudience": "AzureADMyOrg", "tags": [marker], **properties,
        })
    app = matches[0]
    if app.get("signInAudience") != "AzureADMyOrg" or app.get("passwordCredentials") or app.get("keyCredentials"):
        raise ValueError(f"Unexpected audience or credentials on owned application: {name}")
    return app


def configure(app: dict, expected: dict, install: bool) -> dict:
    """Update only verified owned objects; verification never repairs drift."""
    if install:
        graph("PATCH", f"applications/{app['id']}", expected)
        app = graph("GET", f"applications/{app['id']}")
    for key, value in expected.items():
        if isinstance(value, dict):
            if any(app.get(key, {}).get(k) != v for k, v in value.items()):
                raise ValueError(f"Installed application property differs: {key}")
        elif app.get(key) != value:
            raise ValueError(f"Installed application property differs: {key}")
    return app


def service_principal(app: dict, marker: str, install: bool) -> dict:
    """Create only the SP of a proven owned application, retaining assignment policy."""
    response = graph("GET", f"servicePrincipals?$filter=appId%20eq%20'{app['appId']}'")
    matches = response["value"]
    if response.get("@odata.nextLink") or len(matches) > 1:
        raise ValueError("Ambiguous service principal discovery.")
    if not matches:
        if not install:
            raise ValueError("Scenario-owned service principal is missing.")
        return graph("POST", "servicePrincipals", {
            "appId": app["appId"], "tags": [marker], "appRoleAssignmentRequired": False,
        })
    principal = matches[0]
    if marker not in principal.get("tags", []) or principal.get("appRoleAssignmentRequired") is not False:
        raise ValueError("Service principal ownership or assignment policy differs; no policy weakening.")
    return principal


def execute(scope: dict, install: bool) -> dict:
    """Create/verify the API and PKCE public client and capture real nonsecret outputs."""
    account = json.loads(command(["az", "account", "show", "--subscription", scope["subscriptionId"], "-o", "json"]))
    if (account["id"] != scope["subscriptionId"] or account["tenantId"] != scope["tenantId"]
            or account["user"]["name"].casefold() != scope["account"].casefold()):
        raise ValueError("CLI identity differs from authorized targets; no account switch attempted.")
    default = json.loads(command(["az", "account", "show", "-o", "json"]))
    if default["id"] != scope["subscriptionId"] or default["tenantId"] != scope["tenantId"]:
        raise ValueError("Graph CLI tenant differs; arrange the selected identity outside this worker.")
    principal = os.environ.get("AZURE_PRINCIPAL_ID")
    if not principal:
        raise ValueError("Capture the actual authorized deployer principal before identity installation.")
    for args, field in (
        (["az", "account", "get-access-token", "--subscription", scope["subscriptionId"],
          "--resource", "https://management.azure.com/", "-o", "json"], "accessToken"),
        (["azd", "auth", "token", "--tenant-id", scope["tenantId"], "--scope",
          "https://management.azure.com/.default", "--no-prompt", "-o", "json"], "token"),
    ):
        raw = json.loads(command(args, secret=True))[field]
        payload = raw.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims.get("tid") != scope["tenantId"] or claims.get("oid") != principal:
            raise ValueError("CLI/azd tenant or deployer differs; no identity switch attempted.")
        # Decoding proves alignment only; live authenticated API acceptance remains separate.
    ownership = {key: scope[key] for key in ("tenantId", "subscriptionId", "resourceGroup", "environment")}
    marker = "abcbuilder:" + str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(ownership, sort_keys=True)))
    scope_id = str(uuid.uuid5(uuid.NAMESPACE_URL, marker + ":access_as_user"))
    api = owned_application(f"hospitality-feedback-{scope['environment']}-api", marker, install, {})
    permission = {
        "id": scope_id, "value": "access_as_user", "isEnabled": True, "type": "User",
        "adminConsentDisplayName": "Operate the hotel feedback reference",
        "adminConsentDescription": "Access scenario operator APIs as the signed-in user.",
        "userConsentDisplayName": "Operate hotel feedback",
        "userConsentDescription": "Access the synthetic hotel feedback APIs as you.",
    }
    api = configure(api, {
        "identifierUris": [f"api://{api['appId']}"],
        "api": {"requestedAccessTokenVersion": 2, "oauth2PermissionScopes": [permission]},
    }, install)
    client = owned_application(f"hospitality-feedback-{scope['environment']}-operator", marker, install, {
        "publicClient": {"redirectUris": ["http://localhost"]},
    })
    client = configure(client, {
        "publicClient": {"redirectUris": ["http://localhost"]},
        "requiredResourceAccess": [{
            "resourceAppId": api["appId"], "resourceAccess": [{"id": scope_id, "type": "Scope"}],
        }],
    }, install)
    api_sp = service_principal(api, marker, install)
    client_sp = service_principal(client, marker, install)
    output = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "scope": scope, "ownershipMarker": marker,
        "apiClientId": api["appId"], "apiObjectId": api["id"], "apiServicePrincipalId": api_sp["id"],
        "operatorClientId": client["appId"], "operatorObjectId": client["id"],
        "operatorServicePrincipalId": client_sp["id"], "scopeId": scope_id,
        "delegatedScope": f"api://{api['appId']}/access_as_user", "apiAudience": api["appId"],
        "redirectUris": ["http://localhost"], "appRoleAssignmentRequired": False,
        "consentVerified": False, "tokenFlowVerified": False,
    }
    path = ROOT / ".local" / "identity-outputs.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if install:
        for variable, value in [("API_AUDIENCE", api["appId"]), ("OPERATOR_CLIENT_ID", client["appId"])]:
            command(["azd", "env", "set", variable, value, "--environment", scope["environment"]])
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["plan", "install", "verify", "guard"])
    args = parser.parse_args()
    if args.operation == "plan":
        print(json.dumps({
            "directoryActions": DIRECTORY_ACTIONS, "redirectUris": ["http://localhost"],
            "delegatedPermission": "access_as_user", "applicationPermissions": [],
            "secretsCreated": False, "adminConsentGranted": False, "cloudOperations": False,
        }, indent=2))
        return
    state_directory = os.environ.get("ABCBUILDER_PROJECT_STATE") or os.environ.get("HACKBUILDER_PROJECT_STATE")
    if not state_directory:
        raise ValueError("Run through the canonical portal; project state context is required.")
    repository = Path(state_directory).parents[1]
    state = json.loads(command(["python", str(repository / "scripts" / "portal_workflow.py"), "read"]))
    owner = os.environ.get("ABCBUILDER_RUN_ID") or os.environ.get("HACKBUILDER_RUN_ID")
    if not owner or state.get("writer") != owner:
        raise ValueError("The current canonical project writer lease is required.")
    scope = authorize(state, dict(os.environ))
    if args.operation == "guard":
        print("Canonical exact-target deployment and directory scope verified; no cloud operation.")
        return
    print(json.dumps(execute(scope, args.operation == "install"), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError, IndexError, subprocess.TimeoutExpired) as error:
        print(f"Scenario identity operation blocked: {error}", file=sys.stderr)
        sys.exit(1)
