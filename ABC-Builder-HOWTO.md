# ABC Builder: a new user's how-to guide

ABC Builder turns a business idea into a working Microsoft Foundry reference scenario,
then turns that reference into a hack experience **only after you approve its suitability**.
You use a local browser app to describe the idea, follow progress and browse outputs.
You use GitHub Copilot in VS Code to discuss the design, authorize operations and review the working solution.

This guide follows the browser workflow using screenshots captured on **October 25, 2026**.
The example is `feedback-campaign`, a Media & Communications scenario with human-reviewed engagement decisions.
Its business rules, services, costs and timestamps are examples, not defaults for your project.
The screenshots show successive moments, including an intentional stop for missing authorization;
they are not a claim that every pictured stage was already complete.

## In this guide

- [Understand the two-window workflow](#understand-the-two-window-workflow)
- [Prepare your machine and open ABC Builder](#prepare-your-machine-and-open-abc-builder)
- [Choose manual, online or cached setup](#choose-manual-online-or-cached-setup)
- [Manual tool inventory and official downloads](#manual-tool-inventory-and-official-downloads)
- [Navigate the browser app](#navigate-the-browser-app)
- [Step 1: describe your scenario](#step-1-describe-your-scenario)
- [Step 2: continue in VS Code](#step-2-continue-in-vs-code)
- [Step 3: follow Build & validate](#step-3-follow-build--validate)
- [Step 4: review and authorize Azure work](#step-4-review-and-authorize-azure-work)
- [Step 5: approve the working scenario](#step-5-approve-the-working-scenario)
- [Step 6: create and export the hack](#step-6-create-and-export-the-hack)
- [Find your files and return later](#find-your-files-and-return-later)
- [Troubleshoot common situations](#troubleshoot-common-situations)
- [First-run checklist](#first-run-checklist)

## Understand the two-window workflow

Think of the browser as the **brief, dashboard and output viewer**, and VS Code as the **workbench and conversation**.
Keep both available while building.

| Component | What it does | What it does not do |
| --- | --- | --- |
| Local browser app | Saves briefs, opens chats, shows reports/files and exports packages. | Run agents. |
| `az-01-conductor` | Builds, tests and demonstrates the authorized reference in VS Code. | Author an unapproved hack. |
| `HackCreator Agent` | Derives learner/coach materials in VS Code after approval. | Automatically deploy an event. |
| Your Azure environment | Hosts authorized resources and the real Foundry runtime. | Host the local portal. |
| You | Set goals, review decisions and approve scope/suitability. | Coordinate specialist agents. |

The two canonical agents work through reusable repository **skills**: procedures for requirements, architecture,
diagrams, infrastructure, application development, validation and authoring.
They do not fan out work to specialist Copilot agents.
A multi-agent pattern selected for your business solution describes the **generated runtime**,
not additional Copilot sessions building it.

### What happens when you select Start building?

1. The portal saves your brief and prepares a scenario-specific handoff.
1. It opens the repository in VS Code and requests the real `az-01-conductor` custom-agent chat.
1. Copilot reads the handoff and existing scenario evidence, then works in that VS Code context.
1. At stage boundaries, Copilot writes short JSON progress reports.
1. The browser polls for those reports, normally every four seconds, and refreshes the dashboard.
1. When a decision is needed, you respond in the existing VS Code chat.
1. After the working reference is approved, you explicitly open a separate composition context.

The active browser workflow does **not** launch background Copilot CLI workers, schedule implementation stages,
proxy your answers to the model or supervise an agent process.
The System page is an exception to display-only behavior: on request, it runs shared diagnostics,
not scenario implementation or Azure deployment.

> [!IMPORTANT]
> A browser status is the latest **reported state**, not a live process monitor.
> Switching tabs, refreshing the board or reopening a chat does not grant permission or restart the build.

## Prepare your machine and open ABC Builder

### Prepare once

Use the [setup choices below](#choose-manual-online-or-cached-setup), not just the System diagnostic.
We provide an opt-in PowerShell installer and a local native-installer download cache under
[`system-tools`](system-tools/README.md), as well as manual download links.
The [prerequisite guide](PREREQUISITES.md) covers authentication and detailed troubleshooting.
Before your first scenario:

1. Open this repository as the active VS Code workspace and review Workspace Trust.
1. Sign in to GitHub Copilot and confirm custom agents are available.
1. Confirm the VS Code `code` launcher is available to the local portal.
1. Prepare Python and the repository environment, PowerShell, .NET 10, Graphviz, Azure CLI, azd and Bicep.
1. Prepare the other tools required by the shared System profile, including a running Docker **Linux** engine.
1. Sign in to Azure CLI and azd using the intended account and compatible tenant/subscription context.
1. For browser-to-existing-chat navigation, install the local
   [Scenario Chat bridge](tools/vscode-chat-bridge/README.md) as documented there.
   The bridge requires VS Code 1.143 or later and a trusted local workspace.

The portal itself uses Python's standard library.
The broader toolchain is needed to generate and validate the reference, not simply to render the page.
Do not install arbitrary packages in response to a scenario delay; use the documented diagnostics first.

### Choose manual, online or cached setup

Run these commands from the repository root in PowerShell. Windows PowerShell 5.1 can bootstrap setup;
PowerShell 7+ is still required for scenario work. Follow your organization's script approval/signing policy.
The scripts do not bypass execution policy.

| Route | Best when | What happens |
| --- | --- | --- |
| Manual | Automated installation is not permitted. | Use the official links below; run checks afterward. |
| Download baseline | You want the same native versions locally. | Downloads every pinned tool; installs nothing. |
| Download and install | You want one opt-in Windows x64 flow. | Verifies all downloads, then installs from cache. |

**Cached/offline native installation is not fully offline ABC Builder setup.**
The cache includes the native tools and Bicep, but does not include Python wheels, vendor dependencies, WSL images,
VS Code extensions or generated application NuGet packages.
Installation still needs network access for missing Python requirements.
Final checks include NuGet HTTPS, and Copilot/Azure sign-in needs connectivity.
For an air-gapped machine, use your organization's separately approved complete software/package mirror;
this repository does not supply or certify one.

Check the full System profile first; this installs nothing:

```powershell
.\system-tools\Install-SystemTools.ps1 -Mode Check
```

Download the complete pinned native baseline without installing anything, including Node.js and GitHub CLI:

```powershell
.\system-tools\Install-SystemTools.ps1 -WhatIf
.\system-tools\Install-SystemTools.ps1 -AcceptPackageAgreements -Verbose
```

To download/reuse the same files and optionally install missing tools in **one flow**,
finish scenario work, close the portal, review vendor agreements and add `-Install`:

```powershell
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -Verbose
```

The script installs only missing/failed native tools, creates or preserves the repository `.venv`,
installs [`requirements.txt`](requirements.txt), copies cached Bicep into the Azure CLI configuration directory
and reruns the complete selected checks. All native downloads must verify before any native installation.
Clean machines receive pinned versions; existing compatible versions are preserved rather than forcibly downgraded.
Readiness checks verify supported versions and behavior, not exact equality with the download baseline.
Timestamped messages distinguish already-ready tools, installation, verification, manual actions and failures.
`-Verbose` streams command details/output. JSON outcomes go to the ignored `system-tools\reports` folder.
An installer exit alone never means the toolchain passed.

Docker licensing is a separate choice. If Docker is missing, the preceding command leaves it as a manual action.
After reviewing [Docker's Windows requirements and subscription terms][docker-download],
prepare working WSL 2.1.5+ and virtualization, then explicitly permit Docker installation:

```powershell
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose
```

The script does not enable WSL/Hyper-V, restart Windows or start Docker.
Docker Desktop is unsupported on Windows Server; the Linux engine must actually be running for System readiness.
An installed but stopped/misconfigured Docker engine is reported for manual repair, not reinstalled.
Some vendor installers require administrator approval or a reboot; setup does not relaunch itself elevated.

The default download uses `system-tools\cache` and reuses matching verified files.
To install on Windows **x64** without permitting any additional native downloads:

```powershell
.\system-tools\Install-SystemTools.ps1 -Install -UseCachedInstallers -AcceptPackageAgreements -Verbose
```

Add `-AcceptDockerLicense` if a new Docker installation is wanted.
This automated baseline is x64-only; downloading it from an ARM64 host is supported, installing it is not.
Manual ARM64/native installers remain available from the official sources below.
Downloads can be large, especially Docker and the .NET SDK; allow several GB of space.

[`tool-catalog.json`](system-tools/tool-catalog.json) pins each native version, official download URL and SHA256.
Every user gets the same locked native files, without WinGet or resolving "latest".
Download and reuse check the bytes against the repository-pinned SHA256 and Authenticode status/publisher.
Catalogued open-source exceptions (Graphviz, k6 and GitHub CLI) may be unsigned;
their hashes must still match the repository lock.
Keep installer files **and receipts** trusted: a locally generated receipt is not a signed publisher manifest.
Corrupt, missing or unexpected cache files stop installation; there is no silent online fallback.
Vendor format changes may require a recipe update or manual installation.

Downloaded binaries, receipts and reports are ignored by Git and are not shipped with the source repository.
Do not force-add them or redistribute third-party installers without permission.
Existing verified downloads are reused. Maintainers update versions/hashes through a reviewed catalog change.
To recover an incomplete or older-baseline download, inspect/preserve the old cache and select a new `-CacheDirectory`.

Node.js/npm and GitHub CLI are included by default; no contributor switch is needed.
Use `-Mode Check` for read-only checks or `-SkipVSCode` if VS Code is managed separately.
Setup does not install Copilot extensions or sign you in.
See the [setup reference](system-tools/README.md) for custom paths, reports and exit codes.

After setup, open a fresh terminal/VS Code, complete Copilot and Azure sign-in yourself,
start Docker's Linux engine, rerun **Check**, and rerun both diagnostics in the portal's System page.
The installer does not update the portal's saved diagnostic results or grant Azure deployment permission.

### Manual tool inventory and official downloads

You can install everything manually. Prefer your approved software channel or these official sources.
Select installers for your OS/CPU; the automated cache is specifically Windows x64.
The **full System profile** requires Docker, Functions Core Tools and k6 even if your first scenario does not use them.
Narrow scenario checks may require less; a narrower successful report is not a full System pass.

| Tool | Official source | Verification / requirement |
| --- | --- | --- |
| WinGet / Microsoft App Installer | [Installation guide][winget-download] | Optional legacy online installer |
| Python 3.10+ | [Python downloads][python-download] | `python --version`; bootstrap selects 3.13 if missing |
| Git | [Git for Windows][git-download] | `git --version` |
| PowerShell 7+ | [PowerShell installation][pwsh-download] | `pwsh --version`; 5.1 alone is not enough |
| .NET **10 SDK** | [.NET 10 downloads][dotnet-download] | `dotnet --list-sdks`; stable 10.x, not just runtime |
| Native Graphviz | [Graphviz downloads][graphviz-download] | `dot -V`; Python's graphviz package is not enough |
| Azure CLI | [Azure CLI installation][az-download] | `az --version` |
| Azure Developer CLI | [azd installation][azd-download] | `azd version` |
| Azure CLI Bicep component | [Bicep installation][bicep-download] | `az bicep install`, then `az bicep version` |
| Docker Desktop | [Docker Windows setup][docker-download] | `docker info`; responsive **Linux** engine |
| WSL 2 / virtualization | [WSL installation][wsl-download] | `wsl --version` and `wsl --status`; manual OS setup |
| Functions Core Tools 4+ | [Functions local development][functions-download] | `func --version` |
| Grafana k6 | [k6 installation][k6-download] | `k6 version` |
| Visual Studio Code | [VS Code downloads][vscode-download] | `code --version`; 1.143+ for the local bridge |
| GitHub Copilot | [Copilot setup in VS Code][copilot-download] | Install/enable, sign in and review Workspace Trust |
| Scenario Chat bridge | [Local bridge instructions][bridge-setup] | Optional existing-chat navigation |
| Node.js LTS, npm/npx | [Node.js downloads][node-download] | Included in setup; `node --version` must be 22+ |
| GitHub CLI | [GitHub CLI downloads][gh-download] | Included in setup; `gh --version` |

The repository Python environment is also required, not just a global Python installation:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B scripts\check_prerequisites.py --system
```

Do not recreate or overwrite an existing `.venv`; preserve and repair it if necessary.
[`requirements.txt`](requirements.txt) is authoritative. Current minimums and official package pages:

- [diagrams on PyPI](https://pypi.org/project/diagrams/): `>=0.23.4`.
- [matplotlib on PyPI](https://pypi.org/project/matplotlib/): `>=3.8`.
- [Pillow on PyPI](https://pypi.org/project/pillow/): `>=10.0`.
- [Checkov on PyPI](https://pypi.org/project/checkov/): `>=3.0`.

The checker verifies package minimums, dependency consistency and a real PNG render, not merely imports.
Generated .NET apps restore their own packages using the repository's approved
[`NuGet.Config`](NuGet.Config) feed. Corporate proxy/certificate issues need an approved IT fix,
not disabled TLS verification.
The portal needs no Node/npm installation task, Copilot CLI or Python Playwright/Chromium baseline.
Scenario-specific browser tests or other extra tools must be documented separately when chosen.

[winget-download]: https://learn.microsoft.com/windows/package-manager/winget/
[python-download]: https://www.python.org/downloads/windows/
[git-download]: https://git-scm.com/downloads/win
[pwsh-download]: https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows
[dotnet-download]: https://dotnet.microsoft.com/download/dotnet/10.0
[graphviz-download]: https://graphviz.org/download/
[az-download]: https://learn.microsoft.com/cli/azure/install-azure-cli-windows
[azd-download]: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd
[bicep-download]: https://learn.microsoft.com/azure/azure-resource-manager/bicep/install
[docker-download]: https://docs.docker.com/desktop/setup/install/windows-install/
[wsl-download]: https://learn.microsoft.com/windows/wsl/install
[functions-download]: https://learn.microsoft.com/azure/azure-functions/functions-run-local
[k6-download]: https://grafana.com/docs/k6/latest/set-up/install-k6/
[vscode-download]: https://code.visualstudio.com/download
[copilot-download]: https://code.visualstudio.com/docs/copilot/setup
[node-download]: https://nodejs.org/en/download
[gh-download]: https://cli.github.com/
[bridge-setup]: tools/vscode-chat-bridge/README.md

### Open the browser app

From the repository root in PowerShell:

```powershell
.\Start-ABCBuilder.cmd
```

Alternatively:

```powershell
python scripts\start_portal.py
```

The launcher starts a local server or reuses a healthy, compatible server for this workspace,
then opens its loopback address in your browser.
Use the address the launcher opens; do not expose the portal on a public interface.
The normal server uses port 8765.

You can also select **az-01-conductor** directly in VS Code and ask it to build a scenario.
Its interactive startup hook opens the portal; hosts without that hook use the helper once.
Opening the portal alone does not submit a brief or start a scenario.

### Check the System page

Although **System** is navigation item 4, it is useful before your first build.

1. Open **System**.
1. Expand **Check tools and existing Azure sign-in**.
1. Read and select the consent checkbox for read-only diagnostics.
1. Select **Check prerequisites**.
1. Inspect failures, affected stages and suggested remedies.
1. Select **Check Azure sign-in** to verify the existing Azure CLI and azd identities.
1. Resolve gaps outside the diagnostic and recheck after the relevant environment changes.

The shared profile covers all catalog services, local container builds, Functions Core Tools and k6.
It does not change when you select a different scenario or different services.
**Ready** requires both the complete toolchain check and the Azure sign-in check to pass.
Earlier or narrower reports are not proof that the full profile passed.

Checks do not install tools, start Docker, sign you in, change Azure defaults,
query resource readiness, grant RBAC or deploy anything.
A green System result is not proof of model quota, regional availability or a working scenario.
The scenario agent checks those separately within the scope you authorize.

> [!NOTE]
> The walkthrough screenshots show **System: Not checked**.
> That describes the saved diagnostic state at capture time, not a recommended setup step to skip.
> Requirements and design can proceed without cloud access; later stages still need their actual dependencies.

## Navigate the browser app

| Navigation area | Use it for | Important behavior |
| --- | --- | --- |
| **1. Create scenario** | Enter the customer story and solution goals. | Saves a brief and opens VS Code. |
| **2. Build & validate** | Follow milestones, read reviews and preview files. | Incomplete references stay here. |
| **3. Create hack** | Compose, validate and export packages. | Only eligible references appear here. |
| **4. System** | Check shared tools and existing Azure sign-in. | No scenario selection is required. |

Use **Working scenario** or a scenario card to select a project in Build & validate or Create hack.
The lists are phase-specific: eligible approved references move to Create hack rather than appearing in both boards.
An empty selector can therefore mean the scenario belongs to the other phase.
Navigation preserves your current form and selection in the page; it does not submit your form.
Browser Back/Forward also navigates the sections.

Use **Appearance** at the top right to choose **System**, **Light** or **Dark**.
System follows your operating-system appearance.
Explicit preferences persist in that browser when local storage is available.
On narrower screens, the left navigation becomes a compact menu.

## Step 1: describe your scenario

### Name the project and choose an industry

Open **Create scenario**.

1. Enter a **Project name**, which is also the project slug.
   Use at most 40 lowercase letters, digits and single hyphens, such as `campaign-review-demo`.
   Do not use spaces, uppercase letters, leading/trailing hyphens or consecutive hyphens.
1. Select exactly one **Industry**.
   The cards look like checkboxes but are single-choice controls.
1. Describe the outcome under **What should the scenario achieve?**
   The form accepts up to 6,000 characters.

For a new project, use your own slug rather than assuming the screenshot's `feedback-campaign` is available.
For an existing scenario, return to its saved chat and files instead of creating a duplicate brief.

![Create scenario form with project name, Media & Communications industry and customer brief][screen-01]

*Figure 1. Start with the business story, not a list of Azure resources.*

A useful brief identifies:

- The imaginary customer and industry.
- Intended users and business units.
- Inputs, such as campaign feedback or approved documents.
- The decision or action the agent should support.
- Thresholds and exceptions that must be tested.
- Human approval requirements and actions that must never be automatic.
- Constraints on data, access, budget and deployment.

For example:

> Build a Media & Communications campaign-feedback scenario for Sales and Marketing.
> Distinguish feedback about the company from feedback about its products.
> Route product complaints to a product reviewer, and require human approval before an external response.
> Use synthetic messages, explain routing decisions and demonstrate an unsupported or invalid input.
> Prepare locally first; present the Azure targets and costs before cloud operations.

Do not include live credentials, customer personal data or secrets.
Use synthetic data for the demonstration.

### Refine a rough idea with AI

Select **Refine with AI** instead of **Start building** if you want to improve the brief before implementation.
The portal saves your original prompt and opens the real scenario agent in VS Code in **scoping-only** mode.
It does not run a browser-side model or use a predefined set of questions.

The agent gives a short interpretation, identifies missing pointers, contradictions and consequential edge cases,
and asks a few questions tailored to your scenario, usually 2-4 and at most 5 at once.
Questions explain what the answer would change; recommendations are labeled as proposals, not your decisions.
Already answered details are reused. A sufficiently descriptive brief does not need an artificial interview.

Answer in that same chat. The agent maintains the refined brief, actual decisions, assumptions and open points
in `scoping.md` beside the saved `request.json`; the original intake is not overwritten.
Select the scenario in **Build & validate** to read **AI scoping notes and refined brief** as notes are saved.
These are agent-written context, not proof that all architectural risks have been eliminated.
No scenario workspace, architecture, app or cloud operation is started by scoping alone.

When satisfied, select **Confirm brief**. The portal sends a fixed continuation to the existing scenario chat
and resumes the normal workflow, starting with requirements and architecture artifacts.
No typed follow-up prompt, duplicate project or new conversation is needed.
**Modify brief** and **Save changes** send a scoping-only revision request for a new brief review.
Older confirmation-only receipts and failed sends use the same **Confirm brief** button to continue or retry.
There is no separate Continue action. Uncertain sends are not blindly repeated.
**Start building** also includes a bounded prompt gap review before architecture, asking only material open questions.
Confirming the brief does not approve Azure deployment, working-scenario suitability or hack composition.

### Choose an agentic workflow pattern

Select one of the 18 patterns or keep **Let AI decide**.
The short description under the selection explains the requested behavior.
Let AI decide is useful when the business outcome is clear but the architecture is not.

![Agentic workflow pattern cards with Human-in-the-Loop selected][screen-02]

*Figure 2. The example requests Human-in-the-Loop behavior in the generated business workflow.*

A pattern is a design input, not a guarantee that every region, SDK or hosting option implements it natively.
Copilot should explain the selected approach, a simpler alternative and how the behavior will be verified.
If your explicit choice conflicts with feasibility or business needs, resolve that in chat rather than
expecting the tool to substitute a different design silently.

### Add optional technical and organizational priorities

Expand **Services, business units and architecture priorities**.

![Expanded Azure services, business units, Well-Architected priorities and technical domains][screen-03]

*Figure 3. Optional selections constrain the design; they do not authorize provisioning.*

- **Azure services:** Microsoft Foundry is the baseline. Select supporting services you need.
  The pictured example requests Service Bus and Monitor; your scenario may need a different set.
- **Business units:** choose one or more specific units, or **Generic**.
  Generic is exclusive: it means a typical industry workflow without a specific unit.
- **Well-Architected priorities:** emphasize Security, Reliability, Cost Optimization,
  Operational Excellence or Performance Efficiency.
- **Technical domains:** highlight concerns such as least privilege, private networking,
  observability, deployment automation or load testing.

Business units shape personas, workflow, application behavior, synthetic data and later learner materials.
Service selections are requirements inputs, not Azure consent or proof those services are provisioned.
If you are unsure, describe the constraint in the brief and discuss the trade-off with Copilot.

When the required fields are valid, select **Start building** once.

## Step 2: continue in VS Code

VS Code opens the scenario conversation with the saved handoff attached.
Available shared prerequisite and identity observations can also be attached.

![VS Code Copilot chat with the scenario handoff and shared System reports attached][screen-04]

*Figure 4. The browser hands context to the actual editor conversation.*

The unique chat trace shown in the handoff is an association identifier, not an Azure credential.
You do not need to copy it or paste a chat link into the browser.

In VS Code:

1. Verify the repository workspace and intended scenario.
1. Let Copilot read the saved brief and any existing reference evidence.
1. Answer real business or architecture questions there.
1. Review requested tool permissions according to your organization's policy.
1. Keep this conversation as the place to request changes and authorize scenario work.

**Open scenario chat** in the browser locates and reopens the existing scenario conversation.
It does not send a new prompt, restart the agent or grant additional permissions.
If the bridge reports an error, use the existing chat manually and resolve the bridge setup;
do not repeatedly create replacement conversations.

## Step 3: follow Build & validate

### Read the scenario board

After submission, the browser moves to **Build & validate**.
Select your project through **Working scenario** or its card.
Use **Refresh** for an immediate update; normal polling also refreshes the view.

![Build & validate board showing the selected feedback-campaign scenario in Starting][screen-05]

*Figure 5. Starting means the brief was sent; the first agent report has not arrived yet.*

| Board label | Meaning | Your next action |
| --- | --- | --- |
| **Ready to start** | A saved brief is available. | Open its scenario chat when ready. |
| **Starting** | A handoff was sent; activity is not yet established by a report. | Check the VS Code handoff. |
| **Building** | Work is reported in progress. | Read the latest summary; let the current chat continue. |
| **Waiting for you** | A genuine decision is needed. | Read the request and respond in chat. |
| **Needs attention** | A reported stage failed or is blocked. | Review the issue in the existing chat. |
| **Scenario approved** | Current suitability approval is recorded. | Continue in Create hack when eligible. |
| **Ready to export** | Packages have current validation; no build is active. | Download audience-specific ZIPs. |
| **Status unavailable** | Existing files have no current progress report. | Inspect the existing scenario and chat. |

A completed individual step does not make the entire scenario complete.
Older projects can have files without modern reports; the portal does not turn those files into passed tests.

### Read the nine reference milestones

Scroll below the board to **Scenario milestones**.
Completed rows remain visible as later work progresses.
Each row can show a status, summary and report timestamp.

![Initial scenario milestone checklist with zero of nine milestones completed][screen-06]

*Figure 6. Empty boxes mean no completion report is recorded, not proof that no work exists.*

| Milestone | What it establishes |
| --- | --- |
| **Scenario description** | Business story, users, rules, scope and acceptance criteria are recorded. |
| **Architecture** | Services, identity/data paths, deployment choices, costs and trade-offs are documented. |
| **Architecture and runtime diagrams** | The resource design and business execution flow are rendered. |
| **Bicep infrastructure** | Infrastructure and azd wiring are implemented and locally checked. |
| **Application development** | The real reference application, synthetic fixtures and integration are implemented. |
| **Local validation** | Relevant local builds, tests and infrastructure checks have run. |
| **Azure deployment** | The authorized reference scope has been deployed. |
| **Live runtime validation** | Real model, agent and app behavior is verified, including required error cases. |
| **Scenario suitability approval** | You explicitly approved this working reference for use as the hack. |

These are evidence milestones, not a stopwatch or a rigid process scheduler.
Copilot can repair or revisit earlier work without opening a new implementation agent.

### Understand tool permissions

The next screenshot returns to VS Code while Copilot works.
The highlighted permission area belongs to the editor, not the browser.

![VS Code chat during implementation with the editor tool-permission area highlighted][screen-07]

*Figure 7. Permission controls and model labels depend on your VS Code/Copilot installation.*

**Allow all** can allow potentially destructive tool calls without further confirmation.
It is optional, not a requirement for ABC Builder.
Use narrowly scoped approvals where appropriate and follow your organization's policy.
The portal cannot choose this setting for you or copy a session-only grant to another chat.
The model shown in the screenshot is not a required or pinned model.

> [!WARNING]
> Tool permission is not Azure deployment consent, Entra directory consent,
> working-scenario suitability approval or authorization to deploy an event.

### Understand milestone indicators

![Scenario description and architecture completed while reference implementation continues][screen-08]

*Figure 8. Two completed milestones do not imply deployment or live acceptance has passed.*

| Milestone status | Meaning |
| --- | --- |
| **Completed**, green check | That milestone has completion evidence or its required current approval/receipt. |
| **Running**, spinner | Work was reported as underway. It is not a live process heartbeat. |
| **Not started / unreported**, empty box | No completion report is recorded. |
| **Artifacts available** | Relevant files exist, but completion/testing has not been established. |
| **Awaiting approval**, question mark | Read the summary to identify the actual decision and prerequisites. |
| **Blocked**, exclamation mark | A prerequisite, authorization or external constraint prevents that stage. |
| **Failed**, exclamation mark | An attempted operation or check failed. |
| **Handed off** | A handoff is recorded; it does not establish that the agent is running. |

Timestamps are displayed in your browser's local date/time format.
Read the summary as well as the icon: **Awaiting approval** is not an invitation to skip unresolved runtime checks.
An outstanding failed, blocked or waiting stage takes priority over an unrelated later completion report.
Expand **Agent-reported steps** when you need the underlying per-stage summaries.

## Step 4: review and authorize Azure work

Local preparation can produce code, diagrams, tests, a target proposal and a cost estimate before deployment.
The agent must not treat selected services or editor tool permissions as cloud consent.
Readiness reads, what-if and writes must each stay within your actual authorization.

When requested, use **Open scenario chat** to review:

- The exact account, tenant, subscription, region, resource groups and environment targets.
- The architecture and security/access paths, including how private resources will be managed and tested.
- Required Azure resource operations and any separate Entra directory operations.
- Authorized readiness/what-if results and checks still pending.
- Expected cost, assumptions, ongoing charges and limitations.
- What was already authorized and what additional scope, if any, needs your decision.

The browser can show a formatted **Deployment review and next decision** when a suitable review file is available.
You still answer in VS Code; reading that panel is not approval.
If the review is only listed under **Reference files**, preview it there or open it in the editor.

![Local checks completed with Azure deployment and live runtime validation blocked pending authorization][screen-09]

*Figure 9. This captured stop is correct: local success does not permit cloud deployment or suitability approval.*

In this screenshot, implementation and local tests are complete, but deployment and live validation have not run.
The stated cost ceiling and authority requirements belong to that example only.
First resolve the deployment review in chat; do not approve suitability just because local tests passed.

You can authorize the exact reviewed operations, request a design change or stop.
For example:

> Proceed with the exact Azure targets and operations in the reviewed deployment plan,
> within its stated budget and security constraints. Do not deploy coach/team environments or publish anything.

Use that wording only after checking the actual plan and resolving any directory-operation questions.
It is not blanket consent for future resources or unrelated environments.
Matching prior same-scenario approval can be reused; material new scope requires a focused review.
Real host, tenant, policy or RBAC denials remain blockers, not something permissive tool settings can bypass.

After authorization, the conductor deploys, repairs in-scope implementation issues and validates real runtime behavior.
A provisioned resource or a responding homepage is not enough.
The expected proof includes model inference, agent invocation, application chat,
required grounding/tools and a negative case.
Use the live app URL and demonstration guide supplied by the agent to inspect the business outcome yourself.

## Step 5: approve the working scenario

Deployment approval and suitability approval answer different questions:

- **Deployment:** may the reviewed cloud operations run against these targets?
- **Suitability:** does this proven business scenario work well enough to become this hack?

Before approving suitability, review the story, diagrams, live application, runtime results,
demonstration, costs and known limitations.
If something is wrong, ask for changes in the existing conductor chat.

When satisfied, give an explicit response such as:

> I approve this working reference scenario as suitable for the hack.

The agent records your actual decision against a fingerprinted review snapshot using the workflow helper.
You do not need to edit approval JSON manually.
If the reference or relevant evidence changes, the helper can require revalidation and renewed approval.
An older approval or an existing package is not permission to bypass review of a changed reference.

Once all nine reference milestones are complete and current suitability approval is valid,
the scenario moves from **Build & validate** into **Create hack**.
For older scenarios, a current validated-package receipt plus current approval can establish eligibility
without rewriting missing historical reports; explicit incomplete or failed reference stages still prevent the move.

The conductor stops at suitability review.
It does not automatically start composition, deploy an event or publish a repository.

## Step 6: create and export the hack

### Start the separate composition context

1. Open **Create hack**.
1. Select your approved scenario.
1. Select **Create hack materials** when available.
1. Continue in the separate **HackCreator Agent** VS Code conversation.
1. Let composition derive and locally validate the learner and private coach packages.

Composition uses the approved reference, not a newly invented solution.
Its saved handoff trace supports reuse of that composition context on follow-ups.
**Open scenario chat** remains the navigation action for the reference conversation;
do not assume it is a replacement for the separate composition context.

![Create hack board showing separate challenge, starter, coach and validation milestone progress][screen-10]

*Figure 10. Hack authoring has its own four-milestone checklist; in-progress packages are not export-ready.*

| Hack milestone | Result |
| --- | --- |
| **Hack challenges** | Progressive learner challenges and supporting content derived from the approved outcome. |
| **Participant starter** | The minimum deployable/access foundation, not the completed reference solution. |
| **Private coach materials** | Sanitized full reference, coach guidance, answers and private Finale notes. |
| **Hack package validation** | Local builds/tests, content and isolation checks with a current receipt. |

The standard experience has five outcome-led challenges totaling 150 build minutes,
within a three-hour event including kickoff and wrap-up.
Learners build toward business outcomes rather than receiving the complete architecture and answers at the start.
The minimum starter includes only indispensable access, isolation, fixtures or prerequisites.

Industry intake and Skillable authoring support are separate catalogs.
Check the current [supported authoring industries][industry-catalog] before planning a package.
An unsupported industry requires an explicit support extension or a revised and reapproved scenario;
it must not be silently mapped to another industry.

### Export the right audience's files

When current validation passes and no build is in progress, the portal offers:

- **Export learner ZIP:** learner content and the participant starter.
- **Export private coach ZIP:** the full coach solution and private coach guide.
- **Open package folder:** opens the existing local packages directory in Windows File Explorer.

An existing package folder can be browsed before validation finishes.
Opening it neither validates the contents nor unlocks exports.
The screenshot shows this distinction: one of four milestones is complete and folder browsing is available,
but validation is still running.

> [!CAUTION]
> The local package folder contains private coach materials as well as learner materials.
> Distribute only the learner ZIP to participants.
> Never send the entire scenario folder or private coach ZIP as learner instructions.

Keep deployment-specific passwords and access records private.
Public templates and distributed materials must not contain live credentials.
For larger exports, the portal's 200 MiB limit can require using the agent-generated release archives in VS Code.

### Event rollout and publication are separate

Package completion means the hack is authored and locally validated, **not** that participant environments exist.
If you want an event rollout, explicitly request it and provide the team count, from 1 to 20.
The rollout uses one coach environment and isolated numbered participant environments,
with separate resource groups and azd environments.
Review its targets, costs and authorization separately.

Likewise, exporting a ZIP does not create a GitHub repository, push content or publish Skillable instructions.
Publication/contribution is a separate user-requested operation.
Azure resources can continue to incur charges after you close the browser or VS Code.
Review cleanup with the agent against the exact scenario/event scope; do not delete shared resources indiscriminately.

## Find your files and return later

### Reference files in the browser

In **Build & validate**, scroll to **Reference files**.
Select a listed document, source file or diagram to preview it.
Markdown renders as formatted content; source files display as text and supported images display inline.
The portal is a viewer, not a general-purpose file editor.
Some relative links in Markdown previews remain inert; open the source in VS Code when you need full navigation.

After the reference moves into Create hack, use VS Code for full reference browsing
and **Open package folder** for the generated package files.
The hack view deliberately emphasizes milestones, exports and folder access rather than listing every file.

### Workspace layout

The logical scenario location is `generated-scenarios\<projectSlug>` under the repository.
New workspaces normally use a junction to the adjacent physical `azd-projects` folder.
That is why the screenshot's package path begins with `C:\azd-projects` rather than the repository folder.
Existing legacy workspaces remain in place.

Typical outputs include:

- Requirements, architecture assessment, architecture/runtime diagrams and implementation documentation.
- Infrastructure under `infra`, application source under `src` and azd wiring.
- A deployment summary, runtime evidence, `scenario-validation.json` and a demonstration guide.
- Fingerprinted review/approval state in `workflow-state.json`.
- After composition: a package contract, supporting-artifact inventory and audience-specific packages.

The package layout is:

```text
packages/
  coach/          Full deployable reference for coaches
  participant/    Minimum learner starter
  hack/           Public learner instructions
  coach-guide/    Private solution guidance and Finale
```

Portal-local state is stored separately under `.abcbuilder-portal`,
or the existing legacy `.hackbuilder-portal` state directory.
It includes saved briefs, handoffs, status reports and conversation associations.
These local state folders and generated scenarios are ignored by Git by default;
they are not automatically published or backed up by committing repository documentation.

For implementation details, see the [portal documentation](portal/README.md),
[customization inventory](AGENTSEXPLAINED.md) and [workflow contract][workflow-contract].

### Resume without starting over

1. Reopen the repository in the same intended VS Code workspace/profile.
1. Run the portal launcher again; it reuses a compatible healthy server.
1. Open **Build & validate** or **Create hack**, depending on the scenario's phase.
1. Select the existing scenario.
1. Use **Open scenario chat** for the saved reference conversation,
   or return to the existing HackCreator conversation for composition follow-ups.
1. Read the most recent summary and timestamp before asking the agent to continue.

Closing or reloading the browser does not reset the scenario and is not a stop command for Copilot.
Closing VS Code can interrupt agent work; the browser may still show its last running report.
Ask to resume from the saved brief and evidence rather than rebuilding from scratch.
Do not run two chats or an old legacy worker against the same scenario concurrently.

## Troubleshoot common situations

| Situation | What to check or do |
| --- | --- |
| **Start building** is disabled | Enter a valid slug and nonempty brief, select an industry and confirm a pattern. |
| The portal does not open | Run the launcher in a terminal; read the error and verify Python/setup. |
| An outdated server is reported | Inspect its reported PID and active work; safely stop only that server. |
| VS Code receives no handoff | Check `code`, agent discovery, sign-in, Workspace Trust and the portal error. |
| The project stays **Starting** | Inspect the chat and tool prompts. A handoff does not prove activity. |
| **Open scenario chat** fails | Check the bridge, editor version and URI prompt; use the existing chat manually. |
| Chat association is ambiguous | Use the bridge's repair command only for the known existing conversation. |
| The dashboard looks stale | Select **Refresh**, read the timestamp and inspect the chat for actual activity. |
| **Needs attention** persists | Resolve the outstanding blocked/failed stage; unrelated progress cannot clear it. |
| Files exist but boxes are empty | Ask Copilot to verify and report results; file availability is not completion. |
| Deployment is **Blocked** | Read the reason: authority, readiness, policy, quota and access need different remedies. |
| System tools pass but System is not **Ready** | Also run **Check Azure sign-in** and resolve identity mismatches. |
| Docker is installed but the check fails | Start Docker Desktop's Linux engine and wait for readiness, then recheck. |
| The scenario is absent from Build & validate | Look in Create hack; approved eligible references move phases. |
| Create hack has no scenario | Check reference milestones, approval and blockers in Build & validate. |
| Composition is unavailable | Check approval, phase eligibility, active work and existing validated packages. |
| ZIP exports are unavailable | Wait for current validation and active work to finish; folder existence is not enough. |
| Approval/validation is stale | Revalidate and renew the review/receipt; do not edit state to force readiness. |

The portal intentionally reports missing or ambiguous chat identity rather than opening an arbitrary conversation.
It does not repair authentication, reset permissions or infer consent from an older screenshot.
If the issue is a real host/tenant restriction, follow the approved resolution path rather than bypassing it.

## First-run checklist

- [ ] I opened and trusted the correct repository workspace.
- [ ] I prepared the documented toolchain and checked existing Azure CLI/azd sign-in.
- [ ] I understand that browser reports are not live agent supervision.
- [ ] I entered a business-focused brief with a valid unique slug and industry.
- [ ] I checked the pattern, business units and optional architecture priorities.
- [ ] I continued in the real VS Code scenario chat.
- [ ] I reviewed exact targets, operations, costs and security before authorizing cloud work.
- [ ] I saw real runtime evidence and inspected the working application.
- [ ] I explicitly approved suitability separately from deployment.
- [ ] I started hack composition as a separate context and waited for package validation.
- [ ] I kept learner and private coach exports separate.
- [ ] I treated event rollout, publication and cleanup as explicit scoped operations.

[screen-01]: docs/images/abc-builder/01-create-scenario.png
[screen-02]: docs/images/abc-builder/02-workflow-pattern.png
[screen-03]: docs/images/abc-builder/03-design-priorities.png
[screen-04]: docs/images/abc-builder/04-vscode-handoff.png
[screen-05]: docs/images/abc-builder/05-scenario-board.png
[screen-06]: docs/images/abc-builder/06-initial-milestones.png
[screen-07]: docs/images/abc-builder/07-vscode-permissions.png
[screen-08]: docs/images/abc-builder/08-reference-progress.png
[screen-09]: docs/images/abc-builder/09-deployment-review-boundary.png
[screen-10]: docs/images/abc-builder/10-hack-progress.png
[industry-catalog]: .github/skills/skillable-lod-authoring/references/industry-catalog.md
[workflow-contract]: .github/skills/hack-builder-workflow/SKILL.md
