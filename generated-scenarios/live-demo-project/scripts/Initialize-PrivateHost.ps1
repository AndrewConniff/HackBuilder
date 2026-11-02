<#
.SYNOPSIS
    Bootstraps Azure CLI on the newly provisioned scenario VM and installs its agent.
.DESCRIPTION
    Runs only on the approved dedicated Windows VM. Uses its managed identity,
    checks private endpoint resolution and creates or verifies the exact agent.
.EXAMPLE
    Invoked by Install-PrivateAgent.ps1 after template substitution.
#>
$ErrorActionPreference = 'Stop'
$endpoint = '__PROJECT_ENDPOINT__'
$agentName = '__AGENT_NAME__'
$definition = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__AGENT_DEFINITION_BASE64__'))
$null = New-Item -ItemType Directory -Path 'C:\Scenario' -Force
[IO.File]::WriteAllBytes('C:\Scenario\Test-OperatorAccess.ps1',
    [Convert]::FromBase64String('__OPERATOR_SCRIPT_BASE64__'))
$az = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
if (-not (Test-Path -LiteralPath $az)) {
    $installer = Join-Path $env:TEMP 'scenario-azure-cli.msi'
    Invoke-WebRequest -Uri 'https://aka.ms/installazurecliwindowsx64' -OutFile $installer
    $process = Start-Process msiexec.exe -ArgumentList @('/i', $installer, '/quiet', '/norestart') -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw "VM Azure CLI installation failed: $($process.ExitCode)" }
    Remove-Item -LiteralPath $installer
}
$hostName = ([uri]$endpoint).DnsSafeHost
$addresses = [Net.Dns]::GetHostAddresses($hostName)
if (-not ($addresses | Where-Object { $_.IPAddressToString -like '10.84.1.*' })) {
    throw 'Foundry did not resolve to the scenario private endpoint from the actual execution host.'
}
& $az login --identity --allow-no-subscriptions --output none
if ($LASTEXITCODE -ne 0) { throw 'Scenario VM managed identity sign-in failed.' }
$headers = @('Content-Type=application/json')
$path = Join-Path $env:TEMP 'scenario-agent-definition.json'
Set-Content -LiteralPath $path -Value $definition -Encoding utf8
try {
    $agents = $null
    for ($attempt = 0; $attempt -lt 6; $attempt++) {
        $raw = & $az rest --method get --url "$endpoint/agents?api-version=v1" `
            --resource 'https://ai.azure.com' --output json
        if ($LASTEXITCODE -eq 0) { $agents = $raw | ConvertFrom-Json; break }
        if ($attempt -lt 5) { Start-Sleep -Seconds 20 }
    }
    if ($null -eq $agents) { throw 'Private project access failed after bounded RBAC propagation retries.' }
    $existing = @($agents.data | Where-Object { $_.name -eq $agentName })
    if ($existing.Count -gt 1) { throw 'Multiple scenario agents found; ownership is ambiguous.' }
    if ($existing.Count -eq 0) {
        $created = & $az rest --method post --url "$endpoint/agents?api-version=v1" `
            --resource 'https://ai.azure.com' --headers $headers --body "@$path" --output json
        if ($LASTEXITCODE -ne 0) { throw 'Foundry prompt agent creation failed.' }
        $agent = $created | ConvertFrom-Json
        if ($agent.name -ne $agentName) { throw 'Foundry returned an unexpected agent identity.' }
    } else {
        $raw = & $az rest --method get --url "$endpoint/agents/$agentName`?api-version=v1" `
            --resource 'https://ai.azure.com' --output json
        if ($LASTEXITCODE -ne 0) { throw 'Existing agent definition could not be inspected.' }
        $agent = $raw | ConvertFrom-Json
        $version = $agent.versions.latest
        if ($null -eq $version -or
            $version.description -ne 'Scenario-owned exact company knowledge selection; live-demo-project') {
            throw 'Agent name already exists without the scenario ownership marker on its latest version.'
        }
        $expected = $definition | ConvertFrom-Json
        if ($version.definition.model -ne $expected.definition.model -or
            $version.definition.instructions.Trim() -ne $expected.definition.instructions.Trim() -or
            @($version.definition.tools).Count -ne 1 -or
            $version.definition.tools[0].name -ne 'select_company_answer' -or
            -not $version.definition.tools[0].strict) {
            throw 'Existing scenario agent definition differs; refuse to declare initialization successful.'
        }
    }
    Write-Output 'BROKERAGE_AGENT_READY'
} finally {
    Remove-Item -LiteralPath $path
}
