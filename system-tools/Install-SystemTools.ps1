<#
.SYNOPSIS
    Downloads the complete pinned FBC Builder tool baseline and optionally installs from that cache.
.DESCRIPTION
    Downloads all native tools by default, including Node.js, GitHub CLI and Azure CLI Bicep.
    Requires explicit package agreement consent. Add -Install to download, verify the entire cache,
    then install missing tools in the same flow. Never executes native installers from online sources.
    Python requirements still need network access; this is not a full offline bundle.
    Never changes execution policy, auto-elevates, signs in, enables WSL or starts Docker.
.PARAMETER Install
    After downloading the full baseline, installs missing tools from the verified cache on Windows x64.
.PARAMETER Mode
    Download (default), Check (read-only), or Install (compatibility alias for Download plus -Install).
.PARAMETER AcceptPackageAgreements
    Explicit agreement consent for real downloads/installation. Review vendor terms first.
.PARAMETER AcceptDockerLicense
    Separately accepts Docker Desktop terms for a new installation; review subscription eligibility first.
.PARAMETER IncludeContributorTools
    Compatibility switch; Node.js and GitHub CLI are now always included.
.PARAMETER SkipVSCode
    Omits VS Code when managed separately; the default baseline includes it.
.PARAMETER UseCachedInstallers
    With installation, validates the complete existing cache without downloading missing files.
.PARAMETER CacheDirectory
    Local native installer cache. Defaults to system-tools\cache, which is ignored by Git.
.PARAMETER ReportPath
    Local JSON outcome. Download/install default to a timestamped file in system-tools\reports.
    Check writes nothing unless supplied; WhatIf never writes reports.
.PARAMETER PythonExecutable
    Existing Python 3.10+ to use for checks/bootstrap; existing .venv is preferred.
.EXAMPLE
    .\system-tools\Install-SystemTools.ps1 -AcceptPackageAgreements -Verbose
.EXAMPLE
    .\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose
.EXAMPLE
    .\system-tools\Install-SystemTools.ps1 -Mode Check
#>
#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [switch]$Install,
    [ValidateSet('Check', 'Download', 'Install')][string]$Mode = 'Download',
    [switch]$AcceptPackageAgreements,
    [switch]$AcceptDockerLicense,
    [switch]$IncludeContributorTools,
    [switch]$SkipVSCode,
    [switch]$UseCachedInstallers,
    [string]$CacheDirectory = (Join-Path $PSScriptRoot 'cache'),
    [string]$ReportPath,
    [ValidateNotNullOrEmpty()][string]$PythonExecutable = 'python'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$installer = Join-Path $root 'scripts\Install-Prerequisites.ps1'
$installRequested = $Install -or $Mode -eq 'Install'
$setupParameters = @{
    AcceptPackageAgreements = $AcceptPackageAgreements; IncludeContributorTools = $true
    AcceptDockerLicense = $AcceptDockerLicense
    UseCachedInstallers = $UseCachedInstallers; CacheDirectory = $CacheDirectory
    ReportPath = $ReportPath; PythonExecutable = $PythonExecutable
    Verbose = [bool]$PSBoundParameters['Verbose']; WhatIf = [bool]$WhatIfPreference
}
# Dot-sourcing binds parameters in this scope; retain the caller's explicit selections.
. $installer @setupParameters

try {
    if ($env:OS -ne 'Windows_NT') { throw 'Use the manual guide on non-Windows hosts.' }
    if ($Mode -eq 'Check' -and $installRequested) { throw 'Choose -Mode Check or -Install, not both.' }
    if ($UseCachedInstallers -and -not $installRequested) { throw '-UseCachedInstallers requires -Install.' }
    if ($Mode -ne 'Check') {
        if (-not $ReportPath) {
            $ReportPath = Join-Path $PSScriptRoot ("reports\setup-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
        }
        if (-not $WhatIfPreference -and -not $AcceptPackageAgreements) {
            throw 'Download/install requires explicit -AcceptPackageAgreements. Review vendor licensing first.'
        }
        if ($installRequested -and -not $WhatIfPreference -and
            [Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne 'X64') {
            throw 'Baseline installation requires Windows x64. Omit -Install to download; use manual native tools on ARM64.'
        }
        if ($installRequested -and -not $WhatIfPreference) { Assert-SetupIdle -RepositoryRoot $root }
        $tools = @(Get-SetupCatalog | Where-Object { -not $SkipVSCode -or $_.id -ne 'vscode' })
        Write-SetupStatus 'Baseline' 'starting' `
            "Preparing all $($tools.Count) pinned native tools, including Node.js and GitHub CLI. No installers run yet."
        for ($index = 0; $index -lt $tools.Count; $index++) {
            $tool = $tools[$index]
            Write-Progress -Activity 'Preparing FBC Builder tool baseline' -Status "$($tool.name) $($tool.version)" `
                -PercentComplete ([int](100 * $index / $tools.Count))
            if ($UseCachedInstallers) {
                $null = Get-SetupCachedInstaller -Tool $tool -Directory $CacheDirectory
                Write-SetupStatus $tool.name 'cached' "Baseline $($tool.version) verified; no download requested."
            } else {
                Save-SetupInstaller -Tool $tool -Directory $CacheDirectory
                if (-not $WhatIfPreference) {
                    $null = Get-SetupCachedInstaller -Tool $tool -Directory $CacheDirectory
                }
            }
        }
        Write-Progress -Activity 'Preparing FBC Builder tool baseline' -Completed
        if (-not $installRequested) {
            Save-SetupOutcome -Path $ReportPath -Status 'downloaded' -Report ([PSCustomObject]@{
                nativeInstallers = @($tools | Select-Object id, version, sha256)
            })
            if ($WhatIfPreference) {
                Write-Information 'Plan only: no files downloaded, reports written or installers executed.' `
                    -InformationAction Continue
                exit 1
            }
            Write-Information 'Complete native baseline cached. Nothing installed. Add -Install to install from this cache.' `
                -InformationAction Continue
            exit 0
        }
        if ($WhatIfPreference) {
            Write-Information 'Plan: verify all downloads, install missing native tools from cache, prepare the Python virtual environment and Bicep, then rerun checks. No changes made.' `
                -InformationAction Continue
            exit 1
        }
    }

    $options = @{
        SystemProfile = $true; IncludeVSCode = -not $SkipVSCode
        IncludeContributorTools = $true; PythonExecutable = $PythonExecutable
        ReportPath = $ReportPath; Verbose = $setupParameters.Verbose
        WhatIf = [bool]$WhatIfPreference
    }
    if ($installRequested) {
        $options.Install = $true
        $options.AcceptPackageAgreements = $AcceptPackageAgreements
        $options.AcceptDockerLicense = $AcceptDockerLicense
        $options.UseCachedInstallers = $true
        $options.CacheDirectory = $CacheDirectory
        $options.InitialEvents = $script:setupEvents.ToArray()
    } else { $options.CheckOnly = $true }
    & $installer @options
    exit $LASTEXITCODE
} catch {
    $failure = $_.Exception.Message
    Write-Error -Message $failure -ErrorAction Continue
    try { Save-SetupOutcome -Path $ReportPath -Status 'failed' -Failure $failure }
    catch { Write-Error "Could not persist setup report: $($_.Exception.Message)" -ErrorAction Continue }
    exit 2
} finally {
    Write-Progress -Activity 'Preparing FBC Builder tool baseline' -Completed
}
