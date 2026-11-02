<#
.SYNOPSIS
    Installs synthetic fixtures, local accounts and owned Foundry agents after authorized provisioning.
.DESCRIPTION
    Consumes only this azd environment, checks its CLI target, restricts private credential files and runs
    the installer with the deploying user's Azure CLI credential. Does not sign in or change CLI defaults.
.EXAMPLE
    .\scripts\Install-Reference.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $values = azd env get-values --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read this azd environment.' }
    $account = az account show --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Azure CLI sign-in is unavailable.' }
    if ($account.user.type -ne 'user' -or $account.id -ne $values.AZURE_SUBSCRIPTION_ID -or
        $account.tenantId -ne $values.AZURE_TENANT_ID) {
        throw 'Azure CLI must match the reviewed human azd subscription and tenant. Defaults were not changed.'
    }
    $authStatus = azd auth login --check-status --no-prompt | Out-String
    if ($LASTEXITCODE -ne 0) { throw 'azd authentication is unavailable.' }
    if ($authStatus -notmatch 'Logged in to Azure as ([^\r\n]+)' -or
        $Matches[1].Trim() -ine $account.user.name) {
        throw 'Azure CLI and azd account names must match. Sign-in defaults were not changed.'
    }
    foreach ($name in @('STORAGE_TABLE_ENDPOINT', 'FOUNDRY_PROJECT_ENDPOINT', 'FOUNDRY_MODEL_DEPLOYMENT',
        'AZURE_SUBSCRIPTION_ID', 'AZURE_RESOURCE_GROUP', 'AZURE_WEBAPP_NAME', 'APPLICATION_URL')) {
        if (-not $values.$name) { throw "Required deployment output missing: $name" }
        [Environment]::SetEnvironmentVariable($name, $values.$name, 'Process')
    }
    $destination = "$($values.AZURE_SUBSCRIPTION_ID)/$($values.AZURE_RESOURCE_GROUP)/$($values.AZURE_WEBAPP_NAME)"
    $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
        [Text.Encoding]::UTF8.GetBytes($destination))).Substring(0, 16).ToLowerInvariant()
    $private = Join-Path (Join-Path $root '.private') $digest
    $null = New-Item -ItemType Directory -Path $private -Force
    if ($IsWindows) {
        $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        icacls $private /inheritance:r /grant:r "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot restrict the private access directory.' }
    } else {
        [System.IO.File]::SetUnixFileMode($private, [System.IO.UnixFileMode]::UserRead -bor
            [System.IO.UnixFileMode]::UserWrite -bor [System.IO.UnixFileMode]::UserExecute)
    }
    $env:PRIVATE_ACCESS_PATH = $private
    dotnet run --project src\BankSupport.Web --no-launch-profile -- --install
    if ($LASTEXITCODE -ne 0) { throw 'Reference installation failed. Private retry files were retained.' }
    Write-Output "Private reference access directory: $private"
} finally {
    Pop-Location
}
