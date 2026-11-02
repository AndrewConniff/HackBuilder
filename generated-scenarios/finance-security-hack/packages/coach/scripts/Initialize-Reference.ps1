<#
.SYNOPSIS
    Installs synthetic FAQs and creates a versioned brokerage agent after authorized provisioning.
.DESCRIPTION
    Requires explicit mutation permission, exact target identity and private network access.
    Does not deploy infrastructure. The application uses AzureCliCredential only in this operator mode.
.EXAMPLE
    .\Initialize-Reference.ps1 -SubscriptionId $subscriptionId -TenantId $tenantId -AccountName $accountName -AuthorizeCloudChanges
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][guid]$TenantId,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$AccountName,
    [Parameter()][ValidateNotNullOrEmpty()][string]$DotnetPath = 'dotnet',
    [Parameter()][switch]$AuthorizeCloudChanges
)
$ErrorActionPreference = 'Stop'
if (-not $AuthorizeCloudChanges) {
    throw 'No Azure changes authorized. Supply this switch only after explicit deployment and installation consent.'
}
$required = @(
    'AZURE_CLIENT_ID', 'GATEWAY_PRINCIPAL_ID', 'BACKEND_AUDIENCE', 'FOUNDRY_PROJECT_ENDPOINT',
    'FOUNDRY_AGENT_NAME', 'FOUNDRY_AGENT_VERSION', 'MODEL_DEPLOYMENT', 'FAQ_BLOB_URL', 'SIGNING_KEY_URL'
)
foreach ($name in $required) {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Missing nonsecret deployment output: $name" }
}
foreach ($name in @('FOUNDRY_PROJECT_ENDPOINT', 'FAQ_BLOB_URL', 'SIGNING_KEY_URL')) {
    $uri = $null
    if (-not [uri]::TryCreate([Environment]::GetEnvironmentVariable($name), [UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -ne 'https' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw "Deployment output must be an HTTPS URL without credentials, query or fragment: $name"
    }
}
$project = Join-Path (Split-Path $PSScriptRoot -Parent) 'src\Brokerage.Web\Brokerage.Web.csproj'
if ($PSCmdlet.ShouldProcess($env:FOUNDRY_PROJECT_ENDPOINT, 'Upload synthetic source and create immutable agent version')) {
    # Keep even read-only Azure access behind ShouldProcess: -WhatIf must remain entirely local.
    $accountJson = & az account show --output json
    if ($LASTEXITCODE -ne 0) { throw 'Azure account check failed.' }
    $account = $accountJson | ConvertFrom-Json
    if ($account.id -ne $SubscriptionId.ToString() -or $account.tenantId -ne $TenantId.ToString() -or
        $account.user.name -ne $AccountName -or $account.state -ne 'Enabled') {
        throw 'Azure CLI account/subscription/tenant differs from the confirmed enabled target. No changes made.'
    }
    $previousTenant = $env:AZURE_TENANT_ID
    try {
        $env:AZURE_TENANT_ID = $TenantId.ToString()
        & $DotnetPath run --project $project --configuration Release -- --initialize
        if ($LASTEXITCODE -ne 0) { throw 'Reference initialization failed. Do not claim acceptance.' }
    }
    finally {
        $env:AZURE_TENANT_ID = $previousTenant
    }
}
