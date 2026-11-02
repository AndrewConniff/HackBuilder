<#
.SYNOPSIS
    Checks FBC Builder prerequisites and optionally installs missing local tooling on Windows.
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
.PARAMETER AcceptDockerLicense
    Separately accepts Docker Desktop licensing for a new Docker installation after reviewing subscription terms.
.PARAMETER SystemProfile
    Uses the portal's full System profile, including Docker, Functions Core Tools and k6.
.PARAMETER IncludeVSCode
    Also checks/installs VS Code 1.143+ and its code launcher. Extensions/sign-in remain manual.
.PARAMETER ReportPath
    Optional local JSON outcome, including checks, progress events and any error. Not written with -WhatIf.
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
    [switch]$AcceptDockerLicense,
    [switch]$SystemProfile,
    [switch]$IncludeVSCode,
    [string]$ReportPath,
    [ValidateNotNullOrEmpty()][string]$PythonExecutable = 'python',
    [string]$GraphvizBin,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Path $PSScriptRoot -Parent
$script:setupEvents = [System.Collections.Generic.List[object]]::new()
$script:setupRebootRequired = $false

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
    Write-Verbose ("Running {0} {1}" -f $FilePath, ($ArgumentList -join ' '))
    # Native commands update global scope; a local variable would hide their failures.
    $global:LASTEXITCODE = -1
    $output = & $command @ArgumentList 2>&1 | ForEach-Object {
        Write-Verbose "$_"
        "$_"
    }
    [PSCustomObject]@{ ExitCode = $global:LASTEXITCODE; Output = ($output -join "`n") }
}

function Assert-SetupIdle {
    <#
    .SYNOPSIS
        Rejects installation while saved portal processes or project writers are active.
    .DESCRIPTION
        Reads both current and legacy state without killing processes or clearing leases.
    .EXAMPLE
        Assert-SetupIdle -RepositoryRoot 'C:\FBCBuilder'
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepositoryRoot)
    foreach ($name in @('.fbcbuilder-portal', '.hackbuilder-portal')) {
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
        Get-SetupPython -RepositoryRoot 'C:\FBCBuilder' -Bootstrap 'python'
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

function Write-SetupStatus {
    <#
    .SYNOPSIS
        Displays and retains timestamped setup progress.
    .DESCRIPTION
        Records local operational feedback without changing machine configuration.
    .EXAMPLE
        Write-SetupStatus -Tool 'Git' -State 'installing' -Message 'Running the vendor installer.'
    #>
    [CmdletBinding()]
    param([string]$Tool, [string]$State, [string]$Message)
    $event = [PSCustomObject]@{
        timeUtc = [DateTime]::UtcNow.ToString('o'); tool = $Tool; state = $State; message = $Message
    }
    $script:setupEvents.Add($event)
    Write-Information "[$($event.timeUtc)] [$State] ${Tool}: $Message" -InformationAction Continue
}

function Save-SetupOutcome {
    <#
    .SYNOPSIS
        Writes an explicitly requested local setup report.
    .DESCRIPTION
        Preserves the final checks, progress, reboot state and failure reason; does not run under WhatIf.
    .EXAMPLE
        Save-SetupOutcome -Path '.\system-tools\reports\setup.json' -Status 'checked' -Report $report
    #>
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([string]$Path, [string]$Status, [object]$Report, [string]$Failure, [switch]$Quiet)
    if (-not $Path -or $WhatIfPreference) { return }
    if ($PSCmdlet.ShouldProcess($Path, 'Write local prerequisite outcome report')) {
        $fullPath = [IO.Path]::GetFullPath($Path)
        $null = New-Item -ItemType Directory -Path (Split-Path $fullPath -Parent) -Force
        $outcome = [ordered]@{
            schemaVersion = 1; checkedAtUtc = [DateTime]::UtcNow.ToString('o'); status = $Status
            ready = [bool]($Status -eq 'ready' -and -not $Failure -and -not $script:setupRebootRequired)
            rebootRequired = $script:setupRebootRequired; error = $Failure
            events = @($script:setupEvents.ToArray()); verification = $Report
        }
        [IO.File]::WriteAllText(
            $fullPath, ($outcome | ConvertTo-Json -Depth 14), [Text.UTF8Encoding]::new($false)
        )
        if (-not $Quiet) { Write-Information "Saved setup report: $fullPath" -InformationAction Continue }
    }
}

function Install-SetupPackage {
    <#
    .SYNOPSIS
        Downloads and installs an explicitly approved native package through WinGet.
    .DESCRIPTION
        Uses repository-owned arguments, never auto-elevates/reboots and surfaces native errors and reboot requests.
    .EXAMPLE
        Install-SetupPackage -PackageId 'Git.Git' -WhatIf
    #>
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([Parameter(Mandatory)][string]$PackageId)
    if (-not $PSCmdlet.ShouldProcess($PackageId, 'Install/repair native prerequisite')) { return }
    if ($PackageId -eq 'Docker.DockerDesktop') {
        if (-not $AcceptDockerLicense) { throw 'New Docker installation requires separate -AcceptDockerLicense consent.' }
        $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        if ($os.ProductType -ne 1) { throw 'Docker Desktop is not supported on Windows Server. Use a supported client host.' }
        $wsl = Get-Command wsl -ErrorAction SilentlyContinue
        if (-not $wsl) { throw 'Prepare WSL 2 and virtualization manually before installing Docker Desktop.' }
        $version = Invoke-SetupCommand wsl @('--version')
        $status = Invoke-SetupCommand wsl @('--status')
        $text = $version.Output -replace "`0", ''
        if ($version.ExitCode -ne 0 -or $status.ExitCode -ne 0 -or
            $text -notmatch '(\d+\.\d+\.\d+)' -or [version]$Matches[1] -lt [version]'2.1.5') {
            throw 'Docker needs working WSL 2.1.5+ and virtualization. Prepare these manually, reboot if needed, then retry.'
        }
    }
    Write-SetupStatus $PackageId 'installing' 'This can take several minutes; -Verbose shows command output.'
    $result = Invoke-SetupCommand winget @(
        'install', '--id', $PackageId, '--exact', '--source', 'winget',
        '--silent', '--disable-interactivity', '--accept-package-agreements', '--accept-source-agreements'
    )
    $code = $result.ExitCode
    $output = $result.Output
    # WinGet wraps vendor reboot requests in its own HRESULTs.
    if ($code -in @(3010, 1641, -1978334967, -1978334966, -1978334965)) {
        $script:setupRebootRequired = $true
        Write-SetupStatus $PackageId 'reboot-required' "Installer returned $code. Reboot manually and recheck."
    } elseif ($code -ne 0) {
        throw "$PackageId installation failed (exit $code): $output"
    } else {
        Write-SetupStatus $PackageId 'installed-unverified' 'Installer completed; final tool probes must still pass.'
    }
    Update-SetupProcessPath
}

function Get-SetupCheckReport {
    <#
    .SYNOPSIS
        Runs the existing checker and optional VS Code launcher probe.
    .DESCRIPTION
        Accepts only valid ready/unmet results; a successful installer command is not proof of readiness.
    .EXAMPLE
        Get-SetupCheckReport -Python 'python' -ArgumentList @('-B', $checker, '--json')
    #>
    [CmdletBinding()]
    param([string]$Python, [string[]]$ArgumentList)
    $result = Invoke-SetupCommand $Python $ArgumentList
    if ($result.ExitCode -notin @(0, 1)) { throw "Prerequisite checker failed: $($result.Output)" }
    $report = $result.Output | ConvertFrom-Json
    if ($report.ready -isnot [bool] -or -not @($report.checks).Count -or
        @($report.checks | Where-Object { $_.ok -isnot [bool] -or -not $_.id }).Count -gt 0 -or
        $report.ready -ne (@($report.checks | Where-Object { -not $_.ok }).Count -eq 0) -or
        $report.ready -ne ($result.ExitCode -eq 0)) { throw 'Invalid or inconsistent prerequisite checker result.' }
    if ($IncludeVSCode) {
        $code = Get-Command code -ErrorAction SilentlyContinue
        $probe = if ($code) { Invoke-SetupCommand code @('--version') } else { $null }
        $version = if ($probe -and $probe.Output -match '(?m)^(\d+\.\d+\.\d+)') { [version]$Matches[1] }
        $report.checks += [PSCustomObject]@{
            id = 'vscode'; name = 'VS Code 1.143+ and code launcher'
            ok = [bool]($probe -and $probe.ExitCode -eq 0 -and $version -ge [version]'1.143.0')
            detail = if ($probe) { $probe.Output } else { 'code launcher missing from this process PATH.' }
            winget = 'Microsoft.VisualStudioCode'
        }
        $report.ready = @($report.checks | Where-Object { -not $_.ok }).Count -eq 0
    }
    return $report
}

function Install-SetupBicep {
    <#
    .SYNOPSIS
        Downloads the Azure CLI Bicep component online.
    .DESCRIPTION
        Does not change Azure configuration, accounts or subscription defaults.
    .EXAMPLE
        Install-SetupBicep -WhatIf
    #>
    [CmdletBinding(SupportsShouldProcess = $true)]
    param()
    if (-not $PSCmdlet.ShouldProcess('Azure CLI local Bicep component', 'Run az bicep install (network required)')) {
        return
    }
    Write-SetupStatus 'Bicep' 'installing' 'Downloading the Azure CLI Bicep component (network required).'
    $result = Invoke-SetupCommand az @('bicep', 'install')
    if ($result.ExitCode -ne 0) { throw "Bicep installation failed: $($result.Output)" }
    Write-SetupStatus 'Bicep' 'installed-unverified' 'Final az bicep version probe must still pass.'
}

if ($MyInvocation.InvocationName -eq '.') { return }

$report = $null
try {
    if ($env:OS -ne 'Windows_NT') { throw 'This installer targets Windows. See PREREQUISITES.md for manual setup.' }
    if ($CheckOnly -and $Install) { throw 'Choose -CheckOnly or -Install, not both.' }
    if ($Json -and $Install) { throw '-Json is a check-only report option.' }
    if ($Install -and -not $WhatIfPreference) {
        if (-not $AcceptPackageAgreements) { throw '-Install requires explicit -AcceptPackageAgreements.' }
        Assert-SetupIdle -RepositoryRoot $repositoryRoot
    }
    if ($Install -and -not $Json) {
        Write-SetupStatus 'Setup' 'starting' 'Installing missing tools only. No sign-in, auto-elevation or automatic reboot.'
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
        if ($PSCmdlet.ShouldProcess('Python.Python.3.13', 'Install Python bootstrap')) {
            Install-SetupPackage -PackageId 'Python.Python.3.13'
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
    if ($SystemProfile) { $checkArguments += '--system' }
    elseif ($IncludeDocker) { $checkArguments += '--docker' }
    if ($Install) { Write-SetupStatus 'Checks' 'checking' 'Probing tools, Python dependencies, PNG rendering and NuGet HTTPS.' }
    $report = Get-SetupCheckReport -Python $python -ArgumentList $checkArguments

    if ($Install) {
        foreach ($tool in @($report.checks | Where-Object { $_.ok })) {
            Write-SetupStatus $tool.name 'skipped' 'Already verified; no installation needed.'
        }
        foreach ($tool in @($report.checks | Where-Object { -not $_.ok -and $_.winget })) {
            if ($tool.id -eq 'docker' -and (Get-Command docker -ErrorAction SilentlyContinue)) {
                Write-SetupStatus $tool.name 'manual-action' `
                    'Docker CLI exists. Start/repair its Linux engine and complete licensing/WSL setup manually; not reinstalling.'
                continue
            }
            if ($tool.id -eq 'docker' -and -not $AcceptDockerLicense) {
                Write-SetupStatus $tool.name 'manual-action' `
                    'Review Docker subscription terms; rerun with -AcceptDockerLicense or install Docker manually.'
                continue
            }
            if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
                throw 'WinGet is unavailable. Install Microsoft App Installer through your approved software channel.'
            }
            if ($PSCmdlet.ShouldProcess($tool.winget, "Install/repair $($tool.name)")) {
                Install-SetupPackage -PackageId $tool.winget
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
                Write-SetupStatus 'Python environment' 'creating' 'Creating .venv; existing environments are never replaced.'
                $result = Invoke-SetupCommand $python @('-m', 'venv', $environmentPath)
                if ($result.ExitCode -ne 0) { throw "Virtual environment creation failed: $($result.Output)" }
            }
        }
        $pythonProblems = @($report.checks | Where-Object {
            -not $_.ok -and ($_.id -like 'python-package:*' -or $_.id -in @('venv', 'pip-health'))
        })
        if ($pythonProblems.Count -gt 0 -and $PSCmdlet.ShouldProcess($environmentPath, 'Install requirements.txt with pip')) {
            Write-SetupStatus 'Python dependencies' 'installing' 'Installing requirements.txt into .venv (network required).'
            $result = Invoke-SetupCommand $environmentPython @(
                '-m', 'pip', 'install', '--requirement', (Join-Path $repositoryRoot 'requirements.txt')
            )
            if ($result.ExitCode -ne 0) { throw "Python dependency installation failed: $($result.Output)" }
        }
        $bicep = $report.checks | Where-Object { $_.id -eq 'bicep' }
        if (-not $bicep.ok) { Install-SetupBicep }
        $python = Get-SetupPython -RepositoryRoot $repositoryRoot -Bootstrap $PythonExecutable
        Write-SetupStatus 'Checks' 'verifying' 'Re-running every selected check; an installer exit alone is not success.'
        $report = Get-SetupCheckReport -Python $python -ArgumentList $checkArguments
        foreach ($tool in $report.checks) {
            $state = if ($tool.ok) { 'verified' } else { 'unmet' }
            Write-SetupStatus $tool.name $state $tool.detail
        }
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
    $status = if ($report.ready -and -not $script:setupRebootRequired) { 'ready' } else { 'unmet' }
    Save-SetupOutcome -Path $ReportPath -Status $status -Report $report -Quiet:$Json
    if ($script:setupRebootRequired) {
        Write-Warning 'A native installer requested a reboot. Reboot manually, then rerun Check. Setup is not yet ready.'
        exit 3010
    }
    if ($report.ready) { exit 0 }
    exit 1
} catch {
    $failure = $_.Exception.Message
    Write-Error -Message $failure -ErrorAction Continue
    try { Save-SetupOutcome -Path $ReportPath -Status 'failed' -Report $report -Failure $failure -Quiet:$Json }
    catch { Write-Error "Could not persist setup report: $($_.Exception.Message)" -ErrorAction Continue }
    exit 2
}
