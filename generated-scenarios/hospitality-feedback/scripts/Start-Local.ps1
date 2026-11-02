[CmdletBinding()]
param([string]$Dotnet = 'dotnet', [int]$Port = 5080)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$env:ASPNETCORE_ENVIRONMENT = 'Development'
$env:Feedback__UseAzurite = 'true'
$env:Feedback__LocalAnonymous = 'true'
$env:ASPNETCORE_URLS = "http://127.0.0.1:$Port"
# Start Azurite separately. Foundry is intentionally not faked if unconfigured.
& $Dotnet run --project src/HospitalityFeedback.Web --no-launch-profile
if ($LASTEXITCODE -ne 0) { throw "Application exited $LASTEXITCODE" }
