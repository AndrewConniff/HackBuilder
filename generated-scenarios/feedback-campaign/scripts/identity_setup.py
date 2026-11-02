"""Idempotent, scenario-owned Entra setup for authorized azd hooks; never grants admin consent."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone

from cloud_io import cli, environment, receipt, request, verify_target

GRAPH = "https://graph.microsoft.com"
NAME = "feedback-campaign-reference"
MARKER = "ABCBuilder:feedback-campaign:owned-registration"
ROLES = ["CampaignOperator", "ProductManager", "ConflictResolutionSpecialist", "ControlAdmin"]


def graph(method: str, path: str, body: dict | None = None) -> dict:
    return request(method, GRAPH + "/v1.0/" + path, GRAPH, body) or {}


def find_application() -> dict | None:
    values = graph("GET", f"applications?$filter=displayName%20eq%20'{NAME}'")["value"]
    if len(values) > 1 or values and MARKER not in values[0].get("tags", []):
        raise RuntimeError("Application name collision; existing unrelated objects will not be adopted.")
    return values[0] if values else None


def main(mode: str) -> None:
    account = verify_target()
    if mode == "prepare":
        # Shared identity helper verifies existing CLI/azd metadata. No login/default changes.
        repo = __import__("pathlib").Path(r"C:\HackBuilder")
        sys.path.insert(0, str(repo / "scripts"))
        from azure_context import identity
        identified = identity(repo)
        if identified["scope"]["tenantId"] != account["tenantId"]:
            raise RuntimeError("Existing CLI and azd target mismatch.")
        me = graph("GET", "me?$select=id,userPrincipalName")
        app = find_application()
        roles = [{"allowedMemberTypes": ["User"], "description": value, "displayName": value,
                  "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{MARKER}/{value}")),
                  "isEnabled": True, "value": value} for value in ROLES]
        if app is None:
            app = graph("POST", "applications", {
                "displayName": NAME, "signInAudience": "AzureADMyOrg", "tags": [MARKER],
                "web": {"redirectUris": [], "implicitGrantSettings": {"enableIdTokenIssuance": True}},
                "appRoles": roles,
            })
            owners = graph("GET", f"applications/{app['id']}/owners?$select=id")["value"]
            if me["id"] not in {owner["id"] for owner in owners}:
                graph("POST", f"applications/{app['id']}/owners/$ref",
                      {"@odata.id": f"{GRAPH}/v1.0/directoryObjects/{me['id']}"})
        else:
            owners = graph("GET", f"applications/{app['id']}/owners?$select=id")["value"]
            if me["id"] not in {owner["id"] for owner in owners}:
                raise RuntimeError("Signed-in installer does not own this scenario registration.")
            graph("PATCH", f"applications/{app['id']}", {"appRoles": roles})
        principals = graph("GET", f"servicePrincipals?$filter=appId%20eq%20'{app['appId']}'")["value"]
        sp = principals[0] if principals else graph("POST", "servicePrincipals", {"appId": app["appId"]})
        graph("PATCH", f"servicePrincipals/{sp['id']}", {"appRoleAssignmentRequired": True})
        assignments = graph("GET", f"servicePrincipals/{sp['id']}/appRoleAssignedTo")["value"]
        for role in roles:
            if not any(a["principalId"] == me["id"] and a["appRoleId"] == role["id"] for a in assignments):
                graph("POST", f"servicePrincipals/{sp['id']}/appRoleAssignedTo",
                      {"principalId": me["id"], "resourceId": sp["id"], "appRoleId": role["id"]})
        for key, value in {"AUTH_CLIENT_ID": app["appId"], "AUTH_OBJECT_ID": app["id"],
                           "AUTH_SERVICE_PRINCIPAL_ID": sp["id"], "INSTALLER_OBJECT_ID": me["id"],
                           "AZURE_TENANT_ID": account["tenantId"]}.items():
            cli("azd", "env", "set", key, value)
        receipt("identity-installation.json", {"checkedAtUtc": datetime.now(timezone.utc).isoformat(),
                "applicationId": app["id"], "clientId": app["appId"], "servicePrincipalId": sp["id"],
                "installerObjectId": me["id"], "roles": ROLES, "tenantId": account["tenantId"]})
    elif mode == "configure":
        env = environment()
        app = find_application()
        if app is None or app["id"] != env["AUTH_OBJECT_ID"]:
            raise RuntimeError("Scenario application output mismatch.")
        if env["APP_URL"] != f"https://{env['AZURE_WEBAPP_NAME']}.azurewebsites.net":
            raise RuntimeError("Callback URL does not match the generated scenario app hostname.")
        graph("PATCH", f"applications/{app['id']}", {
            "web": {"redirectUris": [env["APP_URL"] + "/.auth/login/aad/callback"],
                    "implicitGrantSettings": {"enableIdTokenIssuance": True}},
        })
    elif mode == "acceptance-role":
        # Explicitly reviewed negative-test scope only: alter only this installer's
        # own assignments on this one scenario service principal, then restore via prepare.
        role = sys.argv[2] if len(sys.argv) > 2 else ""
        if role not in ROLES:
            raise ValueError("Specify exactly one scenario role for the authorized acceptance test.")
        env = environment()
        me = graph("GET", "me?$select=id")
        app = find_application()
        if app is None or app["id"] != env["AUTH_OBJECT_ID"] or me["id"] != env["INSTALLER_OBJECT_ID"]:
            raise RuntimeError("Acceptance identity or scenario application mismatch.")
        sp_id = env["AUTH_SERVICE_PRINCIPAL_ID"]
        principal = graph("GET", f"servicePrincipals/{sp_id}?$select=appId")
        if principal["appId"] != app["appId"]:
            raise RuntimeError("Service principal does not belong to this scenario application.")
        assignments = graph("GET", f"servicePrincipals/{sp_id}/appRoleAssignedTo")["value"]
        ids = {value: str(uuid.uuid5(uuid.NAMESPACE_URL, f"{MARKER}/{value}")) for value in ROLES}
        for assignment in assignments:
            if (assignment["principalId"] == me["id"] and assignment["appRoleId"] in ids.values()
                    and assignment["appRoleId"] != ids[role]):
                graph("DELETE", f"servicePrincipals/{sp_id}/appRoleAssignedTo/{assignment['id']}")
        if not any(a["principalId"] == me["id"] and a["appRoleId"] == ids[role] for a in assignments):
            graph("POST", f"servicePrincipals/{sp_id}/appRoleAssignedTo",
                  {"principalId": me["id"], "resourceId": sp_id, "appRoleId": ids[role]})
        receipt("acceptance-role.json", {"checkedAtUtc": datetime.now(timezone.utc).isoformat(),
                "role": role, "installerObjectId": me["id"], "servicePrincipalId": sp_id,
                "restore": "python scripts/identity_setup.py prepare"})
    else:
        raise ValueError("Mode must be prepare, configure or acceptance-role.")


if __name__ == "__main__":
    main(sys.argv[1])
