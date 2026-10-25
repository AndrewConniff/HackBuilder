# ABC Builder visualization portal

The portal is a small local management/view layer. **The real VS Code Copilot agents do the work.**
There is no background Copilot CLI runner, stage scheduler, Azure sign-in manager,
portal approval engine, scenario prerequisite pipeline or worker retry loop in the normal entry point.

For a screenshot-led walkthrough of setup, navigation, VS Code interaction, milestones and exports,
start with the [new-user how-to guide](../ABC-Builder-HOWTO.md).

## Portal sections

The numbered workflow navigation keeps four areas separate:

- **Create scenario**: customer brief, industry, workflow pattern and optional service/business-unit selections.
- **Build & validate**: scenario board, reported progress, deployment-review briefs, continuation and reference files.
- **Create hack**: approval-dependent composition, learner/private coach ZIP exports and local package-folder browsing.
- **System**: shared prerequisite diagnostics and existing Azure CLI/azd sign-in checks.

The working-scenario selector is shared by Build & validate and Create hack only.
System is workspace-wide and never requires a scenario selection.
Create hack lists only scenarios with all nine reference milestones completed and current fingerprint-checked
suitability approval. Missing reports, available artifacts, pending work and failed/blocked stages do not qualify.
Older scenarios with current approval and a current validated-package receipt also qualify when granular reference
reports are missing; explicit pending, running or failed reference stages still prevent the move.
This receipt does not rewrite missing milestone reports as completed.
Eligible scenarios remain listed while hack materials are being authored or are ready to export.
They move from the Build & validate board and selector to the Create hack board and selector, rather than appearing
in both phases. Create hack shows authoring, validation and export readiness, including completed hack validation.
System continues to list every scenario.
Switching sections preserves the form and selected scenario; it never starts an agent or grants approval.
A selection belonging to the other phase is hidden, including its details and chat action, and restored when
returning to its phase or System. Polling updates phase membership as stage reports and approval change.
Starting a new scenario moves to Build & validate. Hash links and browser back/forward navigate the sections.
On smaller screens the left navigation becomes a compact two-column menu. Light/dark appearance applies to all sections.

### Scenario milestones

Select a scenario in **Build & validate** to see its always-visible, ordered reference milestone checklist:
description, architecture, diagrams, Bicep, application, local tests, Azure deployment, runtime validation
and suitability approval. The four hack-authoring stages appear separately in **Create hack**:
challenges, participant starter, private coach materials and package validation. Each list has its own completion count.
Completed stages stay visible beside pending or blocked stages.
Each card shows the recorded summary and its timestamp when available; older reports retain their original summaries.
New agent reports persist a timestamp for each stage, not just the latest overall update.

The checklist reads existing reports without rewriting scenario evidence. Existing source files without a report
are marked **Artifacts available**, not completed or tested. Suitability uses the current fingerprint-checked approval;
a deployment report never grants approval. Approved references move to **Scenario approved** on the board rather
than remaining at an old review prompt. Package completion still requires a current validation receipt.
Milestones appear as a vertical list: green checked boxes for completed stages, a spinner for running work,
empty boxes for **Not started / unreported**, question marks for approval waits and exclamation marks for failures
or blockers. Every icon has a text status; reduced-motion preferences disable spinner animation.
An empty box means no progress was reported, not proof that no work occurred.
Reported limitations remain visible in their original summaries.

## System checks before scenarios

The **System prerequisites** panel restores the shared toolchain checklist before scenario work.
Authorize read-only diagnostics, then select **Check prerequisites**.
One fixed profile covers every catalog service, local container builds, Functions Core Tools and k6 load testing.
The existing checker verifies versions, Python dependencies, PNG rendering, package-feed HTTPS and the Docker
Linux engine. Results include timestamps, affected stages and remedies.
Changing scenario or intake selections never changes or reruns this shared profile.
Earlier narrower reports display **Not checked** until the full workspace profile has been checked.
Reports persist across portal restarts; there is no timed renewal or repeated per-stage whole-machine audit.

**Check Azure sign-in** separately verifies the existing Azure CLI context and matching azd sign-in.
It saves only identity metadata, never an access token. Tenant/subscription IDs come from those tools,
not user-entry fields. Scenario handoffs reuse these observations and revalidate when necessary.
Missing sign-in or conflicting targets require an explicit resolution; no interactive login or default change is automatic.
System reports **Ready** only when the complete toolchain and the Azure CLI/azd authentication checks both pass.

Checks never install/update tools, start Docker, query Azure resources, register providers or deploy.
The portal does not automatically block requirements/design or resume scenarios based on a machine report.
Fix missing dependencies before the affected implementation stage, then recheck.
See [the prerequisite guide](../PREREQUISITES.md).

## User flow

1. Start with `Start-ABCBuilder.cmd` or `python scripts\start_portal.py`.
1. Enter the scenario prompt, project slug, industry, workflow pattern and optional services/priorities.
1. Select **Start building**. The brief is saved, and the real `az-01-conductor` agent chat opens.
1. The agent implements requirements, architecture, diagrams, Bicep, app and tests through its existing skills.
1. Approve the architecture/deployment in that VS Code chat. The agent deploys and proves the reference.
1. Approve the working scenario's suitability in chat and record the fingerprinted approval.
   Open `HackCreator Agent` as a separate VS Code context to derive and validate the hack.
1. Browse scenario/learner/private coach files and download separate learner/coach ZIP exports.

The first handoff opens the scenario chat. The shared working-scenario selector has one **Open scenario chat** action,
available across Build & validate, Create hack and System, including while work is running or approved.
The portal associates the conversation automatically; users do not copy chat links.
It matches the exact original handoff and workspace to read-only native editor identity metadata.
For older duplicate handoffs, the latest successful scenario progress report identifies the continuation.
Pre-portal chats require an exact original requirements attachment and matching successful progress reports.
New launches carry a unique trace ID in their request and phase-started JSON receipt.
The resulting SDK/editor session IDs, native URI and evidence are saved in the scenario's `chat-sessions.json`.
The local [Scenario Chat extension](../tools/vscode-chat-bridge/README.md) reopens that conversation without a prompt.
There are no separate link, replacement or deployment-review chat buttons.
Creating hack materials remains a distinct, approval-checked composition action, not a replacement scenario chat.
Titles are never used for matching. Only identity fields are read from editor databases; history inspection is
limited to the original request and successful progress-report evidence for matching handoffs in this workspace.
Missing or ambiguous evidence produces an explicit error, never an arbitrary association or a new conversation.

Once a phase has been launched, an unlinked follow-up resolves its recorded trace instead of creating a duplicate.
A missing extension or failed reopen never silently starts a replacement chat.
The editor's **ABC Builder: Link Existing Chat to Scenario** command remains an optional advanced repair action.
The bridge acknowledges reopening; it never submits a prompt or approves anything.
On Windows, activation uses the registered editor protocol directly, not a CLI URI relay.
Permissions, authentication, tool execution and decisions remain in the real editor session.
The portal does not proxy responses or run agents itself.

Create hack does not list every generated package file. It keeps separate validated learner and private coach ZIP
exports, plus **Open package folder** and the actual local folder path.
Folder browsing opens Windows File Explorer only after an explicit click and only for the selected scenario's
existing `packages` directory. Browsing does not validate packages or unlock exports.
The folder contains private coach materials; only the learner ZIP belongs with participants.

Outstanding failed/blocked/waiting stages take priority over a later, unrelated completion report.
For example, completed diagrams cannot hide blocked runtime validation or display “No action is needed”.
Resolve the reported issue in the existing chat, then report that stage as running/completed after actual work.

## Workflow pattern choice

**Agentic workflow pattern** is visible in the Create a scenario form, outside the advanced selections.
Industry and workflow pattern use checkable selection cards rather than dropdowns.
Each industry has a distinct inline icon and its exact catalog label.
Both groups are single-choice: the checkbox-style cards use native radio controls for keyboard navigation,
screen-reader semantics and required-selection validation. Industry has no preselected value.
The workflow group offers the 18 patterns in the requirements skill's
[selection guide](../.github/skills/az-scenario-requirements/references/agentic-patterns.md),
with a short description for each. Select one requested pattern or keep **Let AI decide**, the default.
Describe the imaginary customer, intended users, business problem and constraints in the scenario prompt.

The saved brief's `agenticPattern` contains a validated catalog ID. `ai-decides` asks Copilot to propose a fitting
scenario and the simplest useful runtime pattern based on the customer details, industry and business units.
An explicit pattern is honored; fit or feasibility conflicts require a user decision rather than silent substitution.
The handoff asks the agent to record its rationale, simpler alternative and runtime acceptance contract.
Human-in-the-Loop can act as an overlay on a simple primary flow. These are solution-runtime patterns,
not instructions to create extra Copilot build agents.

Older briefs without this field use AI selection for new decisions, while existing recorded scenario decisions
are preserved. Composition still derives the approved reference, not a newly selected design.
Pattern selection does not approve architecture, deployment or hack authoring.

## Appearance

Use the header's **Appearance** selector for **System**, **Light** or **Dark**.
System follows the operating system, including changes while the page is open.
Explicit choices reuse the existing `abcbuilder-theme` browser preference across reloads and tabs.
Selecting System removes the override. If browser storage is blocked, the choice still applies to the
current tab and the portal displays a notice.

## Tool permissions

The portal cannot press **Allow all** or transfer a previous chat's session-only permission grant.
The installed `code chat` launcher has no permission-level argument. Handoffs keep the existing workspace
and profile; they do not change security settings or bypass organization policy.

To reduce prompts for future chats, configure the editor's **Chat: Permissions: Default**
(`chat.permissions.default`) to **Allow all**, if supported and permitted by your installation.
Use workspace scope if that setting supports it and you want the choice limited to this repository.
Alternatively, use the tool approval dialog's workspace-level approvals for specific trusted tools.
A one-session **Allow all** selection is not a persistent default for newly opened chats.

**Allow all** permits potentially destructive tool calls without confirmation. Set it yourself only for a
trusted workspace. Do not enable global auto-approval merely for portal handoffs.
Tool permission does not grant Azure deployment consent, scenario suitability approval or event rollout authority;
business decisions still require a response in the agent chat.
See [Manage approvals and permissions](https://code.visualstudio.com/docs/agents/run/approvals).

Local preparation does not need a separate cloud-authorization prompt: the agent prepares repairs,
private execution-path proposals, implementation wiring and costs within the existing local scope.
Unauthorized Azure/Entra checks remain pending; preparation never implies permission to run them.
For a missing private execution host, the agent should recommend and price a solution before requesting a decision,
not first ask whether it may design one.

Actual same-scenario approvals survive portal migrations and expired worker receipts.
A later read-only grant does not itself revoke earlier deployment consent.
Only an actual user restriction can narrow that consent; agent-written summaries and status cannot do so.
The next review identifies existing approval and requests only missing authority or material additions,
with exact targets, Azure/Entra operations, security impact and incremental/total cost.
Required checks, host/tenant restrictions, suitability approval and separate event/publication requests remain intact.
See [authorization continuity and consolidated review][consent-review].

[consent-review]: ../.github/skills/hack-builder-workflow/SKILL.md#authorization-continuity-and-consolidated-review

## Handoff

The installed VS Code command supports custom agent modes:

```powershell
code chat --help
code chat --mode az-01-conductor --add-file <saved-handoff.txt> --reuse-window <short-instruction>
```

The backend first opens this repository in the reused window, then requests the custom agent chat.
The handoff includes the absolute workspace and exact scenario path; the agent must verify the workspace.
The composition handoff uses `--mode "HackCreator Agent"` and checks recorded suitability approval.
No extension or new runtime dependency is required. VS Code/Copilot must be installed, signed in and trusted
as for a direct manual chat. Missing `code`, a CLI error or timeout is displayed explicitly.
The saved handoff text remains available if manual opening is needed.

The portal records **brief sent**, not **agent started**. Only agent status reports establish activity.
It never launches `copilot`, passes permissive tool flags, changes Azure defaults or invokes deployment tools.

## Deployment review and continuation

When the agent reports `waiting_for_user` at an architecture, local-validation, deployment or review boundary,
the selected scenario shows its latest `deployment-review.md` as formatted headings, tables, lists and code.
Supported locations are the scenario root and `local-evidence/<record>/deployment-review.md`.
The most recently modified safe review is shown with its source path; arbitrary evidence files are not exposed.
Other listed Markdown files also have formatted previews. Raw HTML is displayed as text, never executed;
relative/unsafe links remain inert. No remote scripts, styles or Markdown packages are loaded.

**Continue review in Copilot** opens `az-01-conductor` with the displayed review and a continuation brief.
It is navigation, not a deployment approval button. The scenario agent uses the existing deployment skill directly;
there is no extra deployment agent. Prefer continuing the existing chat when available.
Changed review content or progress invalidates the display fingerprint and requires a refresh before handoff.
The fingerprint is a stale-display guard, not an authorization receipt.

For the same scenario, handoffs include actual authorization and answered-decision history from **both**
`.hackbuilder-portal/projects/<slug>.json` and `.abcbuilder-portal/projects/<slug>.json`, with source provenance.
Neither migration nor a legacy runner lease, timer or initial intake default revokes a later explicit user grant.
The agent reconciles chronology, exact targets, operation scope and actual restrictions, then continues matching
authorized work without routine reapproval. Later explicit restrictions, genuinely changed scope and actual
host/tenant denials still apply. History is not a new grant and is never copied to another scenario.
The portal neither records approval nor resumes a background runner.

## Status

Agents write small JSON reports at stage changes:

```powershell
python scripts\portal_status.py finance-example --stage bicep --status running --summary "Creating infrastructure"
```

The helper atomically updates `.abcbuilder-portal\scenarios\<slug>\status.json`
(existing installations using `.hackbuilder-portal` retain that directory).
The same folder contains the saved request and handoff text.
The status contains `stage`, `status`, `summary`, `updatedAtUtc` and a `steps` map.
It is display-only: no revisions, writer lease, timed receipt, authorization scope or agent scheduling.
The UI polls every four seconds and shows the last report time. It is not a live process monitor.

The board uses these user-facing states:

- **Ready to start**: the brief is saved but has not been handed off. Select **Start building**.
- **Starting**: the brief was sent; the agent has not reported progress yet.
- **Building**: work has been reported, including when an individual step finishes. No new chat is needed.
- **Waiting for you**: respond to the agent's request in the existing chat.
- **Needs attention**: inspect the reported blocker or failure in the existing chat.
- **Ready to export**: a current reference/package-bound validation receipt establishes package completion.
- **Status unavailable**: existing scenario files have no current progress report; check the existing chat.

An individual completed step never resets the scenario to an unstarted brief. Progress reports do not prove
that a process is still running. Stale validation receipts are surfaced, not silently accepted.

**Continue building** is a recovery/start action for unstarted, unknown or blocked scenarios, not an active-build
control. **Create hack materials** appears only after the existing fingerprinted suitability-approval check passes
and no build is reported in progress. Both open new chats; neither restores an existing conversation.
During a build, both are hidden. A waiting-for-user report directs the user to the existing chat.

## Files and exports

Reference documents and diagrams are listed separately from learner and private coach materials.
Learner export contains only `packages/hack` and `packages/participant`.
Private coach export contains only `packages/coach` and `packages/coach-guide`.
Files outside those boundaries, hidden runtime/authentication folders, symbolic-link escapes and common secret
file types are excluded. ZIP actions and the export API require a current package-validation receipt and
no reported build in progress. Draft files remain browsable, but do not unlock exports.
Empty learner/coach file groups are hidden.
Agents remain responsible for sanitizing packages and validating boundaries before distribution.
Exports are capped at 200 MiB; previews at 5 MiB. Existing scenario roots may be repository-managed junctions.
Markdown previews use a shared DOM-only renderer; other document previews remain inert text.

## Existing scenarios and migration

Existing scenario folders, package receipts, approval records and old portal history are preserved.
They appear without inheriting old worker failure/decision cards as current VS Code execution state.
Do not edit a scenario still owned by a legacy worker; finish or stop it before switching.
The launcher refuses to reuse the old runner server. Stop it only while idle, then relaunch.
No Azure resource or permission is changed by this migration.

`portal_visualizer.py` and `visualizer.html/js/css` are the active implementation.
The retired CLI-runner server, workflow engine, dashboard assets and runner-only tests have been removed.
Use `start_portal.py` or `Start-ABCBuilder.cmd`; there is no alternate runner entry point.
Private historical state remains local and is still read for authorization continuity, without executing old jobs.

## Validation

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py"
node --check portal\visualizer.js
node --check portal\markdown.js
node --test scripts\tests\portal_visualizer.test.cjs
```

The server binds only to loopback and validates Host, Origin and Fetch Metadata.
It has no arbitrary shell, process termination, Azure mutation or agent-execution API.
