# FBC Builder system tools

Use this Windows PowerShell 5.1+ entry point to check the complete toolchain and explicitly
download/install missing tools online. No third-party installers are shipped with the repository,
and setup no longer reads or prepares a `system-tools\cache` directory.
The portal's System diagnostics remain read-only and never run this installer.

## Check, preview and install

Run from the repository root after reviewing vendor terms:

```powershell
# Read-only readiness check (also the default with no arguments).
.\system-tools\Install-SystemTools.ps1 -Mode Check

# Preview installation without downloading, installing or writing reports.
.\system-tools\Install-SystemTools.ps1 -Install -WhatIf

# Download and install missing tools from online package sources.
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -Verbose

# Separately authorize a new Docker installation after preparing WSL and reviewing its terms.
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose
```

The full profile includes Python, Git, PowerShell, .NET 10 SDK, Graphviz, Azure CLI,
Azure CLI Bicep, azd, Docker Desktop, Functions Core Tools, k6, VS Code, Node.js/npm and GitHub CLI.
`-Mode Install` is equivalent to `-Install`.
`-IncludeContributorTools` remains accepted for compatibility; Node.js and GitHub CLI are always included.
Use `-SkipVSCode` for a separately managed editor.

Native tools are downloaded through **WinGet** using exact package IDs from the community `winget` source.
Install [Microsoft App Installer](https://learn.microsoft.com/windows/package-manager/winget/#install-winget)
through your approved software channel first if `winget` is unavailable.
WinGet selects available releases for the host; setup no longer pins a native installer catalog.
Bicep is downloaded with `az bicep install`.
Python dependencies are installed into the repository `.venv` from
[`requirements.txt`](../requirements.txt) using pip.
Internet access is required; offline/download-only modes and cache parameters have been removed.
For managed or unsupported hosts, use the [manual inventory and official downloads](
../FBC-Builder-HOWTO.md#manual-tool-inventory-and-official-downloads).

Setup preserves compatible tools and existing environments, installs missing/failed tools, then reruns
readiness checks. An installer exit alone is never proof of readiness.
If Python is missing, a dry run shows the bootstrap step first; rerun after installing Python for the remaining plan.
Timestamped messages and `-Verbose` output distinguish installation, verification and manual actions.

## Manual actions and safety

- Finish active work and close the portal before installation.
- Follow your organization's script-signing policy; setup never changes execution policy or auto-elevates.
- Prepare [WSL 2](https://learn.microsoft.com/windows/wsl/install), virtualization and WSL 2.1.5+ yourself.
  Setup does not enable Windows features or reboot.
- Review [Docker Desktop licensing and requirements](https://docs.docker.com/desktop/setup/install/windows-install/).
  Installing Docker requires separate `-AcceptDockerLicense` consent.
  Docker Desktop is unsupported on Windows Server. Start its Linux engine yourself.
  An installed but stopped/misconfigured engine needs manual repair, not reinstallation.
- Install/enable Copilot and sign in yourself. Install the
  [Scenario Chat bridge](../tools/vscode-chat-bridge/README.md) separately in the local VS Code profile
  that owns the scenario chat. It is required for portal existing-chat navigation, brief confirmation
  and messages, though initial `code chat` handoff can work without it.
  Neither this installer nor a passing System check verifies bridge installation or activation.
- Sign in to Azure CLI and azd yourself; setup never deploys or changes account/subscription defaults.
- Reopen the terminal/VS Code after installation, rerun **Check**, then rerun the portal's System diagnostics.
  Setup does not overwrite the portal's saved reports.

## Reports and exit codes

Installation writes timestamped JSON under the ignored `system-tools\reports` folder.
Checks write nothing unless `-ReportPath` is supplied. `-WhatIf` writes no environment or report files.

```powershell
.\system-tools\Install-SystemTools.ps1 -Mode Check -ReportPath '.\system-tools\reports\check.json'
```

| Exit code | Meaning |
| --- | --- |
| `0` | Selected readiness checks passed. |
| `1` | Unmet checks or a dry run with work remaining. |
| `2` | Setup/check failure; inspect the error and any requested report. |
| `3010` | Installer requested a reboot; reboot manually and rerun checks. |

## Repository hygiene

Keep source, instructions and scripts in Git, not downloaded dependencies.
Legacy `system-tools\cache` folders remain ignored and are never used by setup.
Scenario `.packages` folders are also ignored: restore NuGet dependencies instead of committing them.
Existing local caches are preserved on disk; do not force-add them.
Removing a file in a later commit does not remove its earlier Git objects.
An unpushed commit containing oversized binaries must also be cleaned before GitHub will accept it.
