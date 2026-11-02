"""Exercise installation ordering, output capture and consent failures without cloud or Docker operations."""

import copy
import importlib.util
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("deployment_lifecycle", ROOT / "scripts" / "deployment_lifecycle.py")
LIFECYCLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIFECYCLE)


class DeploymentLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = {
            "ABCBUILDER_RUN_ID": "test-owner",
            "AZURE_ACCOUNT": "offline-test-account",
            "AZURE_SUBSCRIPTION_ID": "offline-subscription",
            "AZURE_TENANT_ID": "offline-tenant",
            "AZURE_RESOURCE_GROUP": "rg-offline", "AZURE_ENV_NAME": "offline",
            "AZURE_LOCATION": "eastus2", "AZURE_PRINCIPAL_ID": "offline-principal",
            "APIM_PUBLISHER_EMAIL": "operator@example.invalid",
        }
        self.scope = {
            key: self.settings[variable] for key, variable in LIFECYCLE.SCOPE_VARIABLES.items()
        } | {
            "directoryWrites": "scenario-owned-secretless-backend-api", "privateExecutionHost": "offline-host",
            "whatIfEvidence": "explicit test receipt, not a real what-if", "estimatedCost": "test estimate only",
        }
        self.project = {
            "projectSlug": "manu-multi-agent", "designConfirmed": True, "writer": "test-owner",
            "stages": {"local-validation": {"status": "completed"}},
            "authorizations": [{"kind": "deployment", "scope": self.scope, "decisionId": "offline-decision"}],
        }

    def test_exact_authorization(self) -> None:
        self.assertEqual(
            "offline-decision", LIFECYCLE.authorize(self.project, self.settings, "OFFLINE-HOST")["decisionId"]
        )

    def test_missing_restricted_and_mismatched_grants_fail(self) -> None:
        mutations = [
            lambda value: value.update(projectSlug="another-project"),
            lambda value: value.update(designConfirmed=False),
            lambda value: value.update(writer="another-owner"),
            lambda value: value["stages"]["local-validation"].update(status="pending"),
            lambda value: value.update(authorizations=[]),
            lambda value: value["authorizations"][0].update(kind="deployment-preparation"),
            lambda value: value["authorizations"][0]["scope"].update(tenantId="another-tenant"),
            lambda value: value["authorizations"][0]["scope"].update(directoryWrites=False),
            lambda value: value["authorizations"][0]["scope"].update(privateExecutionHost="another-host"),
            lambda value: value["authorizations"][0]["scope"].update(whatIfEvidence=""),
            lambda value: value["authorizations"][0]["scope"].update(estimatedCost=""),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                project = copy.deepcopy(self.project)
                mutate(project)
                with self.assertRaises(ValueError):
                    LIFECYCLE.authorize(project, self.settings, "offline-host")

    def test_missing_targets_and_wrong_group_fail(self) -> None:
        for field in (*LIFECYCLE.SCOPE_VARIABLES.values(), "AZURE_RESOURCE_GROUP"):
            with self.subTest(field=field):
                settings = self.settings | {field: "" if field != "AZURE_RESOURCE_GROUP" else "unrelated"}
                with self.assertRaises(ValueError):
                    LIFECYCLE.authorize(self.project, settings, "offline-host")

    def test_canonical_denial_precedes_all_cloud_commands(self) -> None:
        project = self.project | {"authorizations": []}
        environment = self.settings | {"ABCBUILDER_WORKFLOW_HELPER": str(ROOT / "scripts" / "portal_workflow.py")}
        with patch.dict(os.environ, environment), patch.object(
            LIFECYCLE, "execute", return_value=json.dumps(project)
        ) as execute, patch.object(LIFECYCLE.socket, "gethostname", return_value="offline-host"), patch.object(
            LIFECYCLE.Path, "is_file", return_value=True
        ):
            with self.assertRaisesRegex(ValueError, "No exact-target"):
                LIFECYCLE.guard()
            self.assertEqual(1, execute.call_count)
            self.assertEqual("read", execute.call_args.args[0][-1])

    def test_azd_account_mismatch_stops_before_directory_operations(self) -> None:
        environment = self.settings | {"ABCBUILDER_WORKFLOW_HELPER": str(ROOT / "scripts" / "portal_workflow.py")}
        replies = [
            json.dumps(self.project),
            json.dumps({
                "id": self.settings["AZURE_SUBSCRIPTION_ID"], "tenantId": self.settings["AZURE_TENANT_ID"],
                "user": {"name": self.settings["AZURE_ACCOUNT"], "type": "user"},
            }),
            "Logged in to Azure as another-account",
        ]
        with patch.dict(os.environ, environment), patch.object(
            LIFECYCLE, "execute", side_effect=replies
        ) as execute, patch.object(LIFECYCLE.socket, "gethostname", return_value="offline-host"), patch.object(
            LIFECYCLE.Path, "is_file", return_value=True
        ):
            with self.assertRaisesRegex(ValueError, "same authorized account"):
                LIFECYCLE.guard()
            self.assertEqual(3, execute.call_count)

    def test_private_dns_failure_precedes_socket_or_installation(self) -> None:
        for address in ("8.8.8.8", "203.0.113.1", "127.0.0.1", "169.254.169.254", "::1"):
            with self.subTest(address=address):
                with patch.object(LIFECYCLE.socket, "getaddrinfo", return_value=[
                    (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
                ]), patch.object(LIFECYCLE.socket, "create_connection") as connect:
                    with self.assertRaises(ValueError):
                        LIFECYCLE.private_tls("https://offline.example.invalid")
                    connect.assert_not_called()

    def test_failed_tool_is_explicit(self) -> None:
        completed = type("Completed", (), {"returncode": 7, "stderr": "explicit test failure", "stdout": ""})()
        with patch.object(LIFECYCLE.shutil, "which", return_value="offline-tool"), patch.object(
            LIFECYCLE.subprocess, "run", return_value=completed
        ):
            with self.assertRaisesRegex(RuntimeError, "explicit test failure"):
                LIFECYCLE.execute(["az", "deployment"])

    def test_before_reuses_generated_identity_and_workload_without_reset(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".resume-evidence") as directory:
            installation = Path(directory)
            (installation / "backend-identity.json").write_text(json.dumps({
                "tenantId": self.settings["AZURE_TENANT_ID"],
                "subscriptionId": self.settings["AZURE_SUBSCRIPTION_ID"], "backendClientId": "installed-client",
            }))
            parameters = {
                key: {"value": self.settings[variable]} for key, variable in {
                    "environment": "AZURE_ENV_NAME", "location": "AZURE_LOCATION",
                    "principalId": "AZURE_PRINCIPAL_ID",
                }.items()
            } | {key: {"value": "installed-client" if key == "backendClientId" else "installed-output"}
                 for key in LIFECYCLE.workload_variables()}
            (installation / "workload.parameters.json").write_text(json.dumps({"parameters": parameters}))
            with patch.dict(os.environ, self.settings), patch.object(
                LIFECYCLE, "INSTALLATION", installation
            ), patch.object(
                LIFECYCLE, "guard"
            ), patch.object(LIFECYCLE, "execute"), patch.object(LIFECYCLE, "set_values") as set_values:
                LIFECYCLE.before()
                self.assertEqual("workload", set_values.call_args.args[0]["DEPLOYMENT_PHASE"])
                self.assertEqual("installed-client", set_values.call_args.args[0]["BACKEND_CLIENT_ID"])

    def test_after_captures_installer_output_shapes_in_dependency_order(self) -> None:
        commands = []
        with tempfile.TemporaryDirectory(dir=ROOT / ".resume-evidence") as directory:
            installation = Path(directory)
            (installation / "backend-identity.json").write_text(json.dumps({"backendClientId": "installed-client"}))
            values = {
                "AZURE_AI_PROJECT_ENDPOINT": "https://offline.services.ai.azure.com/api/projects/offline",
                "AZURE_AI_MODEL_DEPLOYMENT": "offline-model",
                "FIXTURE_BLOB_ENDPOINT": "https://offline.blob.core.windows.net",
                "SIGNING_KEY_URI": "https://offline.vault.azure.net/keys/offline",
                "AZURE_CONTAINER_REGISTRY_NAME": "offlineregistry",
                "AZURE_CONTAINER_REGISTRY_ENDPOINT": "offlineregistry.azurecr.io",
            }
            digest = "b" * 64
            outputs = {
                "AZURE_CONTAINER_APP_NAME": {"value": "offline-app"},
                "APP_PUBLIC_URL": {"value": "https://offline.example.invalid"},
            }

            def execute(command: list[str], **_kwargs: object) -> str:
                commands.append(command)
                if command[:3] == ["azd", "env", "get-values"]:
                    return json.dumps(values)
                if command[:4] == ["az", "role", "definition", "list"]:
                    return json.dumps([{"roleType": "BuiltInRole", "name": "1" * 36}])
                if command[:3] == ["docker", "image", "inspect"]:
                    return json.dumps([{
                        "Os": "linux", "Architecture": "amd64", "Config": {"User": "1654"}, "Id": "sha256:" + "a" * 64,
                        "RepoDigests": ["offlineregistry.azurecr.io/mobility-commercial@sha256:" + digest],
                    }])
                if command[:2] == ["dotnet", "run"]:
                    (installation / "installation.json").write_text(json.dumps({
                        "tenantId": self.settings["AZURE_TENANT_ID"],
                        "subscriptionId": self.settings["AZURE_SUBSCRIPTION_ID"],
                        "fixtureManifestSha256": "c" * 64, "signingKeyVersion": "d" * 32,
                        "agents": [
                            {"name": name, "version": str(index + 1)}
                            for index, name in enumerate(("sales-fit", "marketing-claims", "handoff-coordinator"))
                        ],
                    }))
                if command[:4] == ["az", "deployment", "group", "create"]:
                    return json.dumps({"properties": {"provisioningState": "Succeeded", "outputs": outputs}})
                return ""

            with patch.dict(os.environ, self.settings), patch.object(
                LIFECYCLE, "INSTALLATION", installation
            ), patch.object(
                LIFECYCLE, "guard", return_value=self.project["authorizations"][0]
            ), patch.object(LIFECYCLE, "private_tls", return_value={"test": "offline"}), patch.object(
                LIFECYCLE, "execute", side_effect=execute
            ), patch.object(LIFECYCLE, "set_values") as set_values, patch("builtins.print"):
                LIFECYCLE.after()
                parameters = json.loads((installation / "workload.parameters.json").read_text())["parameters"]
                self.assertEqual(digest, parameters["imageDigest"]["value"])
                self.assertEqual("3", parameters["coordinatorAgentVersion"]["value"])
                self.assertEqual("installed-client", parameters["backendClientId"]["value"])
                receipt = json.loads((installation / "deployment.json").read_text())
                self.assertEqual("pending", receipt["liveAcceptance"])
                self.assertEqual("workload", set_values.call_args.args[0]["DEPLOYMENT_PHASE"])
                build = next(index for index, command in enumerate(commands) if command[:2] == ["docker", "build"])
                push = next(index for index, command in enumerate(commands) if command[:2] == ["docker", "push"])
                install = next(index for index, command in enumerate(commands) if command[:2] == ["dotnet", "run"])
                deploy = next(index for index, command in enumerate(commands)
                              if command[:4] == ["az", "deployment", "group", "create"])
                self.assertLess(build, push)
                self.assertLess(push, install)
                self.assertLess(install, deploy)
                self.assertEqual(self.settings["AZURE_SUBSCRIPTION_ID"], commands[deploy][5])


if __name__ == "__main__":
    unittest.main()
