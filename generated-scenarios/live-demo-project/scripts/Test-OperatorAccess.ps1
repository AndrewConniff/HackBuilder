<#
.SYNOPSIS
    Verifies the deploying human's administration from the scenario management desktop.
.DESCRIPTION
    Requires the operator to sign in with their own Azure account first. Rejects
    workload identities, verifies private DNS and inherited administration, and
    creates, updates, invokes and deletes a disposable Foundry agent.
    No credentials or tokens are written into the result.
.EXAMPLE
    .\Test-OperatorAccess.ps1 -ReportPath "$HOME\Desktop\operator-access-results.json"
#>
[CmdletBinding()]
param(
    [string]$ReportPath = (Join-Path $HOME 'Desktop\operator-access-results.json')
)
$ErrorActionPreference = 'Stop'
$az = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
$subscription = 'efd64343-6ef4-4926-951f-d3229f38bd76'
$tenant = '16b3c013-d300-468d-ac64-7eda0820b6d3'
$principal = '214d672b-df87-4f3b-94fd-7863032546c1'
$endpoint = 'https://ai-live-demo-project-i7bqs7.services.ai.azure.com/api/projects/brokerage'
$account = & $az account show --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Sign in with your own Azure account on the management desktop first.' }
if ($account.id -ne $subscription -or $account.tenantId -ne $tenant -or $account.user.type -ne 'user') {
    throw 'The management desktop must use the reviewed human subscription and tenant, not a workload identity.'
}
$token = & $az account get-access-token --query accessToken --output tsv
if ($LASTEXITCODE -ne 0) { throw 'Could not verify the current user identity.' }
$payload = $token.Split('.')[1].Replace('-', '+').Replace('_', '/')
$payload = $payload.PadRight($payload.Length + ((4 - $payload.Length % 4) % 4), '=')
$claims = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json
$token = $null
$payload = $null
if ($claims.oid -ne $principal -or $claims.tid -ne $tenant) {
    throw 'The signed-in user is not the reviewed deploying human.'
}
$hostName = ([uri]$endpoint).DnsSafeHost
$addresses = [Net.Dns]::GetHostAddresses($hostName)
if (-not ($addresses | Where-Object { $_.IPAddressToString -like '10.84.1.*' })) {
    throw 'The operator desktop does not resolve the scenario private endpoint.'
}
if (-not (Test-NetConnection -ComputerName $hostName -Port 443 -InformationLevel Quiet)) {
    throw 'The private endpoint is unreachable from the operator desktop.'
}
$roles = @(& $az role assignment list --subscription $subscription --assignee-object-id $principal `
    --scope "/subscriptions/$subscription" --include-inherited --output json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw 'Human role administration could not be verified.' }
if (-not ($roles | Where-Object { $_.roleDefinitionName -eq 'Owner' -and -not $_.condition })) {
    throw 'The expected inherited control-plane administration is unavailable.'
}
$resources = @(& $az resource list --subscription $subscription --resource-group rg-live-demo-project `
    --output json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $resources.Count -eq 0) { throw 'Human resource administration listing failed.' }
$probe = 'operator-access-probe-' + [Guid]::NewGuid().ToString('N').Substring(0, 12)
$file = Join-Path $env:TEMP "$probe.json"
$created = $false
$checks = @('reviewed human identity', 'private DNS and TCP 443', 'inherited Owner and scenario resource listing')
try {
    $definition = @{
        kind = 'prompt'
        model = 'company-selector'
        instructions = 'Reply with the exact text operator-probe-ok. This is disposable synthetic acceptance.'
    }
    @{
        name = $probe
        description = 'Disposable deployment-user administration probe; live-demo-project'
        definition = $definition
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $file -Encoding utf8
    $null = & $az rest --method post --url "$endpoint/agents?api-version=v1" `
        --resource https://ai.azure.com --headers Content-Type=application/json --body "@$file" --output json
    if ($LASTEXITCODE -ne 0) { throw 'Human disposable-agent creation failed.' }
    $created = $true
    $agent = & $az rest --method get --url "$endpoint/agents/$probe`?api-version=v1" `
        --resource https://ai.azure.com --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $agent.name -ne $probe) { throw 'Human disposable-agent read failed.' }
    $checks += 'human agent create and read'
    $definition.instructions = 'Reply with the exact text operator-probe-updated. This is disposable acceptance.'
    @{ definition = $definition } | ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $file -Encoding utf8
    $null = & $az rest --method post --url "$endpoint/agents/$probe/versions?api-version=v1" `
        --resource https://ai.azure.com --headers Content-Type=application/json --body "@$file" --output json
    if ($LASTEXITCODE -ne 0) { throw 'Human disposable-agent version update failed.' }
    $agent = & $az rest --method get --url "$endpoint/agents/$probe`?api-version=v1" `
        --resource https://ai.azure.com --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $agent.versions.latest.definition.instructions -ne $definition.instructions) {
        throw 'Human disposable-agent updated version could not be verified.'
    }
    $checks += 'human agent update and reread'
    @{ input = 'Run the synthetic operator probe.'; store = $false; max_output_tokens = 100 } |
        ConvertTo-Json | Set-Content -LiteralPath $file -Encoding utf8
    $response = & $az rest --method post `
        --url "$endpoint/agents/$probe/endpoint/protocols/openai/responses?api-version=v1" `
        --resource https://ai.azure.com --headers Content-Type=application/json --body "@$file" --output json |
        ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $response.status -ne 'completed' -or -not $response.id) {
        throw 'Human inference through the private agent endpoint failed.'
    }
    $text = ($response.output | ForEach-Object { $_.content } | ForEach-Object { $_.text }) -join ''
    if ($text.Trim() -ne 'operator-probe-updated') { throw 'Human inference returned unexpected probe output.' }
    $checks += 'human private agent inference with real receipt'
} finally {
    if ($created) {
        & $az rest --method delete --url "$endpoint/agents/$probe`?api-version=v1" `
            --resource https://ai.azure.com --output none
        if ($LASTEXITCODE -ne 0) { throw "Probe cleanup failed; remove only disposable agent $probe." }
    }
    if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file }
}
$checks += 'disposable agent and temporary request cleanup'
@{
    status = 'data-plane-passed-browser-confirmation-still-required'
    checkedAtUtc = [DateTimeOffset]::UtcNow.ToString('o')
    host = $env:COMPUTERNAME
    principalId = $principal
    subscriptionId = $subscription
    projectEndpoint = $endpoint
    checks = $checks
    browserEvidence = 'Pending operator confirmation of the Foundry browser experience inside the Bastion desktop.'
    resourcesRead = @($resources | ForEach-Object { $_.id })
    inferenceReceipt = $response.id
    deletedProbe = $probe
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReportPath -Encoding utf8
Write-Output "Human private data-plane checks passed; result saved to $ReportPath."
Write-Output 'Also verify the Foundry project in the browser on this desktop; that human check is still required.'
