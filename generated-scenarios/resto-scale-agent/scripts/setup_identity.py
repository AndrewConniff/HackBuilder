"""Verify or repair the retained scenario-owned Entra pair; never retry the historical consent denial."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from uuid import NAMESPACE_URL, UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("Manager", "Host", "Server", "Kitchen", *(f"Floor.{floor}" for floor in range(1, 6)))


def ownership(scope: dict) -> str:
    """Preserve the original tenant/subscription/group/environment ownership marker."""
    value = "|".join(scope[key] for key in ("tenantId", "subscriptionId", "resourceGroup", "environment"))
    return "abc-resto-scale-agent:" + hashlib.sha256(value.encode()).hexdigest()


def role_id(marker: str, role: str) -> str:
    """Preserve the original deterministic role/scope identifiers."""
    return str(uuid5(NAMESPACE_URL, f"{marker}/{role}"))


def consume(receipt: dict, tenant: str, subscription: str, environment: str, region: str) -> dict:
    """Validate non-secret installed IDs locally; a receipt is not current cloud verification or consent."""
    scope = receipt["scope"]
    if (receipt.get("installed") is not True or receipt.get("ownershipMarker") != ownership(scope)
            or scope["tenantId"] != tenant or scope["subscriptionId"] != subscription
            or scope["environment"] != environment or scope["resourceGroup"] != f"rg-{environment}"
            or scope["region"] != region or receipt["staffTenantId"] != tenant
            or receipt["staffAudience"] != receipt["api"]["clientId"]):
        raise ValueError("Identity receipt differs from the exact scenario target or ownership.")
    for value in (tenant, subscription, *(receipt[kind][field] for kind in ("api", "client")
                  for field in ("clientId", "objectId", "servicePrincipalId"))):
        UUID(value)
    if receipt.get("roleIds") != {
        role: role_id(ownership(scope), role) for role in ROLES
    }:
        raise ValueError("Identity receipt role IDs differ from the owned installation.")
    return {"staffTenantId": tenant, "staffAudience": receipt["api"]["clientId"],
            "staffClientId": receipt["client"]["clientId"]}


class Installer:
    """Bound Azure/Graph operations to an explicit scope; all writes require an explicit installation route."""

    def __init__(self, scope: dict, receipt: Path, authorized: bool = False) -> None:
        self.scope = scope
        self.receipt = receipt
        self.authorized = authorized

    def cli(self, arguments: list[str]) -> dict:
        """Invoke the installed CLI without changing account defaults or retaining access tokens."""
        executable = shutil.which("az")
        if not executable:
            raise RuntimeError("Azure CLI is unavailable.")
        result = subprocess.run([executable, *arguments], capture_output=True, text=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(f"Scoped Azure operation failed ({result.returncode}): {result.stderr.strip()}")
        return json.loads(result.stdout)

    def graph(self, method: str, path: str, body: dict | None = None) -> dict:
        """Use exact Graph endpoints; blocked consent writes cannot be retried by this restored helper."""
        method = method.lower()
        url = path if path.startswith("https://graph.microsoft.com/v1.0/") else (
            "https://graph.microsoft.com/v1.0" + path
        )
        if not url.startswith("https://graph.microsoft.com/v1.0/") or not path.startswith(("/", "https://")):
            raise ValueError("Only Microsoft Graph v1.0 endpoints are supported.")
        if method != "get":
            if not self.authorized:
                raise PermissionError("Directory writes are not authorized.")
            if method != "patch" or not path.startswith("/applications/") or body is None or set(body) != {"spa"}:
                raise PermissionError("Only the reviewed owned-client SPA redirect repair is supported; consent writes remain denied.")
        arguments = ["rest", "--subscription", self.scope["subscriptionId"], "--method", method,
                     "--url", url, "--output", "json"]
        if body is None:
            return self.cli(arguments)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json",
                                         dir=self.receipt.parent, delete=False) as stream:
            json.dump(body, stream)
            temporary = Path(stream.name)
        try:
            arguments += ["--body", f"@{temporary}", "--headers", "Content-Type=application/json"]
            # Graph PATCH returns no body; keep CLI errors explicit without trying to decode an empty response.
            executable = shutil.which("az")
            if not executable:
                raise RuntimeError("Azure CLI is unavailable.")
            result = subprocess.run([executable, *arguments], capture_output=True, text=True, timeout=120, check=False)
            if result.returncode:
                raise RuntimeError(f"Owned-client redirect repair failed ({result.returncode}): {result.stderr.strip()}")
            return json.loads(result.stdout) if result.stdout.strip() else {}
        finally:
            temporary.unlink(missing_ok=True)

    def listing(self, path: str) -> list[dict]:
        """Follow only Graph pagination; do not treat missing results as successful verification."""
        values = []
        seen = set()
        while path:
            if path in seen:
                raise ValueError("Repeated Graph pagination link.")
            seen.add(path)
            page = self.graph("get", path)
            values.extend(page["value"])
            path = page.get("@odata.nextLink")
        return values

    def inspect(self, receipt: dict) -> dict:
        """Verify actual owned applications, principals, API contract and assignment-required configuration."""
        scope = self.scope
        consume(receipt, scope["tenantId"], scope["subscriptionId"], scope["environment"], scope["region"])
        if receipt["scope"] != scope:
            raise ValueError("Receipt does not match the complete authorized scope.")
        account = self.cli(["account", "show", "--subscription", scope["subscriptionId"], "--output", "json"])
        if (account["id"] != scope["subscriptionId"] or account["tenantId"] != scope["tenantId"]
                or account["user"]["name"].casefold() != scope["account"].casefold()
                or account["state"] != "Enabled"):
            raise ValueError("Actual account/subscription/tenant differs from the authorized target.")
        marker = ownership(scope)
        objects = {}
        for kind in ("api", "client"):
            ids = receipt[kind]
            app = self.graph("get", f"/applications/{ids['objectId']}")
            principal = self.graph("get", f"/servicePrincipals/{ids['servicePrincipalId']}")
            if (app.get("id") != ids["objectId"] or app.get("appId") != ids["clientId"]
                    or app.get("notes") != marker or app.get("signInAudience") != "AzureADMyOrg"
                    or principal.get("id") != ids["servicePrincipalId"] or principal.get("appId") != ids["clientId"]
                    or principal.get("appOwnerOrganizationId") != scope["tenantId"]
                    or marker not in principal.get("tags", []) or principal.get("appRoleAssignmentRequired") is not True
                    or principal.get("accountEnabled") is not True
                    or app.get("passwordCredentials") or app.get("keyCredentials")):
                raise ValueError("Owned single-tenant secretless application/principal configuration did not verify.")
            objects[kind] = app
            if kind == "api":
                roles = {role["value"]: role["id"] for role in app.get("appRoles", [])
                         if role.get("isEnabled") is True and role.get("allowedMemberTypes") == ["User"]}
                principal_roles = {role["value"]: role["id"] for role in principal.get("appRoles", [])
                                   if role.get("isEnabled") is True}
                expected = {role: role_id(marker, role) for role in ROLES}
                scopes = [entry for entry in app.get("api", {}).get("oauth2PermissionScopes", [])
                          if entry.get("value") == "access_as_user" and entry.get("isEnabled") is True]
                if (roles != expected or principal_roles != expected
                        or app.get("api", {}).get("requestedAccessTokenVersion") != 2 or len(scopes) != 1
                        or app.get("identifierUris") != [f"api://{ids['clientId']}"]):
                    raise ValueError("Owned API v2 access-token scope and business/floor roles did not verify.")
                objects["scopeId"] = scopes[0]["id"]
        required = [{"resourceAppId": receipt["api"]["clientId"],
                     "resourceAccess": [{"id": objects["scopeId"], "type": "Scope"}]}]
        if objects["client"].get("requiredResourceAccess") != required:
            raise ValueError("Client must request only this scenario's delegated access_as_user scope.")
        return objects


def verify_access(installer: Installer, receipt: dict, objects: dict, redirect: str | None = None) -> dict:
    """Read actual operator assignments and exact operator-only consent; never install a missing grant."""
    operator = installer.graph("get", "/me?$select=id")["id"]
    UUID(operator)
    assignments = {}
    for kind, selected in (("api", role_id(ownership(installer.scope), "Manager")),
                           ("client", "00000000-0000-0000-0000-000000000000")):
        resource = receipt[kind]["servicePrincipalId"]
        matches = [entry for entry in installer.listing(f"/servicePrincipals/{resource}/appRoleAssignedTo")
                   if entry.get("principalId") == operator and entry.get("resourceId") == resource
                   and entry.get("appRoleId") == selected]
        assignments[kind] = len(matches) == 1
    query = urlencode({"$filter": f"clientId eq '{receipt['client']['servicePrincipalId']}' "
                       f"and resourceId eq '{receipt['api']['servicePrincipalId']}'"})
    grants = installer.listing("/oauth2PermissionGrants?" + query)
    consent = len(grants) == 1 and all((
        grants[0].get("consentType") == "Principal", grants[0].get("principalId") == operator,
        grants[0].get("scope") == "access_as_user",
        grants[0].get("clientId") == receipt["client"]["servicePrincipalId"],
        grants[0].get("resourceId") == receipt["api"]["servicePrincipalId"],
    ))
    redirects = objects["client"].get("spa", {}).get("redirectUris", [])
    redirect_ok = redirect in redirects if redirect else False
    return {"passed": all(assignments.values()) and consent and redirect_ok, "readOnly": True,
            "checkedAtUtc": datetime.now(timezone.utc).isoformat(), "operatorId": operator,
            "assignments": assignments, "operatorConsent": consent, "redirectVerified": redirect_ok,
            "matchingApplicationGrantCount": len(grants)}


def callback(application_url: str) -> str:
    """Allow only an exact HTTPS application origin, never arbitrary callback paths."""
    uri = urlparse(application_url)
    if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password
            or uri.query or uri.fragment or uri.path not in ("", "/") or uri.port not in (None, 443)):
        raise ValueError("An exact HTTPS application origin is required.")
    return application_url.rstrip("/") + "/auth.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--receipt", type=Path, default=ROOT / "evidence" / "identity-installation.json")
    parser.add_argument("--verify-local", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--authorize-directory-install", action="store_true")
    parser.add_argument("--application-url")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    scope = receipt["scope"]
    if args.scope:
        scope = json.loads(args.scope.read_text(encoding="utf-8"))["scope"]
    result = consume(receipt, scope["tenantId"], scope["subscriptionId"], scope["environment"], scope["region"])
    if args.verify_local:
        if args.verify_only or args.authorize_directory_install:
            parser.error("Local receipt validation cannot authorize cloud operations.")
        print("Non-secret identity receipt is locally consistent; installed state and consent remain unverified.")
        return
    if not args.scope or not args.application_url or not (args.verify_only ^ args.authorize_directory_install):
        parser.error("Specify exact --scope and --application-url, and one explicit verification or repair route.")
    installer = Installer(scope, args.receipt, args.authorize_directory_install)
    objects = installer.inspect(receipt)
    redirect = callback(args.application_url)
    if args.authorize_directory_install:
        current = objects["client"].get("spa", {}).get("redirectUris", [])
        if redirect not in current:
            installer.graph("patch", f"/applications/{receipt['client']['objectId']}",
                            {"spa": {"redirectUris": [*current, redirect]}})
            objects = installer.inspect(receipt)
    verification = verify_access(installer, receipt, objects, redirect)
    result.update(verification=verification)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification, indent=2))
    if not verification["passed"]:
        raise SystemExit("Staff installation is incomplete; exact operator consent/assignments/redirect must verify. "
                         "No denied consent write was retried; no sign-in success is claimed.")


if __name__ == "__main__":
    main()
