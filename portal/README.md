# FBC Builder visualization portal

The portal is a small local management/view layer. **The real VS Code Copilot agents do the work.**
There is no background Copilot CLI runner, stage scheduler, Azure sign-in manager,
portal approval engine, scenario prerequisite pipeline or worker retry loop in the normal entry point.

For a screenshot-led walkthrough of setup, navigation, VS Code interaction, milestones and exports,
start with the [new-user how-to guide](../FBC-Builder-HOWTO.md).
For implementation, API/state contracts, native bridge integration and maintenance,
see the [FBCBuilder DEV Guide](../FBCBuilder-DEV-Guide.md).

## Portal sections

### Additive agent conversation

**Build & validate** and **Create hack** include an **Agent conversation** pane for the selected scenario and phase.
On screens at least 1200 pixels wide, it sits in a sticky right-hand column beside the scenario content.
On narrower screens, it stacks below the content; its history remains scrollable.
The existing boards, milestone lists, latest status, timestamps, reported steps, files and exports remain unchanged.
The pane adds a chronological view of your messages and concise agent reports, including intermediate reports from
the same stage that the latest-status display would otherwise replace. It shows the latest 100 conversation entries;
the milestone checklist still retains the latest report for every stage.
Older stage summaries remain visible without rewriting historical evidence. Unreported activity is never inferred.

The existing VS Code session is still the execution backend. **Send message** relays your explicit text to that
phase's linked native conversation through the editor bridge; it never creates another session or Copilot worker.
**Open existing agent chat** remains available for the full conversation and native permission prompts.
Scenario and composition histories and unsent drafts are separate. Browser drafts are not persisted across reloads;
saved messages and reported feedback survive portal restarts in local state, outside learner exports.
Reports refresh with the existing four-second status poll. Polling, navigation and history reads never send messages.

New handoffs and portal messages ask the agent to report meaningful within-stage progress, real check results,
blockers and actionable questions, not just milestone transitions. This is agent-reported feedback, not an automatic
tool transcript, private reasoning stream, process monitor or guarantee that every operation is reported.
The portal does not read conversation text from editor history to populate this pane.

Brief confirmation still uses the existing fingerprint-bound controls. Formal architecture/deployment and suitability
decisions and native tool permissions remain in VS Code. Sending text does not record these approvals, start composition,
deploy an event or publish. The existing agent must apply its normal workflow and permission boundaries.
No new cloud authority is inferred from message dispatch.

Messaging requires [FBC Builder Scenario Chat](../tools/vscode-chat-bridge/README.md) **0.3.0 or later**.
Upgrade the bridge and restart its extension host, then restart the portal server and reload the page.
A receipt means only that the editor accepted the dispatch, not that the agent ran or completed work.
Unacknowledged or interrupted delivery remains visibly uncertain and is never automatically replayed.
Check the native conversation before sending again. Only a proven pre-dispatch failure permits an explicit retry.

The numbered workflow navigation keeps four areas separate:

- **Create scenario**: customer brief, industry, workflow pattern and optional service/business-unit selections.
  **Refine with AI** opens scoping-only dialogue in the same real scenario agent.
  **Start building** requests implementation.
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

When an agent-written scoping brief exists, **Your scenario brief** appears as an expanded, paper-style document
with classic Courier typography above the milestone list. There is no disclosure arrow to find or open.
A static review cue and highlighted border draw attention when a response or retry is needed.
The existing **Modify brief**, **Confirm brief**, status and error controls stay with the document.
No document box appears until a brief is available. This visual treatment does not change confirmation or approval.

Select a scenario in **Build & validate** to see its always-visible, ordered reference milestone checklist:
description, architecture, diagrams, Bicep, application, local tests, Azure deployment, runtime validation
and suitability approval. The four hack-authoring stages appear separately in **Create hack**:
challenges, participant starter, private coach materials and package validation. Each list has its own completion count.
Completed stages stay visible beside pending or blocked stages.
Each card shows the recorded summary and its timestamp when available; older reports retain their original summaries.
New agent reports persist a timestamp for each stage, not just the latest overall update.

For a current confirmed scoping brief, **Scenario description** shows **Brief confirmed**
instead of the superseded input wait. Saved change requests show **Changes saved - revision pending**.
These display-only states use the matching brief response; they do not count as completed implementation milestones.
Changed briefs restore the agent-reported wait, and running, failed or completed work is never hidden.
The original report remains in **Agent-reported steps**.
Confirmation resumes the normal scenario workflow, starting with requirements and architecture artifacts.

### Start from an existing scenario

While drafting a **New scenario**, a meaningful prompt pause or blur triggers an automatic local catalog comparison.
Up to three useful suggestions appear below the prompt; no match means no distracting panel.
Matches can cross industries and explain workflow/architecture overlap, differences, local availability,
profile freshness and metadata review status. This first pass is deterministic, not an AI verdict.
An unavailable reference is inspiration-only. Failed comparison never blocks the normal intake buttons.
Typing or changing selections invalidates pending results; old asynchronous responses cannot replace a newer draft.

Choose **Review match**, then **Use as starting point** to attach its inspected manifest/artifact snapshot.
Your project name, prompt, industry, business units, services and pattern remain unchanged.
Both submit buttons then refine the adapted brief before any copying/build. **Keep my original idea** removes
the attachment and dismisses suggestions for that exact draft; editing the idea permits new suggestions.
The separate manual **Start from existing** picker retains its original source-prefill behavior.

**Refine with AI** assesses reuse/partial reuse/build fresh in the existing scenario agent and records a
Recommended starting point in the brief, without selecting it for you or starting another model/session.
The brief's optional **Compare catalog starting points** control supports a later source choice.
That choice creates a separate fingerprint-bound selection and requests scoping-only revision in the same chat.
Confirmation pauses until the agent assesses the selected source and binds a revised brief; fresh confirmation
is then required. The original request never changes. If delivery fails, the existing Modify brief / Save changes
controls retry the saved change request; polling never resends it. Building fresh instead is also an explicit revision.

Technical profiles are portable sidecars in [scenarios/reuse-profiles](../scenarios/reuse-profiles),
outside approved reference folders. Explicit `scenario_match.py enrich` updates them, never portal browsing.
Extracted metadata stays `needs-review` until explicitly reviewed; code/design mentions are not runtime proof.
The rebuildable index is [reuse-profiles.json](../scenarios/reuse-profiles.json); manifest v1 remains compatible.
Automatic discovery requires portal backend **22**; restart the runtime and reload the page to activate it.
No bridge upgrade is needed beyond the existing brief-continuation/messaging requirements.

In **Create scenario**, two large icon buttons make the starting choice explicit:
**New scenario** (selected initially) or **Start from existing**.
Choose **Start from existing** to reveal the source picker, select a local reference and choose
**Modify brief from source**. Its brief and catalog selections populate the same editable intake;
the refined source brief (or requirements when no scoping brief exists) remains visible.
The source file inventory stays internal for artifact validation; it is not shown in the brief editor.
If the full brief exceeds the intake's 6000-character limit, the editable prompt uses the original saved intake
and explicitly labels the full brief as reference-only.
Give the target a new project name and change its industry, business units, prompt and other selections.
**Use as new idea instead** clears source reuse while retaining the edited intake.
Selecting **New scenario** does the same without discarding the form's current text and selections.
Choosing either entry option never starts an agent, copies files or grants approval.
The existing option requires loading a source before submitting, so it cannot silently create an unrelated new idea.

Both submit buttons send adaptations to the existing scoping flow. Use **Modify brief** and **Confirm brief**
as usual. No workspace or files are copied during scoping.
After confirmation, `az-01-conductor` uses the `az-scenario-adapt` skill to prepare an isolated copy and compare
the copied artifacts with the revised brief. It preserves fitting app/infrastructure/design files and changes
only affected surfaces, including target-domain sample data and tests. This is not a separate agent or pipeline.

Source selection is bound to the manifest, brief and reusable file hashes. If any change before save or preparation,
reload the source and review again. Inferred metadata stays visibly `needs-review`;
unavailable references cannot be selected. Credential-pattern matches and nested artifact links block reuse.
Environment settings, parameter-value files, build outputs, packages, approval/consent records and runtime/deployment
evidence are not copied. The source remains untouched, and normal target design, deployment and suitability gates apply.
The baseline and reconciliation reports prove file-copy/change decisions only, never runtime success.

The checklist reads existing reports without rewriting scenario evidence. Existing source files without a report
are marked **Artifacts available**, not completed or tested. Suitability uses the current fingerprint-checked approval;
a deployment report never grants approval. Approved references move to **Scenario approved** on the board rather
than remaining at an old review prompt. Package completion still requires a current validation receipt.
Milestones appear as a vertical list: green checked boxes for completed stages, a spinner for running work,
empty boxes for **Not started / unreported**, question marks for input/approval waits and exclamation marks for failures
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

1. Start with `Start-FBCBuilder.cmd` or `python scripts\start_portal.py`.
1. Enter the scenario prompt, project slug, industry, workflow pattern and optional services/priorities.
1. Optionally select **Refine with AI**. The agent interprets the prompt, spots architectural gaps/edge cases,
   and asks a few tailored questions in VS Code chat, not a predefined questionnaire in the browser.
   It preserves the original intake and saves a concise `scoping.md` beside `request.json`.
   Build & validate shows these agent-written notes as they are saved.
   At the bottom of the brief, **Modify brief** reveals a comments box with **Save changes** and **Cancel**.
   The box stays hidden until requested. **Confirm brief** records acceptance of that exact version and sends
   a fixed continuation to the existing scenario agent, resuming the normal workflow without a typed prompt.
   **Save changes** sends a scoping-only revision request instead; the revised brief needs fresh confirmation.
   Neither action grants new Azure/Entra authority, deployment or suitability approval.
   An edited brief requires a fresh confirmation. The original intake and agent-reported status are preserved.
   Saving feedback and validation/connection errors appear beside these controls.
   A successful confirmation updates the displayed summary and disables the **Brief confirmed** button;
   requested changes display as saved, not as an agent-completed revision. Unsent comments are retained on failure.
   **Confirm brief** is also the retry action for older confirmation-only receipts or failed continuations;
   there is no separate Continue button. It stays enabled until dispatch is acknowledged.
   Missing acknowledgement displays an error; uncertain sends are not blindly repeated.
   For an unsent change request, **Modify brief** restores the saved comments for editing and **Save changes**.
   **Open scenario chat** remains navigation for reviewing progress and responding to genuine decisions.
   The portal never launches a CLI worker, replaces the conversation or weakens its permissions.
   Architecture/deployment review and working-scenario approval remain unchanged; do not submit a duplicate project.
   Scoping alone performs no workspace generation, prerequisite/identity audit or Azure operation.
1. Select **Start building**. The brief is saved, and the real `az-01-conductor` agent chat opens.
1. The agent implements requirements, architecture, diagrams, Bicep, app and tests through its existing skills.
   Normal build requests also get a bounded gap review before architecture, without repeating answered questions
   or forcing an interview when the brief is sufficient. Scoping confirmation is not deployment/suitability approval.
1. Approve the architecture/deployment in that VS Code chat. The agent deploys and proves the reference.
1. Approve the working scenario's suitability in chat and record the fingerprinted approval.
   Open `HackCreator Agent` as a separate VS Code context to derive and validate the hack.
1. Browse scenario/learner/private coach files and download separate learner/coach ZIP exports.

On Windows, a newly started portal opens a console titled **FBC Builder - Browser App Runtime**.
Keep that window open while using the browser app; closing it stops the portal. You can minimize it.
The console shows a static runtime notice; diagnostic output continues to go to the portal's `server.log`.
Opening the launcher again reuses the existing healthy runtime rather than opening another runtime console.

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
The editor's **FBC Builder: Link Existing Chat to Scenario** command remains an optional advanced repair action.
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
Explicit choices use the `fbcbuilder-theme` browser preference across reloads and tabs.
After the FBC migration, choose Light or Dark again if desired; the first visit follows the system theme.
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
`.hackbuilder-portal/projects/<slug>.json` and `.fbcbuilder-portal/projects/<slug>.json`, with source provenance.
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

The helper atomically updates `.fbcbuilder-portal\scenarios\<slug>\status.json`
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
Use `start_portal.py` or `Start-FBCBuilder.cmd`; there is no alternate runner entry point.
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
