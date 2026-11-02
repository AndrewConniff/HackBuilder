"""Assign only the approved operator and scenario-specific delegated consent to verified owned principals."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

SCENARIO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCENARIO / "scripts"))
from setup_identity import Installer, consume, ownership, role_id

OPERATOR = "214d672b-df87-4f3b-94fd-7863032546c1"
DEFAULT_ROLE = "00000000-0000-0000-0000-000000000000"


def install(installer: Installer, receipt: dict) -> dict:
    scope = installer.scope
    consume(receipt, scope["tenantId"], scope["subscriptionId"], scope["environment"], scope["region"])
    if receipt["scope"] != scope:
        raise ValueError("Identity receipt differs from the authorized installation scope.")
    account = installer.cli(["account", "show", "--subscription", scope["subscriptionId"], "--output", "json"])
    if (account["id"] != scope["subscriptionId"] or account["tenantId"] != scope["tenantId"]
            or account["user"]["name"].casefold() != scope["account"].casefold() or account["state"] != "Enabled"):
        raise ValueError("Current CLI account differs from the authorized account/subscription/tenant.")
    current = installer.graph("get", "/me?$select=id,userPrincipalName")
    if current["id"] != OPERATOR:
        raise ValueError("Current Graph operator differs from the expressly authorized assignment user.")
    marker = ownership(scope)
    for kind in ("api", "client"):
        app = installer.graph("get", f"/applications/{receipt[kind]['objectId']}")
        principal = installer.graph("get", f"/servicePrincipals/{receipt[kind]['servicePrincipalId']}")
        if (app.get("notes") != marker or app["appId"] != receipt[kind]["clientId"]
                or principal["appId"] != app["appId"]
                or principal.get("appOwnerOrganizationId") != scope["tenantId"]
                or marker not in principal.get("tags", [])
                or principal.get("appRoleAssignmentRequired") is not True):
            raise ValueError("Application or service-principal ownership/configuration did not verify.")
        if kind == "api" and not any(
            role.get("id") == role_id(marker, "Manager") and role.get("value") == "Manager"
            and role.get("isEnabled") is True for role in principal.get("appRoles", [])
        ):
            raise ValueError("Actual API principal does not expose the installed Manager role.")
    result = {"operatorId": OPERATOR, "assignments": [], "consent": None}
    for kind, selected_role in (("api", role_id(marker, "Manager")), ("client", DEFAULT_ROLE)):
        resource = receipt[kind]["servicePrincipalId"]
        path = f"/servicePrincipals/{resource}/appRoleAssignedTo"
        existing = installer.listing(path)
        matches = [item for item in existing if item.get("principalId") == OPERATOR
                   and item.get("resourceId") == resource and item.get("appRoleId") == selected_role]
        if len(matches) > 1:
            raise ValueError("Duplicate operator assignments; no mutation performed.")
        if not matches:
            installer.graph("post", path, {
                "principalId": OPERATOR, "resourceId": resource, "appRoleId": selected_role,
            })
        verified = [item for item in installer.listing(path)
                    if item.get("principalId") == OPERATOR and item.get("resourceId") == resource
                    and item.get("appRoleId") == selected_role]
        if len(verified) != 1:
            raise ValueError("Operator assignment did not verify after installation.")
        result["assignments"].append({"kind": kind, **verified[0]})
    client = receipt["client"]["servicePrincipalId"]
    resource = receipt["api"]["servicePrincipalId"]
    query = "?" + urlencode({"$filter": f"clientId eq '{client}' and resourceId eq '{resource}'"})
    grants = installer.listing("/oauth2PermissionGrants" + query)
    if any(item.get("consentType") != "Principal" or item.get("principalId") != OPERATOR
           or item.get("scope") != "access_as_user" for item in grants):
        raise ValueError("Unexpected existing delegated consent; no broadening or overwrite is allowed.")
    if len(grants) > 1:
        raise ValueError("Ambiguous delegated consent grants.")
    if not grants:
        installer.graph("post", "/oauth2PermissionGrants", {
            "clientId": client, "consentType": "Principal", "principalId": OPERATOR,
            "resourceId": resource, "scope": "access_as_user",
        })
    verified = installer.listing("/oauth2PermissionGrants" + query)
    if (len(verified) != 1 or verified[0].get("principalId") != OPERATOR
            or verified[0].get("consentType") != "Principal" or verified[0].get("scope") != "access_as_user"):
        raise ValueError("Operator-only scenario delegated consent did not verify.")
    result.update(consent=verified[0], checkedAtUtc=datetime.now(timezone.utc).isoformat())
    return result


def verify(installer: Installer, receipt: dict) -> dict:
    scope = installer.scope
    consume(receipt, scope["tenantId"], scope["subscriptionId"], scope["environment"], scope["region"])
    if scope != receipt["scope"]:
        raise ValueError("Receipt differs from the authorized installation scope.")
    account = installer.cli(["account", "show", "--subscription", scope["subscriptionId"], "--output", "json"])
    if (account["id"] != scope["subscriptionId"] or account["tenantId"] != scope["tenantId"]
            or account["user"]["name"].casefold() != scope["account"].casefold() or account["state"] != "Enabled"):
        raise ValueError("Verification account differs from the authorized target.")
    if installer.graph("get", "/me?$select=id")["id"] != OPERATOR:
        raise ValueError("Verification operator differs from the authorized user.")
    for kind in ("api", "client"):
        principal = installer.graph("get", f"/servicePrincipals/{receipt[kind]['servicePrincipalId']}")
        if (principal.get("appId") != receipt[kind]["clientId"]
                or principal.get("appOwnerOrganizationId") != scope["tenantId"]
                or ownership(scope) not in principal.get("tags", [])
                or principal.get("appRoleAssignmentRequired") is not True):
            raise ValueError("Owned assignment-required principal configuration did not verify.")
    client = receipt["client"]["servicePrincipalId"]
    resource = receipt["api"]["servicePrincipalId"]
    query = "?" + urlencode({"$filter": f"clientId eq '{client}' and resourceId eq '{resource}'"})
    grants = installer.listing("/oauth2PermissionGrants" + query)
    passed = len(grants) == 1 and all((
        grants[0].get("principalId") == OPERATOR, grants[0].get("consentType") == "Principal",
        grants[0].get("scope") == "access_as_user", grants[0].get("clientId") == client,
        grants[0].get("resourceId") == resource,
    ))
    return {
        "passed": passed, "matchingApplicationGrantCount": len(grants),
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "readOnly": True,
        "summary": (
            "Exact operator-only consent verified." if passed else "Required operator-only consent is absent or invalid."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    scope_file = SCENARIO / "evidence" / "identity-install-scope.json"
    authorization = json.loads(scope_file.read_text(encoding="utf-8"))
    if (authorization["authorizationDecisionId"] != "3f3d19a20079404991c95dfe6d23b93f"
            or authorization["operatorObjectId"] != OPERATOR):
        raise ValueError("Recorded exact operator authorization is required.")
    path = SCENARIO / "evidence" / "identity-installation.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if args.verify_only:
        result = verify(Installer(authorization["scope"], path, False), receipt)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["passed"] else 1)
    result = install(Installer(authorization["scope"], path, True), receipt)
    (Path(__file__).parent / "operator-access-receipt.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8",
    )
    print("Verified operator-only Manager/client assignments and scenario delegated consent; real sign-in is pending.")
