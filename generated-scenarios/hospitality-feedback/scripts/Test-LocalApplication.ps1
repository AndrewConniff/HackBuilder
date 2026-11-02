[CmdletBinding()]
param([uri]$ApplicationUrl = 'http://127.0.0.1:5080')
$ErrorActionPreference = 'Stop'
if ($ApplicationUrl.Host -notin @('localhost','127.0.0.1','[::1]')) {
    throw 'This local-only test must never address an Azure endpoint.'
}
$watch = [Diagnostics.Stopwatch]::StartNew()
$started = [DateTimeOffset]::UtcNow
$root = Split-Path $PSScriptRoot -Parent
$base = $ApplicationUrl.ToString().TrimEnd('/')
$page = Invoke-WebRequest $base
if ($page.StatusCode -ne 200 -or $page.Content -notmatch "Margie's Travel") { throw 'Homepage failed.' }
& (Join-Path $PSScriptRoot 'Import-Fixtures.ps1') -ApplicationUrl $ApplicationUrl -LocalOnly
$fixtures = Get-Content -Raw (Join-Path $root 'data/feedback.json') | ConvertFrom-Json
$deadline = [DateTimeOffset]::UtcNow.AddSeconds(60)
do {
    $statuses = Invoke-RestMethod "$base/api/status"
    $completed = @($statuses | Where-Object { $_.state -eq 'completed' -and $_.feedbackId -in $fixtures.feedbackId })
    if ($completed.Count -eq $fixtures.Count) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTimeOffset]::UtcNow -lt $deadline)
if ($completed.Count -ne 12) { throw "Expected 12 completed records; got $($completed.Count)." }
foreach ($source in $fixtures) {
    $evidence = Invoke-RestMethod "$base/api/evidence/$($source.feedbackId)"
    if ($evidence.feedback.text -cne $source.text -or $evidence.feedback.guestName -cne $source.guestName `
        -or $evidence.feedback.language -cne $source.language) { throw "Roundtrip failed for $($source.feedbackId)" }
}
$body = [Text.Encoding]::UTF8.GetBytes(($fixtures[0] | ConvertTo-Json -Compress))
$duplicate = Invoke-RestMethod "$base/api/feedback" -Method Post -ContentType 'application/json; charset=utf-8' -Body $body
if ($duplicate.duplicate -ne $true -or $duplicate.state -ne 'completed') { throw 'Idempotency failed.' }
$collision = $fixtures[0] | Select-Object *
$collision.text = 'Changed synthetic text'
$conflict = Invoke-WebRequest "$base/api/feedback" -Method Post -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes(($collision | ConvertTo-Json -Compress))) -SkipHttpErrorCheck
if ($conflict.StatusCode -ne 409) { throw 'Expected payload conflict HTTP 409.' }
$invalid = $fixtures[0] | Select-Object *
$invalid.feedbackId = 'HF-7000'
$invalid.text = ''
$badInput = Invoke-WebRequest "$base/api/feedback" -Method Post -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes(($invalid | ConvertTo-Json -Compress))) -SkipHttpErrorCheck
if ($badInput.StatusCode -ne 400) { throw 'Expected invalid feedback HTTP 400.' }
$chat = Invoke-WebRequest "$base/api/chat" -Method Post -ContentType 'application/json' `
    -Body '{"question":"Compare check-in complaints","responseLanguage":"en"}' -SkipHttpErrorCheck
if ($chat.StatusCode -ne 503 -or ($chat.Content | ConvertFrom-Json).mockFallback -ne $false) {
    throw 'Unconfigured Foundry must explicitly fail with HTTP 503, never mock success.'
}
$watch.Stop()
$result = [ordered]@{
    status='passed'; scope='local_application_and_azurite_only'; applicationUrl=$base
    startedAtUtc=$started.ToString('o'); checkedAtUtc=[DateTimeOffset]::UtcNow.ToString('o')
    durationSeconds=[math]::Round($watch.Elapsed.TotalSeconds,3)
    fixturesCompleted=12; languages=@('en','es','fr','ja')
    checks=[ordered]@{ homepage=$true; queuedIngestion=$true; unicodeAndGuestProvenance=$true
        duplicateIdempotency=$true; payloadConflict409=$true; invalidInput400=$true; missingFoundry503=$true }
    liveModelInference=$false; liveAgentInvocation=$false; liveManagedIdentity=$false
}
New-Item -ItemType Directory -Force -Path (Join-Path $root 'evidence') | Out-Null
[IO.File]::WriteAllText((Join-Path $root 'evidence/local-application.json'),
    ($result | ConvertTo-Json -Depth 8) + "`n", [Text.UTF8Encoding]::new($false))
$result | ConvertTo-Json -Depth 8
