<#
.SYNOPSIS
Bootstraps the new, reviewed private Windows VM through authenticated ARM Run Command.
.DESCRIPTION
Installs verified Microsoft tooling, enables Bastion-only SSH and returns the SSH public host key, never a secret.
.EXAMPLE
Invoke through the reviewed Initialize-PrivateReference.ps1 postprovision hook.
#>
param([Parameter(Mandatory)][string]$PublicKeyBase64)
$ErrorActionPreference = 'Stop'
$key = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PublicKeyBase64))
if ($key -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+(?: .*)?$') { throw 'Invalid ephemeral public key.' }
if ((Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0').State -ne 'Installed') {
    Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
}
Set-Service -Name sshd -StartupType Automatic
Start-Service -Name sshd
$authorized = 'C:\ProgramData\ssh\administrators_authorized_keys'
if (-not (Test-Path -LiteralPath $authorized) -or
    -not ((Get-Content -LiteralPath $authorized) -contains $key)) {
    Add-Content -LiteralPath $authorized -Value $key -Encoding ascii
}
& icacls.exe $authorized /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the SSH authorization file.' }
Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' | Set-NetFirewallRule -RemoteAddress '10.42.3.0/26'
$working = 'C:\ABCBuilder\bootstrap'
New-Item -ItemType Directory -Path $working -Force | Out-Null
$dotnet = 'C:\Program Files\dotnet\dotnet.exe'
$hasSdk = (Test-Path -LiteralPath $dotnet) -and (@(& $dotnet --list-sdks) -match '^10\.').Count -gt 0
if (-not $hasSdk) {
    $releases = Invoke-RestMethod 'https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json'
    $release = $releases.releases | Where-Object { $_.'release-version' -eq $releases.'latest-release' } |
        Select-Object -First 1
    $file = $release.sdk.files | Where-Object { $_.rid -eq 'win-x64' -and $_.name -like '*.exe' } |
        Select-Object -First 1
    if (-not $file -or $file.url -notmatch '^https://(builds\.dotnet\.microsoft\.com|download\.visualstudio\.microsoft\.com)/') {
        throw 'Official .NET 10 SDK release metadata did not contain the expected signed Windows installer.'
    }
    $installer = Join-Path $working 'dotnet-sdk.exe'
    Invoke-WebRequest $file.url -OutFile $installer -UseBasicParsing
    if ((Get-FileHash $installer -Algorithm SHA512).Hash -ne $file.hash) { throw '.NET installer digest mismatch.' }
    $signature = Get-AuthenticodeSignature $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw '.NET installer signature is not valid Microsoft code.'
    }
    $process = Start-Process $installer -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw ".NET installation failed: $($process.ExitCode)." }
}
if (-not (Test-Path -LiteralPath $dotnet) -or (@(& $dotnet --list-sdks) -match '^10\.').Count -eq 0) {
    throw 'The private execution host does not have the required .NET 10 SDK.'
}
if (-not (Test-Path 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd')) {
    $installer = Join-Path $working 'azure-cli.msi'
    Invoke-WebRequest 'https://aka.ms/installazurecliwindowsx64' -OutFile $installer -UseBasicParsing
    $signature = Get-AuthenticodeSignature $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw 'Azure CLI installer signature is not valid Microsoft code.'
    }
    $process = Start-Process msiexec.exe -ArgumentList '/i', $installer, '/quiet', '/norestart' -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw "Azure CLI installation failed: $($process.ExitCode)." }
}
$hostKey = Get-Content -LiteralPath 'C:\ProgramData\ssh\ssh_host_ed25519_key.pub' -Raw
Write-Output ('ABC_SSH_HOSTKEY:' + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($hostKey.Trim())))
