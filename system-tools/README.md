# ABC Builder system tools

One Windows PowerShell 5.1+ entry point downloads the complete native tool baseline and optionally
installs missing tools from those same files. Node.js and GitHub CLI are included by default.
For granular manual installation, use the [HOWTO's official source links](
../ABC-Builder-HOWTO.md#manual-tool-inventory-and-official-downloads).
The portal's System diagnostics remain read-only and never run this installer.

## Download, then optionally install in one flow

Run from the repository root after reviewing vendor terms:

```powershell
# Preview all baseline downloads. No files are written and nothing is installed.
.\system-tools\Install-SystemTools.ps1 -WhatIf

# Download every pinned native tool into system-tools\cache. Nothing is installed.
.\system-tools\Install-SystemTools.ps1 -AcceptPackageAgreements -Verbose

# Download/reuse the same complete cache, then install missing tools in one invocation.
# Review Docker licensing and prepare WSL first when installing Docker.
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose

# Read-only readiness check, including Node.js, GitHub CLI and the VS Code launcher.
.\system-tools\Install-SystemTools.ps1 -Mode Check
```

The complete native baseline includes Python, Git, PowerShell, .NET 10 SDK, Graphviz, Azure CLI,
Azure CLI Bicep, azd, Docker Desktop, Functions Core Tools, k6, VS Code, Node.js/npm and GitHub CLI.
No contributor switch or separate download script is needed.
`-Mode Download` remains an explicit spelling of the default; `-Mode Install` is equivalent to `-Install`.
The former `-IncludeContributorTools` switch remains accepted for compatibility but changes nothing.
`-SkipVSCode` is retained for separately managed editors; omit it for the complete baseline.
Running without agreement consent fails clearly rather than downloading or installing silently.

Setup verifies every requested cache entry before any native installer runs.
It preserves existing compatible tools and repository environments, installs missing/failed tools,
prepares `.venv`/requirements and the cached Azure CLI Bicep component, then reruns all readiness checks.
Clean machines receive the catalogued native versions; setup does not force reinstall or downgrade
compatible existing tools. A passing readiness check does not assert exact installed-version equality.
Existing but unresponsive Docker requires manual engine repair/start, not reinstallation.

Finish active work and close the portal before installation.
Timestamped messages distinguish downloads, cache reuse, installation, verification and manual actions.
`-Verbose` shows operational details. A combined JSON outcome includes download events and final checks.
An installer exit alone is never reported as proof of readiness.

## Reproducible native baseline

[`tool-catalog.json`](tool-catalog.json) is the authoritative version lock, currently
`2026-10-27-windows-x64`. Each recipe pins a version, immutable official download URL,
SHA256 and trusted install command. Downloads do not resolve "latest" and do not require WinGet.
For VS Code, the baseline uses the official 1.143.1 release, not the older WinGet package.
PowerShell uses its MSI directly, not the alternative MSIX package.
Azure CLI Bicep uses the official standalone binary, copied during installation into
`AZURE_CONFIG_DIR\bin\bicep.exe`, or `~\.azure\bin\bicep.exe` when that variable is unset.
Azure account/configuration defaults are never changed.

The cache lives at `system-tools\cache\<tool-id>` with the installer/binary and a receipt.
The SHA256 must match the repository lock both on download and on every reuse, independently of
the receipt. Authenticode must also validate, except for catalogued open-source unsigned exceptions.
Receipts record version, architecture, filename, SHA256, signature/publisher and download time.
Earlier valid receipts without a version can be reused only when their bytes match the pinned SHA256.
Never edit a receipt/hash just to make a failed verification pass.

The lock is committed; third-party binaries and reports are local and Git-ignored.
A new clone downloads the same locked versions. Local files are not included in source exports.
Transfer an approved cache together with its receipts and the matching repository/catalog revision.
Do not redistribute vendor software without permission.

Re-running setup reuses verified files and downloads only missing entries.
Downloads stop on the first failure; a few existing folders do not mean the complete cache is ready.
Preserve/inspect incomplete or older-baseline entries and select a new cache directory if necessary:

```powershell
.\system-tools\Install-SystemTools.ps1 -AcceptPackageAgreements -CacheDirectory 'D:\ABC-Builder-cache' -Verbose
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense `
    -CacheDirectory 'D:\ABC-Builder-cache' -Verbose
```

To prohibit new downloads and install only from an already complete cache:

```powershell
.\system-tools\Install-SystemTools.ps1 -Install -UseCachedInstallers `
    -AcceptPackageAgreements -AcceptDockerLicense -Verbose
```

Maintainers update the lock deliberately: review the official release/version, architecture, URL,
SHA256 and install arguments, then test a new cache. Existing cache mismatches fail rather than
silently switching versions or falling back to online native installation.
Custom cache/report directories are your responsibility; only the default local directories are ignored.

## Architecture and offline limits

Downloads can prepare the Windows x64 baseline from an ARM64 Windows host.
Installation of this baseline requires **Windows x64**; ARM64 users should use vendor-native manual
installers from the HOWTO. The script does not try to install incompatible packages.
Allow several GB of free space.

**This is not a complete air-gapped prerequisite bundle.**
Native tools, including Bicep, are pinned and cached, but Python requirements are still installed
online from [`requirements.txt`](../requirements.txt), which specifies minimums rather than a lock.
Vendor dependencies, WSL images, Copilot/extensions and generated application NuGet packages are not bundled.
Final NuGet HTTPS verification and Copilot/Azure sign-in require connectivity.
Use an IT-approved complete software/package mirror for genuinely offline setup.

## Manual actions and safety

- Prepare [WSL 2](https://learn.microsoft.com/windows/wsl/install), virtualization and WSL 2.1.5+ yourself.
  Setup does not enable Windows features or reboot.
- Review [Docker Desktop licensing and requirements](https://docs.docker.com/desktop/setup/install/windows-install/).
  Installing Docker additionally requires `-AcceptDockerLicense`; without it, Docker remains a manual action.
  Docker Desktop is unsupported on Windows Server. Start/switch to a Linux engine yourself.
- Vendor installers may need administrator approval. Setup does not auto-elevate or change execution policy.
- Install/enable GitHub Copilot, sign in, review Workspace Trust and configure the `code` launcher yourself.
  Install the optional [Scenario Chat bridge](../tools/vscode-chat-bridge/README.md) separately.
- Sign in to Azure CLI and azd yourself; setup never queries resources, deploys or changes shared defaults.
- Reopen the terminal/VS Code after installation, rerun **Check**, then rerun both System diagnostics in the portal.
  The installer does not overwrite the portal's saved reports.

## Reports and exit codes

Downloads/installation write timestamped JSON under the ignored `system-tools\reports` folder.
Check writes no report unless `-ReportPath` is supplied. `-WhatIf` writes no cache, environment or report files.

```powershell
.\system-tools\Install-SystemTools.ps1 -Mode Check -ReportPath '.\system-tools\reports\check.json'
```

| Exit code | Meaning |
| --- | --- |
| `0` | Checks passed, or every requested baseline download verified. Download success is not readiness. |
| `1` | Unmet checks or a preview with pending work. |
| `2` | Explicit setup/download/checker error; inspect the local report. |
| `3010` | A native installer requested a reboot. Reboot manually and recheck; setup is not yet ready. |

For machine-readable raw checks without progress/table output:

```powershell
.\scripts\Install-Prerequisites.ps1 -CheckOnly -SystemProfile -IncludeContributorTools -IncludeVSCode -Json
.\.venv\Scripts\python.exe -B scripts\check_prerequisites.py --system --contributor --json
```

The [legacy prerequisite installer](../scripts/Install-Prerequisites.ps1) retains its narrower profiles
and online WinGet mode for compatibility; the system-tools entry point always uses the complete cached baseline.
See [PREREQUISITES.md](../PREREQUISITES.md) for PATH, Python, proxy/TLS and identity troubleshooting.
