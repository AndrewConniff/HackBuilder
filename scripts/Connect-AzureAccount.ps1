<#
.SYNOPSIS
    Signs in to Azure CLI with an MFA-compatible browser flow.
.DESCRIPTION
    Uses the username to select the Microsoft Entra tenant, opens Microsoft's
    browser authentication, and verifies the active account after sign-in. The
    script never accepts or stores a password or MFA code.
.PARAMETER Username
    The Microsoft Entra user principal name, such as user@contoso.com.
.PARAMETER Tenant
    The optional Microsoft Entra tenant ID or tenant domain.
.EXAMPLE
    .\scripts\Connect-AzureAccount.ps1 -Username 'user@contoso.com'
.EXAMPLE
    .\scripts\Connect-AzureAccount.ps1 -Username 'user@contoso.com' -Tenant 'contoso.onmicrosoft.com'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [ValidatePattern('^[^@\s]+@[^@\s]+$')]
    [string]$Username,

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$Tenant
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command -Name 'az' -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI is not installed or is not available on PATH.'
}

$tenantIdentifier = if ($Tenant) { $Tenant } else { $Username.Split('@', 2)[1] }
$loginArguments = @('login', '--tenant', $tenantIdentifier)

Write-Information "Complete Microsoft sign-in as $Username in the browser window." -InformationAction Continue
& az @loginArguments
if ($LASTEXITCODE -ne 0) {
    throw "Azure CLI sign-in failed with exit code $LASTEXITCODE."
}

$accountJson = & az account show --output json
if ($LASTEXITCODE -ne 0) {
    throw "Azure account verification failed with exit code $LASTEXITCODE."
}

$account = $accountJson | ConvertFrom-Json
if ($account.user.name -ne $Username) {
    throw "Azure signed in as '$($account.user.name)' instead of '$Username'."
}

$account | Select-Object -Property name, tenantId, @{ Name = 'Username'; Expression = { $_.user.name } }