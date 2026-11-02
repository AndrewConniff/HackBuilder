"""Verify full-profile online setup with mocked commands, never host installation."""

from __future__ import annotations

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
import check_prerequisites as checker
import prerequisite_profiles as profiles

ROOT = Path(__file__).resolve().parents[2]


class SystemProfileTests(unittest.TestCase):
    def test_system_profile_covers_full_toolchain(self) -> None:
        profile = profiles.system_plan()
        self.assertEqual(profiles.plan(sorted(profiles.SERVICE_REQUIREMENTS), "local", True, True), profile)
        planned = {item["id"] for item in checker.planned_checks(profile)}
        self.assertTrue({"docker", "functions-core-tools", "k6"} <= planned)
        self.assertFalse((ROOT / "system-tools" / "tool-catalog.json").exists())

    def test_cli_combines_system_scope_and_contributor_checks(self) -> None:
        with (
            patch.object(sys, "argv", ["check_prerequisites.py", "--system", "--contributor", "--json"]),
            patch.object(checker, "service_report", return_value={"ready": True, "checks": []}) as report,
            patch("builtins.print"),
        ):
            self.assertEqual(0, checker.main())
        report.assert_called_once_with(
            profiles.system_plan()["services"], "local", True, load_tests=True, contributor=True,
        )

    def test_contributor_checks_are_not_lost_with_service_scope(self) -> None:
        with (
            patch.object(checker, "build_report", return_value={"checks": []}) as baseline,
            patch.object(profiles, "stage_failures", return_value=[]),
        ):
            checker.service_report(["foundry"], contributor=True)
        baseline.assert_called_once_with(checker.ROOT, contributor=True, docker=False)

    def test_downloaded_dependencies_are_ignored(self) -> None:
        paths = [
            "system-tools/cache/example/setup.exe",
            "system-tools/reports/setup.json",
            "generated-scenarios/example/.packages/microsoft.playwright/1.0/node.exe",
        ]
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-z", "--stdin"], cwd=ROOT,
            input="\0".join(paths) + "\0", capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(paths, result.stdout.rstrip("\0").split("\0"))


@unittest.skipUnless(os.name == "nt" and shutil.which("pwsh"), "Windows setup requires PowerShell")
class SystemToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fbc system tools ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("scripts", "system-tools"):
            (self.root / name).mkdir()
        for relative in (
            Path("scripts") / "Install-Prerequisites.ps1",
            Path("system-tools") / "Install-SystemTools.ps1",
        ):
            shutil.copyfile(ROOT / relative, self.root / relative)
        self.frontdoor = self.root / "system-tools" / "Install-SystemTools.ps1"
        self.installer = self.root / "scripts" / "Install-Prerequisites.ps1"
        self.cache = self.root / "system-tools" / "cache"
        self.outcome = self.root / "system-tools" / "reports" / "test.json"
        self.trace = self.root / "installer-trace"
        (self.root / "requirements.txt").write_text("", encoding="utf-8")
        (self.root / "scripts" / "check_prerequisites.py").write_text(
            "import json, sys\n"
            "print(json.dumps({'ready':False,'checks':[{'id':'synthetic','name':'Synthetic',"
            "'ok':False,'detail':' '.join(sys.argv[1:])}],'notChecked':['identity']}))\n"
            "raise SystemExit(1)\n", encoding="utf-8",
        )

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(self.frontdoor), "-PythonExecutable", sys.executable, *arguments],
            capture_output=True, text=True, timeout=30, check=False,
        )

    def run_helper(self, body: str, *, exit_code: int = 0) -> subprocess.CompletedProcess:
        def quote(value: Path) -> str:
            return str(value).replace("'", "''")

        script = f"""
$ErrorActionPreference = 'Stop'
. '{quote(self.installer)}'
$ReportPath = '{quote(self.outcome)}'
$trace = '{quote(self.trace)}'
function Invoke-SetupCommand {{
    param($FilePath, $ArgumentList)
    @{{file = $FilePath; arguments = $ArgumentList}} | ConvertTo-Json | Set-Content -LiteralPath $trace
    [PSCustomObject]@{{ExitCode = {exit_code}; Output = 'Simulated vendor output'}}
}}
function Start-Process {{ throw 'No cached installer should execute.' }}
function Update-SetupProcessPath {{ }}
{body}
"""
        return subprocess.run(
            ["pwsh", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=30, check=False,
        )

    def test_default_and_explicit_check_are_read_only(self) -> None:
        for arguments in ((), ("-Mode", "Check")):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments, "-SkipVSCode")
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertFalse(self.outcome.parent.exists())
                self.assertFalse(self.cache.exists())
                self.assertFalse((self.root / ".venv").exists())

    def test_check_forwards_system_contributor_and_report_options(self) -> None:
        result = self.run_script("-Mode", "Check", "-SkipVSCode", "-ReportPath", str(self.outcome))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        report = json.loads(self.outcome.read_text())
        detail = report["verification"]["checks"][0]["detail"]
        self.assertIn("--system", detail)
        self.assertIn("--contributor", detail)
        self.assertFalse(report["ready"])
        self.assertFalse(self.cache.exists())

    def test_frontdoor_forwards_editor_choice_install_mode_and_consent(self) -> None:
        self.installer.write_text(
            "[CmdletBinding(SupportsShouldProcess=$true)]\n"
            "param([switch]$SystemProfile, [bool]$IncludeVSCode, [switch]$IncludeContributorTools,\n"
            "[string]$PythonExecutable, [string]$ReportPath, [switch]$Install,\n"
            "[switch]$AcceptPackageAgreements, [switch]$AcceptDockerLicense)\n"
            "$PSBoundParameters | ConvertTo-Json; exit 0\n", encoding="utf-8",
        )
        for skip in (False, True):
            with self.subTest(skip=skip):
                result = self.run_script(
                    "-Mode", "Install", "-AcceptPackageAgreements", "-AcceptDockerLicense",
                    *(["-SkipVSCode"] if skip else []),
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                options = json.loads(result.stdout)
                for name in ("SystemProfile", "IncludeContributorTools", "Install",
                             "AcceptPackageAgreements", "AcceptDockerLicense"):
                    self.assertTrue(options[name])
                self.assertEqual(not skip, options["IncludeVSCode"])
                self.assertIn("reports", options["ReportPath"])

    def test_install_whatif_never_creates_environment_cache_or_report(self) -> None:
        result = self.run_script("-Install", "-WhatIf", "-SkipVSCode", "-ReportPath", str(self.outcome))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("virtual environment", result.stdout)
        self.assertIn("bicep install", result.stdout)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.outcome.exists())
        self.assertFalse((self.root / ".venv").exists())

    def test_check_and_install_cannot_be_combined(self) -> None:
        result = self.run_script("-Mode", "Check", "-Install")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("not both", result.stderr)
        self.assertFalse(self.cache.exists())

    def test_install_requires_agreements_and_persists_failure(self) -> None:
        result = self.run_script("-Install", "-ReportPath", str(self.outcome))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        report = json.loads(self.outcome.read_text())
        self.assertFalse(report["ready"])
        self.assertIn("AcceptPackageAgreements", report["error"])
        self.assertFalse(self.cache.exists())

    def test_retired_download_and_cache_options_are_rejected(self) -> None:
        for arguments in (("-Mode", "Download"), ("-UseCachedInstallers",), ("-CacheDirectory", str(self.cache))):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments)
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(self.cache.exists())

    def test_online_install_uses_exact_winget_package_and_agreements(self) -> None:
        result = self.run_helper("Install-SetupPackage -PackageId 'Git.Git'")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        trace = json.loads(self.trace.read_text())
        self.assertEqual("winget", trace["file"])
        self.assertEqual([
            "install", "--id", "Git.Git", "--exact", "--source", "winget",
            "--silent", "--disable-interactivity", "--accept-package-agreements", "--accept-source-agreements",
        ], trace["arguments"])
        self.assertIn("[installed-unverified]", result.stdout)
        self.assertFalse(self.cache.exists())

    def test_package_whatif_does_not_invoke_winget(self) -> None:
        result = self.run_helper("Install-SetupPackage -PackageId 'Git.Git' -WhatIf")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse(self.trace.exists())

    def test_bicep_downloads_through_azure_cli(self) -> None:
        result = self.run_helper("Install-SetupBicep")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual({"file": "az", "arguments": ["bicep", "install"]}, json.loads(self.trace.read_text()))
        self.assertFalse(self.cache.exists())

    def test_bicep_whatif_never_invokes_azure_cli(self) -> None:
        result = self.run_helper("Install-SetupBicep -WhatIf")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse(self.trace.exists())

    def test_bicep_download_failure_is_explicit(self) -> None:
        result = self.run_helper("Install-SetupBicep", exit_code=42)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Bicep installation failed", result.stderr)

    def test_reboot_and_failure_are_explicit_in_persistent_outcome(self) -> None:
        for code in (3010, -1978334967, 42):
            with self.subTest(code=code):
                result = self.run_helper("""
try {
    Install-SetupPackage -PackageId 'Git.Git'
    Save-SetupOutcome -Path $ReportPath -Status 'unmet'
} catch {
    Save-SetupOutcome -Path $ReportPath -Status 'failed' -Failure $_.Exception.Message
    exit 2
}
""", exit_code=code)
                self.assertEqual(2 if code == 42 else 0, result.returncode, result.stdout + result.stderr)
                outcome = json.loads(self.outcome.read_text())
                self.assertFalse(outcome["ready"])
                self.assertEqual(code != 42, outcome["rebootRequired"])
                if code == 42:
                    self.assertIn("exit 42", outcome["error"])

    def test_docker_requires_separate_license_consent_before_installation(self) -> None:
        result = self.run_helper("Install-SetupPackage -PackageId 'Docker.DockerDesktop'")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("AcceptDockerLicense", result.stderr)
        self.assertFalse(self.trace.exists())

    def test_stopped_docker_is_not_reinstalled_or_reported_ready(self) -> None:
        report = {
            "ready": False, "notChecked": ["identity"], "checks": [
                {"id": "docker", "name": "Docker", "ok": False, "winget": "Docker.DockerDesktop",
                 "detail": "Linux engine is stopped."},
                {"id": "bicep", "name": "Bicep", "ok": True, "detail": "Ready."},
            ],
        }
        fixture = self.root / "fixture.json"
        fixture.write_text(json.dumps(report), encoding="utf-8")
        root = str(self.root).replace("'", "''")
        script = f"""
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
    if ($args -contains '--json') {{
        $global:LASTEXITCODE = 1
        Get-Content -LiteralPath (Join-Path $root 'fixture.json') -Raw
        return
    }}
    throw "Unexpected simulated Python invocation: $args"
}}
function Test-Forbidden {{ throw 'No installer or Docker start should execute.' }}
function Get-Command {{
    param([string]$Name, [string]$ErrorAction)
    if ($Name -like '*python*') {{ return Microsoft.PowerShell.Core\\Get-Command Test-Python }}
    if ($Name -in @('dot', 'docker', 'winget', 'az')) {{
        return Microsoft.PowerShell.Core\\Get-Command Test-Forbidden
    }}
    Microsoft.PowerShell.Core\\Get-Command -Name $Name -ErrorAction $ErrorAction
}}
& (Join-Path $root 'scripts\\Install-Prerequisites.ps1') -Install -AcceptPackageAgreements -SystemProfile `
    -AcceptDockerLicense -PythonExecutable python -GraphvizBin (Join-Path $root 'absent') `
    -ReportPath (Join-Path $root 'system-tools\\reports\\test.json')
exit $LASTEXITCODE
"""
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        outcome = json.loads(self.outcome.read_text())
        self.assertFalse(outcome["ready"])
        self.assertEqual("unmet", outcome["status"])
        self.assertTrue(any(event["state"] == "manual-action" for event in outcome["events"]))
        self.assertIn("not reinstalling", result.stdout)


if __name__ == "__main__":
    unittest.main()
