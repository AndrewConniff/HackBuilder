<#
.SYNOPSIS
    Checks the complete FBC Builder toolchain or downloads and installs missing tools online.
.DESCRIPTION
    Checks by default. Explicit -Install uses WinGet, pip and Azure CLI Bicep installation.
    Never uses repository-cached installers, signs in, auto-elevates, enables WSL or starts Docker.
.PARAMETER Install
    Downloads and installs missing tools after explicit agreement consent.
.PARAMETER Mode
    Check (default) or Install (equivalent to -Install).
.PARAMETER AcceptPackageAgreements
    Explicitly accepts WinGet package/source agreements. Review vendor terms first.
.PARAMETER AcceptDockerLicense
    Separately accepts Docker Desktop terms for a new installation.
.PARAMETER IncludeContributorTools
    Compatibility switch; Node.js and GitHub CLI are always included.
.PARAMETER SkipVSCode
    Omits VS Code when managed separately.
.PARAMETER ReportPath
    Optional local JSON outcome. Installation defaults to system-tools\reports.
    Check writes nothing unless supplied; WhatIf never writes reports.
.PARAMETER PythonExecutable
    Existing Python 3.10+ for checks/bootstrap; an existing .venv is preferred.
.EXAMPLE
    .\system-tools\Install-SystemTools.ps1
.EXAMPLE
    .\system-tools\Install-SystemTools.ps1 -Install -WhatIf
.EXAMPLE
    .\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose
#>
#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [switch]$Install,
    [ValidateSet('Check', 'Install')][string]$Mode,
    [switch]$AcceptPackageAgreements,
    [switch]$AcceptDockerLicense,
    [switch]$IncludeContributorTools,
    [switch]$SkipVSCode,
    [string]$ReportPath,
    [ValidateNotNullOrEmpty()][string]$PythonExecutable = 'python'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$installer = Join-Path $root 'scripts\Install-Prerequisites.ps1'
if ($Mode -eq 'Check' -and $Install) {
    Write-Error 'Choose -Mode Check or -Install, not both.' -ErrorAction Continue
    exit 2
}
$installRequested = $Install -or $Mode -eq 'Install'
if ($installRequested -and -not $ReportPath) {
    $ReportPath = Join-Path $PSScriptRoot ("reports\setup-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
}
$options = @{
    SystemProfile = $true; IncludeVSCode = -not $SkipVSCode
    IncludeContributorTools = $true; PythonExecutable = $PythonExecutable
    ReportPath = $ReportPath; Verbose = [bool]$PSBoundParameters['Verbose']
    WhatIf = [bool]$WhatIfPreference
}
if ($PSBoundParameters.ContainsKey('Confirm')) { $options.Confirm = $PSBoundParameters['Confirm'] }
if ($installRequested) {
    $options.Install = $true
    $options.AcceptPackageAgreements = $AcceptPackageAgreements
    $options.AcceptDockerLicense = $AcceptDockerLicense
} else { $options.CheckOnly = $true }
& $installer @options
exit $LASTEXITCODE
