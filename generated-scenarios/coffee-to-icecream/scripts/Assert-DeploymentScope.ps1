<#
.SYNOPSIS
    Blocks provisioning unless an actual reviewed destination scope has been recorded.
.DESCRIPTION
    Compares local scope evidence with the active CLI and azd destination. It grants no permissions.
.EXAMPLE
    .\scripts\Assert-DeploymentScope.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$scopePath = Join-Path $root 'deployment-scope.json'
if (-not (Test-Path -LiteralPath $scopePath)) {
    throw 'No target deployment approval is recorded. Complete authorized readiness, what-if and scope review first.'
}
$scope = Get-Content -Raw -LiteralPath $scopePath | ConvertFrom-Json
if ($scope.projectSlug -ne 'coffee-to-icecream' -or -not $scope.userApproved -or
    [string]::IsNullOrWhiteSpace($scope.userMessage) -or [string]::IsNullOrWhiteSpace($scope.referenceDigest)) {
    throw 'The scope must contain the actual user response and reviewed reference digest.'
}
$inputs = Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object {
    $_.FullName.Substring($root.Length) -notmatch '\\(\.azure|\.private|bin|obj|node_modules|__pycache__)\\' -and
    ($_.Extension -in @('.cs', '.csproj', '.bicep', '.cshtml', '.js', '.css', '.py', '.ps1', '.csv', '.yaml', '.md') -or
        $_.Name -in @('stores.json', 'provenance.json', 'packages.lock.json', 'main.parameters.json')) -or
    ($_.DirectoryName -eq $root -and $_.Name -in @('01-requirements.md', '02-architecture-assessment.md',
        '00-region-availability.json'))
} | Sort-Object FullName
$manifest = ($inputs | ForEach-Object {
    $relative = $_.FullName.Substring($root.Length + 1).Replace('\', '/')
    "$relative`:$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())"
}) -join "`n"
$actualDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData(
    [Text.Encoding]::UTF8.GetBytes($manifest))).ToLowerInvariant()
if ($actualDigest -ne $scope.referenceDigest) {
    throw 'Reviewed design/code inputs changed. Review the affected scope before deployment.'
}
$evidence = Get-Content -Raw (Join-Path $root '00-region-availability.json') | ConvertFrom-Json
if ($evidence.status -ne 'passed' -or $evidence.selectedRegion -ne $scope.region -or
    $evidence.subscriptionId -ne $scope.subscriptionId -or $evidence.tenantId -ne $scope.tenantId) {
    throw 'Exact-target regional readiness has not passed for the reviewed scope.'
}
$context = az account show --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Azure CLI identity observation failed.' }
azd auth login --check-status | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'azd is not authenticated.' }
$destination = azd env get-values --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read the destination azd environment.' }
if ($context.id -ne $scope.subscriptionId -or $context.tenantId -ne $scope.tenantId -or
    $context.user.name -ne $scope.account -or $destination.AZURE_SUBSCRIPTION_ID -ne $scope.subscriptionId -or
    $destination.AZURE_LOCATION -ne $scope.region -or $destination.AZURE_ENV_NAME -ne $scope.environmentName) {
    throw 'CLI/azd target differs from the actual approved destination. Shared defaults were not changed.'
}
Write-Output 'Recorded target scope matches CLI/azd. Native authorization and Azure policy still apply.'
