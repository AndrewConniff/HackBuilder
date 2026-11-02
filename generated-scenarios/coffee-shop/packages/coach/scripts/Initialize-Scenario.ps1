<#
.SYNOPSIS
Installs fixtures/agents from this host over public authenticated endpoints and wires real agent outputs.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if ($env:COFFEE_DEPLOY_AUTHORIZED -ne 'yes') { throw 'Deployment authorization required.' }
& (Join-Path $PSScriptRoot 'Assert-DeploymentScope.ps1')
$root = Split-Path $PSScriptRoot -Parent
$values = azd env get-values -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot obtain deployment outputs.' }
$env:Storage__Endpoint = $values.STORAGE_ENDPOINT
$env:Foundry__Endpoint = $values.FOUNDRY_ENDPOINT
$env:Foundry__Model = $values.FOUNDRY_MODEL
# Bootstrap uses the authorized operator, never attempts the workstation's nonexistent managed identity.
$previous = $env:ASPNETCORE_ENVIRONMENT
$env:ASPNETCORE_ENVIRONMENT = 'Development'
Push-Location (Join-Path $root 'src\CoffeeShop.Web')
try {
    dotnet run --no-launch-profile -- --initialize
    if ($LASTEXITCODE -ne 0) { throw 'Fixture/agent initialization failed; do not publish incomplete app.' }
    $settings = Get-Content 'agent-installation.json' -Raw | ConvertFrom-Json -AsHashtable
} finally {
    Pop-Location
    $env:ASPNETCORE_ENVIRONMENT = $previous
}
$arguments = @('webapp','config','appsettings','set','--subscription',$env:AZURE_SUBSCRIPTION_ID,
    '--resource-group',$values.AZURE_RESOURCE_GROUP,'--name',$values.AZURE_WEB_NAME,'--settings')
foreach ($entry in $settings.GetEnumerator()) { $arguments += "$($entry.Key)=$($entry.Value)" }
& az @arguments
if ($LASTEXITCODE -ne 0) { throw 'Real agent configuration output installation failed.' }
