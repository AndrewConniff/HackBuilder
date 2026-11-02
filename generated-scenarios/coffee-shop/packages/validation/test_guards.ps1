[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$packages = Split-Path $PSScriptRoot -Parent
$failures = @()
Get-ChildItem (Join-Path $packages 'coach/scripts/*.ps1'),
    (Join-Path $packages 'participant/scripts/*.ps1') | ForEach-Object {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors) { $failures += $errors } else { Write-Output "Parsed $($_.Name)" }
}
if ($failures) { $failures; throw 'PowerShell parser errors.' }
# Mock before calling guards: any unexpected CLI contact makes the test fail.
function az { throw 'UNEXPECTED_CLOUD_COMMAND' }
$env:COFFEE_DEPLOY_AUTHORIZED = ''
$env:COFFEE_TEAM_DEPLOY_AUTHORIZED = ''
$env:AZURE_ENV_NAME = ''
$env:AZURE_RESOURCE_GROUP = ''
$env:AZURE_LOCATION = ''
$env:AZURE_SUBSCRIPTION_ID = ''
function Assert-Rejected([string]$script, [string]$expected) {
    try { & $script; throw 'Guard unexpectedly accepted.' }
    catch {
        if ($_.Exception.Message -notlike "*$expected*") { throw }
        Write-Output "Rejected locally: $expected"
    }
}
$coach = Join-Path $packages 'coach/scripts/Assert-DeploymentScope.ps1'
$team = Join-Path $packages 'participant/scripts/Assert-TeamScope.ps1'
Assert-Rejected $coach 'Separate event deployment authorization'
Assert-Rejected (Join-Path $packages 'coach/scripts/Initialize-Scenario.ps1') 'Deployment authorization required'
$env:COFFEE_DEPLOY_AUTHORIZED = 'yes'
Assert-Rejected $coach 'Wrong coach environment'
$env:AZURE_ENV_NAME = 'coffee-shop-coach'
$env:AZURE_RESOURCE_GROUP = 'rg-coffee-shop-coach'
Assert-Rejected $coach 'Missing destination input'
Assert-Rejected $team 'Separate team rollout authorization'
$env:COFFEE_TEAM_DEPLOY_AUTHORIZED = 'yes'
Assert-Rejected $team 'Invalid team environment'
$env:AZURE_ENV_NAME = '01-coffee-shop-hack'
$env:AZURE_RESOURCE_GROUP = 'rg-coffee-shop-coach'
Assert-Rejected $team 'Wrong team group'
$env:AZURE_RESOURCE_GROUP = 'rg-01-coffee-shop-hack'
Assert-Rejected $team 'Explicit destination required'
Write-Output 'All script parser and fail-closed guards passed; mock confirms no cloud commands.'
