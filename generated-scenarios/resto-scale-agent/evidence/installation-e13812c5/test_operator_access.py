"""Offline checks for bounded, idempotent operator setup; synthetic objects are not deployment evidence."""

import copy
import unittest
from unittest.mock import Mock

import operator_access as target

SCOPE = {
    "account": "synthetic@example.invalid",
    "tenantId": "00000000-0000-0000-0000-000000000001",
    "subscriptionId": "00000000-0000-0000-0000-000000000002",
    "environment": "resto-test", "resourceGroup": "rg-resto-test", "region": "centralus",
}


class OperatorAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.marker = target.ownership(SCOPE)
        self.receipt = {
            "installed": True, "scope": SCOPE, "ownershipMarker": self.marker,
            "staffTenantId": SCOPE["tenantId"],
            "api": {
                "objectId": "00000000-0000-0000-0000-000000000003",
                "clientId": "00000000-0000-0000-0000-000000000004",
                "servicePrincipalId": "00000000-0000-0000-0000-000000000005",
            },
            "client": {
                "objectId": "00000000-0000-0000-0000-000000000006",
                "clientId": "00000000-0000-0000-0000-000000000007",
                "servicePrincipalId": "00000000-0000-0000-0000-000000000008",
            },
            "staffAudience": "00000000-0000-0000-0000-000000000004",
        }
        self.objects = {}
        for kind in ("api", "client"):
            values = self.receipt[kind]
            self.objects[f"/applications/{values['objectId']}"] = {
                "appId": values["clientId"], "notes": self.marker,
            }
            self.objects[f"/servicePrincipals/{values['servicePrincipalId']}"] = {
                "appId": values["clientId"], "appOwnerOrganizationId": SCOPE["tenantId"],
                "tags": [self.marker], "appRoleAssignmentRequired": True,
                "appRoles": [{"id": target.role_id(self.marker, "Manager"), "value": "Manager", "isEnabled": True}],
            }
        self.objects["/me?$select=id,userPrincipalName"] = {
            "id": target.OPERATOR, "userPrincipalName": SCOPE["account"],
        }
        self.objects["/me?$select=id"] = {"id": target.OPERATOR}
        self.rows = {}
        self.worker = Mock(scope=SCOPE)
        self.worker.cli.return_value = {
            "id": SCOPE["subscriptionId"], "tenantId": SCOPE["tenantId"],
            "state": "Enabled", "user": {"name": SCOPE["account"]},
        }
        self.worker.graph.side_effect = self.graph
        self.worker.listing.side_effect = lambda path: copy.deepcopy(self.rows.get(path.split("?")[0], []))

    def graph(self, method: str, path: str, body: dict | None = None) -> dict:
        if method == "get":
            return copy.deepcopy(self.objects[path])
        if method != "post":
            raise AssertionError("No patch/delete or unrelated method is expected.")
        if body["principalId"] != target.OPERATOR:
            raise AssertionError("Assignments and consent must remain operator-only.")
        self.rows.setdefault(path, []).append(copy.deepcopy(body))
        return copy.deepcopy(body)

    def test_setup_is_idempotent_and_operator_only(self) -> None:
        first = target.install(self.worker, self.receipt)
        target.install(self.worker, self.receipt)
        writes = [call for call in self.worker.graph.call_args_list if call.args[0] != "get"]
        self.assertEqual(3, len(writes))
        self.assertEqual(2, len(first["assignments"]))
        self.assertEqual("Principal", first["consent"]["consentType"])
        self.assertEqual("access_as_user", first["consent"]["scope"])
        self.assertTrue(all(call.args[2]["principalId"] == target.OPERATOR for call in writes))
        self.assertTrue(all("?" not in call.args[0] for call in self.worker.listing.call_args_list
                            if "appRoleAssignedTo" in call.args[0]))

    def test_unowned_principal_and_wrong_operator_fail_before_writes(self) -> None:
        for key, field, value in (
            (f"/servicePrincipals/{self.receipt['api']['servicePrincipalId']}", "tags", []),
            ("/me?$select=id,userPrincipalName", "id", "unapproved-operator"),
        ):
            with self.subTest(field=field):
                original = self.objects[key][field]
                self.objects[key][field] = value
                with self.assertRaises(ValueError):
                    target.install(self.worker, self.receipt)
                self.objects[key][field] = original
        self.assertFalse(any(call.args[0] != "get" for call in self.worker.graph.call_args_list))

    def test_denied_operation_is_not_retried(self) -> None:
        self.worker.graph.side_effect = PermissionError("Synthetic Graph authorization denial")
        with self.assertRaises(PermissionError):
            target.install(self.worker, self.receipt)
        self.assertEqual(1, self.worker.graph.call_count)

    def test_guest_upn_does_not_replace_verified_account_or_object_id(self) -> None:
        self.objects["/me?$select=id,userPrincipalName"]["userPrincipalName"] = (
            "synthetic_example.invalid#EXT#@example.onmicrosoft.com"
        )
        self.assertEqual(target.OPERATOR, target.install(self.worker, self.receipt)["operatorId"])
        self.worker.cli.return_value["tenantId"] = "foreign"
        with self.assertRaisesRegex(ValueError, "account/subscription/tenant"):
            target.install(self.worker, self.receipt)

    def test_verification_is_read_only_and_requires_actual_exact_consent(self) -> None:
        self.assertFalse(target.verify(self.worker, self.receipt)["passed"])
        self.assertFalse(any(call.args[0] != "get" for call in self.worker.graph.call_args_list))
        target.install(self.worker, self.receipt)
        self.worker.graph.reset_mock()
        self.assertTrue(target.verify(self.worker, self.receipt)["passed"])
        self.assertFalse(any(call.args[0] != "get" for call in self.worker.graph.call_args_list))
        self.rows["/oauth2PermissionGrants"][0]["consentType"] = "AllPrincipals"
        self.assertFalse(target.verify(self.worker, self.receipt)["passed"])


if __name__ == "__main__":
    unittest.main()
