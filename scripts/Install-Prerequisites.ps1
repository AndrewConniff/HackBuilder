<#
.SYNOPSIS
    Checks ABC Builder prerequisites and optionally installs missing local tooling on Windows.
.DESCRIPTION
    Checks by default. -Install opts in to WinGet packages, a repository .venv,
    requirements.txt and the Azure CLI Bicep component. Never signs in, deploys,
    changes execution policies, stops processes or modifies Copilot permission rules.
.PARAMETER CheckOnly
    Explicitly selects the default check-only behavior.
.PARAMETER Install
    Installs missing prerequisites. Finish workers and close the portal first.
.PARAMETER AcceptPackageAgreements
    Explicitly accepts WinGet package/source agreements for installation.
.PARAMETER IncludeContributorTools
    Also checks/installs Node.js 22+ and GitHub CLI for tests and publication.
.PARAMETER IncludeDocker
    Also checks/installs Docker Desktop. Engine setup, licensing and reboots remain manual.
.PARAMETER PythonExecutable
    Bootstrap interpreter used to create .venv. Existing repository environments are preserved.
.PARAMETER GraphvizBin
    Optional existing Graphviz bin directory to add to User PATH during -Install.
.PARAMETER Json
    Emits a machine-readable report in check-only mode.
.EXAMPLE
    .\scripts\Install-Prerequisites.ps1 -CheckOnly
.EXAMPLE
    .\scripts\Install-Prerequisites.ps1 -Install -WhatIf
.EXAMPLE
    .\scripts\Install-Prerequisites.ps1 -Install -AcceptPackageAgreements -IncludeContributorTools
#>
#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [switch]$CheckOnly,
    [switch]$Install,
    [switch]$AcceptPackageAgreements,
    [switch]$IncludeContributorTools,
    [switch]$IncludeDocker,
    [ValidateNotNullOrEmpty()][string]$PythonExecutable = 'python',
    [string]$GraphvizBin,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Path $PSScriptRoot -Parent

function Invoke-SetupCommand {
    <#
    .SYNOPSIS
        Captures a local executable's output and exit code.
    .DESCRIPTION
        Returns nonzero exits explicitly for version probes and throws only for invocation failures.
    .EXAMPLE
        Invoke-SetupCommand -FilePath 'dot' -ArgumentList @('-V')
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$FilePath, [string[]]$ArgumentList = @())
    $command = Get-Command -Name $FilePath -ErrorAction Stop
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    # Native commands update global scope; a local variable would hide their failures.
    $global:LASTEXITCODE = -1
    $output = & $command @ArgumentList 2>&1 | ForEach-Object { "$_" }
    [PSCustomObject]@{ ExitCode = $global:LASTEXITCODE; Output = ($output -join "`n") }
}

function Assert-SetupIdle {
    <#
    .SYNOPSIS
        Rejects installation while saved portal processes or project writers are active.
    .DESCRIPTION
        Reads both current and legacy state without killing processes or clearing leases.
    .EXAMPLE
        Assert-SetupIdle -RepositoryRoot 'C:\ABCBuilder'
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepositoryRoot)
    foreach ($name in @('.abcbuilder-portal', '.hackbuilder-portal')) {
        $state = Join-Path $RepositoryRoot $name
        $connection = Join-Path $state 'server.json'
        if (Test-Path -LiteralPath $connection) {
            $config = Get-Content -LiteralPath $connection -Raw | ConvertFrom-Json
            if ($config.pid -and (Get-Process -Id $config.pid -ErrorAction SilentlyContinue)) {
                throw "Close the portal after workers finish (recorded PID $($config.pid)), then retry installation."
            }
        }
        $projects = Join-Path $state 'projects'
        if (Test-Path -LiteralPath $projects) {
            foreach ($file in Get-ChildItem -LiteralPath $projects -Filter '*.json') {
                $project = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
                if ($project.writer) {
                    throw "Project '$($project.projectSlug)' has a writer lease. Finish/recover it before installation."
                }
            }
        }
    }
}

function Get-SetupPython {
    <#
    .SYNOPSIS
        Selects the repository virtual environment or the requested bootstrap Python.
    .DESCRIPTION
        Does not create or replace an environment.
    .EXAMPLE
        Get-SetupPython -RepositoryRoot 'C:\ABCBuilder' -Bootstrap 'python'
    #>
    [CmdletBinding()]
    param([string]$RepositoryRoot, [string]$Bootstrap)
    $candidate = Join-Path $RepositoryRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    return $Bootstrap
}

function Update-SetupProcessPath {
    <#
    .SYNOPSIS
        Refreshes the current setup process's PATH after a package installation.
    .DESCRIPTION
        Preserves existing process entries and does not update a running portal's environment.
    .EXAMPLE
        Update-SetupProcessPath
    #>
    [CmdletBinding()]
    param()
    $paths = @(
        [Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [Environment]::GetEnvironmentVariable('Path', 'User'),
        $env:PATH
    )
    $env:PATH = ($paths | Where-Object { $_ }) -join ';'
}

function Repair-SetupGraphvizPath {
    <#
    .SYNOPSIS
        Adds a verified Graphviz installation to User PATH when dot is unresolved.
    .DESCRIPTION
        Runs only with explicit installation consent and ShouldProcess approval.
        Does not scan arbitrary folders or change another process's environment.
    .EXAMPLE
        Repair-SetupGraphvizPath -Directory 'C:\Program Files\Graphviz\bin' -WhatIf
    #>
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([Parameter(Mandatory)][string]$Directory)
    if (Get-Command dot -ErrorAction SilentlyContinue) { return }
    if (-not (Test-Path -LiteralPath (Join-Path $Directory 'dot.exe') -PathType Leaf)) { return }
    if ($PSCmdlet.ShouldProcess($Directory, 'Add verified Graphviz bin directory to User PATH')) {
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        $entries = @($userPath -split ';' | Where-Object { $_ })
        if ($entries -notcontains $Directory) {
            [Environment]::SetEnvironmentVariable('Path', (($entries + $Directory) -join ';'), 'User')
        }
        Update-SetupProcessPath
    }
}

if ($MyInvocation.InvocationName -eq '.') { return }

try {
    if ($env:OS -ne 'Windows_NT') { throw 'This installer targets Windows. See PREREQUISITES.md for manual setup.' }
    if ($CheckOnly -and $Install) { throw 'Choose -CheckOnly or -Install, not both.' }
    if ($Json -and $Install) { throw '-Json is a check-only report option.' }
    if ($Install -and -not $WhatIfPreference) {
        if (-not $AcceptPackageAgreements) { throw '-Install requires explicit -AcceptPackageAgreements.' }
        Assert-SetupIdle -RepositoryRoot $repositoryRoot
    }
    if ($Install) {
        if (-not $GraphvizBin) { $GraphvizBin = Join-Path $env:ProgramFiles 'Graphviz\bin' }
        Repair-SetupGraphvizPath -Directory $GraphvizBin
    }
    $python = Get-SetupPython -RepositoryRoot $repositoryRoot -Bootstrap $PythonExecutable
    $pythonAvailable = Get-Command -Name $python -ErrorAction SilentlyContinue
    if ($pythonAvailable) {
        $probe = Invoke-SetupCommand $python @(
            '-c', 'import sys; print(sys.executable); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
        )
        $pythonAvailable = $probe.ExitCode -eq 0
    }
    if (-not $pythonAvailable) {
        if (-not $Install) { throw 'A working Python 3.10+ is required. Use -PythonExecutable for its exact path.' }
        if (Test-Path -LiteralPath (Join-Path $repositoryRoot '.venv')) {
            throw 'Existing .venv is incomplete or unusable. Preserve/repair it manually; setup will not replace it.'
        }
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            throw 'WinGet is unavailable. Install Microsoft App Installer through your approved software channel.'
        }
        if ($PSCmdlet.ShouldProcess('Python.Python.3.13', 'Install Python bootstrap with WinGet')) {
            $result = Invoke-SetupCommand winget @(
                'install', '--id', 'Python.Python.3.13', '--exact', '--source', 'winget',
                '--silent', '--disable-interactivity', '--accept-package-agreements', '--accept-source-agreements'
            )
            if ($result.ExitCode -ne 0) { throw "Python installation failed: $($result.Output)" }
            Update-SetupProcessPath
            $PythonExecutable = 'python'
            if (Get-Command py -ErrorAction SilentlyContinue) {
                $selection = Invoke-SetupCommand py @('-3.13', '-c', 'import sys; print(sys.executable)')
                if ($selection.ExitCode -ne 0) { throw "Select the new Python explicitly: $($selection.Output)" }
                $PythonExecutable = $selection.Output.Trim()
            }
            $python = $PythonExecutable
        } else {
            Write-Information 'Plan only: bootstrap Python first, then rerun to inspect the remaining tool plan.' `
                -InformationAction Continue
            exit 1
        }
    }
    $checker = Join-Path $repositoryRoot 'scripts\check_prerequisites.py'
    $checkArguments = @('-B', $checker, '--json')
    if ($IncludeContributorTools) { $checkArguments += '--contributor' }
    if ($IncludeDocker) { $checkArguments += '--docker' }
    $result = Invoke-SetupCommand $python $checkArguments
    if ($result.ExitCode -notin @(0, 1)) { throw "Prerequisite checker failed: $($result.Output)" }
    $report = $result.Output | ConvertFrom-Json

    if ($Install) {
        foreach ($tool in @($report.checks | Where-Object { -not $_.ok -and $_.winget })) {
            if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
                throw 'WinGet is unavailable. Install Microsoft App Installer through your approved software channel.'
            }
            if ($PSCmdlet.ShouldProcess($tool.winget, "Install/repair $($tool.name) with WinGet")) {
                $result = Invoke-SetupCommand winget @(
                    'install', '--id', $tool.winget, '--exact', '--source', 'winget',
                    '--silent', '--disable-interactivity', '--accept-package-agreements', '--accept-source-agreements'
                )
                if ($result.ExitCode -ne 0) { throw "$($tool.name) installation failed: $($result.Output)" }
                Update-SetupProcessPath
                if ($tool.id -eq 'python' -and (Get-Command py -ErrorAction SilentlyContinue)) {
                    $selection = Invoke-SetupCommand py @('-3.13', '-c', 'import sys; print(sys.executable)')
                    if ($selection.ExitCode -ne 0) { throw "Select the new Python explicitly: $($selection.Output)" }
                    $PythonExecutable = $selection.Output.Trim()
                    $python = $PythonExecutable
                }
            }
        }
        Repair-SetupGraphvizPath -Directory $GraphvizBin
        $environmentPath = Join-Path $repositoryRoot '.venv'
        $environmentPython = Join-Path $environmentPath 'Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $environmentPython -PathType Leaf)) {
            if (Test-Path -LiteralPath $environmentPath) {
                throw 'Existing .venv is incomplete. Preserve/repair it manually; setup will not delete or replace it.'
            }
            if ($PSCmdlet.ShouldProcess($environmentPath, 'Create repository Python virtual environment')) {
                $result = Invoke-SetupCommand $python @('-m', 'venv', $environmentPath)
                if ($result.ExitCode -ne 0) { throw "Virtual environment creation failed: $($result.Output)" }
            }
        }
        $pythonProblems = @($report.checks | Where-Object {
            -not $_.ok -and ($_.id -like 'python-package:*' -or $_.id -in @('venv', 'pip-health'))
        })
        if ($pythonProblems.Count -gt 0 -and $PSCmdlet.ShouldProcess($environmentPath, 'Install requirements.txt with pip')) {
            $result = Invoke-SetupCommand $environmentPython @(
                '-m', 'pip', 'install', '--requirement', (Join-Path $repositoryRoot 'requirements.txt')
            )
            if ($result.ExitCode -ne 0) { throw "Python dependency installation failed: $($result.Output)" }
        }
        $bicep = $report.checks | Where-Object { $_.id -eq 'bicep' }
        if (-not $bicep.ok -and $PSCmdlet.ShouldProcess('Azure CLI local Bicep component', 'Run az bicep install')) {
            $result = Invoke-SetupCommand az @('bicep', 'install')
            if ($result.ExitCode -ne 0) { throw "Bicep installation failed: $($result.Output)" }
        }
        $python = Get-SetupPython -RepositoryRoot $repositoryRoot -Bootstrap $PythonExecutable
        $result = Invoke-SetupCommand $python $checkArguments
        if ($result.ExitCode -notin @(0, 1)) { throw "Final prerequisite check failed: $($result.Output)" }
        $report = $result.Output | ConvertFrom-Json
    }
    if ($Json) {
        $report | ConvertTo-Json -Depth 8
    } else {
        $report.checks | Select-Object name, ok, detail | Format-Table -Wrap
        Write-Information ("Not checked: " + ($report.notChecked -join '; ')) -InformationAction Continue
        if ($Install) {
            Write-Information 'Reopen your terminal/VS Code after installation. Start the portal only after checks pass.' `
                -InformationAction Continue
        }
    }
    if ($report.ready) { exit 0 }
    exit 1
} catch {
    Write-Error -Message $_.Exception.Message -ErrorAction Continue
    exit 2
}
