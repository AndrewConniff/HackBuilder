<#
.SYNOPSIS
    Orders authorized identity setup and reference validation within azd.
.DESCRIPTION
    Uses canonical portal grants, never historical consent files or shared-default changes.
    Postdeploy requires an operator token acquired through the prepared PKCE helper.
.EXAMPLE
    .\scripts\Invoke-ReferenceHook.ps1 -Phase preprovision
#>
[CmdletBinding()]
param([Parameter(Mandatory)][ValidateSet('preprovision','predeploy','postdeploy')][string]$Phase)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python scripts\scenario_identity.py guard
if ($LASTEXITCODE -ne 0) { throw 'Canonical authorization guard failed; no Azure operation attempted.' }
switch ($Phase) {
    'preprovision' {
        python scripts\scenario_identity.py install
        if ($LASTEXITCODE -ne 0) { throw 'Scenario identity installation failed.' }
        $identity = Get-Content -Raw .local\identity-outputs.json | ConvertFrom-Json
        $valuesJson = azd env get-values --environment $identity.scope.environment --output json
        if ($LASTEXITCODE -ne 0) { throw 'Cannot read the exact azd environment after identity installation.' }
        $values = $valuesJson | ConvertFrom-Json -AsHashtable
        $template = Get-Content -Raw infra\main.parameters.json
        $resolved = [regex]::Replace($template, '\$\{([A-Z_]+)\}', {
            param($match)
            $name = $match.Groups[1].Value
            if ([string]::IsNullOrWhiteSpace([string]$values[$name])) { throw "Missing deployment output/input: $name" }
            return ([string]$values[$name]).Replace('\','\\').Replace('"','\"')
        }) | ConvertFrom-Json -AsHashtable
        $resolved.parameters.apiAudience.value = $identity.apiAudience
        $resolved.parameters.modelCapacity.value = [int]$resolved.parameters.modelCapacity.value
        $parameterFile = '.local\install.parameters.json'
        $resolved | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 $parameterFile
        $preview = az deployment sub what-if --subscription $identity.scope.subscriptionId `
            --location $identity.scope.region --template-file infra\main.bicep `
            --parameters "@$parameterFile" --validation-level Provider `
            --result-format FullResourcePayloads --no-pretty-print --no-prompt true --output json
        if ($LASTEXITCODE -ne 0) { throw 'Final-identity what-if failed; no ARM provisioning is allowed.' }
        $preview | Set-Content -Encoding utf8 evidence\install-final-identity-what-if.json
        $result = $preview | ConvertFrom-Json
        if ($result.status -ne 'Succeeded') { throw 'Final-identity what-if did not succeed.' }
        $prefix = "/subscriptions/$($identity.scope.subscriptionId)/resourceGroups/$($identity.scope.resourceGroup)"
        foreach ($change in $result.changes) {
            if ($change.changeType -in @('NoChange','Ignore')) { continue }
            if ($change.changeType -notin @('Create','Unsupported') -or `
                ($change.resourceId -ne $prefix -and -not $change.resourceId.StartsWith("$prefix/"))) {
                throw 'Material change or out-of-scope resource detected; consolidated deployment review required.'
            }
            if ($change.changeType -eq 'Unsupported' -and `
                $change.resourceId -notmatch '/providers/Microsoft.Authorization/roleAssignments/') {
                throw 'Unreviewed unsupported resource in final-identity what-if.'
            }
        }
    }
    'predeploy' {
        python scripts\scenario_identity.py verify
        if ($LASTEXITCODE -ne 0) { throw 'Scenario identity verification failed.' }
        $identity = Get-Content -Raw .local\identity-outputs.json | ConvertFrom-Json
        if ($env:API_AUDIENCE -ne $identity.apiAudience -or $env:API_AUDIENCE -like '*preview-only*') {
            throw 'Final verified identity audience must be wired before publication.'
        }
    }
    'postdeploy' {
        dotnet run --project src\HospitalityFeedback.Operator -c Release --no-launch-profile
        if ($LASTEXITCODE -ne 0) { throw 'Authenticated reference installation/acceptance failed.' }
    }
}
