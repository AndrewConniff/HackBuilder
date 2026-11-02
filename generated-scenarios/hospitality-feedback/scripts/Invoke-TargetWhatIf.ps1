[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$AuthorizationFile,
    [Parameter(Mandatory)][string]$ResolvedParametersFile,
    [Parameter(Mandatory)][string]$ExpectedEnvironment,
    [switch]$PreviewOnly
)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
function Assert-Equal($Actual, $Expected, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace([string]$Expected) -or $Actual -ne $Expected) {
        throw "$Label mismatch or missing. Stop; never switch targets automatically."
    }
}
$consent = Get-Content -LiteralPath $AuthorizationFile -Raw | ConvertFrom-Json
if ($consent.operation -ne 'read-only-preflight-and-what-if' -or $consent.authorized -ne $true `
    -or [string]::IsNullOrWhiteSpace($consent.userMessage)) {
    throw 'Explicit user-provided exact-target preflight/what-if authorization is required.'
}
foreach ($field in @('account','subscriptionId','tenantId','resourceGroupName','azdEnvironment')) {
    if ([string]::IsNullOrWhiteSpace([string]$consent.$field)) {
        throw "Exact target field '$field' is required before any Azure query."
    }
}
$parameters = (Get-Content -LiteralPath $ResolvedParametersFile -Raw | ConvertFrom-Json).parameters
Assert-Equal $parameters.resourceGroupName.value $consent.resourceGroupName 'Resource group'
Assert-Equal $parameters.environmentName.value $consent.azdEnvironment 'azd environment'
Assert-Equal $ExpectedEnvironment $consent.azdEnvironment 'Expected environment'
if ([string]::IsNullOrWhiteSpace($parameters.location.value) -or $parameters.location.value -match '\$\{|<') {
    throw 'Resolve and validate region/model parameters first.'
}
# No Azure query precedes consent validation. These commands never switch the account.
$accountJson = az account show --output json
if ($LASTEXITCODE -ne 0) { throw 'Authentication is missing. No interactive login attempted.' }
$account = $accountJson | ConvertFrom-Json
Assert-Equal $account.user.name $consent.account 'Account'
Assert-Equal $account.id $consent.subscriptionId 'Subscription'
Assert-Equal $account.tenantId $consent.tenantId 'Tenant'
azd auth login --check-status
if ($LASTEXITCODE -ne 0) { throw 'azd authentication unavailable.' }
$envInfo = azd env get-values --environment $ExpectedEnvironment --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'azd environment is unavailable; no automatic creation.' }
Assert-Equal $envInfo.AZURE_SUBSCRIPTION_ID $consent.subscriptionId 'azd subscription'
Assert-Equal $envInfo.AZURE_RESOURCE_GROUP $consent.resourceGroupName 'azd resource group'
Assert-Equal $envInfo.AZURE_TENANT_ID $consent.tenantId 'azd tenant'
$regionEvidence = Get-Content -Raw '00-region-availability.json' | ConvertFrom-Json
$allowedStatus = $regionEvidence.status -eq 'validated' -or `
    ($PreviewOnly -and $regionEvidence.status -eq 'validated_for_what_if')
if (!$allowedStatus -or $regionEvidence.subscriptionId -ne $consent.subscriptionId `
    -or $regionEvidence.tenantId -ne $consent.tenantId `
    -or $regionEvidence.selectedRegion -ne $parameters.location.value) {
    throw 'Live resource/model/quota/capacity/governance evidence must be recorded first.'
}
$region = $parameters.location.value
if ($parameters.apiAudience.value -like '*preview-only*' -and !$PreviewOnly) {
    throw 'Unresolved API audience is allowed only with -PreviewOnly. Never deploy these parameters.'
}
$started = [DateTime]::UtcNow.ToString('o')
$output = az deployment sub what-if --subscription $consent.subscriptionId --location $region `
    --template-file infra/main.bicep --parameters "@$ResolvedParametersFile" `
    --name "hotel-feedback-$ExpectedEnvironment" --result-format FullResourcePayloads --no-pretty-print `
    --validation-level Provider --no-prompt true --output json 2>&1 | Out-String
$exitCode = $LASTEXITCODE
$record = [ordered]@{
    startedAtUtc = $started
    completedAtUtc = [DateTime]::UtcNow.ToString('o')
    subscriptionId = $consent.subscriptionId
    tenantId = $consent.tenantId
    resourceGroupName = $consent.resourceGroupName
    azdEnvironment = $ExpectedEnvironment
    location = $region
    previewOnly = [bool]$PreviewOnly
    parametersFile = $ResolvedParametersFile
    command = "az deployment sub what-if --subscription $($consent.subscriptionId) --location $region --template-file infra/main.bicep --parameters @$ResolvedParametersFile --name hotel-feedback-$ExpectedEnvironment --result-format FullResourcePayloads --no-pretty-print --validation-level Provider --no-prompt true --output json"
    exitCode = $exitCode
}
try { $record.result = $output | ConvertFrom-Json } catch { $record.output = $output }
[IO.File]::WriteAllText((Join-Path $PWD 'evidence/what-if.json'), ($record | ConvertTo-Json -Depth 100))
Write-Output $output
if ($exitCode -ne 0) { throw "What-if failed (exit $exitCode). See evidence/what-if.json. Do not deploy." }
Write-Output 'STOP: persist and review actual what-if, then obtain separate exact-target deployment confirmation.'
