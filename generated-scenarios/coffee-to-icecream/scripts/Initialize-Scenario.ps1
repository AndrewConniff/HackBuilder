<#
.SYNOPSIS
    Initializes destination-owned fixtures, local accounts and Foundry agents after authorized provisioning.
.DESCRIPTION
    Generates private unique passwords, preserves them for idempotent retries and installs actual endpoint settings.
    No credentials are placed in application content or azd environment settings.
.EXAMPLE
    .\scripts\Initialize-Scenario.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Assert-DeploymentScope.ps1')
$root = Split-Path -Parent $PSScriptRoot
$private = Join-Path $root '.private'
$null = New-Item -ItemType Directory -Path $private -Force
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $private /inheritance:r /grant:r "${identity}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict destination credential directory access.' }
$accessFile = Join-Path $private 'reference-access.json'
if (-not (Test-Path -LiteralPath $accessFile)) {
    $accounts = @()
    foreach ($number in 1..10) {
        $store = '{0:000}' -f $number
        $accounts += @{
            Username = "store$store"; Role = 'StoreManager'; Stores = @($store)
            Password = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
        }
    }
    foreach ($area in @('north', 'south')) {
        $range = if ($area -eq 'north') { 1..5 } else { 6..10 }
        $accounts += @{
            Username = "area$area"; Role = 'AreaManager'; Stores = @($range | ForEach-Object { '{0:000}' -f $_ })
            Password = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
        }
    }
    $accounts | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $accessFile -Encoding utf8
}
$settings = azd env get-values --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read actual provisioned outputs.' }
$env:Storage__Endpoint = $settings.STORAGE_ENDPOINT
$env:Foundry__Endpoint = $settings.FOUNDRY_ENDPOINT
$env:Foundry__Model = $settings.FOUNDRY_MODEL
$env:ICECREAM_ACCESS_FILE = $accessFile
$env:ICECREAM_AGENT_OUTPUT = Join-Path $private 'agent-installation.json'
$project = Join-Path $root 'src\CoffeeShop.Web\CoffeeShop.Web.csproj'
$originalEnvironment = $env:ASPNETCORE_ENVIRONMENT
Push-Location (Split-Path -Parent $project)
try {
    $env:ASPNETCORE_ENVIRONMENT = 'Development'
    dotnet run --project $project --configuration Release --no-launch-profile -- --initialize
    if ($LASTEXITCODE -ne 0) { throw 'Fixture/account/agent installation failed. No runtime success is claimed.' }
} finally {
    $env:ASPNETCORE_ENVIRONMENT = $originalEnvironment
    Pop-Location
}
$agents = Get-Content -Raw -LiteralPath $env:ICECREAM_AGENT_OUTPUT | ConvertFrom-Json
$agentSettings = @($agents.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" })
az webapp config appsettings set --subscription $settings.AZURE_SUBSCRIPTION_ID `
    --resource-group $settings.AZURE_RESOURCE_GROUP --name $settings.AZURE_WEB_NAME `
    --settings @agentSettings --output none
if ($LASTEXITCODE -ne 0) { throw 'Could not wire actual agent endpoints to the web application.' }
Write-Output 'Destination initialized. Private reference-access.json contains local logins; runtime proof remains required.'
