"""Verify prerequisite detection and opt-in setup without installing host software."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_prerequisites as prerequisites

ROOT = Path(__file__).resolve().parents[2]


class PrerequisiteChecksTests(unittest.TestCase):
    def test_k6_is_checked_only_for_selected_load_tests_and_gates_validation(self) -> None:
        profile = prerequisites.profiles.plan(["foundry"], load_tests=True)
        self.assertEqual(["local-validation"], next(
            item["stages"] for item in prerequisites.planned_checks(profile) if item["id"] == "k6"
        ))
        checks = [
            prerequisites.check(key, key, True, "Synthetic ready")
            for key in {key for keys in profile["stages"].values() for key in keys} if key != "k6"
        ]
        with (
            patch.object(prerequisites, "build_report", return_value={"checks": checks}),
            patch.object(prerequisites, "tool_check", return_value=
                         prerequisites.check("k6", "k6", False, "Missing")) as tool,
        ):
            report = prerequisites.service_report(["foundry"], load_tests=True)
        tool.assert_called_once()
        self.assertEqual([], report["blockedStages"]["application"])
        self.assertEqual(["k6"], report["blockedStages"]["local-validation"])
        self.assertNotIn("k6", prerequisites.profiles.plan(["foundry"])["stages"]["local-validation"])

    @unittest.skipUnless(os.name == "nt", "Windows k6 installation")
    def test_existing_k6_is_added_to_child_path_without_host_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / "programs" / "k6" / "k6.exe"
            executable.parent.mkdir(parents=True)
            executable.touch()
            with patch.dict(os.environ, {"PATH": "", "ProgramFiles": str(root / "programs")}):
                environment = prerequisites.execution_environment(root)
                self.assertEqual("", os.environ["PATH"])
            self.assertEqual(executable, Path(shutil.which("k6", path=environment["PATH"])))

    def test_manifest_declares_load_tests_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "generated-scenarios" / "example" / "scenario-manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"validationTools": ["k6"]}', encoding="utf-8")
            self.assertTrue(prerequisites.profiles.requires_load_tests(root, "example"))
            manifest.write_text('{"validationTools": "k6"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "validationTools"):
                prerequisites.profiles.requires_load_tests(root, "example")

    def test_worker_cache_trust_is_scoped_and_does_not_create_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            local = home / "AppData" / "Local"
            with (
                patch.object(prerequisites.Path, "home", return_value=home),
                patch.dict(os.environ, {
                    "LOCALAPPDATA": str(local), "NUGET_PACKAGES": "", "PLAYWRIGHT_BROWSERS_PATH": "",
                }),
            ):
                directories = prerequisites.worker_cache_directories(Path(temp) / "repo")
            self.assertEqual(
                [(home / ".nuget" / "packages").resolve(), (local / "ms-playwright").resolve()], directories,
            )
            self.assertFalse(home.exists())

    def test_worker_cache_overrides_do_not_expand_approved_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            for variable in ("NUGET_PACKAGES", "PLAYWRIGHT_BROWSERS_PATH"):
                with (
                    self.subTest(variable=variable),
                    patch.dict(os.environ, {
                        "NUGET_PACKAGES": "", "PLAYWRIGHT_BROWSERS_PATH": "", variable: str(Path(temp) / "other"),
                    }),
                    self.assertRaisesRegex(ValueError, "outside approved"),
                ):
                    prerequisites.worker_cache_directories(root)
            with patch.dict(os.environ, {
                "NUGET_PACKAGES": str(root / ".packages"), "PLAYWRIGHT_BROWSERS_PATH": "0",
            }):
                self.assertEqual(2, len(prerequisites.worker_cache_directories(root)))

    def test_nuget_probe_uses_normal_powershell_tls_and_bounded_metadata_validation(self) -> None:
        with (
            patch.object(prerequisites.shutil, "which", return_value="pwsh"),
            patch.object(prerequisites, "run_command", return_value=(0, "Metadata verified")) as run,
        ):
            result = prerequisites.nuget_check()
        self.assertTrue(result["ok"])
        command = run.call_args.args[0]
        self.assertEqual(["pwsh", "-NoProfile", "-NonInteractive", "-Command"], command[:4])
        self.assertIn("-TimeoutSec 30", command[4])
        self.assertIn(prerequisites.NUGET_METADATA_URL, command[4])
        self.assertIn("PackageBaseAddress/3.0.0", command[4])
        self.assertNotIn("api.nuget.org", command[4])
        self.assertEqual(75, run.call_args.kwargs["timeout"])
        self.assertIn("$metadata.versions -is [array]", command[4])
        self.assertNotIn("SkipCertificateCheck", command[4])
        self.assertNotIn("SecurityProtocol", command[4])
        self.assertIn("metadata only", result["detail"])

    def test_repository_nuget_sources_use_only_the_approved_proxy(self) -> None:
        import xml.etree.ElementTree as ET

        sources = ET.parse(ROOT / "NuGet.Config").getroot().find("packageSources")
        self.assertEqual(["clear", "add"], [entry.tag for entry in sources])
        self.assertEqual(
            {"key": "MicrosoftPackageFeedProxy", "value": prerequisites.NUGET_METADATA_URL},
            sources.find("add").attrib,
        )

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell required for local probe fixtures")
    def test_nuget_script_validates_feed_and_metadata_without_network(self) -> None:
        for index, metadata, ready in (
            ('{"resources":[{"@type":"PackageBaseAddress/3.0.0","@id":"https://feed.test/flat/"}]}',
             '{"versions":["1.0.0"]}', True),
            ('{"resources":[]}', '{"versions":["1.0.0"]}', False),
            ('{"resources":[{"@type":"PackageBaseAddress/3.0.0","@id":"http://feed.test/flat/"}]}',
             '{"versions":["1.0.0"]}', False),
            ('{"resources":[{"@type":"PackageBaseAddress/3.0.0","@id":"https://feed.test/flat/"}]}',
             '{"versions":[3]}', False),
        ):
            with self.subTest(index=index, metadata=metadata):
                fixture = (
                    "function Invoke-RestMethod { param($Uri, $TimeoutSec, $ErrorAction) "
                    f"if ($Uri -eq '{prerequisites.NUGET_METADATA_URL}') "
                    f"{{ '{index}' | ConvertFrom-Json }} else {{ '{metadata}' | ConvertFrom-Json }} }}; "
                )
                code, output = prerequisites.run_command(
                    ["pwsh", "-NoProfile", "-NonInteractive", "-Command", fixture + prerequisites.NUGET_SMOKE],
                )
                self.assertEqual(ready, code == 0, output)

    def test_nuget_probe_failures_remain_setup_errors_without_install_or_retry(self) -> None:
        for message in ("Remote TLS HandshakeFailure", "Operation timed out", "Malformed metadata response"):
            with (
                self.subTest(message=message),
                patch.object(prerequisites.shutil, "which", return_value="pwsh"),
                patch.object(prerequisites, "run_command", return_value=(1, message)) as run,
            ):
                result = prerequisites.nuget_check()
                self.assertFalse(result["ok"])
                self.assertIn(message, result["detail"])
                self.assertIn("Do not disable certificate validation", result["fix"])
                run.assert_called_once()

    def test_nuget_probe_missing_powershell_does_not_claim_network_success(self) -> None:
        with (
            patch.object(prerequisites.shutil, "which", return_value=None),
            patch.object(prerequisites, "run_command") as run,
        ):
            result = prerequisites.nuget_check()
        self.assertFalse(result["ok"])
        self.assertIn("probe was not run", result["detail"])
        run.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows installation locations")
    def test_execution_environment_resolves_existing_tools_without_changing_host_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            programs = root / "programs"
            graphviz = programs / "Graphviz" / "bin" / "dot.exe"
            dotnet = programs / "dotnet" / "dotnet.exe"
            for executable in (graphviz, dotnet):
                executable.parent.mkdir(parents=True)
                executable.touch()
            with patch.dict(os.environ, {"PATH": "", "ProgramFiles": str(programs)}):
                before = dict(os.environ)
                environment = prerequisites.execution_environment(root)
                self.assertEqual(before, dict(os.environ))
                self.assertEqual(graphviz, Path(shutil.which("dot", path=environment["PATH"])))
                self.assertEqual(dotnet, Path(shutil.which("dotnet", path=environment["PATH"])))
                self.assertEqual(environment["PATH"], prerequisites.execution_environment(root)["PATH"])

    @unittest.skipUnless(os.name == "nt", "Windows installation locations")
    def test_execution_environment_preserves_selected_tools_and_does_not_invent_installations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = root / "selected"
            selected.mkdir()
            (selected / "dot.exe").touch()
            with patch.dict(os.environ, {"PATH": str(selected), "ProgramFiles": str(root / "absent")}):
                environment = prerequisites.execution_environment(root)
            self.assertEqual(str(selected), environment["PATH"])
            self.assertNotIn(str(root / "absent"), environment["PATH"])

    def tool(self, identifier: str) -> tuple:
        return next(item for item in prerequisites.TOOLS if item[0] == identifier)

    def test_missing_executable_is_an_explicit_failure(self) -> None:
        with patch.object(prerequisites.shutil, "which", return_value=None):
            result = prerequisites.tool_check(self.tool("graphviz"))
        self.assertFalse(result["ok"])
        self.assertEqual("Graphviz.Graphviz", result["winget"])
        self.assertIn("PATH", result["detail"])

    def test_dotnet_requires_stable_sdk_10_not_runtime_or_other_major(self) -> None:
        for output, ready in (
            ("Microsoft.NETCore.App 10.0.1 [runtime]", False),
            ("9.0.100 [sdk]\n11.0.100 [sdk]", False),
            ("10.0.100-preview.7 [sdk]", False),
            ("9.0.100 [sdk]\n10.0.402 [C:\\Program Files\\dotnet\\sdk]", True),
        ):
            with (
                self.subTest(output=output),
                patch.object(prerequisites.shutil, "which", return_value="dotnet"),
                patch.object(prerequisites, "run_command", return_value=(0, output)),
            ):
                self.assertEqual(ready, prerequisites.tool_check(self.tool("dotnet"))["ok"])

    def test_failed_version_probe_never_passes(self) -> None:
        with (
            patch.object(prerequisites.shutil, "which", return_value="dotnet"),
            patch.object(prerequisites, "run_command", return_value=(7, "10.0.100 [sdk]")),
        ):
            self.assertFalse(prerequisites.tool_check(self.tool("dotnet"))["ok"])

    def test_graphviz_must_identify_itself(self) -> None:
        with (
            patch.object(prerequisites.shutil, "which", return_value="dot"),
            patch.object(prerequisites, "run_command", return_value=(0, "unrelated dot command")),
        ):
            self.assertFalse(prerequisites.tool_check(self.tool("graphviz"))["ok"])

    def test_docker_distinguishes_missing_cli_from_a_stopped_or_wrong_engine(self) -> None:
        spec = ("docker", "Docker Linux engine", "docker", ["info"], None, "Docker.DockerDesktop")
        with patch.object(prerequisites.shutil, "which", return_value=None):
            result = prerequisites.tool_check(spec)
            self.assertFalse(result["installed"])
            self.assertEqual("not-found", result["state"])
        for code, output, ready in ((1, "pipe not found", False), (0, "28.0.1 windows", False),
                                    (0, "28.0.1 linux", True)):
            with (
                self.subTest(output=output),
                patch.object(prerequisites.shutil, "which", return_value="docker.exe"),
                patch.object(prerequisites, "run_command", return_value=(code, output)),
            ):
                result = prerequisites.tool_check(spec)
            self.assertEqual(ready, result["ok"])
            self.assertTrue(result["installed"])
            if not ready:
                self.assertIn("Start Docker Desktop", result["fix"])
                self.assertEqual("engine-unavailable", result["state"])

    def test_service_report_aggregates_failures_without_blocking_unrelated_stages(self) -> None:
        identifiers = {tool for tools in prerequisites.profiles.plan(["container-apps"])["stages"].values()
                       for tool in tools}
        checks = [prerequisites.check(key, key, key not in {"docker", "graphviz"}, "Synthetic result")
                  for key in identifiers]
        with patch.object(prerequisites, "build_report", return_value={"checks": checks}):
            report = prerequisites.service_report(["container-apps"])
        self.assertFalse(report["ready"])
        self.assertEqual(["graphviz"], report["blockedStages"]["diagrams"])
        self.assertEqual([], report["blockedStages"]["bicep"])
        self.assertEqual(["docker"], report["blockedStages"]["local-validation"])
        self.assertEqual([], report["blockedStages"]["requirements"])

    def test_copilot_requires_portal_flags(self) -> None:
        for help_text, expected in (
            ("--agent --prompt", False),
            ("--agent --prompt --allow-all-tools --no-ask-user --add-dir", True),
        ):
            with (
                self.subTest(help_text=help_text),
                patch.object(prerequisites.shutil, "which", return_value="copilot"),
                patch.object(prerequisites, "run_command", side_effect=[
                    (0, "GitHub Copilot CLI"), (0, help_text),
                ]),
            ):
                self.assertEqual(expected, prerequisites.tool_check(self.tool("copilot"))["ok"])

    def test_minimum_versions_handle_padding_and_prereleases(self) -> None:
        for actual, minimum, ready in (
            ("10.0", "10", True), ("10.0rc1", "10.0", False),
            ("10.0.dev1", "10.0", False), ("10.0.post1", "10.0", True),
            ("11.0rc1", "10.0", True), ("9.9", "10.0", False), ("invalid", "10.0", False),
        ):
            with self.subTest(actual=actual):
                self.assertEqual(ready, prerequisites.minimum_satisfied(actual, minimum))

    def test_python_requirements_use_manifest_and_report_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("# comment\npillow>=10.0\n", encoding="utf-8")
            with (
                patch.object(prerequisites.importlib.metadata, "version",
                             side_effect=importlib.metadata.PackageNotFoundError("pillow")),
                patch.object(prerequisites, "run_command", return_value=(1, "broken dependency")),
            ):
                checks = {item["id"]: item for item in prerequisites.python_checks(root)}
            self.assertFalse(checks["venv"]["ok"])
            self.assertFalse(checks["python-package:pillow"]["ok"])
            self.assertIn("pillow>=10.0", checks["python-package:pillow"]["detail"])
            self.assertFalse(checks["pip-health"]["ok"])
            (root / "requirements.txt").write_text("pillow==10.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                prerequisites.python_checks(root)

    def test_timeout_and_os_errors_are_explicit(self) -> None:
        for error in (OSError("denied"), subprocess.TimeoutExpired("dot", 45)):
            with (
                self.subTest(error=type(error).__name__),
                patch.object(prerequisites.subprocess, "run", side_effect=error),
            ):
                code, detail = prerequisites.run_command(["dot", "-V"])
                self.assertNotEqual(0, code)
                self.assertIn(type(error).__name__, detail)

    def test_report_runs_real_smoke_command_only_when_dependencies_pass(self) -> None:
        for packages_ready, render_code in ((False, 0), (True, 1), (True, 0)):
            with (
                self.subTest(packages_ready=packages_ready, render_code=render_code),
                patch.object(prerequisites, "python_checks", return_value=[
                    prerequisites.check("python-package:diagrams", "diagrams", packages_ready, "test"),
                ]),
                patch.object(prerequisites, "tool_check", side_effect=lambda spec:
                             prerequisites.check(spec[0], spec[1], True, "test")),
                patch.object(prerequisites, "nuget_check", return_value=
                             prerequisites.check("nuget-https", "NuGet HTTPS/TLS", True, "Synthetic metadata probe")),
                patch.object(prerequisites, "run_command", return_value=(render_code, "PNG result")) as run,
            ):
                report = prerequisites.build_report(contributor=True, docker=True)
            self.assertEqual(packages_ready and render_code == 0, report["ready"])
            self.assertEqual(packages_ready, run.called)
            if packages_ready:
                self.assertEqual(prerequisites.DIAGRAM_SMOKE, run.call_args.args[0][-1])
            self.assertIn("node", [item["id"] for item in report["checks"]])
            self.assertIn("docker", [item["id"] for item in report["checks"]])
            self.assertIn("nuget-https", [item["id"] for item in report["checks"]])

    def test_smoke_script_verifies_png_and_cleans_temporary_directory(self) -> None:
        self.assertIn("with tempfile.TemporaryDirectory(", prerequisites.DIAGRAM_SMOKE)
        self.assertIn('image.format == "PNG"', prerequisites.DIAGRAM_SMOKE)
        self.assertIn("image.verify()", prerequisites.DIAGRAM_SMOKE)

    def test_active_guidance_uses_baseline_tools_instead_of_worker_installs(self) -> None:
        skills = ROOT / ".github" / "skills"
        validation = (skills / "az-azure-validate" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("az bicep build --file", validation)
        self.assertIn("az bicep lint --file", validation)
        self.assertNotIn("\nbicep build ", validation)
        self.assertNotIn("\nbicep lint ", validation)
        consolidated = (skills / "az-consolidated" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("PREREQUISITES.md", consolidated)
        self.assertNotIn("choco install graphviz", consolidated)


@unittest.skipUnless(os.name == "nt" and shutil.which("pwsh"), "Windows PowerShell setup")
class WindowsSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="abc setup test ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir()
        self.script = self.root / "scripts" / "Install-Prerequisites.ps1"
        shutil.copyfile(ROOT / "scripts" / self.script.name, self.script)
        self.report = {
            "ready": False, "checks": [
                prerequisites.check("graphviz", "Graphviz", False, "missing", "Graphviz.Graphviz"),
                prerequisites.check("venv", "Environment", False, "missing"),
                prerequisites.check("bicep", "Bicep", False, "missing"),
            ], "notChecked": ["authentication"],
        }
        (self.root / "scripts" / "check_prerequisites.py").write_text(
            f"import json\nprint(json.dumps({self.report!r}))\nraise SystemExit(1)\n", encoding="utf-8",
        )
        (self.root / "requirements.txt").write_text("", encoding="utf-8")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.sentinel = self.root / "installer-called"
        for command in ("winget", "az"):
            (self.bin / f"{command}.cmd").write_text(
                f'@echo off\r\necho forbidden>"{self.sentinel}"\r\nexit /b 99\r\n', encoding="utf-8",
            )

    def run_setup(self, *arguments: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(self.script), "-PythonExecutable", sys.executable, *arguments],
            env={**os.environ, "PATH": str(self.bin) + os.pathsep + os.environ["PATH"]},
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertFalse(self.sentinel.exists(), result.stdout + result.stderr)
        return result

    def test_check_only_reports_missing_tools_without_mutations(self) -> None:
        result = self.run_setup("-CheckOnly", "-Json")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout)["ready"])
        self.assertFalse((self.root / ".venv").exists())

    def test_whatif_does_not_install_or_create_environment_or_persist_path(self) -> None:
        graphviz = self.root / "graphviz"
        graphviz.mkdir()
        (graphviz / "dot.exe").touch()
        result = self.run_setup("-Install", "-WhatIf", "-GraphvizBin", str(graphviz))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        for operation in ("Graphviz", "virtual environment", "requirements.txt", "bicep install"):
            self.assertIn(operation, result.stdout)
        self.assertFalse((self.root / ".venv").exists())

    def test_install_requires_agreements(self) -> None:
        result = self.run_setup("-Install", "-GraphvizBin", str(self.root / "absent"))
        self.assertEqual(2, result.returncode)
        self.assertIn("AcceptPackageAgreements", result.stderr)

    def test_active_portal_or_writer_blocks_installation(self) -> None:
        for legacy, lease in ((False, False), (False, True), (True, True)):
            with self.subTest(legacy=legacy, lease=lease):
                state = self.root / (".hackbuilder-portal" if legacy else ".abcbuilder-portal")
                state.mkdir(exist_ok=True)
                if lease:
                    (state / "projects").mkdir(exist_ok=True)
                    record = state / "projects" / "example.json"
                    record.write_text(json.dumps({"projectSlug": "example", "writer": {"runId": "test"}}))
                else:
                    record = state / "server.json"
                    record.write_text(json.dumps({"pid": os.getpid()}))
                result = self.run_setup(
                    "-Install", "-AcceptPackageAgreements", "-GraphvizBin", str(self.root / "absent"),
                )
                self.assertEqual(2, result.returncode)
                self.assertIn("writer lease" if lease else "Close the portal", result.stderr)
                self.assertFalse((self.root / ".venv").exists())
                record.unlink()

    def test_incomplete_environment_is_preserved(self) -> None:
        environment = self.root / ".venv"
        environment.mkdir()
        marker = environment / "preserve"
        marker.write_text("user data")
        result = self.run_setup("-Install", "-WhatIf", "-GraphvizBin", str(self.root / "absent"))
        self.assertEqual(2, result.returncode)
        self.assertIn("incomplete", result.stderr)
        self.assertEqual("user data", marker.read_text())

    def test_native_command_failures_and_exit_codes_are_not_success(self) -> None:
        script = str(self.script).replace("'", "''")
        python = sys.executable.replace("'", "''")
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command",
             f". '{script}'; $result = Invoke-SetupCommand '{python}' @('-c', 'raise SystemExit(7)'); "
             "$result | ConvertTo-Json; "
             "try { Invoke-SetupCommand 'abc-builder-nonexistent-executable' } catch { exit 23 }"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(23, result.returncode, result.stderr)
        self.assertEqual(7, json.loads(result.stdout)["ExitCode"])

    def test_install_sequence_with_simulated_tools_rechecks_before_success(self) -> None:
        (self.root / "initial.json").write_text(json.dumps(self.report), encoding="utf-8")
        final = {**self.report, "ready": True,
                 "checks": [{**item, "ok": True} for item in self.report["checks"]]}
        (self.root / "final.json").write_text(json.dumps(final), encoding="utf-8")
        root = str(self.root).replace("'", "''")
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", f"""
$root = '{root}'
function Test-Python {{
    $global:LASTEXITCODE = 0
    if ($args -contains '-c') {{ return 'Simulated Python' }}
    if ($args -contains 'venv') {{
        $directory = Join-Path $root '.venv\\Scripts'
        $null = New-Item -ItemType Directory -Path $directory -Force
        $null = New-Item -ItemType File -Path (Join-Path $directory 'python.exe')
        return
    }}
    if ($args -contains 'pip') {{
        Set-Content -LiteralPath (Join-Path $root 'pip-completed') -Value 'simulated'
        return
    }}
    if ($args -contains 'playwright') {{
        Set-Content -LiteralPath (Join-Path $root 'browser-completed') -Value ($args -join ' ')
        return
    }}
    if ($args -contains '--json') {{
        $name = if (Test-Path (Join-Path $root 'pip-completed')) {{ 'final.json' }} else {{ 'initial.json' }}
        Get-Content -LiteralPath (Join-Path $root $name) -Raw
        return
    }}
    throw "Unexpected simulated Python invocation: $args"
}}
function Test-Winget {{
    $global:LASTEXITCODE = 0
    Add-Content -LiteralPath (Join-Path $root 'trace') -Value ($args -join ' ')
}}
function Test-Azure {{
    $global:LASTEXITCODE = 0
    Add-Content -LiteralPath (Join-Path $root 'trace') -Value ($args -join ' ')
}}
function Test-Dot {{ throw 'The simulated dot must not execute' }}
function Get-Command {{
    param([string]$Name, [string]$ErrorAction)
    $target = switch -Wildcard ($Name) {{
        '*python*' {{ 'Test-Python' }}
        'winget' {{ 'Test-Winget' }}
        'az' {{ 'Test-Azure' }}
        'dot' {{ 'Test-Dot' }}
        default {{ throw "Unexpected simulated executable: $Name" }}
    }}
    Microsoft.PowerShell.Core\\Get-Command -Name $target -CommandType Function
}}
& (Join-Path $root 'scripts\\Install-Prerequisites.ps1') -Install -AcceptPackageAgreements `
    -PythonExecutable python -GraphvizBin (Join-Path $root 'absent')
"""],
            capture_output=True, text=True, timeout=20, check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        trace = (self.root / "trace").read_text(encoding="utf-8")
        self.assertIn("--id Graphviz.Graphviz --exact --source winget", trace)
        self.assertIn("bicep install", trace)
        self.assertTrue((self.root / ".venv" / "Scripts" / "python.exe").exists())
        self.assertTrue((self.root / "pip-completed").exists())
        self.assertIn("playwright install chromium", (self.root / "browser-completed").read_text())


if __name__ == "__main__":
    unittest.main()
