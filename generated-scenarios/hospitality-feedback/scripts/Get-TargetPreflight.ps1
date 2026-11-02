<#
.SYNOPSIS
Records authorized read-only subscription evidence without changing Azure resources.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$consent = Get-Content (Join-Path $root 'evidence/preflight-consent.json') -Raw | ConvertFrom-Json
if (!$consent.authorized -or $consent.operation -ne 'read-only-preflight-and-what-if') { throw 'Missing consent' }
$subscription = $consent.subscriptionId
$scope = "/subscriptions/$subscription"
$directory = Join-Path $root 'evidence/preflight'
[System.IO.Directory]::CreateDirectory($directory) | Out-Null
function Invoke-RecordedQuery {
    <#
    .SYNOPSIS
    Records one Azure CLI read, including its actual exit code and timestamp.
    #>
    [CmdletBinding()]
    param([string]$Name, [string[]]$Arguments)
    $started = [DateTime]::UtcNow.ToString('o')
    $output = & az @Arguments 2>&1 | Out-String
    $code = $LASTEXITCODE
    $record = [ordered]@{ checkedAtUtc = $started; command = "az $($Arguments -join ' ')"; exitCode = $code }
    try { $record.result = $output | ConvertFrom-Json } catch { $record.output = $output }
    [System.IO.File]::WriteAllText((Join-Path $directory "$Name.json"), ($record | ConvertTo-Json -Depth 100))
    Write-Host "$Name exit=$code"
    return $record
}
$account = Invoke-RecordedQuery 'account' @('account','show','--subscription',$subscription,'-o','json')
if ($account.exitCode -ne 0 -or $account.result.id -ne $subscription -or
    $account.result.tenantId -ne $consent.tenantId -or $account.result.user.name -ne $consent.account -or
    $account.result.state -ne 'Enabled') { throw 'Target identity mismatch' }
$null = Invoke-RecordedQuery 'deployer' @('ad','signed-in-user','show','--query','{id:id,userPrincipalName:userPrincipalName}','-o','json')
$null = Invoke-RecordedQuery 'rg-exists' @('group','exists','--subscription',$subscription,'--name',$consent.resourceGroupName)
foreach ($provider in @('Microsoft.Resources','Microsoft.Authorization','Microsoft.ManagedIdentity','Microsoft.Storage','Microsoft.CognitiveServices','Microsoft.Web')) {
    $null = Invoke-RecordedQuery "provider-$provider" @('provider','show','--subscription',$subscription,'--namespace',$provider,'-o','json')
}
$policyRecord = Invoke-RecordedQuery 'policies' @('policy','assignment','list','--subscription',$subscription,'--scope',$scope,'--disable-scope-strict-match','-o','json')
foreach ($assignment in $policyRecord.result) {
    $definitionId = $assignment.policyDefinitionId
    $definitionName = $definitionId.Split('/')[-1]
    $definition = Invoke-RecordedQuery "policy-definition-$definitionName" @('rest','--method','get','--url',"https://management.azure.com${definitionId}?api-version=2023-04-01")
    foreach ($child in $definition.result.properties.policyDefinitions) {
        $childId = $child.policyDefinitionId
        $childName = $childId.Split('/')[-1]
        $null = Invoke-RecordedQuery "policy-rule-$childName" @('rest','--method','get','--url',"https://management.azure.com${childId}?api-version=2023-04-01")
    }
}
$null = Invoke-RecordedQuery 'policy-exemptions' @('policy','exemption','list','--subscription',$subscription,'--scope',$scope,'-o','json')
$null = Invoke-RecordedQuery 'permissions' @('rest','--method','get','--url',"https://management.azure.com$scope/providers/Microsoft.Authorization/permissions?api-version=2022-04-01")
$null = Invoke-RecordedQuery 'foundry-role' @('role','definition','list','--subscription',$subscription,'--name','53ca6127-db72-4b80-b1b0-d745d6d5456d','-o','json')
$null = Invoke-RecordedQuery 'web-runtimes' @('webapp','list-runtimes','--os','linux','-o','json')
$null = Invoke-RecordedQuery 'storage-skus-rest' @('rest','--method','get','--url',"https://management.azure.com$scope/providers/Microsoft.Storage/skus?api-version=2024-01-01")
$stackUrl = '"https://management.azure.com/providers/Microsoft.Web/locations/eastus2/webAppStacks?api-version=2024-11-01&stackOsType=Linux"'
$null = Invoke-RecordedQuery 'web-stacks-eastus2' @('rest','--method','get','--url',$stackUrl)
foreach ($region in @('eastus2','westus3','swedencentral')) {
    $null = Invoke-RecordedQuery "models-$region" @('cognitiveservices','model','list','--subscription',$subscription,'--location',$region,'-o','json')
    $null = Invoke-RecordedQuery "usage-$region" @('cognitiveservices','usage','list','--subscription',$subscription,'--location',$region,'-o','json')
    # az.cmd requires embedded quotes to preserve ampersands in a query-string URL on Windows.
    $capacityUrl = "https://management.azure.com$scope/providers/Microsoft.CognitiveServices/locations/$region/modelCapacities?api-version=2025-06-01&modelFormat=OpenAI&modelName=gpt-4.1-mini&modelVersion=2025-04-14"
    if ($IsWindows -or $env:OS -eq 'Windows_NT') { $capacityUrl = "`"$capacityUrl`"" }
    $null = Invoke-RecordedQuery "capacity-$region" @('rest','--method','get','--url',$capacityUrl)
}
$null = Invoke-RecordedQuery 'web-b1-regions' @('appservice','list-locations','--subscription',$subscription,'--sku','B1','--linux-workers-enabled','-o','json')
Write-Output "Read-only evidence saved to $directory"
