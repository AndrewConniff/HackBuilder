# ABC Builder prerequisites

Prepare this machine before starting scenario workers. The portal itself uses Python's standard library,
but reference generation also needs the SDKs, native diagram tooling and Python packages below.
The setup covers the shipped baseline, not every package a future scenario might introduce.

## Quick start on Windows

Run from the repository root in PowerShell. Check-only is the default; it installs nothing:

```powershell
.\scripts\Install-Prerequisites.ps1 -CheckOnly
```

Preview changes without installing packages, creating an environment or updating persisted PATH:

```powershell
.\scripts\Install-Prerequisites.ps1 -Install -WhatIf -IncludeContributorTools
```

After finishing workers and closing the portal, explicitly opt in to installation and package agreements:

```powershell
.\scripts\Install-Prerequisites.ps1 -Install -AcceptPackageAgreements -IncludeContributorTools
```

`-IncludeContributorTools` adds Node.js and GitHub CLI for tests, browser MCP tooling and publication.
Omit it for the core scenario-generation toolchain. Add `-IncludeDocker` only if you need local container builds,
after reviewing Docker Desktop licensing and virtualization requirements.

Open a fresh terminal after installation, rerun check-only, then double-click
[`Start-ABCBuilder.cmd`](Start-ABCBuilder.cmd). Do not restart a portal with active workers.
The launcher and startup helper prefer the repository `.venv` for a **new** server and put its scripts on worker PATH.
Existing servers are reused without changing their interpreter or environment.

If PowerShell blocks the script, follow your organization's script-signing/approval procedure.
Setup does not change execution policy. If Python is missing, check-only explains the bootstrap requirement;
installation uses WinGet. A missing-Python dry run lists that first step and must be rerun after Python is available.

## Dependency inventory

| Dependency | Required for | Windows installer ID |
| ---------- | ------------ | -------------------- |
| Python 3.10+ | Portal, workflow helpers and diagrams | `Python.Python.3.13` |
| Git | Repository and local CLI workflows | `Git.Git` |
| GitHub Copilot CLI | Real portal scenario jobs | `GitHub.Copilot` |
| PowerShell 7+ | Workspace and deployment scripts | `Microsoft.PowerShell` |
| .NET **10 SDK** | Building the generated C# application | `Microsoft.DotNet.SDK.10` |
| Graphviz, including `dot` | Rendering architecture/runtime diagrams | `Graphviz.Graphviz` |
| Azure CLI | Authorized Azure validation/deployment | `Microsoft.AzureCLI` |
| Azure Developer CLI | `azd` provisioning/deployment workflows | `Microsoft.Azd` |
| Azure CLI Bicep component | `az bicep build` and `az bicep lint` | Installed with `az bicep install` |
| Repository `.venv` and Python requirements | Diagram generation and policy scanning | See below |
| Node.js 22+, npm/npx | Optional frontend tests and configured browser MCP | `OpenJS.NodeJS.LTS` |
| GitHub CLI | Optional, explicitly requested GitHub publication | `GitHub.cli` |
| Docker Desktop and running engine | Optional local container builds | `Docker.DockerDesktop` |
| VS Code and recommended extensions | Optional interactive editor/custom-agent experience | Manual |

Windows PowerShell 5.1 can run the bootstrap script; PowerShell 7+ remains part of the scenario toolchain.
WinGet comes from Microsoft App Installer. If unavailable, use your approved software channel or manual installers.
Package installers may need elevation, network/proxy access or a reboot; setup reports nonzero failures and stops.
It does not automatically elevate, reboot, enable WSL/Hyper-V, start Docker, or accept Docker licensing for you.

The authoritative Python dependency list is [`requirements.txt`](requirements.txt):
`diagrams`, `matplotlib`, `pillow` and `checkov`, including their minimum versions.
Setup installs it into `.venv`, not system Python. No npm project/install task is required for the portal.
Generated applications restore their own NuGet packages; scenario-specific dependencies remain explicit local work.
Use `az bicep build --file ...` and `az bicep lint --file ...`; a separate bare `bicep` command is not required.

The checker verifies:

- Executables on this process's PATH and successful version probes.
- A stable **10.x SDK** from `dotnet --list-sdks`; a runtime alone, SDK 9 or SDK 11 does not satisfy it.
- Copilot CLI flags used by the portal, not merely an unrelated `copilot` executable.
- Repository environment, package minimum versions and `pip check`.
- A real diagrams/Graphviz render to a temporary PNG, opened and verified with Pillow; temporary output is removed.
- With optional profiles, Node.js 22+, GitHub CLI and a responsive Docker engine.

For JSON output or direct Python checks:

```powershell
.\scripts\Install-Prerequisites.ps1 -CheckOnly -Json
.\.venv\Scripts\python.exe -B scripts\check_prerequisites.py --json --contributor
```

Exit codes are `0` for ready, `1` for unmet checks (including a dry-run plan with pending work),
and `2` for setup/checker errors. A ready local toolchain is **not** evidence of a working deployed scenario.

## Graphviz: native executable versus Python package

Installing `diagrams` or the Python `graphviz` package does not install native Graphviz.
Both the native `dot.exe` and the repository Python packages are required.

```powershell
Get-Command dot
dot -V
```

If Graphviz is already installed but is missing from PATH, installation mode checks the standard
`C:\Program Files\Graphviz\bin` directory before attempting another package installation.
It only adds the directory if `dot.exe` exists. For an approved custom installation:

```powershell
.\scripts\Install-Prerequisites.ps1 -Install -AcceptPackageAgreements `
    -GraphvizBin 'D:\Tools\Graphviz\bin'
```

Only explicit installation mode can update User PATH; check-only and `-WhatIf` never persist PATH changes.
This cannot update the environment of an already running VS Code, portal or worker.

## Restart sequence after installing tools

1. Let existing scenario workers finish, or stop their selected runs through the portal.
1. Close the portal's server using its terminal, or your normal process-management procedure.
   Closing the browser tab alone does not stop the server.
1. Open a fresh terminal. If launching from VS Code, fully restart VS Code so it inherits the new PATH.
1. Run check-only again and resolve failures before launching the portal.
1. Start the portal and open its newly authenticated entry page. Resume the scenario only afterward.

Refreshing the page or clicking Resume cannot refresh an old server's PATH.
The installer refuses real installation while a recorded portal PID is live or a project has a writer lease.
It never kills processes, clears leases or overwrites saved project decisions.
Stale leases must be recovered through the normal project workflow, not deleted to force setup through.

## Python version, architecture and existing environments

Python 3.13 is the bootstrap choice for a new Windows installation,
not an upgrade requirement for a working 3.10+ setup.
Very new Python versions and Windows ARM64 can lack wheels for scientific or Checkov dependencies.
If pip reports unsupported wheels or tries a failing native build, select a supported Python version/architecture
through your approved installation route; x64 Python on Windows ARM64 may offer broader package compatibility.
Do not suppress these failures or automatically install a compiler toolchain.

Select an explicit interpreter if the Windows Store alias is unusable or several versions are installed:

```powershell
.\scripts\Install-Prerequisites.ps1 -Install -AcceptPackageAgreements `
    -PythonExecutable 'C:\Path\To\Python313\python.exe'
```

An existing repository `.venv` takes precedence and is never deleted or replaced.
If incomplete or created with an incompatible Python, preserve it and recreate/repair it manually
while workers are idle.
The checker always reports which interpreter it actually used.

## Authentication, trust and permissions remain manual

After installing Copilot CLI, authenticate as the intended user:

```powershell
copilot login
```

Confirm access to Copilot, repository/workspace trust and any applicable execution-host tool permissions.
The portal's **Allow local Copilot CLI tool execution** checkbox is separate from a scenario decision.
Neither one overrides a host denial for an executable, download URL or filesystem location.
Ask the owner/administrator to authorize the specific intended operation; do not broadly disable permission checks.

Before separately authorized Azure work, confirm Azure CLI and `azd` use the same intended account,
tenant and subscription. Azure login, RBAC, provider registration, policy, budget, model availability and quota
are not checked or changed by this installer. It never signs in, changes subscription defaults or deploys resources.
Deployment consent, scenario suitability approval, hack composition and event rollout remain separate decisions.

For VS Code, review [recommended extensions](.vscode/extensions.json) and
[MCP configuration](.vscode/mcp.json). HTTP MCP servers require connectivity and their own authentication.
The configured stdio Playwright MCP server also requires Node/npm/npx and its supported browser.
First use may request package/browser downloads: review those separately, rather than pre-approving all tools.
The setup does not edit MCP configuration, extension settings or Copilot approval rules.

## Manual or non-Windows setup

Use the official installers below when WinGet is unavailable or enterprise software management owns installation.
On macOS/Linux, install equivalent Git, Python, PowerShell, Copilot CLI, .NET 10 SDK,
Graphviz, Azure CLI and `azd` packages through their supported channels, then:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.txt
az bicep install
.venv/bin/python -B scripts/check_prerequisites.py
.venv/bin/python scripts/start_portal.py
```

For manual Windows Python setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
az bicep install
.\.venv\Scripts\python.exe -B scripts\check_prerequisites.py
```

No activation is necessary when invoking the environment's Python explicitly.
The startup helper selects `.venv\Scripts\python.exe` on Windows and `.venv/bin/python` on macOS/Linux.

## Official installation references

- [Python on Windows](https://docs.python.org/3/using/windows.html)
- [Git downloads](https://git-scm.com/downloads)
- [Copilot CLI quickstart](https://docs.github.com/en/copilot/get-started/cli-quickstart)
- [PowerShell installation](https://learn.microsoft.com/powershell/scripting/install/installing-powershell)
- [.NET on Windows](https://learn.microsoft.com/dotnet/core/install/windows)
- [Graphviz downloads](https://graphviz.org/download/)
- [Azure CLI on Windows](https://learn.microsoft.com/cli/azure/install-azure-cli-windows)
- [Azure Developer CLI installation](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Node.js downloads](https://nodejs.org/en/download)
- [GitHub CLI installation](https://cli.github.com/)
- [Docker Desktop installation](https://docs.docker.com/desktop/)
