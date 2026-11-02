<#
.SYNOPSIS
Collect exact-target read-only evidence and independent ARM what-if ONLY after explicit authorization.
.DESCRIPTION
Does not register providers, request quota, create directory objects or deploy resources.
Unknown/denied checks are never treated as availability. Raw results require engineering review.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][guid]$TenantId,
    [string[]]$CandidateRegion = @('eastus2','swedencentral'),
    [switch]$AuthorizedReadOnly
)
$ErrorActionPreference = 'Stop'
if (-not $AuthorizedReadOnly) { throw 'Explicit chat authorization for exact-target reads/what-if is required.' }
$root = Split-Path $PSScriptRoot -Parent
$evidence = Join-Path $root 'evidence\readiness'
$null = New-Item -ItemType Directory -Path $evidence -Force
function Save-ReadinessQuery {
    <#
    .SYNOPSIS
    Saves actual CLI output and failure state without claiming eligibility.
    .DESCRIPTION
    Uses the explicit subscription for ARM commands and the verified tenant context for directory commands.
    .EXAMPLE
    Save-ReadinessQuery 'installer' @('ad','signed-in-user','show') -DirectoryQuery
    #>
    [CmdletBinding()]
    param([string]$Name, [string[]]$Arguments, [switch]$DirectoryQuery)
    $queryArguments = @($Arguments)
    if (-not $DirectoryQuery) {
        $queryArguments += @('--subscription', $SubscriptionId.ToString())
    }
    $output = & az @queryArguments -o json 2>&1
    $code = $LASTEXITCODE
    $record = @{
        checkedAtUtc=[DateTimeOffset]::UtcNow.ToString('o');exitCode=$code
        arguments=$queryArguments;status=$(if ($code -eq 0) {'observed-requires-review'} else {'unknown-or-denied'})
        output=($output -join "`n")
    }
    $record | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $evidence "$Name.json") -Encoding utf8
    if ($code -ne 0) { throw "Readiness query failed: $Name. Evidence retained; no fallback authorization." }
    return ($output | ConvertFrom-Json)
}
$account = Save-ReadinessQuery 'account' @('account','show')
if ($account.tenantId -ne $TenantId.ToString() -or $account.id -ne $SubscriptionId.ToString()) {
    throw 'Exact target mismatch.'
}
$null = Save-ReadinessQuery 'providers' @('provider','list')
$null = Save-ReadinessQuery 'policy' @('policy','assignment','list','--scope',"/subscriptions/$SubscriptionId")
$null = Save-ReadinessQuery 'appservice-locations' @('appservice','list-locations','--sku','P0V3','--linux-workers-enabled')
$null = Save-ReadinessQuery 'web-runtimes' @('webapp','list-runtimes','--os','linux')
$roles = Save-ReadinessQuery 'agent-consumer-role' @('role','definition','list','--name','Foundry Agent Consumer')
if (@($roles).Count -ne 1) { throw 'Exact Agent Consumer role unavailable; never substitute broader role silently.' }
$me = Save-ReadinessQuery 'installer' @('ad','signed-in-user','show') -DirectoryQuery
foreach ($region in $CandidateRegion) {
    if ($region -notmatch '^[a-z0-9]+$') { throw 'Invalid region.' }
    $null = Save-ReadinessQuery "$region-models" @('cognitiveservices','model','list','--location',$region)
    $null = Save-ReadinessQuery "$region-model-usage" @('cognitiveservices','usage','list','--location',$region)
    $null = Save-ReadinessQuery "$region-web-usage" @('rest','--method','get','--url',
        "https://management.azure.com/subscriptions/$SubscriptionId/providers/Microsoft.Web/locations/$region/usages?api-version=2024-11-01")
}
Write-Output 'Review candidate evidence: exact model/version/type/capacity 30, P0v3 maximum 3 workers, policies and providers.'
Write-Output 'No region has been automatically selected. Prepare what-if only for an eligible, authorized candidate.'
Write-Output "Installer object ID captured in evidence; consumer role GUID: $($roles.name)"
Write-Output 'ARM what-if cannot predict directory changes, model allocation or post-install authentication.'
