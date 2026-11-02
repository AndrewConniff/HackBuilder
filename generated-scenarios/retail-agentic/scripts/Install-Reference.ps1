#Requires -Version 7.4
<#
.SYNOPSIS
Deploys the root reference only after the actual reviewed Azure authorization.
.DESCRIPTION
Requires exact-target live readiness evidence, preserves private credentials and invokes azd in one process tree.
This script is not authorization and must not be run during local-only preparation.
.EXAMPLE
.\scripts\Install-Reference.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
. (Join-Path $PSScriptRoot 'PrivateDirectory.ps1')
$evidence = Get-Content -LiteralPath '00-region-availability.json' -Raw | ConvertFrom-Json
if ($evidence.evidenceType -eq 'provisional_local_design' -or
    -not $evidence.selectedRegion -or -not $evidence.subscriptionId -or -not $evidence.tenantId) {
    throw 'Authorized exact-target readiness and architecture/deployment review are still required. No Azure command ran.'
}
$accountText = & az account show --output json
if ($LASTEXITCODE -ne 0) { throw 'Azure CLI context could not be read.' }
$account = $accountText | ConvertFrom-Json
if ($account.id -ne $evidence.subscriptionId -or $account.tenantId -ne $evidence.tenantId) {
    throw 'Azure CLI does not match the reviewed subscription/tenant. Shared defaults were not changed.'
}
$authStatus = (& azd auth login --check-status --no-prompt 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'Azure Developer CLI is not authenticated. No sign-in was attempted.' }
if ($authStatus -notmatch 'Logged in to Azure as ([^\r\n]+)' -or
    $Matches[1].Trim() -ne $account.user.name) {
    throw 'Azure CLI and azd did not identify the same signed-in account. No defaults were changed.'
}
foreach ($field in @('AZURE_SUBSCRIPTION_ID', 'AZURE_TENANT_ID')) {
    $value = & azd env get-value $field
    $expected = if ($field -eq 'AZURE_SUBSCRIPTION_ID') { $evidence.subscriptionId } else { $evidence.tenantId }
    if ($LASTEXITCODE -ne 0 -or $value -ne $expected) {
        throw "The selected azd environment $field does not match the reviewed target."
    }
}
& az extension show --name bastion --query name --output tsv
if ($LASTEXITCODE -ne 0) {
    throw 'The Bastion Azure CLI extension is required. This installer does not install workstation software.'
}
$environmentName = & azd env get-value AZURE_ENV_NAME
if ($LASTEXITCODE -ne 0 -or $environmentName -notmatch '^[a-zA-Z0-9-]{3,20}$') {
    throw 'Select the reviewed azd environment first.'
}
$region = & azd env get-value AZURE_LOCATION
if ($LASTEXITCODE -ne 0 -or $region -ne $evidence.selectedRegion) {
    throw 'The azd location does not match the reviewed exact-target evidence.'
}
$private = Join-Path $root ".private\$environmentName"
Initialize-PrivateDirectory -Path $private
$accessFile = Join-Path $private 'management-access.json'
if (Test-Path -LiteralPath $accessFile) {
    $access = Get-Content -LiteralPath $accessFile -Raw | ConvertFrom-Json
} else {
    $password = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(36)) + '!aA1'
    $access = @{ Username = 'scenarioadmin'; Password = $password }
    $access | ConvertTo-Json | Set-Content -LiteralPath $accessFile -Encoding utf8NoBOM
}
$previousPassword = $env:MANAGEMENT_ADMIN_PASSWORD
try {
    $env:MANAGEMENT_ADMIN_PASSWORD = $access.Password
    & azd up --no-prompt
    if ($LASTEXITCODE -ne 0) { throw 'Reference deployment failed. Retain the actual azd error and private receipts.' }
} finally {
    $env:MANAGEMENT_ADMIN_PASSWORD = $previousPassword
}
Write-Output 'Provisioning/publishing finished. Real business, identity, network and deploying-user acceptance are still required.'
