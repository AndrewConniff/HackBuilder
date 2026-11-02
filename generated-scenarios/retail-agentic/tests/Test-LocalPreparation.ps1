#Requires -Version 7.4
<#
.SYNOPSIS
Validates installer syntax and the incomplete-evidence guard without running any Azure command.
.DESCRIPTION
Parses every installation script and replaces az/azd with failing sentinels before testing the local-only guard.
It never invokes VM bootstrap, the private initialization hook or provisioning.
.EXAMPLE
pwsh -NoProfile -File .\tests\Test-LocalPreparation.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
foreach ($file in Get-ChildItem (Join-Path $root 'scripts') -Filter '*.ps1') {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -gt 0) { throw ($errors.Message -join "`n") }
    Write-Output "PASS syntax: $($file.Name)"
}
$evidence = Get-Content (Join-Path $root '00-region-availability.json') -Raw | ConvertFrom-Json
if ($evidence.evidenceType -ne 'provisional_local_design' -and
    $evidence.selectedRegion -and $evidence.subscriptionId -and $evidence.tenantId) {
    throw 'The guard test requires incomplete target evidence; it never replaces actual deployment evidence.'
}
$script:cliCalls = 0
function az { $script:cliCalls++; throw 'Unexpected Azure CLI invocation in a local-only test.' }
function azd { $script:cliCalls++; throw 'Unexpected azd invocation in a local-only test.' }
$previousLocation = Get-Location
try {
    & (Join-Path $root 'scripts\Install-Reference.ps1')
    throw 'The installer unexpectedly accepted incomplete target evidence.'
} catch {
    if ($_.Exception.Message -notmatch 'No Azure command ran\.' -or $script:cliCalls -ne 0) { throw }
    Write-Output 'PASS incomplete target evidence blocks before any CLI invocation.'
} finally {
    Set-Location $previousLocation
}
