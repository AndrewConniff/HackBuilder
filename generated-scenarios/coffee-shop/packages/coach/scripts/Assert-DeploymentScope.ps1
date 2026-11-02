<#
.SYNOPSIS
Rejects deployment unless a separate event review supplies an exact destination.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if ($env:COFFEE_DEPLOY_AUTHORIZED -ne 'yes') { throw 'Separate event deployment authorization required.' }
if ($env:AZURE_ENV_NAME -ne 'coffee-shop-coach' -or
    $env:AZURE_RESOURCE_GROUP -ne 'rg-coffee-shop-coach') { throw 'Wrong coach environment or resource group.' }
foreach ($name in @('AZURE_LOCATION','AZURE_SUBSCRIPTION_ID','COFFEE_EXPECTED_SUBSCRIPTION_ID',
    'COFFEE_EXPECTED_TENANT_ID','AZURE_PRINCIPAL_ID','FOUNDRY_CONSUMER_ROLE_ID',
    'COFFEE_STORE_PASSWORD','COFFEE_AREA_PASSWORD')) {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Missing destination input: $name" }
}
if ($env:AZURE_SUBSCRIPTION_ID -ne $env:COFFEE_EXPECTED_SUBSCRIPTION_ID) {
    throw 'Subscription differs from separately reviewed destination.'
}
$account = az account show --subscription $env:AZURE_SUBSCRIPTION_ID -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $account.tenantId -ne $env:COFFEE_EXPECTED_TENANT_ID) {
    throw 'Authenticated tenant differs from separately reviewed destination.'
}
