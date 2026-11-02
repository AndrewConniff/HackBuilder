[CmdletBinding()]
param([string]$Dotnet = 'dotnet', [switch]$WithAzurite)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
New-Item -ItemType Directory -Force -Path '.local','evidence' | Out-Null
$results = [Collections.Generic.List[object]]::new()
function Invoke-Check([string]$Name, [scriptblock]$Action) {
    $started = [DateTimeOffset]::UtcNow
    $watch = [Diagnostics.Stopwatch]::StartNew()
    & $Action
    $code = $LASTEXITCODE
    $watch.Stop()
    $results.Add([ordered]@{ name=$Name; startedAtUtc=$started.ToString('o')
        durationSeconds=[math]::Round($watch.Elapsed.TotalSeconds,3); exitCode=$code })
    $evidence = [ordered]@{ scope='local_only'; checkedAtUtc=[DateTimeOffset]::UtcNow.ToString('o')
        status= $(if($code -eq 0) {'passed_so_far'} else {'failed'}); commands=$results
        liveDeployment=$false; liveModelInference=$false; liveAgentInvocation=$false }
    [IO.File]::WriteAllText((Join-Path $root 'evidence/local-validation.json'),
        ($evidence | ConvertTo-Json -Depth 8) + "`n", [Text.UTF8Encoding]::new($false))
    if ($code -ne 0) { throw "$Name failed with exit code $code" }
}
Invoke-Check 'dotnet build -c Release' { & $Dotnet build src/HospitalityFeedback.Web -c Release --nologo }
Invoke-Check 'az bicep build (local compilation)' {
    az bicep build --file infra/main.bicep --outfile .local/main.json
}
Invoke-Check 'az bicep lint (local analysis)' { az bicep lint --file infra/main.bicep }
if ($WithAzurite) {
    $env:RUN_AZURITE_TESTS = '1'
    Invoke-Check 'dotnet test (unit and Azurite)' {
        & $Dotnet test tests/HospitalityFeedback.Tests -c Release --nologo `
            --logger 'trx;LogFileName=local-tests.trx' --results-directory evidence/tests
    }
} else {
    Invoke-Check 'dotnet test (unit only)' {
        & $Dotnet test tests/HospitalityFeedback.Tests -c Release --nologo --filter 'Category!=Azurite' `
            --logger 'trx;LogFileName=unit-tests.trx' --results-directory evidence/tests
    }
}
Invoke-Check 'architecture PNG generation' { python 03-architect-diagram.py }
Invoke-Check 'runtime PNG generation' { python 04-runtime-diagram.py }
$final = Get-Content -Raw (Join-Path $root 'evidence/local-validation.json') | ConvertFrom-Json
$final.status = 'passed'
[IO.File]::WriteAllText((Join-Path $root 'evidence/local-validation.json'),
    ($final | ConvertTo-Json -Depth 8) + "`n", [Text.UTF8Encoding]::new($false))
Write-Output 'Local checks complete. No live Azure acceptance or scenario approval is recorded.'
