[CmdletBinding()]
param(
    [Parameter(Mandatory)][uri]$ApplicationUrl,
    [string]$FixturePath = (Join-Path $PSScriptRoot '../data/feedback.json'),
    [string]$Token = $env:FEEDBACK_API_TOKEN,
    [switch]$LocalOnly
)
$ErrorActionPreference = 'Stop'
if ($LocalOnly) {
    if ($ApplicationUrl.Host -notin @('localhost','127.0.0.1','[::1]')) { throw 'LocalOnly requires loopback.' }
} elseif ($ApplicationUrl.Scheme -ne 'https' -or [string]::IsNullOrWhiteSpace($Token)) {
    throw 'Live fixture import requires HTTPS and an authorized operator token.'
}
$headers = @{}
if ($Token) { $headers.Authorization = "Bearer $Token" }
$data = Get-Content -Raw -LiteralPath $FixturePath | ConvertFrom-Json
foreach ($item in $data) {
    $result = Invoke-RestMethod -Uri "$($ApplicationUrl.ToString().TrimEnd('/'))/api/feedback" `
        -Method Post -ContentType 'application/json; charset=utf-8' -Headers $headers `
        -Body ([Text.Encoding]::UTF8.GetBytes(($item | ConvertTo-Json -Compress)))
    Write-Output "$($result.feedbackId) $($result.state) duplicate=$($result.duplicate) correlation=$($result.correlationId)"
}
