"""Local-only installer/retry/security contracts; never call Graph or provision resources."""

import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_identity", ROOT / "scripts" / "install_identity.py")
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)
SCOPE = {
    "account": "test@example.invalid", "subscriptionId": str(uuid.uuid4()), "tenantId": str(uuid.uuid4()),
    "environment": "equip-test", "resourceGroup": "rg-equip-test", "region": "centralus",
}


class FakeInstaller(identity.Installer):
    def __init__(self, directory: Path) -> None:
        super().__init__(SCOPE, {"authorizationReference": "local-unit-test"})
        self.directory = directory
        self.receipt_path = directory / "identity.json"
        self.owner = str(uuid.uuid4())
        self.apps = {}
        self.principals = {}
        self.mutations = []
        self.exported = False

    def export(self) -> None:
        self.exported = True

    def graph(self, method: str, route: str, body: dict | None = None) -> dict:
        parsed = urlparse(route)
        parts = parsed.path.strip("/").split("/")
        store = self.apps if parts[0] == "applications" else self.principals
        if method == "get" and len(parts) == 1:
            query = parse_qs(parsed.query)["$filter"][0]
            key, value = query.split(" eq ")
            return {"value": [copy.deepcopy(x) for x in store.values() if x.get(key) == value.strip("'")]}
        if method == "get" and parts[-1] == "owners":
            return {"value": [{"id": self.owner}]}
        if method == "get":
            return copy.deepcopy(store[parts[1]])
        self.mutations.append((method, route, copy.deepcopy(body)))
        if method == "post":
            item = {"id": str(uuid.uuid4()), **body}
            if parts[0] == "applications":
                item["appId"] = str(uuid.uuid4())
            else:
                item["appOwnerOrganizationId"] = SCOPE["tenantId"]
            store[item["id"]] = item
            return copy.deepcopy(item)
        if parts[0] == "applications":
            installed_scopes = {
                scope["id"] for scope in store[parts[1]].get("api", {}).get("oauth2PermissionScopes", [])
            }
            for client in body.get("api", {}).get("preAuthorizedApplications", []):
                if not set(client["delegatedPermissionIds"]) <= installed_scopes:
                    raise ValueError("Graph requires scopes installed before preauthorization.")
        store[parts[1]].update(copy.deepcopy(body))
        return {}


class PreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".worker")
        self.addCleanup(self.temporary.cleanup)
        self.installer = FakeInstaller(Path(self.temporary.name))

    def test_missing_cloud_authorization_is_not_local_consent(self) -> None:
        with self.assertRaisesRegex(ValueError, "Separate exact-scope"):
            identity.validate_authorization({}, SCOPE, "registrations", datetime.now(timezone.utc))

    def test_exact_target_and_operation_required(self) -> None:
        now = datetime.now(timezone.utc)
        grant = {
            "scope": SCOPE, "directoryOperations": ["registrations"], "approvedBy": "test",
            "authorizationReference": "test", "expiresAtUtc": (now + timedelta(minutes=5)).isoformat(),
        }
        identity.validate_authorization(grant, SCOPE, "registrations", now)
        for target, operation in (({**SCOPE, "region": "westus2"}, "registrations"), (SCOPE, "assignments")):
            with self.assertRaises(ValueError):
                identity.validate_authorization(grant, target, operation, now)

    def test_expired_grant_is_rejected(self) -> None:
        grant = {
            "scope": SCOPE, "directoryOperations": ["registrations"], "approvedBy": "test",
            "authorizationReference": "test", "expiresAtUtc": "2020-01-01T00:00:00+00:00",
        }
        with self.assertRaisesRegex(ValueError, "expired"):
            identity.validate_authorization(grant, SCOPE, "registrations", datetime.now(timezone.utc))

    def test_retry_reuses_all_real_ids(self) -> None:
        self.installer.registrations()
        first = copy.deepcopy(self.installer.receipt)
        posts = sum(x[0] == "post" for x in self.installer.mutations)
        self.installer.registrations()
        self.assertEqual(4, posts)
        self.assertEqual(posts, sum(x[0] == "post" for x in self.installer.mutations))
        for role in ("api", "spa"):
            self.assertEqual(first[role], self.installer.receipt[role])
        self.assertEqual(first["definitions"], self.installer.receipt["definitions"])
        self.assertTrue(self.installer.exported)
        self.assertEqual("pending-explicit-principal-nominations", self.installer.receipt["assignmentsStatus"])

    def test_partial_creation_recovers_without_duplicate(self) -> None:
        app = self.installer.application("api")
        self.installer.receipt.pop("api")
        self.assertEqual(app["id"], self.installer.application("api")["id"])
        self.assertEqual(1, len(self.installer.apps))

    def test_scope_is_persisted_before_preauthorization(self) -> None:
        self.installer.registrations()
        updates = [
            body["api"] for method, route, body in self.installer.mutations
            if method == "patch" and "api" in body
        ]
        self.assertEqual(2, len(updates))
        self.assertNotIn("preAuthorizedApplications", updates[0])
        self.assertIn("preAuthorizedApplications", updates[1])
        self.assertEqual(updates[0]["oauth2PermissionScopes"], updates[1]["oauth2PermissionScopes"])

    def test_missing_scope_readback_blocks_preauthorization(self) -> None:
        original = self.installer.graph

        def without_scope(method: str, route: str, body: dict | None = None) -> dict:
            result = original(method, route, body)
            if method == "get" and result.get("displayName") == "equip-test-api" and "api" in result:
                result["api"]["oauth2PermissionScopes"] = []
            return result

        with patch.object(self.installer, "graph", side_effect=without_scope):
            with self.assertRaisesRegex(ValueError, "API read scope is not installed"):
                self.installer.registrations()
        self.assertFalse(self.installer.principals)

    def test_unowned_same_name_never_adopted(self) -> None:
        self.installer.apps["foreign"] = {"id": "foreign", "displayName": "equip-test-api", "tags": []}
        with self.assertRaisesRegex(ValueError, "unowned"):
            self.installer.application("api")
        self.assertEqual([], self.installer.mutations)

    def test_unexpected_credentials_fail_closed(self) -> None:
        app = self.installer.application("api")
        self.installer.apps[app["id"]]["passwordCredentials"] = [{"keyId": "test"}]
        with self.assertRaisesRegex(ValueError, "Unexpected credentials"):
            self.installer.application("api")

    def test_no_default_statewide_assignment(self) -> None:
        with self.assertRaisesRegex(ValueError, "No explicit principal"):
            self.installer.assignments()
        self.assertEqual([], self.installer.mutations)

    def test_temporary_role_removal_is_exact_and_preserves_spa_access(self) -> None:
        principal, role, target = (str(uuid.uuid4()) for _ in range(3))
        self.installer.authorization["assignments"] = [
            {"principalId": principal, "role": "tacoma", "action": "remove-api-role"}]
        self.installer.receipt["definitions"]["tacoma"] = role
        self.installer.receipt["api"] = {"servicePrincipalId": target}
        self.installer.receipt["spa"] = {"servicePrincipalId": "unchanged-spa"}
        with patch.object(self.installer, "application"), patch.object(
            self.installer, "collection", side_effect=[
                [{"id": "temporary-role", "principalId": principal, "appRoleId": role},
                 {"id": "other-user", "principalId": str(uuid.uuid4()), "appRoleId": role}], []]
        ), patch.object(self.installer, "graph") as graph:
            self.installer.assignments()
        graph.assert_called_once_with(
            "delete", f"/servicePrincipals/{target}/appRoleAssignedTo/temporary-role")

    def test_registration_contract_has_no_graph_permission(self) -> None:
        self.installer.registrations()
        api = self.installer.apps[self.installer.receipt["api"]["objectId"]]
        spa = self.installer.apps[self.installer.receipt["spa"]["objectId"]]
        self.assertEqual(2, api["api"]["requestedAccessTokenVersion"])
        self.assertEqual("Admin", api["api"]["oauth2PermissionScopes"][0]["type"])
        self.assertEqual(api["appId"], spa["requiredResourceAccess"][0]["resourceAppId"])
        self.assertEqual(["Scope"], [x["type"] for x in spa["requiredResourceAccess"][0]["resourceAccess"]])
        self.assertTrue(all(x["appRoleAssignmentRequired"] for x in self.installer.principals.values()))
        self.assertNotIn("spa", spa)
        self.assertFalse(spa["isFallbackPublicClient"])

    def test_plaintext_azd_output_is_not_json(self) -> None:
        result = type("Result", (), {"returncode": 0, "stdout": "Environment updated\n", "stderr": ""})()
        with patch.object(identity.shutil, "which", return_value="azd"), patch.object(
            identity.subprocess, "run", return_value=result,
        ):
            self.assertEqual("Environment updated\n", identity.command(["azd", "env", "set"], json_output=False))

    def test_redirect_uses_actual_arm_output_and_readback(self) -> None:
        self.installer.registrations()
        site_id = (
            f"/subscriptions/{SCOPE['subscriptionId']}/resourceGroups/"
            f"{SCOPE['resourceGroup']}/providers/Microsoft.Web/sites/owned"
        )
        with patch.dict(identity.os.environ, {"AZURE_WEB_RESOURCE_ID": site_id}), patch.object(
            identity, "command", return_value={"id": site_id, "defaultHostName": "owned.azurewebsites.net"},
        ):
            with self.assertRaisesRegex(ValueError, "actual ARM"):
                self.installer.redirect("https://other.azurewebsites.net")
            self.installer.redirect("https://owned.azurewebsites.net")
        self.assertEqual("https://owned.azurewebsites.net/", self.installer.receipt["redirectUri"])

    def test_generated_ids_flow_to_exact_azd_environment(self) -> None:
        self.installer.registrations()
        self.installer.receipt["installerObjectId"] = self.installer.owner
        calls = []

        def capture(arguments: list[str], **kwargs: object) -> list | str:
            calls.append(arguments)
            if arguments[:3] == ["az", "role", "definition"]:
                name = arguments[arguments.index("--name") + 1]
                return [{"name": str(uuid.uuid4()), "roleName": name}]
            return "Environment updated"

        with patch.object(identity, "command", side_effect=capture):
            identity.Installer.export(self.installer)
        updates = [x for x in calls if x[0] == "azd"]
        self.assertEqual(6, len(updates))
        self.assertTrue(all(x[-2:] == ["--environment", SCOPE["environment"]] for x in updates))
        self.assertIn(
            ["azd", "env", "set", "EQUIP_API_CLIENT_ID", self.installer.receipt["api"]["clientId"],
             "--environment", SCOPE["environment"]],
            updates,
        )

    def test_endpoint_and_auth_producer_consumer_order(self) -> None:
        executable = shutil.which("az")
        self.assertIsNotNone(executable, "Azure CLI Bicep is required for the current-template contract.")
        compiled = Path(self.temporary.name) / "main.json"
        result = subprocess.run(
            [executable, "bicep", "build", "--no-restore", "--file", str(ROOT / "infra" / "main.bicep"),
             "--outfile", str(compiled)],
            capture_output=True, text=True, encoding="utf-8", check=False, timeout=180,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        template = json.loads(compiled.read_text(encoding="utf-8"))
        resources = template["resources"]
        registry_assignments = json.dumps(resources["hub"]["properties"]["parameters"]["roleAssignments"])
        self.assertIn("parameters('principalId')", registry_assignments)
        self.assertIn("4ea46cd5-c1b2-4a8e-910b-273211f9ce47", registry_assignments)
        self.assertIn("User", registry_assignments)
        self.assertIn("empty(parameters('principalId'))", registry_assignments)
        app_text = json.dumps(resources["apps"])
        self.assertNotIn("parameters('apiClientId')", app_text)
        self.assertNotIn("parameters('spaClientId')", app_text)
        endpoint = resources["cleanerEndpoint"]["properties"]["parameters"]
        self.assertEqual(["sites"], endpoint["privateLinkServiceConnections"]["value"][0]["properties"]["groupIds"])
        self.assertIn("appNames", json.dumps(endpoint["privateLinkServiceConnections"]))
        self.assertIn("cleanerEndpoint", json.dumps(template["outputs"]["CLEANER_PRIVATE_ENDPOINT_ID"]))
        self.assertIn("apps", json.dumps(resources["runtimeConfiguration"]["dependsOn"]))
        assignments = resources["agentAccess"]["properties"]["template"]["resources"]
        self.assertTrue(any("parameters('runtimeRoleId')" in json.dumps(x) for x in assignments))
        self.assertEqual(["apps", "dns", "network"], sorted(resources["cleanerEndpoint"]["dependsOn"]))


if __name__ == "__main__":
    unittest.main()
