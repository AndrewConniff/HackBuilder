"""Install only authorized, scenario-owned Entra objects and capture azd inputs automatically."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
GRAPH = "https://graph.microsoft.com/v1.0"
OPERATIONS = {"registrations", "redirect", "assignments"}


def save(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def command(arguments: list[str], *, json_output: bool = True, timeout: int = 120) -> dict | list | str:
    executable = shutil.which(arguments[0])
    if executable is None:
        raise RuntimeError(f"Required tool is missing: {arguments[0]}")
    result = subprocess.run(
        [executable, *arguments[1:]], capture_output=True, text=True, encoding="utf-8", check=False, timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(f"{arguments[0]} {arguments[1:3]} failed ({result.returncode}): {result.stderr}")
    if not json_output:
        return result.stdout
    return json.loads(result.stdout) if result.stdout.strip() else {}


def scope_from_environment() -> dict:
    keys = {
        "account": "EQUIP_INSTALLER_ACCOUNT", "subscriptionId": "AZURE_SUBSCRIPTION_ID",
        "tenantId": "AZURE_TENANT_ID", "environment": "AZURE_ENV_NAME",
        "resourceGroup": "AZURE_RESOURCE_GROUP", "region": "AZURE_LOCATION",
    }
    scope = {key: os.environ.get(value, "") for key, value in keys.items()}
    if (not all(scope.values()) or scope["resourceGroup"] != f"rg-{scope['environment']}"
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,27}", scope["environment"])):
        raise ValueError("Explicit installer account and complete scenario target environment are required.")
    for field in ("subscriptionId", "tenantId"):
        uuid.UUID(scope[field])
    return scope


def validate_authorization(document: dict, scope: dict, operation: str, now: datetime) -> None:
    if document.get("scope") != scope or operation not in document.get("directoryOperations", []):
        raise ValueError("Separate exact-scope directory authorization is required; ARM consent is insufficient.")
    if not document.get("authorizationReference") or not document.get("approvedBy"):
        raise ValueError("Directory authorization must retain its actual approval provenance.")
    # Only a genuine user-imposed expiry limits consent. Worker lease/receipt timers are not revocations.
    if document.get("expiresAtUtc"):
        expires = datetime.fromisoformat(document["expiresAtUtc"])
        if expires.tzinfo is None or now >= expires:
            raise ValueError("Directory authorization is expired or has no timezone.")


class Installer:
    def __init__(self, scope: dict, authorization: dict) -> None:
        self.scope = scope
        self.authorization = authorization
        self.directory = ROOT / ".installation" / scope["environment"]
        self.receipt_path = self.directory / "identity.json"
        marker = hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()[:24]
        self.marker = f"ABCBuilder:equip-ai:{marker}"
        self.receipt = json.loads(self.receipt_path.read_text()) if self.receipt_path.exists() else {
            "scope": scope, "ownershipMarker": self.marker,
            "definitions": {key: str(uuid.uuid4()) for key in ("read", "tacoma", "statewide")},
        }
        if self.receipt["scope"] != scope or self.receipt["ownershipMarker"] != self.marker:
            raise ValueError("Installation receipt belongs to a different scenario target.")

    def graph(self, method: str, route: str, body: dict | None = None) -> dict:
        arguments = [
            "az", "rest", "--method", method, "--url", GRAPH + route,
            "--subscription", self.scope["subscriptionId"], "--output", "json",
        ]
        if body is not None:
            path = self.directory / "request.json"
            save(path, body)
            arguments += ["--headers", "Content-Type=application/json", "--body", f"@{path}"]
        return command(arguments)

    def collection(self, route: str, query: dict | None = None) -> list[dict]:
        result = self.graph("get", route + ("?" + urlencode(query) if query else ""))
        if result.get("@odata.nextLink"):
            raise ValueError("Ambiguous/paginated identity lookup; refusing partial ownership evidence.")
        return result["value"]

    def checkpoint(self) -> None:
        self.receipt["authorizationReference"] = self.authorization["authorizationReference"]
        self.receipt["checkedAtUtc"] = datetime.now(timezone.utc).isoformat()
        save(self.receipt_path, self.receipt)

    def verify_context(self) -> None:
        observed = command([
            "az", "account", "show", "--subscription", self.scope["subscriptionId"], "--output", "json",
        ])
        if (observed["tenantId"] != self.scope["tenantId"] or observed["id"] != self.scope["subscriptionId"]
                or observed["user"]["name"].casefold() != self.scope["account"].casefold()):
            raise ValueError("Installer Azure identity differs from authorized scope.")
        metadata = command([
            "az", "account", "get-access-token", "--resource-type", "ms-graph",
            "--subscription", self.scope["subscriptionId"],
            "--query", "{tenant:tenant,subscription:subscription}", "--output", "json",
        ])
        if metadata["tenant"] != self.scope["tenantId"]:
            raise ValueError("Graph token tenant differs from authorized scope.")
        installer = self.graph("get", "/me")["id"]
        if self.authorization.get("installerObjectId", installer) != installer:
            raise ValueError("Current directory user is not the authorized installer.")
        self.owner = installer
        self.receipt["installerObjectId"] = installer

    def application(self, role: str) -> dict:
        name = f"{self.scope['environment']}-{role}"
        found = self.collection("/applications", {"$filter": f"displayName eq '{name}'"})
        if len(found) > 1:
            raise ValueError(f"Ambiguous application name: {name}")
        if not found:
            if role in self.receipt:
                raise ValueError("Recorded application was removed; refusing silent replacement.")
            self.checkpoint()
            app = self.graph("post", "/applications", {
                "displayName": name, "signInAudience": "AzureADMyOrg", "tags": [self.marker],
                "owners@odata.bind": [f"{GRAPH}/users/{self.owner}"],
                "isFallbackPublicClient": False,
                "web": {"implicitGrantSettings": {
                    "enableAccessTokenIssuance": False, "enableIdTokenIssuance": False,
                }},
            })
        else:
            app = found[0]
        owners = self.collection(f"/applications/{app['id']}/owners")
        if self.marker not in app.get("tags", []) or self.owner not in {x["id"] for x in owners}:
            raise ValueError(f"Refusing unowned application {name}; names are not ownership.")
        if app.get("passwordCredentials") or app.get("keyCredentials"):
            raise ValueError("Unexpected credentials on public-client/API registration.")
        if role == "api" and app.get("requiredResourceAccess"):
            raise ValueError("The scenario API must not request Graph or other resource permissions.")
        recorded = self.receipt.get(role, {})
        if recorded and (recorded["objectId"] != app["id"] or recorded["clientId"] != app["appId"]):
            raise ValueError("Recorded application identifiers changed.")
        self.receipt[role] = {**recorded, "objectId": app["id"], "clientId": app["appId"]}
        self.checkpoint()
        return app

    def principal(self, role: str) -> dict:
        app = self.receipt[role]
        found = self.collection("/servicePrincipals", {"$filter": f"appId eq '{app['clientId']}'"})
        if len(found) > 1:
            raise ValueError("Ambiguous service principal.")
        if not found and app.get("servicePrincipalId"):
            raise ValueError("Recorded service principal was removed.")
        principal = found[0] if found else self.graph("post", "/servicePrincipals", {
            "appId": app["clientId"], "tags": [self.marker], "appRoleAssignmentRequired": True,
        })
        if (self.marker not in principal.get("tags", [])
                or principal.get("appOwnerOrganizationId") != self.scope["tenantId"]
                or app.get("servicePrincipalId", principal["id"]) != principal["id"]):
            raise ValueError("Service principal ownership/tenant does not match.")
        self.graph("patch", f"/servicePrincipals/{principal['id']}", {"appRoleAssignmentRequired": True})
        observed = self.graph("get", f"/servicePrincipals/{principal['id']}")
        if observed.get("appRoleAssignmentRequired") is not True:
            raise ValueError("Service principal assignment-required policy readback failed.")
        app["servicePrincipalId"] = principal["id"]
        self.checkpoint()
        return principal

    def registrations(self) -> None:
        self.application("api")
        self.application("spa")
        api, spa, definitions = self.receipt["api"], self.receipt["spa"], self.receipt["definitions"]
        roles = [{
            "id": definitions[key], "value": value, "displayName": value, "description": description,
            "allowedMemberTypes": ["User"], "isEnabled": True,
        } for key, value, description in (
            ("tacoma", "Operations.Tacoma", "Read Tacoma equipment evidence"),
            ("statewide", "Operations.Statewide", "Read all five Washington site evidence"),
        )]
        api_settings = {
            "requestedAccessTokenVersion": 2,
            "oauth2PermissionScopes": [{
                "id": definitions["read"], "value": "Equipment.Read", "type": "Admin", "isEnabled": True,
                "adminConsentDisplayName": "Read equipment evidence",
                "adminConsentDescription": "Read fresh equipment evidence within assigned Operations site roles",
            }],
        }
        self.graph("patch", f"/applications/{api['objectId']}", {
            "identifierUris": [f"api://{api['clientId']}"], "appRoles": roles, "api": api_settings,
        })
        observed = self.graph("get", f"/applications/{api['objectId']}")
        if not any(
            scope.get("id") == definitions["read"] and scope.get("value") == "Equipment.Read"
            and scope.get("isEnabled") is True
            for scope in observed.get("api", {}).get("oauth2PermissionScopes", [])
        ):
            raise ValueError("API read scope is not installed; refusing dependent SPA preauthorization.")
        # Graph validates preauthorization against scopes persisted before this request.
        self.graph("patch", f"/applications/{api['objectId']}", {
            "api": {
                **api_settings,
                "preAuthorizedApplications": [{
                    "appId": spa["clientId"], "delegatedPermissionIds": [definitions["read"]],
                }],
            },
        })
        self.graph("patch", f"/applications/{spa['objectId']}", {
            "requiredResourceAccess": [{
                "resourceAppId": api["clientId"], "resourceAccess": [{"id": definitions["read"], "type": "Scope"}],
            }],
        })
        self.principal("api")
        self.principal("spa")
        actual_api = self.graph("get", f"/applications/{api['objectId']}")
        actual_spa = self.graph("get", f"/applications/{spa['objectId']}")
        if (actual_api["api"]["requestedAccessTokenVersion"] != 2
                or actual_api["identifierUris"] != [f"api://{api['clientId']}"]
                or actual_api["api"]["preAuthorizedApplications"] != [{
                    "appId": spa["clientId"], "delegatedPermissionIds": [definitions["read"]],
                }]
                or {x["value"] for x in actual_api["appRoles"]} != {"Operations.Tacoma", "Operations.Statewide"}
                or actual_spa["requiredResourceAccess"] != [{
                    "resourceAppId": api["clientId"],
                    "resourceAccess": [{"id": definitions["read"], "type": "Scope"}],
                }]):
            raise ValueError("Directory readback does not match the approved identity contract.")
        self.receipt["assignmentsStatus"] = "pending-explicit-principal-nominations"
        self.receipt["registrationStatus"] = "installed-not-runtime-validated"
        self.checkpoint()
        self.export()

    def export(self) -> None:
        values = {
            "EQUIP_API_CLIENT_ID": self.receipt["api"]["clientId"],
            "EQUIP_SPA_CLIENT_ID": self.receipt["spa"]["clientId"],
            "AZURE_PRINCIPAL_ID": self.receipt["installerObjectId"],
        }
        for name, key in (
            ("Foundry Agent Consumer", "EQUIP_AGENT_CONSUMER_ROLE_ID"),
            ("Foundry Project Runtime User", "EQUIP_AGENT_RUNTIME_ROLE_ID"),
            ("Foundry User", "EQUIP_AGENT_INSTALLER_ROLE_ID"),
        ):
            definitions = command([
                "az", "role", "definition", "list", "--name", name,
                "--subscription", self.scope["subscriptionId"], "--output", "json",
            ])
            if len(definitions) != 1 or definitions[0]["roleName"] != name:
                raise ValueError(f"Required built-in role is missing or ambiguous: {name}")
            values[key] = definitions[0]["name"]
        self.receipt["azdInputs"] = values
        self.checkpoint()
        for key, value in values.items():
            command(
                ["azd", "env", "set", key, value, "--environment", self.scope["environment"]],
                json_output=False,
            )

    def redirect(self, application_url: str) -> None:
        observed = command([
            "az", "webapp", "show", "--ids", os.environ["AZURE_WEB_RESOURCE_ID"],
            "--subscription", self.scope["subscriptionId"], "--output", "json",
        ])
        expected_prefix = (
            f"/subscriptions/{self.scope['subscriptionId']}/resourceGroups/"
            f"{self.scope['resourceGroup']}/providers/Microsoft.Web/sites/"
        )
        if not observed["id"].casefold().startswith(expected_prefix.casefold()):
            raise ValueError("Redirect source site is outside the authorized target.")
        expected = f"https://{observed['defaultHostName']}"
        if application_url.rstrip("/") != expected or urlparse(expected).scheme != "https":
            raise ValueError("Redirect must come from the actual ARM site output.")
        self.application("spa")
        self.graph("patch", f"/applications/{self.receipt['spa']['objectId']}", {
            "spa": {"redirectUris": [expected + "/"]},
        })
        observed_spa = self.graph("get", f"/applications/{self.receipt['spa']['objectId']}")
        if observed_spa.get("spa", {}).get("redirectUris") != [expected + "/"]:
            raise ValueError("Exact SPA redirect readback failed.")
        self.receipt["redirectUri"] = expected + "/"
        self.checkpoint()

    def assignments(self) -> None:
        if not self.authorization.get("assignments"):
            raise ValueError("No explicit principal/role nominations authorized; no default access will be assigned.")
        self.application("api")
        self.application("spa")
        for nomination in self.authorization.get("assignments", []):
            role = nomination["role"]
            if role not in {"tacoma", "statewide"}:
                raise ValueError("Only explicitly approved Operations roles can be assigned.")
            action = nomination.get("action", "assign")
            if action not in {"assign", "remove-api-role"}:
                raise ValueError("Only assignment or explicitly nominated API-role removal is supported.")
            principal = str(uuid.UUID(nomination["principalId"]))
            for resource, app_role in (
                ("api", self.receipt["definitions"][role]), ("spa", str(uuid.UUID(int=0))),
            ):
                target = self.receipt[resource]["servicePrincipalId"]
                if action == "remove-api-role" and resource != "api":
                    continue
                existing = self.collection(f"/servicePrincipals/{target}/appRoleAssignedTo")
                if action == "remove-api-role":
                    for assignment in existing:
                        if assignment["principalId"] == principal and assignment["appRoleId"] == app_role:
                            self.graph("delete", f"/servicePrincipals/{target}/appRoleAssignedTo/{assignment['id']}")
                    observed = self.collection(f"/servicePrincipals/{target}/appRoleAssignedTo")
                    if any(x["principalId"] == principal and x["appRoleId"] == app_role for x in observed):
                        raise ValueError("Temporary API-role removal was not verified.")
                    continue
                if not any(x["principalId"] == principal and x["appRoleId"] == app_role for x in existing):
                    self.graph("post", f"/servicePrincipals/{target}/appRoleAssignedTo", {
                        "principalId": principal, "resourceId": target, "appRoleId": app_role,
                    })
                observed = self.collection(f"/servicePrincipals/{target}/appRoleAssignedTo")
                if not any(x["principalId"] == principal and x["appRoleId"] == app_role for x in observed):
                    raise ValueError("Approved role assignment has not propagated; sign-in remains unverified.")
        self.receipt["assignments"] = self.authorization.get("assignments", [])
        self.receipt["assignmentsStatus"] = "installed-not-signin-validated"
        self.checkpoint()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=sorted(OPERATIONS))
    parser.add_argument("--authorization-file", type=Path)
    args = parser.parse_args()
    scope = scope_from_environment()
    path = args.authorization_file or ROOT / ".installation" / scope["environment"] / "directory-authorization.json"
    if not path.exists():
        raise ValueError("Directory authorization absent; retained read-only preparation does not allow installation.")
    authorization = json.loads(path.read_text())
    validate_authorization(authorization, scope, args.operation, datetime.now(timezone.utc))
    installer = Installer(scope, authorization)
    installer.verify_context()
    if args.operation == "registrations":
        installer.registrations()
    elif args.operation == "redirect":
        installer.redirect(os.environ["APPLICATION_URL"])
    else:
        installer.assignments()
    print(f"Identity {args.operation} captured in scenario-owned tooling; live sign-in remains unverified.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, KeyError) as error:
        print(f"Identity installation failed: {error}", file=sys.stderr)
        sys.exit(1)
