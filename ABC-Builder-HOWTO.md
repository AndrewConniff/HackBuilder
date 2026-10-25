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

Follow the [prerequisite guide](PREREQUISITES.md) for installation and authentication instructions.
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
