<#
.SYNOPSIS
Creates or validates this scenario's dedicated single-tenant backend API identity.
.DESCRIPTION
Run only after separately recorded authorization for these exact directory mutations in the target tenant.
Creates one application and service principal, no secret, Graph permissions, consent grants or administrator roles.
Never adopts an object by display name. Exact ownership tags and tenant must match.
.EXAMPLE
.\Initialize-BackendIdentity.ps1 -TenantId $authorizedTenant -SubscriptionId $authorizedSubscription `
    -Account $authorizedAccount -AuthorizedDirectoryWrites -Confirm:$false
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)][guid]$TenantId,
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Account,
    [Parameter(Mandatory)][switch]$AuthorizedDirectoryWrites
)
$ErrorActionPreference = 'Stop'
if (-not $AuthorizedDirectoryWrites) { throw 'Separate exact-tenant directory-write authorization is required.' }
if ($TenantId -eq [guid]::Empty -or $SubscriptionId -eq [guid]::Empty) { throw 'Real authorized IDs required.' }
function Invoke-ScopedAzure {
    <#
    .SYNOPSIS
    Executes an Azure CLI command without changing shared defaults.
    .DESCRIPTION
    Captures JSON and fails explicitly on any CLI error; no token values are requested.
    .EXAMPLE
    Invoke-ScopedAzure -Arguments @('account', 'show')
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string[]]$Arguments)
    $result = & az @Arguments --subscription $SubscriptionId.ToString() --only-show-errors --output json
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI failed: $($Arguments[0..1] -join ' ')" }
    if ($result) { return ($result | ConvertFrom-Json) }
}
$context = Invoke-ScopedAzure -Arguments @('account', 'show')
if ($context.tenantId -ne $TenantId.ToString() -or $context.id -ne $SubscriptionId.ToString() `
    -or $context.user.name -ne $Account) {
    throw 'CLI identity differs from authorized tenant/subscription/account. Review targets in the portal.'
}
$marker = "abc:manu-multi-agent:$($TenantId.ToString())"
$filter = [uri]::EscapeDataString("tags/any(t:t eq '$marker')")
$applications = Invoke-ScopedAzure -Arguments @(
    'rest', '--method', 'GET',
    '--url', "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&`$select=id,appId,tags,signInAudience,identifierUris,api"
)
if ($applications.'@odata.nextLink') { throw 'Unexpected paginated ownership match; review targets.' }
$owned = @($applications.value)
if ($owned.Count -gt 1) { throw 'Multiple owned API applications; target conflict requires review.' }
if ($owned.Count -eq 0) {
    if (-not $PSCmdlet.ShouldProcess($marker, 'Create scenario-owned backend API application')) { return }
    $body = @{
        displayName = 'ABC manu-multi-agent backend'
        signInAudience = 'AzureADMyOrg'
        tags = @($marker)
        api = @{ requestedAccessTokenVersion = 2 }
    } | ConvertTo-Json -Depth 5 -Compress
    $application = Invoke-ScopedAzure -Arguments @(
        'rest', '--method', 'POST', '--url', 'https://graph.microsoft.com/v1.0/applications', '--body', $body
    )
} else {
    $application = $owned[0]
    if ($application.signInAudience -ne 'AzureADMyOrg' -or $marker -notin $application.tags) {
        throw 'Owned object has incompatible audience/ownership; review target rather than broadening access.'
    }
}
$resourceUri = "api://$($application.appId)"
if (@($application.identifierUris).Count -gt 0 -and $resourceUri -notin $application.identifierUris) {
    throw 'Owned object has a conflicting resource URI; target review required.'
}
if ($resourceUri -notin $application.identifierUris -or $application.api.requestedAccessTokenVersion -ne 2) {
    if (-not $PSCmdlet.ShouldProcess($application.id, 'Set unique backend URI and v2 token contract')) { return }
    $body = @{ identifierUris = @($resourceUri); api = @{ requestedAccessTokenVersion = 2 } } |
        ConvertTo-Json -Depth 5 -Compress
    $null = Invoke-ScopedAzure -Arguments @(
        'rest', '--method', 'PATCH',
        '--url', "https://graph.microsoft.com/v1.0/applications/$($application.id)", '--body', $body
    )
}
$filter = [uri]::EscapeDataString("appId eq '$($application.appId)'")
$principals = Invoke-ScopedAzure -Arguments @(
    'rest', '--method', 'GET', '--url', "https://graph.microsoft.com/v1.0/servicePrincipals?`$filter=$filter"
)
if (@($principals.value).Count -gt 1) { throw 'Multiple service principals for owned application.' }
if (@($principals.value).Count -eq 0) {
    if (-not $PSCmdlet.ShouldProcess($application.appId, 'Create owned backend service principal without secrets')) { return }
    $body = @{ appId = $application.appId; tags = @($marker) } | ConvertTo-Json -Compress
    $principal = Invoke-ScopedAzure -Arguments @(
        'rest', '--method', 'POST', '--url', 'https://graph.microsoft.com/v1.0/servicePrincipals', '--body', $body
    )
} else { $principal = $principals.value[0] }
if ($principal.appOwnerOrganizationId -and $principal.appOwnerOrganizationId -ne $TenantId.ToString()) {
    throw 'Backend service principal is not owned by the authorized tenant.'
}
$directory = Join-Path $PSScriptRoot '..\.installation'
$null = New-Item -ItemType Directory -Path $directory -Force
@{
    schemaVersion = 1
    scenario = 'manu-multi-agent'
    tenantId = $TenantId.ToString()
    subscriptionId = $SubscriptionId.ToString()
    ownershipMarker = $marker
    backendClientId = $application.appId
    applicationObjectId = $application.id
    servicePrincipalObjectId = $principal.id
    resourceUri = $resourceUri
    recordedAtUtc = [DateTimeOffset]::UtcNow.ToString('o')
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $directory 'backend-identity.json') -Encoding utf8NoBOM
Write-Output 'Dedicated backend identity recorded privately; no secrets, consent grants or role elevation created.'
