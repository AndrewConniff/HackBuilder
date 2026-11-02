<#
.SYNOPSIS
Build scenario-local, pinned browser assets; no shared tools are installed.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..\src\CoffeeShop.Web')
try {
    npm ci --ignore-scripts --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Browser dependency restore failed.' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Browser build failed.' }
    dotnet restore --locked-mode
    if ($LASTEXITCODE -ne 0) { throw 'Locked .NET restore failed.' }
} finally { Pop-Location }
