"""Verify full-profile setup and cache safety with mocked installers, never host installation."""

from __future__ import annotations

import hashlib
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
    def test_system_profile_matches_portal_and_has_every_native_recipe(self) -> None:
        profile = profiles.system_plan()
        self.assertEqual(profiles.plan(sorted(profiles.SERVICE_REQUIREMENTS), "local", True, True), profile)
        planned = {item["id"] for item in checker.planned_checks(profile)}
        self.assertTrue({"docker", "functions-core-tools", "k6"} <= planned)
        catalog = json.loads((ROOT / "system-tools" / "tool-catalog.json").read_text(encoding="utf-8"))
        tools = {item["id"]: item for item in catalog["tools"]}
        self.assertEqual(len(tools), len(catalog["tools"]))
        for spec in (*checker.TOOLS, *checker.CONTRIBUTOR_TOOLS):
            if spec[5]:
                self.assertEqual(spec[5], tools[spec[0]]["packageId"])
        self.assertEqual("Microsoft.Azure.FunctionsCoreTools", tools["functions-core-tools"]["packageId"])
        self.assertEqual("GrafanaLabs.k6", tools["k6"]["packageId"])
        self.assertEqual("Docker.DockerDesktop", tools["docker"]["packageId"])
        self.assertEqual("Microsoft.Bicep", tools["bicep"]["packageId"])
        self.assertGreaterEqual(len(tools), 14)
        self.assertTrue(catalog["baseline"])
        for tool in tools.values():
            self.assertRegex(tool["version"], r"^\d+(?:\.\d+)+$")
            self.assertRegex(tool["sha256"], r"^[a-fA-F0-9]{64}$")
            self.assertTrue(tool["url"].startswith("https://"))
            self.assertNotIn("/latest/", tool["url"])
        self.assertEqual(
            ["graphviz", "k6", "gh"], [tool["id"] for tool in tools.values() if tool.get("allowUnsigned")],
        )
        self.assertTrue(all(tool["source"].startswith("https://") for tool in tools.values()))

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


@unittest.skipUnless(os.name == "nt" and shutil.which("pwsh"), "Windows setup requires PowerShell")
class SystemToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="abc system tools ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("scripts", "system-tools"):
            (self.root / name).mkdir()
        for relative in (
            Path("scripts") / "Install-Prerequisites.ps1",
            Path("system-tools") / "Install-SystemTools.ps1",
            Path("system-tools") / "tool-catalog.json",
        ):
            shutil.copyfile(ROOT / relative, self.root / relative)
        self.frontdoor = self.root / "system-tools" / "Install-SystemTools.ps1"
        self.installer = self.root / "scripts" / "Install-Prerequisites.ps1"
        self.cache = self.root / "system-tools" / "cache"
        self.outcome = self.root / "system-tools" / "reports" / "test.json"
        self.trace = self.root / "installer-trace"
        self.catalog = json.loads((self.root / "system-tools" / "tool-catalog.json").read_text())
        for tool in self.catalog["tools"]:
            tool["sha256"] = hashlib.sha256(b"fixture").hexdigest()
        (self.root / "system-tools" / "tool-catalog.json").write_text(json.dumps(self.catalog), encoding="utf-8")
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

    def run_helper(self, body: str, *, signature: str = "Valid", exit_code: int = 0) -> subprocess.CompletedProcess:
        def quote(value: Path) -> str:
            return str(value).replace("'", "''")

        script = f"""
$ErrorActionPreference = 'Stop'
. '{quote(self.installer)}'
$CacheDirectory = '{quote(self.cache)}'
$ReportPath = '{quote(self.outcome)}'
$trace = '{quote(self.trace)}'
$UseCachedInstallers = $true
function Get-AuthenticodeSignature {{
    param($LiteralPath)
    [PSCustomObject]@{{ Status = '{signature}'; SignerCertificate = [PSCustomObject]@{{Subject = 'Trusted test publisher'}} }}
}}
function Start-Process {{
    param($FilePath, $ArgumentList, [switch]$Wait, [switch]$PassThru)
    @{{file = $FilePath; arguments = $ArgumentList; wait = [bool]$Wait}} |
        ConvertTo-Json | Set-Content -LiteralPath $trace
    [PSCustomObject]@{{ExitCode = {exit_code}}}
}}
function Update-SetupProcessPath {{ }}
{body}
"""
        return subprocess.run(
            ["pwsh", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=30, check=False,
        )

    def create_cache(self, identifier: str = "git", **changes: object) -> tuple[Path, Path]:
        tool = next(item for item in self.catalog["tools"] if item["id"] == identifier)
        directory = self.cache / identifier
        directory.mkdir(parents=True, exist_ok=True)
        installer = directory / ("fixture" + tool["extension"])
        installer.write_bytes(b"fixture")
        receipt = {
            "schemaVersion": 1, "packageId": tool["packageId"], "architecture": "x64",
            "version": tool["version"],
            "file": installer.name, "sha256": hashlib.sha256(installer.read_bytes()).hexdigest(),
            "signatureStatus": "Valid", "publisher": "Trusted test publisher", **changes,
        }
        receipt_path = directory / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return installer, receipt_path

    def test_frontdoor_check_forwards_system_contributor_and_report_options(self) -> None:
        result = self.run_script(
            "-Mode", "Check", "-SkipVSCode", "-ReportPath", str(self.outcome),
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        report = json.loads(self.outcome.read_text())
        detail = report["verification"]["checks"][0]["detail"]
        self.assertIn("--system", detail)
        self.assertIn("--contributor", detail)
        self.assertFalse(report["ready"])
        self.assertFalse(self.cache.exists())
        self.assertFalse((self.root / ".venv").exists())

    def test_download_whatif_lists_full_profile_without_mutations(self) -> None:
        result = self.run_script(
            "-WhatIf", "-ReportPath", str(self.outcome),
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        for tool in self.catalog["tools"]:
            self.assertIn(tool["packageId"], result.stdout)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.outcome.exists())
        self.assertFalse((self.root / ".venv").exists())

    def test_install_whatif_never_creates_environment_or_report(self) -> None:
        result = self.run_script(
            "-Install", "-WhatIf", "-ReportPath", str(self.outcome),
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        for tool in self.catalog["tools"]:
            self.assertIn(tool["packageId"], result.stdout)
        self.assertIn("virtual environment", result.stdout)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.outcome.exists())
        self.assertFalse((self.root / ".venv").exists())

    def test_check_and_install_cannot_be_combined(self) -> None:
        result = self.run_script("-Mode", "Check", "-Install", "-ReportPath", str(self.outcome))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("not both", json.loads(self.outcome.read_text())["error"])
        self.assertFalse(self.cache.exists())

    def test_download_is_the_default_and_still_requires_agreement_consent(self) -> None:
        result = self.run_script("-ReportPath", str(self.outcome))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("AcceptPackageAgreements", json.loads(self.outcome.read_text())["error"])
        self.assertFalse(self.cache.exists())

    def test_download_requires_explicit_agreements_and_persists_failure(self) -> None:
        result = self.run_script("-Mode", "Download", "-ReportPath", str(self.outcome))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        report = json.loads(self.outcome.read_text())
        self.assertFalse(report["ready"])
        self.assertEqual("failed", report["status"])
        self.assertIn("AcceptPackageAgreements", report["error"])
        self.assertFalse(self.cache.exists())

    def test_download_uses_pinned_vendor_url_and_can_reuse_verified_cache(self) -> None:
        result = self.run_helper("""
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec, $ErrorAction)
    $Uri | Set-Content -LiteralPath $trace
    [IO.File]::WriteAllText($OutFile, 'fixture')
}
$tool = Get-SetupCatalog | Where-Object { $_.id -eq 'git' }
Save-SetupInstaller -Tool $tool -Directory $CacheDirectory
Save-SetupInstaller -Tool $tool -Directory $CacheDirectory
""")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("[cached]", result.stdout)
        tool = next(item for item in self.catalog["tools"] if item["id"] == "git")
        self.assertEqual(tool["url"], self.trace.read_text().strip())
        receipt = json.loads((self.cache / "git" / "receipt.json").read_text())
        self.assertEqual("Valid", receipt["signatureStatus"])
        self.assertEqual(tool["version"], receipt["version"])
        self.assertEqual(hashlib.sha256(b"fixture").hexdigest().upper(), receipt["sha256"])

    def test_powershell_download_uses_pinned_msi_instead_of_msix(self) -> None:
        result = self.run_helper("""
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec, $ErrorAction)
    $Uri | Set-Content -LiteralPath $trace
    [IO.File]::WriteAllText($OutFile, 'fixture')
}
$tool = Get-SetupCatalog | Where-Object { $_.id -eq 'powershell' }
Save-SetupInstaller -Tool $tool -Directory $CacheDirectory
""")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PowerShell-7.6.9-win-x64.msi", self.trace.read_text())
        receipt = json.loads((self.cache / "powershell" / "receipt.json").read_text())
        self.assertEqual("powershell-7.6.9.0.msi", receipt["file"])

    def test_download_rejects_bytes_not_matching_pinned_hash(self) -> None:
        result = self.run_helper("""
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec, $ErrorAction)
    [IO.File]::WriteAllText($OutFile, 'Unexpected package content')
}
$tool = Get-SetupCatalog | Where-Object { $_.id -eq 'powershell' }
try {
    Save-SetupInstaller -Tool $tool -Directory $CacheDirectory
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
""")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Baseline SHA256 mismatch", result.stderr)
        self.assertFalse((self.cache / "powershell" / "receipt.json").exists())

    def test_bad_cache_receipts_or_hashes_never_execute(self) -> None:
        cases = [
            {"architecture": "arm64"}, {"packageId": "Unexpected.Package"}, {"file": "..\\outside.exe"},
            {"file": "C:\\outside.exe"}, {"file": "other.msi"}, {"sha256": "0" * 64},
            {"publisher": "Different publisher"}, {"signatureStatus": "NotSigned"}, {"version": "0.0.0"},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.create_cache(**changes)
                result = self.run_helper("Install-SetupPackage -PackageId 'Git.Git'")
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertFalse(self.trace.exists())

    def test_cached_install_uses_trusted_recipe_and_waits_for_vendor_exit(self) -> None:
        self.create_cache()
        result = self.run_helper("Install-SetupPackage -PackageId 'Git.Git'")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        trace = json.loads(self.trace.read_text())
        self.assertTrue(trace["wait"])
        self.assertIn("/NORESTART", trace["arguments"])
        self.assertIn("[installed-unverified]", result.stdout)

    def test_recomputed_receipt_hash_cannot_replace_the_repository_baseline(self) -> None:
        installer, receipt_path = self.create_cache()
        installer.write_bytes(b"Changed executable and receipt")
        receipt = json.loads(receipt_path.read_text())
        receipt["sha256"] = hashlib.sha256(installer.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = self.run_helper("Install-SetupPackage -PackageId 'Git.Git'")
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.trace.exists())

    def test_legacy_receipt_without_version_requires_matching_pinned_bytes(self) -> None:
        _, receipt_path = self.create_cache()
        receipt = json.loads(receipt_path.read_text())
        del receipt["version"]
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = self.run_helper("""
$tool = Get-SetupCatalog | Where-Object { $_.id -eq 'git' }
$null = Get-SetupCachedInstaller -Tool $tool -Directory $CacheDirectory
""")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse(self.trace.exists())

    def test_cached_bicep_copies_verified_binary_without_installer_or_online_fallback(self) -> None:
        self.create_cache("bicep")
        config = self.root / "private azure config"
        result = self.run_helper(f"""
$env:AZURE_CONFIG_DIR = '{str(config).replace("'", "''")}'
function Invoke-SetupCommand {{ throw 'No online Bicep download should execute.' }}
Install-SetupBicep
""")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(b"fixture", (config / "bin" / "bicep.exe").read_bytes())
        self.assertFalse(self.trace.exists())

    def test_cached_bicep_whatif_does_not_create_azure_config(self) -> None:
        self.create_cache("bicep")
        config = self.root / "private azure config"
        result = self.run_helper(f"""
$env:AZURE_CONFIG_DIR = '{str(config).replace("'", "''")}'
Install-SetupBicep -WhatIf
""")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse(config.exists())

    def test_preparation_events_survive_final_verification_report(self) -> None:
        installer = str(self.installer).replace("'", "''")
        python = sys.executable.replace("'", "''")
        result = self.run_helper(f"""
& '{installer}' -CheckOnly -PythonExecutable '{python}' -ReportPath $ReportPath `
    -InitialEvents @([PSCustomObject]@{{tool = 'Baseline'; state = 'downloaded'; message = 'Verified all files'}})
exit $LASTEXITCODE
""")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        report = json.loads(self.outcome.read_text())
        self.assertEqual("Baseline", report["events"][0]["tool"])
        self.assertFalse(report["ready"])

    def test_msi_uses_system_msiexec_and_quotes_cached_path(self) -> None:
        installer, _ = self.create_cache("powershell")
        result = self.run_helper("Install-SetupPackage -PackageId 'Microsoft.PowerShell'")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        trace = json.loads(self.trace.read_text())
        self.assertEqual("msiexec.exe", Path(trace["file"]).name)
        self.assertIn(f'/i "{installer}"', trace["arguments"])
        self.assertIn("/qn /norestart", trace["arguments"])

    def test_unsigned_exception_is_limited_to_catalogued_open_source_tools(self) -> None:
        self.create_cache("graphviz", signatureStatus="NotSigned", publisher=None)
        result = self.run_helper("Install-SetupPackage -PackageId 'Graphviz.Graphviz'", signature="NotSigned")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue(self.trace.exists())
        self.trace.unlink()
        self.create_cache("git", signatureStatus="NotSigned", publisher=None)
        result = self.run_helper("Install-SetupPackage -PackageId 'Git.Git'", signature="NotSigned")
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(self.trace.exists())

    def test_reboot_and_failure_are_explicit_in_persistent_outcome(self) -> None:
        self.create_cache()
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

    def test_docker_requires_separate_license_consent_before_any_installer(self) -> None:
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
