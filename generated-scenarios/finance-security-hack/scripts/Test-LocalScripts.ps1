<#
.SYNOPSIS
    Tests operator-script syntax and consent guards without contacting Azure.
.DESCRIPTION
    Uses process-local command doubles and scenario-local temporary fixtures.
    Never invokes the real Azure CLI, installer, deployment or what-if service.
.EXAMPLE
    .\scripts\Test-LocalScripts.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$scratch = Join-Path $root "artifacts\script-guards-$([guid]::NewGuid().ToString('N'))"
$null = New-Item -ItemType Directory -Path $scratch -Force
$results = [System.Collections.Generic.List[string]]::new()
if (Test-Path variable:global:FinanceSecurityGuardState) { throw 'Guard suite is already active in this process.' }
$global:FinanceSecurityGuardState = @{
    AzureCalls = 0
    InstallerCalls = 0
    Account = @{
        id = '11111111-1111-1111-1111-111111111111'
        tenantId = '22222222-2222-2222-2222-222222222222'
        state = 'Enabled'
        user = @{ name = 'operator@example.invalid' }
    }
}

function az {
    # This lexical command double prevents all real Azure CLI execution in this test process.
    $global:FinanceSecurityGuardState.AzureCalls++
    $global:LASTEXITCODE = 0
    $global:FinanceSecurityGuardState.Account | ConvertTo-Json -Depth 4 -Compress
}
function Invoke-BlockedInstaller {
    $global:FinanceSecurityGuardState.InstallerCalls++
    throw 'The installer must not execute in this local guard suite.'
}
function Assert-Rejected {
    param([string]$Name, [scriptblock]$Action, [string]$Expected)
    $caught = $false
    try { & $Action | Out-Null }
    catch {
        if ($_.Exception.Message -notlike "*$Expected*") { throw }
        $caught = $true
    }
    if (-not $caught) { throw "Expected rejection did not occur: $Name" }
    $results.Add($Name)
}

$outputs = @{
    AZURE_CLIENT_ID = '33333333-3333-3333-3333-333333333333'
    GATEWAY_PRINCIPAL_ID = '44444444-4444-4444-4444-444444444444'
    BACKEND_AUDIENCE = 'api://55555555-5555-5555-5555-555555555555'
    FOUNDRY_PROJECT_ENDPOINT = 'https://local-test.services.ai.azure.com/api/projects/brokerage'
    FOUNDRY_AGENT_NAME = 'brokerage-educator'
    FOUNDRY_AGENT_VERSION = '1'
    MODEL_DEPLOYMENT = 'brokerage-model'
    FAQ_BLOB_URL = 'https://localtest.blob.core.windows.net/knowledge/brokerage-faq.md'
    SIGNING_KEY_URL = 'https://local-test.vault.azure.net/keys/receipt'
}
$original = @{}
foreach ($name in $outputs.Keys) { $original[$name] = [Environment]::GetEnvironmentVariable($name) }
$originalTenant = $env:AZURE_TENANT_ID
$initialize = Join-Path $PSScriptRoot 'Initialize-Reference.ps1'
$prepare = Join-Path $PSScriptRoot 'Prepare-WhatIf.ps1'
$installArgs = @{
    SubscriptionId = $global:FinanceSecurityGuardState.Account.id
    TenantId = $global:FinanceSecurityGuardState.Account.tenantId
    AccountName = $global:FinanceSecurityGuardState.Account.user.name
    DotnetPath = 'Invoke-BlockedInstaller'
    Confirm = $false
}
$targetFile = Join-Path $scratch 'target.json'
$preview = Join-Path $scratch 'preview'
$validTarget = @{
    targetConfirmed = $true
    liveEvidenceVerified = $true
    accountName = 'operator@example.invalid'
    subscriptionId = $global:FinanceSecurityGuardState.Account.id
    tenantId = $global:FinanceSecurityGuardState.Account.tenantId
    resourceGroup = 'rg-local-test'
    location = 'eastus2'
    environment = 'local-test'
    principalId = '66666666-6666-6666-6666-666666666666'
    publisherEmail = 'operator@example.invalid'
    backendAudience = $outputs.BACKEND_AUDIENCE
    agentConsumerRoleId = '77777777-7777-7777-7777-777777777777'
    modelName = 'gpt-4.1-mini'
    modelVersion = '2025-04-14'
    modelSku = 'GlobalStandard'
}

try {
    foreach ($file in Get-ChildItem $PSScriptRoot -Filter '*.ps1') {
        $tokens = $null
        $parseErrors = $null
        $null = [System.Management.Automation.Language.Parser]::ParseFile(
            $file.FullName, [ref]$tokens, [ref]$parseErrors)
        if ($parseErrors.Count) { throw "PowerShell syntax errors in $($file.Name): $parseErrors" }
        $results.Add("Syntax: $($file.Name)")
    }
    foreach ($name in $outputs.Keys) { [Environment]::SetEnvironmentVariable($name, $outputs[$name]) }
    Assert-Rejected 'Initialization requires explicit mutation consent' {
        & $initialize @installArgs
    } 'No Azure changes authorized'
    [Environment]::SetEnvironmentVariable('MODEL_DEPLOYMENT', $null)
    Assert-Rejected 'Initialization rejects missing output before Azure access' {
        & $initialize @installArgs -AuthorizeCloudChanges
    } 'Missing nonsecret deployment output'
    $env:MODEL_DEPLOYMENT = $outputs.MODEL_DEPLOYMENT
    $env:FAQ_BLOB_URL = 'http://local-test.invalid/source'
    Assert-Rejected 'Initialization rejects insecure URL before Azure access' {
        & $initialize @installArgs -AuthorizeCloudChanges
    } 'Deployment output must be an HTTPS URL'
    $env:FAQ_BLOB_URL = $outputs.FAQ_BLOB_URL
    & $initialize @installArgs -AuthorizeCloudChanges -WhatIf | Out-Null
    if ($global:FinanceSecurityGuardState.AzureCalls -or $global:FinanceSecurityGuardState.InstallerCalls) {
        throw '-WhatIf or a rejected installation attempted an external command.'
    }
    $results.Add('Initialization WhatIf is local with no Azure or installer execution')
    $global:FinanceSecurityGuardState.Account.user.name = 'different-operator@example.invalid'
    Assert-Rejected 'Initialization rejects mismatched account before installation' {
        & $initialize @installArgs -AuthorizeCloudChanges
    } 'differs from the confirmed enabled target'
    if ($global:FinanceSecurityGuardState.InstallerCalls -or $global:FinanceSecurityGuardState.AzureCalls -ne 1 -or
        $env:AZURE_TENANT_ID -ne $originalTenant) {
        throw ("Account rejection invariant failed: AzureDoubleCalls={0}; InstallerDoubleCalls={1}; TenantRestored={2}" -f
            $global:FinanceSecurityGuardState.AzureCalls, $global:FinanceSecurityGuardState.InstallerCalls,
            ($env:AZURE_TENANT_ID -eq $originalTenant))
    }

    foreach ($case in @(
        @{ Name = 'Reject unconfirmed target'; Field = 'targetConfirmed'; Value = $false; Error = 'Target confirmation' },
        @{ Name = 'Reject string consent'; Field = 'targetConfirmed'; Value = 'true'; Error = 'Target confirmation' },
        @{ Name = 'Reject missing live evidence'; Field = 'liveEvidenceVerified'; Value = $false;
            Error = 'Target confirmation' },
        @{ Name = 'Reject missing account'; Field = 'accountName'; Value = ''; Error = 'field is missing' },
        @{ Name = 'Reject invalid subscription GUID'; Field = 'subscriptionId'; Value = 'not-a-guid';
            Error = 'nonempty GUID' },
        @{ Name = 'Reject environment command text'; Field = 'environment'; Value = 'local; invalid';
            Error = 'simple Azure identifiers' },
        @{ Name = 'Reject resource group mismatch'; Field = 'resourceGroup'; Value = 'rg-other';
            Error = 'must match' }
    )) {
        $target = $validTarget.Clone()
        $target[$case.Field] = $case.Value
        $target | ConvertTo-Json | Set-Content -LiteralPath $targetFile -Encoding utf8
        Assert-Rejected $case.Name {
            & $prepare -ConfirmedTargetFile $targetFile -OutputDirectory $preview
        } $case.Error
    }
    if (Test-Path $preview) { throw 'Rejected preparation wrote output.' }
    $validTarget | ConvertTo-Json | Set-Content -LiteralPath $targetFile -Encoding utf8
    & $prepare -ConfirmedTargetFile $targetFile -OutputDirectory $preview -WhatIf | Out-Null
    if (Test-Path $preview) { throw 'Preparation WhatIf wrote output.' }
    $results.Add('Preparation WhatIf writes nothing')
    $printed = & $prepare -ConfirmedTargetFile $targetFile -OutputDirectory $preview -Confirm:$false
    $document = Get-Content (Join-Path $preview 'confirmed.parameters.json') -Raw | ConvertFrom-Json
    if ($document.parameters.location.value -ne 'eastus2' -or
        $document.parameters.environment.value -ne 'local-test' -or
        @($document.parameters.PSObject.Properties).Count -ne 9 -or
        ($printed -join "`n") -notmatch 'az deployment group what-if --subscription' -or
        $global:FinanceSecurityGuardState.AzureCalls -ne 1 -or $global:FinanceSecurityGuardState.InstallerCalls) {
        throw 'Preview parameters/command or no-cloud invariant failed.'
    }
    $results.Add('Confirmed synthetic fixture produces parameters and command only')
    [pscustomobject]@{
        Status = 'passed'
        Passed = $results.Count
        Checks = $results.ToArray()
        RealAzureCommands = 0
        RealInstallerInvocations = 0
        Note = 'Synthetic local guard tests; not target, installation or live acceptance evidence.'
    } | ConvertTo-Json -Depth 5
}
finally {
    foreach ($name in $original.Keys) { [Environment]::SetEnvironmentVariable($name, $original[$name]) }
    $env:AZURE_TENANT_ID = $originalTenant
    Remove-Item -LiteralPath $scratch -Recurse -Force
    Remove-Variable -Name FinanceSecurityGuardState -Scope Global
}
