<#
.SYNOPSIS
    Creates an external project folder that is compatible with the conductor workflow.
.DESCRIPTION
    Creates a project under a sibling azd-projects directory and a Windows directory
    junction at generated-scenarios/<project>. The conductor uses its expected local
    path while all generated project files remain outside this Git repository.
.PARAMETER ProjectName
    The kebab-case project folder name used by the conductor.
.PARAMETER ExternalRoot
    The external parent directory for projects. The default is ../azd-projects.
.EXAMPLE
    .\scripts\New-AzdScenarioWorkspace.ps1 -ProjectName 'retail-order-api'
.EXAMPLE
    .\scripts\New-AzdScenarioWorkspace.ps1 -ProjectName 'retail-order-api' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9]+(?:-[a-z0-9]+)*$')]
    [string]$ProjectName,

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$ExternalRoot
)

$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Path $PSScriptRoot -Parent
$repositoryParent = Split-Path -Path $repositoryRoot -Parent
$externalProjectsRoot = if ($ExternalRoot) {
    [System.IO.Path]::GetFullPath($ExternalRoot)
} else {
    Join-Path -Path $repositoryParent -ChildPath 'azd-projects'
}
$externalProjectPath = Join-Path -Path $externalProjectsRoot -ChildPath $ProjectName
$generatedScenariosPath = Join-Path -Path $repositoryRoot -ChildPath 'generated-scenarios'
$conductorProjectPath = Join-Path -Path $generatedScenariosPath -ChildPath $ProjectName

if ($externalProjectPath.StartsWith($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "External project path must be outside the repository: $repositoryRoot"
}

if (Test-Path -LiteralPath $conductorProjectPath) {
    $existingItem = Get-Item -LiteralPath $conductorProjectPath -Force
    $existingTarget = [string]($existingItem.Target | Select-Object -First 1)
    $targetMatches = $existingItem.LinkType -eq 'Junction' -and
        [System.IO.Path]::GetFullPath($existingTarget) -eq [System.IO.Path]::GetFullPath($externalProjectPath)

    if (-not $targetMatches) {
        throw "Conductor path already exists and does not target '$externalProjectPath'."
    }
} elseif ($PSCmdlet.ShouldProcess($externalProjectPath, 'Create external project and conductor junction')) {
    $null = New-Item -ItemType Directory -Path $externalProjectPath -Force
    $null = New-Item -ItemType Directory -Path $generatedScenariosPath -Force
    $null = New-Item -ItemType Junction -Path $conductorProjectPath -Target $externalProjectPath
}

[PSCustomObject]@{
    ProjectName = $ProjectName
    ExternalPath = $externalProjectPath
    ConductorPath = $conductorProjectPath
    GitIgnored = $true
}