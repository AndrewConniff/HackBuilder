<#
.SYNOPSIS
Runs authorized subscription what-if without identity installation; records the dependent configuration limitation.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][guid]$TenantId,
    [Parameter(Mandatory)][guid]$PrincipalId,
    [Parameter(Mandatory)][guid]$AgentConsumerRoleId,
    [Parameter(Mandatory)][string]$Location,
    [switch]$AuthorizedReadOnly
)
$ErrorActionPreference = 'Stop'
if (-not $AuthorizedReadOnly) { throw 'Exact-target read/what-if authorization required.' }
if ($Location -notin 'eastus2','swedencentral') { throw 'Location outside prepared candidate scope.' }
$root = Split-Path $PSScriptRoot -Parent
$parameters = @{
    environmentName=@{value='coffee-shop-ref'};location=@{value=$Location}
    principalId=@{value=$PrincipalId.ToString()}
    agentConsumerRoleId=@{value=$AgentConsumerRoleId.ToString()}
}
$file = [System.IO.Path]::GetTempFileName()
try {
    @{parameters=$parameters} | ConvertTo-Json -Depth 20 | Set-Content $file -Encoding utf8
    $result = az deployment sub what-if --subscription $SubscriptionId --location $Location `
        --template-file (Join-Path $root 'infra\main.bicep') --parameters "@$file" --no-pretty-print -o json 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        @{
            checkedAtUtc=[DateTimeOffset]::UtcNow.ToString('o');exitCode=$code
            subscriptionId=$SubscriptionId;tenantId=$TenantId;location=$Location
            status='failed';output=($result -join "`n")
        } | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $root 'evidence\what-if-failure.json') -Encoding utf8
        throw "ARM what-if failed: $($result -join "`n"). Evidence retained; no readiness claimed."
    }
    @{
        checkedAtUtc=[DateTimeOffset]::UtcNow.ToString('o');subscriptionId=$SubscriptionId;tenantId=$TenantId
        location=$Location;status='resource-preview';whatIf=($result | ConvertFrom-Json)
        limitation='No directory registration. Local accounts are initialized after provisioning; runtime remains untested.'
    } | ConvertTo-Json -Depth 60 | Set-Content (Join-Path $root 'evidence\what-if.json') -Encoding utf8
} finally { Remove-Item -LiteralPath $file -Force }
