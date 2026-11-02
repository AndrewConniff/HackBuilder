"""Offline identity/runtime-hook checks with synthetic Graph objects, never live directory evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install_reference
import setup_identity as target

SCOPE = {
    "account": "synthetic@example.invalid", "tenantId": "00000000-0000-0000-0000-000000000001",
    "subscriptionId": "00000000-0000-0000-0000-000000000002",
    "resourceGroup": "rg-resto-test", "environment": "resto-test", "region": "centralus",
}


class EntraRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        marker = target.ownership(SCOPE)
        self.receipt = {
            "installed": True, "scope": SCOPE, "ownershipMarker": marker,
            "staffTenantId": SCOPE["tenantId"], "staffAudience": "00000000-0000-0000-0000-000000000004",
            "roleIds": {role: target.role_id(marker, role) for role in target.ROLES},
            "api": {"clientId": "00000000-0000-0000-0000-000000000004",
                    "objectId": "00000000-0000-0000-0000-000000000005",
                    "servicePrincipalId": "00000000-0000-0000-0000-000000000006"},
            "client": {"clientId": "00000000-0000-0000-0000-000000000007",
                       "objectId": "00000000-0000-0000-0000-000000000008",
                       "servicePrincipalId": "00000000-0000-0000-0000-000000000009"},
        }
        self.objects = {}
        self.rows = {}
        self.operator = "00000000-0000-0000-0000-000000000010"
        for kind in ("api", "client"):
            ids = self.receipt[kind]
            roles = [{"value": role, "id": target.role_id(marker, role), "isEnabled": True,
                      "allowedMemberTypes": ["User"]} for role in target.ROLES] if kind == "api" else []
            self.objects[f"/applications/{ids['objectId']}"] = {
                "id": ids["objectId"], "appId": ids["clientId"], "notes": marker, "signInAudience": "AzureADMyOrg",
                "appRoles": roles, "identifierUris": [f"api://{ids['clientId']}"],
                "api": {"requestedAccessTokenVersion": 2, "oauth2PermissionScopes": [
                    {"id": target.role_id(marker, "access_as_user"), "value": "access_as_user", "isEnabled": True}]},
                "requiredResourceAccess": [{"resourceAppId": self.receipt["api"]["clientId"],
                                           "resourceAccess": [{"id": target.role_id(marker, "access_as_user"),
                                                               "type": "Scope"}]}],
                "spa": {"redirectUris": ["https://scenario.example/auth.html"]},
            }
            self.objects[f"/servicePrincipals/{ids['servicePrincipalId']}"] = {
                "id": ids["servicePrincipalId"], "appId": ids["clientId"],
                "appOwnerOrganizationId": SCOPE["tenantId"], "tags": [marker],
                "appRoleAssignmentRequired": True, "accountEnabled": True, "appRoles": roles,
            }
            self.rows[f"/servicePrincipals/{ids['servicePrincipalId']}/appRoleAssignedTo"] = [
                {"principalId": self.operator, "resourceId": ids["servicePrincipalId"],
                 "appRoleId": target.role_id(marker, "Manager") if kind == "api"
                 else "00000000-0000-0000-0000-000000000000"}
            ]
        self.objects["/me?$select=id"] = {"id": self.operator}
        self.worker = target.Installer(SCOPE, ROOT / "evidence" / "unused-offline-receipt.json")
        self.worker.cli = Mock(return_value={
            "id": SCOPE["subscriptionId"], "tenantId": SCOPE["tenantId"],
            "state": "Enabled", "user": {"name": SCOPE["account"]}})
        self.worker.graph = Mock(side_effect=lambda method, path: copy.deepcopy(self.objects[path]))
        self.worker.listing = Mock(side_effect=lambda path: copy.deepcopy(self.rows.get(path.split("?")[0], [])))

    def test_historical_identifiers_remain_byte_compatible(self) -> None:
        retained = json.loads((ROOT / "evidence" / "identity-installation.json").read_text())
        self.assertEqual(retained["ownershipMarker"], target.ownership(retained["scope"]))
        for role, identifier in retained["roleIds"].items():
            self.assertEqual(identifier, target.role_id(retained["ownershipMarker"], role))

    def test_inspection_and_access_verification_are_read_only_and_require_exact_consent(self) -> None:
        objects = self.worker.inspect(self.receipt)
        verify = lambda: target.verify_access(self.worker, self.receipt, objects, "https://scenario.example/auth.html")
        self.assertFalse(verify()["passed"])
        grant = {"clientId": self.receipt["client"]["servicePrincipalId"],
                 "resourceId": self.receipt["api"]["servicePrincipalId"],
                 "principalId": self.operator, "consentType": "Principal", "scope": "access_as_user"}
        self.rows["/oauth2PermissionGrants"] = [grant]
        self.assertTrue(verify()["passed"])
        grant["consentType"] = "AllPrincipals"
        self.assertFalse(verify()["passed"])
        self.assertTrue(all(call.args[0] == "get" for call in self.worker.graph.call_args_list))

    def test_foreign_objects_missing_assignments_and_configuration_drift_fail(self) -> None:
        path = f"/applications/{self.receipt['api']['objectId']}"
        for field, value in (("notes", "unowned"), ("signInAudience", "AzureADMultipleOrgs"), ("appRoles", [])):
            with self.subTest(field=field):
                previous = self.objects[path][field]
                self.objects[path][field] = value
                with self.assertRaises(ValueError):
                    self.worker.inspect(self.receipt)
                self.objects[path][field] = previous
        self.worker.cli.return_value["tenantId"] = "foreign"
        with self.assertRaisesRegex(ValueError, "account/subscription/tenant"):
            self.worker.inspect(self.receipt)

    def test_denied_consent_write_is_never_available_even_with_installation_flag(self) -> None:
        worker = target.Installer(SCOPE, ROOT / "evidence" / "unused.json", authorized=True)
        with patch.object(worker, "cli") as cli, self.assertRaises(PermissionError):
            worker.graph("post", "/oauth2PermissionGrants", {"scope": "access_as_user"})
        cli.assert_not_called()

    def test_scope_and_role_drift_do_not_become_runtime_parameters(self) -> None:
        self.receipt["roleIds"]["Manager"] = self.receipt["api"]["clientId"]
        with self.assertRaisesRegex(ValueError, "role IDs"):
            target.consume(self.receipt, SCOPE["tenantId"], SCOPE["subscriptionId"], SCOPE["environment"], SCOPE["region"])

    def test_redirect_requires_exact_https_origin(self) -> None:
        self.assertEqual("https://scenario.example/auth.html", target.callback("https://scenario.example"))
        for url in ("http://scenario.example", "https://scenario.example/other", "https://scenario.example?secret=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                target.callback(url)

    def test_runtime_hook_requires_current_plan_bound_grant_and_writer(self) -> None:
        digest = hashlib.sha256((ROOT / "scripts" / "reference-installation-plan.json").read_bytes()).hexdigest()
        state = {"projectSlug": ROOT.name, "writer": "offline",
                 "stages": {"local-validation": {"status": "completed"}}, "authorizations": []}
        with patch.dict(os.environ, {"ABCBUILDER_RUN_ID": "offline"}):
            with self.assertRaises(PermissionError):
                install_reference.authorized_scope(state, digest)
            state["authorizations"] = [{"kind": "deployment", "scope": SCOPE | {"installationPlanDigest": digest}}]
            self.assertEqual(SCOPE, install_reference.authorized_scope(state, digest))
            with self.assertRaises(PermissionError):
                install_reference.authorized_scope(state, "changed-plan")
            state["writer"] = "other-worker"
            with self.assertRaises(PermissionError):
                install_reference.authorized_scope(state, digest)


if __name__ == "__main__":
    unittest.main()
