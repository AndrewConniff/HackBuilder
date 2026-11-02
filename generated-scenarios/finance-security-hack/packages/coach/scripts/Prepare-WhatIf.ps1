<#
.SYNOPSIS
    Writes target-specific ARM parameters and prints a what-if command without running Azure.
.DESCRIPTION
    Refuses unconfirmed targets. Does not log in, choose an account, query Azure or deploy resources.
    Resolve the model and consumer role from live evidence before producing a deployment preview.
.EXAMPLE
    .\Prepare-WhatIf.ps1 -ConfirmedTargetFile ./approved-target.json -OutputDirectory ./preview
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)][string]$ConfirmedTargetFile,
    [Parameter(Mandatory)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$target = Get-Content -LiteralPath $ConfirmedTargetFile -Raw | ConvertFrom-Json
if ($target.targetConfirmed -isnot [bool] -or $target.targetConfirmed -ne $true -or
    $target.liveEvidenceVerified -isnot [bool] -or $target.liveEvidenceVerified -ne $true) {
    throw 'Target confirmation and live service/model/quota/provider evidence are required before what-if preparation.'
}
foreach ($name in @('accountName', 'subscriptionId', 'tenantId', 'resourceGroup', 'location', 'environment', 'principalId',
    'publisherEmail', 'backendAudience', 'agentConsumerRoleId', 'modelName', 'modelVersion', 'modelSku')) {
    if (-not $target.$name) { throw "Confirmed target field is missing: $name" }
}
foreach ($name in @('subscriptionId', 'tenantId', 'principalId', 'agentConsumerRoleId')) {
    $parsed = [guid]::Empty
    if (-not [guid]::TryParse($target.$name, [ref]$parsed) -or $parsed -eq [guid]::Empty) {
        throw "Confirmed target field must be a nonempty GUID: $name"
    }
}
if ($target.environment -notmatch '^[a-z][a-z0-9-]{1,39}$' -or
    $target.location -notmatch '^[a-z][a-z0-9]{1,39}$') {
    throw 'Environment and location must be simple Azure identifiers, not command text.'
}
if ($target.resourceGroup -ne "rg-$($target.environment)") { throw 'Resource group must match rg-{environment}.' }
$parameters = @{}
foreach ($name in @('location', 'environment', 'principalId', 'publisherEmail', 'backendAudience',
    'agentConsumerRoleId', 'modelName', 'modelVersion', 'modelSku')) {
    $parameters[$name] = @{ value = $target.$name }
}
$document = @{
    '$schema' = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
    contentVersion = '1.0.0.0'
    parameters = $parameters
}
if ($PSCmdlet.ShouldProcess($OutputDirectory, 'Write confirmed-target what-if inputs')) {
    $null = New-Item -ItemType Directory -Path $OutputDirectory -Force
    $path = Join-Path $OutputDirectory 'confirmed.parameters.json'
    $document | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding utf8
    $template = Join-Path (Split-Path $PSScriptRoot -Parent) 'infra\main.bicep'
    $quotedTemplate = $template.Replace("'", "''")
    $quotedParameters = "@$path".Replace("'", "''")
    Write-Output "Confirmed account: $($target.accountName); tenant: $($target.tenantId)."
    Write-Output "Verify Azure CLI and azd environment '$($target.environment)' before execution."
    Write-Output "az deployment group what-if --subscription $($target.subscriptionId) --resource-group $($target.resourceGroup) --template-file '$quotedTemplate' --parameters '$quotedParameters'"
    Write-Output 'Command prepared only. No Azure command executed. Review changes and costs before separate consent.'
}
