#Requires -Version 7.4
<#
.SYNOPSIS
Runs private Foundry/data initialization on the actual VNet-connected Windows VM.
.DESCRIPTION
Uses a bounded Bastion SSH tunnel, ARM-authenticated host-key pinning and SHA256-verified artifact transfer.
The local azd process never claims direct private endpoint reachability.
.EXAMPLE
Invoked by azd postprovision after the separately reviewed deployment is authorized.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
. (Join-Path $PSScriptRoot 'PrivateDirectory.ps1')
$values = @{}
foreach ($required in @('AZURE_ENV_NAME', 'AZURE_RESOURCE_GROUP', 'MANAGEMENT_VM_NAME',
        'MANAGEMENT_VM_ID', 'BASTION_NAME', 'STORAGE_TABLE_ENDPOINT', 'STORAGE_BLOB_ENDPOINT',
        'FOUNDRY_PROJECT_ENDPOINT', 'FOUNDRY_MODEL_DEPLOYMENT')) {
    $value = & azd env get-value $required
    if ($LASTEXITCODE -ne 0 -or -not $value) { throw "Missing actual deployment output: $required." }
    $values[$required] = ($value -join "`n").Trim()
}
if ($values.AZURE_ENV_NAME -notmatch '^[a-zA-Z0-9-]{3,20}$') { throw 'Invalid environment name.' }
$private = Join-Path $root ".private\$($values.AZURE_ENV_NAME)"
Initialize-PrivateDirectory -Path $private
$key = Join-Path $private 'initialization-key'
if (-not (Test-Path -LiteralPath $key)) {
    & ssh-keygen.exe -q -t ed25519 -N '' -f $key
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the private deployment SSH key.' }
}
$publicKey = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content "$key.pub" -Raw).Trim()))
$bootstrap = & az vm run-command invoke --resource-group $values.AZURE_RESOURCE_GROUP `
    --name $values.MANAGEMENT_VM_NAME --command-id RunPowerShellScript `
    --scripts "@$PSScriptRoot\Bootstrap-Management.ps1" --parameters "PublicKeyBase64=$publicKey" --output json
if ($LASTEXITCODE -ne 0) { throw 'Private-host bootstrap failed.' }
$message = (($bootstrap | ConvertFrom-Json).value.message -join "`n")
if ($message -notmatch 'ABC_SSH_HOSTKEY:([A-Za-z0-9+/=]+)') { throw 'Bootstrap returned no authenticated SSH host key.' }
$hostKey = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Matches[1]))
if ($hostKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+') { throw 'Invalid returned SSH host key.' }
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = $listener.LocalEndpoint.Port
$listener.Stop()
$knownHosts = Join-Path $private 'known-hosts'
"[127.0.0.1]:$port $hostKey" | Set-Content -LiteralPath $knownHosts -Encoding ascii
$publish = Join-Path $private 'publish'
& dotnet restore (Join-Path $root 'src\Woodgrove.Web\Woodgrove.Web.csproj') --locked-mode --nologo
if ($LASTEXITCODE -ne 0) { throw 'Locked application restore failed; do not silently regenerate dependency locks.' }
& dotnet publish (Join-Path $root 'src\Woodgrove.Web\Woodgrove.Web.csproj') --configuration Release `
    --no-restore --no-self-contained -o $publish --nologo
if ($LASTEXITCODE -ne 0) { throw 'Application publish failed.' }
$archive = Join-Path $private 'reference-runtime.zip'
Compress-Archive -Path (Join-Path $publish '*') -DestinationPath $archive -Force
$digest = (Get-FileHash $archive -Algorithm SHA256).Hash
$tunnel = Start-Process -FilePath (Get-Command az).Source -ArgumentList @(
    'network', 'bastion', 'tunnel', '--resource-group', $values.AZURE_RESOURCE_GROUP,
    '--name', $values.BASTION_NAME, '--target-resource-id', $values.MANAGEMENT_VM_ID,
    '--resource-port', '22', '--port', $port
) -PassThru -WindowStyle Hidden
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($tunnel.HasExited) { throw 'Bastion tunnel exited before readiness.' }
        $probe = [Net.Sockets.TcpClient]::new()
        try {
            $probe.Connect('127.0.0.1', $port)
            $ready = $true
        } catch [Net.Sockets.SocketException] {
            Start-Sleep -Seconds 2
        } finally { $probe.Dispose() }
        if ($ready) { break }
    }
    if (-not $ready) { throw 'Bastion tunnel did not become responsive.' }
    $sshOptions = @('-i', $key, '-o', 'StrictHostKeyChecking=yes', '-o', "UserKnownHostsFile=$knownHosts")
    $target = 'scenarioadmin@127.0.0.1'
    & scp.exe @sshOptions -P $port $archive "${target}:reference-runtime.zip"
    if ($LASTEXITCODE -ne 0) { throw 'Private-host artifact transfer failed.' }
    $remoteRoot = "C:\ABCBuilder\$($values.AZURE_ENV_NAME)"
    $settings = @{
        StorageTableEndpoint = $values.STORAGE_TABLE_ENDPOINT
        StorageBlobEndpoint = $values.STORAGE_BLOB_ENDPOINT
        FoundryProjectEndpoint = $values.FOUNDRY_PROJECT_ENDPOINT
        FoundryModelDeployment = $values.FOUNDRY_MODEL_DEPLOYMENT
    } | ConvertTo-Json -Compress
    $settings64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($settings))
    $remote = @"
`$ErrorActionPreference = 'Stop'
if ((Get-FileHash 'reference-runtime.zip' -Algorithm SHA256).Hash -ne '$digest') { throw 'Artifact digest mismatch.' }
New-Item -ItemType Directory -Path '$remoteRoot' -Force | Out-Null
Expand-Archive -LiteralPath 'reference-runtime.zip' -DestinationPath '$remoteRoot' -Force
Set-Location '$remoteRoot'
`$settings = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$settings64')) | ConvertFrom-Json
`$env:StorageTableEndpoint = `$settings.StorageTableEndpoint
`$env:StorageBlobEndpoint = `$settings.StorageBlobEndpoint
`$env:FoundryProjectEndpoint = `$settings.FoundryProjectEndpoint
`$env:FoundryModelDeployment = `$settings.FoundryModelDeployment
& 'C:\Program Files\dotnet\dotnet.exe' .\Woodgrove.Web.dll --Install=true --InstallationIdentity=ManagedIdentity --AccessDirectory='$remoteRoot\.private'
if (`$LASTEXITCODE -ne 0) { throw 'Private reference initialization failed.' }
Write-Output 'Private initialization completed; runtime and human-administration acceptance still pending.'
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remote))
    & ssh.exe @sshOptions -p $port $target "powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"
    if ($LASTEXITCODE -ne 0) { throw 'Private-host initialization failed.' }
    foreach ($account in @('customer-001', 'customer-002', 'operator-001')) {
        & scp.exe @sshOptions -P $port "${target}:$remoteRoot\.private\$account-access.json" $private
        if ($LASTEXITCODE -ne 0) { throw "Private $account credential retrieval failed." }
    }
    $revoke = @"
`$ErrorActionPreference = 'Stop'
`$key = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$publicKey'))
`$path = 'C:\ProgramData\ssh\administrators_authorized_keys'
`$retained = @(Get-Content -LiteralPath `$path | Where-Object { `$_.Trim() -ne `$key.Trim() })
Set-Content -LiteralPath `$path -Value `$retained -Encoding ascii
if (@(Get-Content -LiteralPath `$path | Where-Object { `$_.Trim() -eq `$key.Trim() }).Count -gt 0) {
    throw 'Deployment SSH authorization was not revoked.'
}
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($revoke))
    & ssh.exe @sshOptions -p $port $target "powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"
    if ($LASTEXITCODE -ne 0) { throw 'Deployment SSH key cleanup failed; private recovery material is retained.' }
    Remove-Item -LiteralPath $key, "$key.pub"
    Write-Output "Separate private account files retrieved to the owner-only deployment directory: $private"
} finally {
    if (-not $tunnel.HasExited) { $tunnel.Kill($true); $tunnel.WaitForExit() }
    if (Test-Path -LiteralPath $key) {
        Write-Warning 'Initialization is incomplete. Restricted SSH recovery material remains for an installer retry.'
    }
}
