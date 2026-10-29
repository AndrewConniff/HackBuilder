# ABC Builder prerequisites

Prepare this machine before starting scenario work in VS Code. The portal itself uses Python's standard library,
but reference generation also needs the SDKs, native diagram tooling and Python packages below.
The setup covers the shipped baseline, not every package a future scenario might introduce.

## Agent-owned scenario execution

The user prepares tools, Azure CLI/azd authentication and the Docker Linux engine once.
The canonical scenario agent uses its existing skills to check prerequisites before the work needing them.
The portal does not require a Chromium launch, temporary .NET build, sign-in or timed receipt before
every scenario run. Requirements and local design do not require cloud access.
Use the portal's **System prerequisites** panel to check the shared baseline before scenarios.
**Check Azure sign-in** separately verifies the existing Azure CLI/azd identities and displays their
tenant/subscription metadata without retaining tokens or asking for manual IDs.
No resource, quota or provider query is included. The active portal does not install/update tools,
start Docker, sign in, or resume a scenario when a check completes.
The former Backend readiness/setup/retry controls belong to the historical runner and are not active.

The agent owns scheduling, Bicep/application builds and validation in one context until an actual approval
boundary or blocker. Python displays reported status and hands off to the actual agent, without repeating those builds
or creating a subprocess per stage. Scenario-specific packages, container behavior and real Azure/Foundry
acceptance still require actual scenario validation; a baseline diagnostic cannot prove them.

## Workspace-wide System checklist and service-aware validation

The portal **System** page lists the end-to-end toolchain before it has been checked.
Unchecked items are **Not checked**, never assumed ready. Authorize read-only diagnostics and select
**Check prerequisites** to verify versions, Python dependencies, a real PNG, NuGet metadata HTTPS/TLS
and any required running engine.
Green checked indicators mean the check passed at the displayed time, not merely that a file exists.
Failures show the command result, affected stages and a corrective action.
For **Docker installed, engine unavailable**, start Docker Desktop's Linux engine and wait until it is ready;
do not reinstall Docker merely because its named pipe is unavailable. The audit never starts Docker for you.

System uses one fixed workspace-wide profile: all catalog services, local container builds, Functions Core Tools
and k6 load testing. It has no scenario, service or build-mode selector.
Changing the working scenario or intake never changes this profile or triggers another audit.
System reports **Ready** only after both the complete toolchain and Azure CLI/azd authentication checks pass.
Earlier narrower reports are not presented as workspace-wide readiness.
This prepares shared capabilities once; the scenario agent still applies only the dependencies its design needs.
The conditional matrix below describes scenario validation, not additional System setup choices.

| Service or build choice | Additional local requirement beyond the shared baseline |
| --- | --- |
| Foundry | .NET 10 application; actual package restore/build verifies SDK dependencies |
| Cosmos DB, AI Search, Storage, SQL | Application packages; no mandatory local database/search emulator |
| App Service | Default .NET publish/zip path; Docker only for a chosen container build |
| Container Apps | Default local image build: Docker CLI and a responsive **Linux** engine |
| Functions | Application packages; Core Tools 4+ only for an explicit local Functions host |
| Key Vault, managed identity | Application packages; live identity/RBAC verification remains separate |
| Virtual Network, API Management | Shared infrastructure tools; live connectivity/gateway checks remain separate |
| Service Bus, Monitor | Application packages; live messaging/telemetry tests remain separate |
| Explicit remote image build | No local Docker gate; separate authorization is still required for Azure builds |

The shared checklist includes Python, repository `.venv`, all packages in `requirements.txt`, dependency consistency,
Git, PowerShell 7+, .NET 10 SDK, Graphviz, Azure CLI, azd and Azure CLI Bicep.
VS Code with GitHub Copilot and the `code` launcher handles agent conversations;
the retired portal runner's Copilot CLI and Python Playwright/Chromium dependencies are not required.
Node.js/GitHub CLI are included by default in the complete automated system-tools bundle.
The raw checker/portal retain their narrower runtime profile; contributor checks are an additional setup check.

| Stage | Tool gate |
| --- | --- |
| Requirements and architecture | No tooling gate; collect all future setup issues together |
| Diagrams | Python environment/packages, Graphviz and a real PNG render |
| Bicep | Azure CLI/Bicep and Python Checkov dependencies |
| Application scaffolding | .NET 10 SDK |
| Local validation | Build tools, NuGet HTTPS/TLS, plus Docker/Functions tools when the build path needs them |
| Deployment | CLI/azd/PowerShell, plus Docker for local image packaging; cloud consent remains separate |

Run a selected-service audit outside a worker:

```powershell
.\.venv\Scripts\python.exe scripts\check_prerequisites.py `
    --services foundry container-apps cosmos-db service-bus --json
```

The System panel records a shared full-toolchain audit and reuses matching observations across scenarios.
Recheck after relevant tool/environment changes, not after changing scenario selections or on a timer.
For a focused stage result, use the same standalone diagnostic:

```powershell
python scripts\check_prerequisites.py --services foundry --stage requirements --json
python scripts\check_prerequisites.py --services foundry --stage local-validation --json
```

The checker prints observations; it does not issue worker receipts, leases or execution permission.
Early-stage commands can succeed while reporting future failures. Resolve required dependencies
before the affected operation; there is no additional portal-stage gate.
Use `--build-mode local` or `--build-mode remote` only for the confirmed architecture.
Use `--local-functions` only for an explicit local Functions host.
These switches describe checks, not authorization or a change to deployment configuration.

Unknown design-specific dependencies still require explicit checks. Actual NuGet restore/build,
generated Dockerfiles, host restrictions, sign-in, Azure target/region/model capacity and runtime acceptance
cannot be proven by this local tool inventory. No audit installs software, grants permission or repairs a failed host.

## Package-feed HTTPS and TLS connectivity

Installing the .NET SDK is not sufficient: the actual portal worker account must be able to reach
the application's configured NuGet feeds and required package metadata/download endpoints over
organization-approved HTTPS. Host proxy configuration, certificate trust and outbound access must
work for that worker, not just for an interactive browser or a different terminal account.

This environment requires **MicrosoftPackageFeedProxy**, not direct NuGet.org. Repository
[`NuGet.Config`](./NuGet.Config) clears inherited package sources and enables only the approved proxy.
The host already has this proxy enabled as `azure-default`; the source name does not affect connectivity.

```powershell
dotnet nuget list source
python scripts\check_prerequisites.py --services foundry --json
```

For a new host, configure the portal worker account outside a running job:

```powershell
dotnet nuget disable source nuget.org
dotnet nuget add source https://packagefeedproxy.microsoft.io/nuget/v3/index.json -n MicrosoftPackageFeedProxy
```

Disable NuGet.org only if it is listed; add the proxy only if its URL is not already enabled.
These commands change that account's NuGet configuration, not every machine account.
Generated workspaces can live outside the repository through a junction and may not inherit repository
configuration. Verify their effective sources with `dotnet nuget list source` from the physical workspace.
For an explicit local restore, pass `--configfile C:\HackBuilder\NuGet.Config` to `dotnet restore`.
Container or remote builds need the same approved source configured inside their build environment;
the host's user-level configuration is not automatically copied into an image.

The checklist fetches the proxy's NuGet v3 service index, discovers its HTTPS `PackageBaseAddress/3.0.0`
resource, then validates Azure.Identity version metadata there. The advertised package endpoint can use
a different hostname; approved outbound access must cover it too. There is no direct NuGet.org fallback.
This does not prove all feeds, package downloads or restore. Follow it with the generated application's
actual restore/build using its configured NuGet sources.

A remote TLS `HandshakeFailure` is a setup/network blocker, not a request for more deployment approval.
Have the environment administrator investigate proxy/TLS inspection, approved certificate trust,
outbound policy and feed access outside the worker. Do not disable certificate validation, weaken TLS,
install certificates or upgrade shared tools from a scenario worker to work around the failure.
After authorized setup correction, recheck in System and rerun the affected build in VS Code.
Keep the blocker active until the actual endpoint and required restore/build checks pass.

The automated checklist runs this probe through PowerShell 7 with a 30-second timeout per request,
a 75-second process timeout and normal certificate validation.
Its separate **NuGet package metadata HTTPS/TLS** result
gates local validation, not requirements, architecture or application scaffolding. Missing PowerShell,
TLS/network errors or malformed metadata fail the check with a setup action; a green SDK indicator
alone is not a package-feed connectivity result. A System-page audit runs as the server account;
scenario validation still needs actual restore/build under its execution identity.
The approved proxy is the baseline probe; a successful probe does not prove a workspace's source configuration.
For historical direct-NuGet failures, use the approved proxy audit and verify the
effective restore sources before retrying. Historical failures remain unchanged.

## Scenario-specific runtime tools

Inventory additional SDK and test-tool requirements before implementation and probe them separately.
A missing optional browser or load-test tool must not block unrelated application authoring.
Actual required tool execution, restore/build and browser/load validation still need evidence.
PowerShell checks must not assign results to automatic/read-only variables such as `$HOME`, `$PID`
or `$Host`; variable names are case-insensitive. Use `$homeResponse` for an HTTP response.
Generated-command errors must not be repaired by broadening filesystem trust or weakening host restrictions.

Use the reusable local runtime check instead of generated multi-command PowerShell for container smoke tests:

```powershell
python scripts\check_container_runtime.py --image scenario-local:owned-tag --marker "Expected company"
```

It requires an existing nonroot Linux x64 image, never pulls images, uses a read-only filesystem,
publishes only to an ephemeral loopback port, retries startup for up to 90 seconds, captures container
logs on success/failure and stops only the exact container it created. No host mounts or cloud access
are involved. JSON `ok:true` requires the health and homepage checks and successful cleanup.
This is shell/liveness evidence only, not live Foundry or full application acceptance.
HTTP/startup failures are application diagnostics, not permission failures. Workers must inspect the
actual failure before requesting additional access; genuine unknown paths/URLs still require approval.

For a design that explicitly uses k6, record `"validationTools": ["k6"]` in the scenario manifest.
The scenario agent checks k6 when that design needs it; standalone audits can use
`python scripts\check_prerequisites.py --services foundry --load-tests --json`.
Missing k6 gates local validation, not application authoring. It is not required for other scenarios.
An operator can install it outside workers with
`winget install --id GrafanaLabs.k6 --exact --source winget`.
The portal resolves an existing standard `Program Files\k6\k6.exe` installation on its child PATH,
without changing the host PATH. Restart the affected execution host after installation.

## Azure identity and target readiness

The System page's **Check Azure sign-in** resolves existing local context
after explicit read-only diagnostic consent. It checks `az account show`, token expiry/tenant/subscription
metadata only (never retains the token), and `azd auth login --check-status --no-prompt`.
It never signs in automatically, switches shared defaults or runs Azure resource queries.
Matching CLI/azd account names are checked; azd target-tenant access, RBAC, policy, providers,
SKU/model quota and capacity remain separate authorized preflight checks.

In VS Code, the scenario agent reuses previously saved targets first, then local azd environment/configuration,
the scenario architecture region and `projectSlug` / `rg-{environment}` naming conventions.
Conflicting local azd subscription/tenant values or ambiguous environments require reconciliation.
Identity changes are visible rather than silently inheriting old consent.
Review environment, resource group and region in the scenario chat; account changes remain explicit local CLI actions.
Keep private target values, provenance and verification time outside public catalog metadata.

Resolving context does not authorize anything. The scenario agent runs exact-target readiness/what-if only
within the user's granted scope, reviews cost and changes, and obtains deployment consent in VS Code.
There is no additional portal approval queue. Reuse matching saved identity and same-scenario decisions.

## Quick start on Windows

Use the [HOWTO's manual inventory and official download links](
ABC-Builder-HOWTO.md#manual-tool-inventory-and-official-downloads) if automated setup is not permitted.
Otherwise run the [full System-profile installer](system-tools/README.md) from the repository root.
The default downloads every pinned native tool. Use explicit Check mode for read-only diagnostics:

```powershell
.\system-tools\Install-SystemTools.ps1 -Mode Check
```

Preview changes without installing packages, creating an environment or updating persisted PATH:

```powershell
.\system-tools\Install-SystemTools.ps1 -Install -WhatIf
```

Download everything without installing, or add `-Install` for a single download-and-install flow
after finishing work and closing the portal:

```powershell
.\system-tools\Install-SystemTools.ps1 -AcceptPackageAgreements -Verbose
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose
```

This entry point reuses [`scripts/Install-Prerequisites.ps1`](scripts/Install-Prerequisites.ps1),
selecting the complete System profile plus Node.js/GitHub CLI and a VS Code 1.143+ launcher check.
Every native tool is included by default. Use `-SkipVSCode` for a separately managed editor.
[`tool-catalog.json`](system-tools/tool-catalog.json) pins versions, official URLs and SHA256,
including Azure CLI Bicep. Every native cache entry must verify before installation begins.
Clean machines receive pinned native versions; existing compatible tools are not forcibly reinstalled or downgraded.
New Docker installation additionally requires separate `-AcceptDockerLicense` consent,
working WSL 2.1.5+ and virtualization. Without consent it remains a manual action.
Installed-but-stopped Docker requires manual engine repair/start, not reinstallation.
No automatic WSL configuration, Docker startup, sign-in or reboot occurs.
Vendor installers may request administrator approval; the script never relaunches itself elevated.

To install exclusively from an already complete cache without additional native downloads:

```powershell
.\system-tools\Install-SystemTools.ps1 -Install -UseCachedInstallers -AcceptPackageAgreements -Verbose
```

Add `-AcceptDockerLicense` to the install command if needed.
**This is an offline native-installer cache, not a fully offline prerequisite bundle.**
Python requirements still need connectivity when missing; their minimum versions are not a complete package lock.
Vendor dependencies, WSL images, extensions and app NuGet packages are not included.
The automated baseline is Windows x64 only; ARM64 hosts can download it but need manual native tools to install.
Downloads use pinned official URLs directly, without WinGet.
Downloads and JSON outcomes remain local under ignored `system-tools\cache` and `system-tools\reports`.
Hash/signature checks protect reuse; preserve trusted receipts.
Do not redistribute vendor binaries without permission.

For intentionally narrower core checks, the legacy entry point remains available:

```powershell
.\scripts\Install-Prerequisites.ps1 -CheckOnly
.\scripts\Install-Prerequisites.ps1 -Install -WhatIf -IncludeContributorTools
```

Its default profile omits Docker, Functions and k6; it is not proof of full System readiness.
Use `-SystemProfile` for parity, `-IncludeVSCode` for the extra editor check,
or `-IncludeDocker` for a Docker-only addition.

Open a fresh terminal after installation, rerun check-only, then double-click
[`Start-ABCBuilder.cmd`](Start-ABCBuilder.cmd). Do not restart a portal with active workers.
The launcher and startup helper prefer the repository `.venv` for a **new** server and put its scripts on worker PATH.
Existing servers are reused without changing their interpreter or environment.

If PowerShell blocks the script, follow your organization's script-signing/approval procedure.
Setup does not change execution policy. If Python is missing, check-only explains the bootstrap requirement.
The system-tools flow downloads the complete native baseline before bootstrapping Python from its cache.
The legacy installer's online mode uses WinGet; its missing-Python dry run lists that first step only.

## Dependency inventory

| Dependency | Required for | Windows installer ID |
| ---------- | ------------ | -------------------- |
| Python 3.10+ | Portal, workflow helpers and diagrams | `Python.Python.3.13` |
| Git | Repository and local CLI workflows | `Git.Git` |
| PowerShell 7+ | Workspace and deployment scripts | `Microsoft.PowerShell` |
| .NET **10 SDK** | Building the generated C# application | `Microsoft.DotNet.SDK.10` |
| Graphviz, including `dot` | Rendering architecture/runtime diagrams | `Graphviz.Graphviz` |
| Azure CLI | Authorized Azure validation/deployment | `Microsoft.AzureCLI` |
| Azure Developer CLI | `azd` provisioning/deployment workflows | `Microsoft.Azd` |
| Azure CLI Bicep component | `az bicep build` and `az bicep lint` | Cached binary or manual `az bicep install` |
| Repository `.venv` and Python requirements | Diagram generation and policy scanning | See below |
| Node.js 22+, npm/npx | Included in setup; frontend tests and browser MCP | `OpenJS.NodeJS.LTS` |
| GitHub CLI | Included in setup; user-requested publication | `GitHub.cli` |
| Docker Desktop and running Linux engine | Full System profile / local container builds | `Docker.DockerDesktop` |
| Functions Core Tools 4+ | Full System profile / local Functions host | `Microsoft.Azure.FunctionsCoreTools` |
| k6 | Full System profile / load testing | `GrafanaLabs.k6` |
| VS Code and `code` launcher | Interactive custom-agent handoffs | Cached installer; Copilot setup manual |

Windows PowerShell 5.1 can run the bootstrap script; PowerShell 7+ remains part of the scenario toolchain.
The system-tools bundle does not require WinGet. Legacy online installation uses Microsoft App Installer's WinGet.
Package installers may need elevation, network/proxy access or a reboot; setup reports nonzero failures and stops.
It does not relaunch itself elevated, reboot, enable WSL/Hyper-V or start Docker.
Docker licensing requires separate explicit `-AcceptDockerLicense` consent before installing a missing Docker Desktop.
Docker Desktop is unsupported on Windows Server.

The authoritative Python dependency list is [`requirements.txt`](requirements.txt):
`diagrams`, `matplotlib`, `pillow` and `checkov`, including their minimum versions.
Setup installs it into `.venv`, not system Python. No npm project/install task is required for the portal.
Generated applications restore their own NuGet packages; scenario-specific dependencies remain explicit local work.
Use `az bicep build --file ...` and `az bicep lint --file ...`; a separate bare `bicep` command is not required.

The checker verifies:

- Executables on this process's PATH and successful version probes.
- A stable **10.x SDK** from `dotnet --list-sdks`; a runtime alone, SDK 9 or SDK 11 does not satisfy it.
- Repository environment, package minimum versions and `pip check`.
- A real diagrams/Graphviz render to a temporary PNG, opened and verified with Pillow; temporary output is removed.
- With the full System profile, a responsive Docker Linux engine, Functions Core Tools 4+ and k6.
- With the complete system-tools entry point (or raw contributor option), Node.js 22+ and GitHub CLI.

For JSON output or direct Python checks:

```powershell
.\scripts\Install-Prerequisites.ps1 -CheckOnly -Json
.\scripts\Install-Prerequisites.ps1 -CheckOnly -SystemProfile -Json
.\.venv\Scripts\python.exe -B scripts\check_prerequisites.py --system --json --contributor
```

Exit codes are `0` for ready, `1` for unmet checks (including a dry-run plan with pending work),
and `2` for setup/checker errors. Installation returns `3010` if a native installer requests a manual reboot;
reboot and rerun checks before treating setup as ready.
A ready local toolchain is **not** evidence of a working deployed scenario.

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

1. Let scenario tool operations finish in VS Code; the portal does not own or stop agent runs.
1. Close the portal's server using its terminal, or your normal process-management procedure.
   Closing the browser tab alone does not stop the server.
1. Open a fresh terminal. If launching from VS Code, fully restart VS Code so it inherits the new PATH.
1. Run check-only again and resolve failures before launching the portal.
1. Start the portal and open its loopback page. Continue the existing scenario chat afterward.

Refreshing the page or reopening a chat cannot refresh an old server's PATH.
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

New portal processes and workers prefer the repository `.venv` when present.
On Windows, when `dot` or `dotnet` is unresolved, they also expose an already installed executable
under `%ProgramFiles%\Graphviz\bin` or `%ProgramFiles%\dotnet` on that process's PATH.
Existing PATH selections take precedence. This does not install software, edit User/Machine PATH
or relax host permissions. Version and diagram checks must still pass in the actual worker.
This handles the standard Graphviz installer location even when an older terminal lacks its PATH entry.
Nonstandard installation locations still require explicit environment setup.

## Authentication, trust and permissions remain manual

Sign in to GitHub Copilot in VS Code and confirm custom-agent access, workspace trust
and applicable tool permissions. The portal never launches a Copilot CLI job.
An editor permission grant does not override a host denial for an executable, download URL or filesystem location.
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
On macOS/Linux, install equivalent Git, Python, PowerShell, VS Code with GitHub Copilot, .NET 10 SDK,
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
- [PowerShell installation](https://learn.microsoft.com/powershell/scripting/install/installing-powershell)
- [.NET on Windows](https://learn.microsoft.com/dotnet/core/install/windows)
- [Graphviz downloads](https://graphviz.org/download/)
- [Azure CLI on Windows](https://learn.microsoft.com/cli/azure/install-azure-cli-windows)
- [Azure Developer CLI installation](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Node.js downloads](https://nodejs.org/en/download)
- [GitHub CLI installation](https://cli.github.com/)
- [Docker Desktop installation](https://docs.docker.com/desktop/)
