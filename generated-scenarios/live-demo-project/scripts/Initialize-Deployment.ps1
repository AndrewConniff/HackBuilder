<#
.SYNOPSIS
    Prepares private values for an explicitly authorized scenario deployment.
.DESCRIPTION
    Checks the selected subscription, resolves the existing user and consumer role,
    and generates a deployment-specific VM password without changing shared CLI defaults.
.EXAMPLE
    .\scripts\Initialize-Deployment.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

if (-not $env:AZURE_SUBSCRIPTION_ID -or -not $env:AZURE_LOCATION) {
    throw 'Set the reviewed scenario subscription and location in the azd environment first.'
}
$account = az account show --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Azure CLI context is unavailable.' }
if ($account.id -ne $env:AZURE_SUBSCRIPTION_ID) {
    throw 'Azure CLI subscription differs from the reviewed azd subscription; do not change defaults automatically.'
}
foreach ($key in @('FOUNDRY_MODEL_NAME', 'FOUNDRY_MODEL_VERSION', 'FOUNDRY_MODEL_SKU')) {
    if (-not [Environment]::GetEnvironmentVariable($key)) { throw "Missing reviewed model setting: $key" }
}
$token = az account get-access-token --query accessToken --output tsv
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve current user token metadata.' }
$payload = $token.Split('.')[1].Replace('-', '+').Replace('_', '/')
$payload = $payload.PadRight($payload.Length + ((4 - $payload.Length % 4) % 4), '=')
$claims = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json
$token = $null
if (-not $claims.oid -or $claims.idtyp -eq 'app' -or $claims.tid -ne $account.tenantId) {
    throw 'A matching signed-in human deployment identity is required.'
}
$role = @(az role definition list --name 'Foundry Agent Consumer' --subscription $env:AZURE_SUBSCRIPTION_ID `
    --query '[].name' --output json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or @($role).Count -ne 1) { throw 'Cannot resolve the current consumer role unambiguously.' }
azd env set AZURE_PRINCIPAL_ID $claims.oid
if ($LASTEXITCODE -ne 0) { throw 'Could not save deploying principal.' }
azd env set FOUNDRY_CONSUMER_ROLE_ID $role[0]
if ($LASTEXITCODE -ne 0) { throw 'Could not save the verified consumer role.' }

$inherited = @(az role assignment list --subscription $env:AZURE_SUBSCRIPTION_ID `
    --assignee-object-id $claims.oid --include-inherited `
    --scope "/subscriptions/$($env:AZURE_SUBSCRIPTION_ID)" --output json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw 'Could not verify inherited deployment-user access.' }
$roleIds = @($inherited | Where-Object {
    -not $_.condition -and $_.scope -eq "/subscriptions/$($env:AZURE_SUBSCRIPTION_ID)" -and
    $_.principalId -eq $claims.oid
} |
    ForEach-Object { ($_.roleDefinitionId -split '/')[-1] })
$roleMode = 'assign'
if ($roleIds -contains '8e3af657-a8ff-443c-a75c-2fe8c4bcb635' -and
    $roleIds -contains '53ca6127-db72-4b80-b1b0-d745d6d5456d') {
    $roleMode = 'inherited'
}
azd env set AZURE_DEPLOYER_ROLE_MODE $roleMode
if ($LASTEXITCODE -ne 0) { throw 'Could not save verified deployment-user role mode.' }

$privatePath = Join-Path (Split-Path $PSScriptRoot -Parent) '.private'
$null = New-Item -ItemType Directory -Path $privatePath -Force
if ($IsWindows) {
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $security = [IO.FileSystemAclExtensions]::GetAccessControl(
        [IO.DirectoryInfo]::new($privatePath), [Security.AccessControl.AccessControlSections]::Access)
    $security.SetAccessRuleProtection($true, $false)
    foreach ($rule in $security.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])) {
        $null = $security.RemoveAccessRuleSpecific($rule)
    }
    $security.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($privatePath), $security)
} else {
    & chmod 700 $privatePath
    if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the private directory.' }
}
$accessPath = Join-Path $privatePath 'management-access.json'
if (Test-Path -LiteralPath $accessPath) {
    $access = Get-Content -LiteralPath $accessPath -Raw | ConvertFrom-Json
    if ($access.environment -ne $env:AZURE_ENV_NAME) { throw 'Existing VM credentials belong to another environment.' }
    $password = $access.password
} else {
    $password = 'Aa1!' + [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    @{
        environment = $env:AZURE_ENV_NAME
        username = 'scenarioadmin'
        password = $password
        entry = 'Azure Bastion browser RDP; VM has no public IP'
    } | ConvertTo-Json | Set-Content -LiteralPath $accessPath -Encoding utf8
}
azd env set AZURE_MANAGEMENT_PASSWORD $password
if ($LASTEXITCODE -ne 0) { throw 'Could not save private VM deployment parameter.' }
$password = $null
Write-Output 'Deployment identity, role and private management credential prepared. No resources provisioned by this hook.'
