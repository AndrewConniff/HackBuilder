<#
.SYNOPSIS
Verifies the approved scenario target without creating any directory object.
.DESCRIPTION
Stops on target, authorization or initialization-input mismatches before azd provisioning.
.EXAMPLE
.\scripts\Assert-DeploymentScope.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if ($env:COFFEE_DEPLOY_AUTHORIZED -ne 'yes') { throw 'Recorded deployment authorization required.' }
if ($env:AZURE_ENV_NAME -ne 'coffee-shop-ref' -or $env:AZURE_LOCATION -ne 'swedencentral' -or
    $env:AZURE_SUBSCRIPTION_ID -ne 'efd64343-6ef4-4926-951f-d3229f38bd76') {
    throw 'Target differs from the approved scenario deployment.'
}
$account = az account show --subscription $env:AZURE_SUBSCRIPTION_ID -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $account.tenantId -ne '16b3c013-d300-468d-ac64-7eda0820b6d3') {
    throw 'Authenticated tenant does not match the approved target.'
}
if (-not $env:COFFEE_STORE_PASSWORD -or -not $env:COFFEE_AREA_PASSWORD) {
    throw 'Provide initialization passwords through process environment only; never through source or ARM parameters.'
}
