"""Verify identity consent/ownership boundaries without any CLI or cloud calls."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scenario_identity.py"
SPEC = importlib.util.spec_from_file_location("scenario_identity", SCRIPT)
identity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(identity)


class IdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.values = {variable: f"test-{field}" for field, variable in identity.TARGETS.items()}
        self.scope = {field: self.values[variable] for field, variable in identity.TARGETS.items()}
        self.state = {
            "projectSlug": "hospitality-feedback", "designConfirmed": True,
            "authorizations": [], "decisions": [], "setupBlocker": None,
        }

    def grant(self) -> None:
        self.state["authorizations"] = [{
            "kind": "deployment", "scope": {**self.scope, "directoryActions": identity.DIRECTORY_ACTIONS},
        }]

    def test_local_consent_and_free_text_are_not_directory_permission(self) -> None:
        self.state["history"] = [{"message": "Confirm preserved design and continue local validation"}]
        with self.assertRaisesRegex(ValueError, "Exact deployment consent"):
            identity.authorize(self.state, self.values)

    def test_read_only_preparation_is_not_directory_permission(self) -> None:
        self.grant()
        self.state["authorizations"][0]["kind"] = "deployment-preparation"
        with self.assertRaises(ValueError):
            identity.authorize(self.state, self.values)

    def test_arm_only_grant_is_not_directory_permission(self) -> None:
        self.grant()
        self.state["authorizations"][0]["scope"]["directoryActions"] = []
        with self.assertRaises(ValueError):
            identity.authorize(self.state, self.values)

    def test_exact_covered_scope_passes(self) -> None:
        self.grant()
        self.assertEqual(self.scope, identity.authorize(self.state, self.values))

    def test_changed_tenant_or_environment_rejected(self) -> None:
        self.grant()
        for variable in ("AZURE_TENANT_ID", "AZURE_ENV_NAME"):
            with self.subTest(variable=variable), self.assertRaises(ValueError):
                identity.authorize(self.state, {**self.values, variable: "other"})

    def test_blocker_or_pending_decision_rejected(self) -> None:
        self.grant()
        self.state["decisions"] = [{"status": "pending"}]
        with self.assertRaises(ValueError):
            identity.authorize(self.state, self.values)
        self.state["decisions"] = []
        self.state["setupBlocker"] = {"kind": "host-permission"}
        with self.assertRaises(ValueError):
            identity.authorize(self.state, self.values)

    def test_unowned_application_never_adopted_or_duplicated(self) -> None:
        with patch.object(identity, "graph", return_value={"value": [{"id": "unrelated", "tags": []}]}) as graph:
            with self.assertRaisesRegex(ValueError, "ownership conflict"):
                identity.owned_application("same-name", "marker", True, {})
            self.assertEqual(1, graph.call_count)
            self.assertEqual("GET", graph.call_args.args[0])

    def test_interrupted_creation_reuses_owned_object(self) -> None:
        app = {"id": "owned", "appId": "client", "tags": ["marker"], "signInAudience": "AzureADMyOrg"}
        with patch.object(identity, "graph", return_value={"value": [app]}) as graph:
            self.assertEqual(app, identity.owned_application("same-name", "marker", True, {}))
            self.assertEqual(1, graph.call_count)

    def test_duplicate_or_truncated_matches_rejected(self) -> None:
        for response in (
            {"value": [{"tags": ["marker"]}, {"tags": ["marker"]}]},
            {"value": [], "@odata.nextLink": "more"},
        ):
            with self.subTest(response=response), patch.object(identity, "graph", return_value=response):
                with self.assertRaises(ValueError):
                    identity.owned_application("same-name", "marker", True, {})

    def test_assignment_policy_never_weakened(self) -> None:
        response = {"value": [{"id": "owned", "tags": ["marker"], "appRoleAssignmentRequired": True}]}
        with patch.object(identity, "graph", return_value=response) as graph:
            with self.assertRaisesRegex(ValueError, "no policy weakening"):
                identity.service_principal({"appId": "client"}, "marker", True)
            self.assertEqual(1, graph.call_count)

    def test_verification_does_not_repair_drift(self) -> None:
        with patch.object(identity, "graph") as graph:
            with self.assertRaises(ValueError):
                identity.configure({"id": "owned", "identifierUris": []}, {"identifierUris": ["api://client"]}, False)
            graph.assert_not_called()


if __name__ == "__main__":
    unittest.main()
