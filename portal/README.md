# Local ABC Builder scenario studio

The intake portal launches real local Copilot CLI jobs, using the current user's
Copilot authentication. It is not a hosted agent service or an Azure deployment.
There are no browser-side Azure/GitHub credentials and no new runtime packages.

## Appearance and accessibility

Use the **Dark mode** switch in the upper-right corner to choose light or dark appearance.
With no saved choice, the portal follows your operating system's color preference, including live changes.
An explicit choice is remembered locally in your browser and synchronized across portal tabs.
If browser storage is blocked, the switch still works for the current tab and displays a notice.
Appearance changes never start jobs, authorize tools or alter scenario state.

The interface uses the supplied Microsoft Neutral / ILT palette: purple `#8661C5`, expanded teal `#389A91`,
blue `#0078D4`, magenta `#C03BC4`, teal `#49C5B1` and light purple `#C5B4E3`.
Light mode uses white `#FFFFFF`, warm off-white `#FFF8F3`, black `#000000` and blue-black `#091F2E`.
Dark mode uses blue-black surfaces and light text. Contrast-safe accent shades are used for small text;
the exact palette colors remain available for fills, borders and highlights.
The switch supports keyboard activation, visible focus, an announced on/off state and a 44-pixel touch target.
Reduced-motion preferences disable smooth scrolling.

## Run

**Easiest on Windows:** double-click [`Start-ABCBuilder.cmd`](../Start-ABCBuilder.cmd)
in the repository root. It starts or reuses the local server and opens the authenticated browser page.
You can create a Windows shortcut to this file for desktop access. Python must be on PATH.

**In VS Code:** select **Terminal > Run Task > ABC Builder: Open Portal**.
Both launchers reuse the existing startup helper; they do not launch a scenario, deploy resources,
or grant approval. A stopped web server cannot serve a button to start itself.

From the repository root:

```powershell
copilot login
python scripts\portal_server.py
```

For automatic startup and browser opening, use:

```powershell
python scripts\start_portal.py
```

The scenario agent (`az-01-conductor`) runs this helper automatically when
invoked interactively in VS Code. An agent-scoped `sessionStart` hook provides
the startup on supported hosts; on hosts without scoped-hook execution, the
agent instructions require the same helper once at task start. Hook discovery
depends on the selected runtime, trusted workspace and enterprise hook policy.
See [VS Code hook support](https://code.visualstudio.com/docs/agent-customization/hooks).
Restart the chat session after changing the agent definition.

On the installed CLI tested on 2026-10-22, scoped startup was deferred at the
workspace-trust gate; the actual scenario agent successfully used the fallback
helper. Hook configuration alone is not proof of execution. If startup fails,
the agent reports it and the manual helper remains available.

The helper verifies the authenticated health endpoint before reusing a server,
starts a detached local Python process if needed, and opens the private entry
point in your default browser. Opening the portal does not launch a scenario.
Portal-launched CLI jobs inherit `ABCBUILDER_PORTAL_JOB=1` and skip startup.
The legacy `HACKBUILDER_PORTAL_JOB` guard remains supported for existing workers.
This prevents recursive portal/browser launches. It does not change Azure
deployment or scenario-approval gates.

Open the **private URL printed by the server**, including its token fragment.
The browser removes the fragment after putting the token in session storage.
Do not share the URL. The server binds only to `127.0.0.1`; API requests require
the random per-start token and reject foreign origins/hosts.
Use `--port 8766` if the default port is busy. Stop with Ctrl+C.

After updating backend code, stop the existing portal server and run the helper again, then reload
the page. The launcher verifies the backend workflow version before reusing a server.
If outdated, it reports the server PID and stops without opening the browser, replacing the server
or interrupting workers. The dashboard also rejects incompatible backends.
Re-running the launcher or refreshing the page does not restart a running Python server.
Finish/stop active workers before a planned server restart.
When starting a replacement, readiness waits for the new process's connection record before authenticating,
so a previous server's per-start token is not sent to a newly bound listener.

No server is installed as a system service. Automatic startup leaves the local
process available after the chat turn. Connection details (including the private
token) are saved in ignored `.abcbuilder-portal/server.json`; never publish it.
Background diagnostics are in `.abcbuilder-portal/server.log`, without the launch
URL. For a foreground server, use the original command and Ctrl+C to stop.
To stop a background server on Windows, inspect the PID in `server.json` and
verify that it belongs to this workspace's `portal_server.py`, then use
`Stop-Process -Id <PID>`. Never terminate by process name. Re-running the helper
reuses a responsive instance; it does not kill another process occupying the port.
Use a trusted personal/local machine: this version is not designed for multiple
users, remote hosting or untrusted local accounts.

Existing checkouts reuse `.hackbuilder-portal` if it exists and the new state directory does not.
This compatibility path preserves running jobs, leases and history; it is not an automatic migration.
The physical checkout and GitHub repository retain their existing locations.

## Intake and execution

The navigation separates three views: **Shape the scenario** is intake; **Build & validate** shows
technical reference progress, deployment consent and runtime validation; **Compose the hack** shows
approval, five composition steps and the actual package documents/downloads. Selecting a view updates
the active navigation item; it does not launch work. The scenario selector is shared by build/hack views.
Authenticated artifact previews render Markdown headings, lists, tables, quotes and fenced code.
Raw HTML stays inert; only HTTP/HTTPS external links become clickable. Relative document links remain
labels (select their document from the inventory). This lightweight preview is not a full Jekyll renderer.
Release ZIP downloads
retain public/private labels. Coach solutions and Finale must not be distributed to participants.
Only allowlisted package Markdown and named release ZIPs are served; arbitrary workspace paths are denied.

The right-hand scenario summary includes a live **Before you build** checklist explaining every disabled-build reason.
Choose a unique project slug, one industry, at least one business unit (Generic is preselected), and explicit local
tool execution consent. Field links focus the relevant control without changing selections or granting consent.
Invalid project names, missing selections and consent errors appear inline after editing or following a checklist link.
Project names use lowercase letters, numbers and single hyphens, with a maximum of 40 characters.
Prompts are optional when services are selected; technical priorities and architecture reuse are optional.
Missing CLI installation, initial catalog/status loading, all four worker slots being busy and a submission
in progress are
shown as execution blockers, not missing fields. Preview/download validate the brief without requiring tool consent.
Both preview and launch recheck input before sending; duplicate launch submissions are blocked.

The project name identifies a saved workspace; **Reuse a scenario** selects a source architecture, not a project
to continue. Reusing an architecture still requires a unique target name. If a name already exists, the intake
offers **Open existing project** (or a read-only file preview) and an explicit suggested new name.
Opening a project never starts a worker or grants approval. Choosing the suggestion changes only the name,
preserving the rest of the intake. Saved project records are checked even when no scenario folder exists.
Launch refreshes the saved-project list; a conflicting request is rejected without overwriting the original.
If a record has no available run, the portal explains that its saved state remains intact.

For older jobs lacking stage telemetry, a valid approved snapshot labels constituent reference
artifacts **reviewed**, not pending or newly tested. Runtime and local test outcomes are not invented.

1. Describe a scenario or select Azure building blocks. Choose one industry,
   one or more business units, optional Well-Architected priorities and technical domains, and a project slug.
   Generic is exclusive: it describes a typical industry workflow without targeting a specific unit.
1. Preview the generated prompt or download the normalized JSON request.
1. Explicitly authorize local CLI tool execution and select **Build my scenario**.
1. Follow the scenario dashboard while the backend completes requirements and architecture.
   Answer its design confirmation card in the portal; no VS Code handoff or document editing is needed.
1. The backend creates diagrams, Bicep, application and tests. Step summaries are primary;
   raw logs remain collapsed under **Technical details and execution log**.
1. Answer only displayed unresolved decisions. Cloud preparation permission is separate from deployment
   consent after actual what-if, exact targets and estimated costs are available.
1. Once live acceptance and the review snapshot exist, open and test the app.
   Confirm functionality, write affirmative suitability approval, then select
   **Approve & compose hack**.
1. The backend verifies the current fingerprint, records approval and starts
   the hack composition agent. Event rollout and publication are not authorized.

The initial job is instructed to implement locally and stop before Azure mutations.
Local design uses current public evidence and delegated provisional region/model choices.
Account, quota and budget checks are deferred until authorized deployment preparation.
Follow-ups consume canonical intake, all answers and history, not just the latest free-text message.
The portal displays structured decisions; free-text instructions cannot grant cloud consent.
**Refresh status** only reads persisted state and never starts another agent.
Refresh also reads fingerprint-bound composition receipts from the scenario workspace, including
work completed by a standalone composition job. Five hack stages cover planning, learner content,
starter, coach and package validation. An approved review is shown as approved, not another prompt
to approve. Historical deployment remains user-attested, never upgraded to independently passed tests.

After successful package validation, the composition worker runs:

```powershell
python scripts\hack_workflow.py record-packages generated-scenarios\{projectSlug}
```

This requires approval and successful named command evidence in `packages/validation/local-checks.json`.
It saves `composition-status.json` there, bound to the approved reference and all package contents.
Missing receipts do not imply success; edited packages make the receipt stale. Refresh checks this
without changing project revisions, decisions, approval or starting an agent. Existing portal project
records gain pending hack stages in memory on read; their old progress/history remains unchanged.

The backend invokes the installed `copilot` executable with an argument list,
the canonical agent name, `--prompt`, `--allow-all-tools`, `--no-ask-user` and
text output. It inherits host model preferences and existing authentication.
Up to **four independent scenario workers** can run concurrently in the portal.
A durable project writer lease rejects overlapping jobs for the **same scenario**, including across portal instances;
every state update checks its expected revision under a kernel lock.
This coordinates cooperating tools, not arbitrary filesystem editors. VS Code work must check the
same project state and must not edit a scenario with an active writer. Never manually clear a live lease.
Path access additionally allows only the adjacent `azd-projects` workspace
directory; it does not enable unrestricted filesystem access.

### Working across scenarios

Switch between scenarios and between **Build & validate** and **Compose the hack** without stopping running jobs.
The worker status lists active scenarios and the four-slot capacity. Reaching capacity blocks new launches,
resumes and composition jobs, not navigation, read-only inspection, or stopping a specific selected run.
Finishing, failing or stopping one worker does not clear another worker's process, logs, progress or writer lease.
An orderly server shutdown stops and joins all workers owned by that server.

Unsaved instructions, decision choices, approval text and review confirmations are kept separately for each scenario
in the current tab, along with its last workspace stage. They are not persisted across a browser reload.
Review confirmations are restored only for the same run and reference fingerprint; changed evidence clears them.
An in-flight response from a previously selected scenario cannot replace the current selection or erase its draft.
Scenario actions are disabled while a newly selected run is loading. Starting or resuming work and then navigating
elsewhere does not switch you back when that request finishes.

[GitHub supports multiple concurrent CLI sessions][cli-sessions].
Four workers is this portal's chosen limit, not a promise of unlimited machine resources or Copilot usage.
Authentication, rate limits and account policies still apply. Workers share the host and installed tools:
their instructions prohibit editing other scenarios, changing shared CLI account/subscription defaults or
installing/upgrading shared SDKs during a job. Missing prerequisites or potentially conflicting Azure targets
require user coordination. Each scenario retains its own deployment consents and suitability approval.
These instructions coordinate cooperating workers; they are not OS-enforced isolation.

[cli-sessions]: https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/work-with-multiple-sessions

**Local tool consent is significant:** tools can modify files and execute
commands as your user with your existing credentials. Workflow instructions are
not a sandbox or an OS-enforced cloud-mutation boundary. Do not use this portal
for untrusted prompts. Inspect generated what-if and targets before authorizing
deployment; keep Azure permissions least-privileged. There is no auto-login,
token collection, automatic scenario approval or hidden event rollout.

If Copilot authentication is missing/expired, the job fails visibly; run
`copilot login` in a terminal, then retry. CLI presence is not an authentication
health check. A successful CLI exit is not a passed scenario.

## Catalogs

- Industry choices and verticals come from
  [`microsoft_industry_verticals.csv`](../microsoft_industry_verticals.csv).
- [`catalog.json`](catalog.json) is the editable initial **repository intake
  allowlist**, not organizational governance approval or proof of subscription
  availability. Selected services are design inputs; live regions/SKUs/models,
  required dependencies and quota must still be verified by the orchestrator.
- The five pillars match the
  [Azure Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/pillars).
  High availability and recovery are Reliability domains, not extra pillars.
- The intake supports more industries than the current Skillable publication
  catalog. Unsupported industries require a composition classification decision,
  not a silent substitution.

## Reuse an architecture

The intake catalog reads `generated-scenarios/*/scenario-manifest.json`, including top-level junctions.
Select a source, choose a **new** project slug, target industry and business units, and review the service choices.
The source architecture guides a new reference; it is not a deployment clone or an approved hack package.
The worker adapts the sample app, agent grounding, synthetic data, personas and acceptance cases.
Current technology evidence, design confirmation, validation and suitability approval are all required again.
No source files are automatically copied. Credentials, `.azure`, endpoints, deployment scopes,
approval records, runtime receipts and packages are never adaptation inputs.

Backfill existing folders and export portable metadata into the repository:

```powershell
python scripts\scenario_catalog.py refresh
```

Workers refresh their own manifest after material changes; the backend refreshes it when a scenario job exits.
For reviewed metadata, supply a JSON object with `title`, `summary`, `industry`, `businessUnits`,
`services`, `pillars`, `domains` and `metadataStatus: "curated"`:

```powershell
python scripts\scenario_catalog.py refresh generated-scenarios\finance-security-hack --metadata reviewed-metadata.json
python scripts\scenario_catalog.py index
```

Automatically initialized manifests are visibly `needs-review`; no deployment success is inferred.
The schema includes `schemaVersion: 1`, stable slug `id`, those metadata fields,
allowlisted relative `artifacts`, and `source` (null or `{scenarioId, manifestDigest}`).
Catalog metadata is excluded from the approval fingerprint; actual source/app/infra edits still invalidate approval.
The manifest digest prevents silently adapting a different metadata revision than the one selected.
Manifest metadata must contain no secrets, customer data or deployment identifiers.

[`scenarios/catalog.json`](../scenarios/catalog.json) contains portable metadata only.
It is distinct from the existing external contribution registry. Entries without local reference files are
visible but unavailable for reuse. To consolidate later, transfer each reference folder and its manifest into
the shared location, then expose those folders under `generated-scenarios` and rebuild the index.
No storage credentials, automatic remote sync, Azure operations or GitHub publication are introduced.
**Refresh catalog** is read-only; invalid manifests appear as errors instead of silently disappearing.
Reusing a source never modifies it. New adaptations record their source ID and digest in their own manifest.

## Local data and recovery

The scenario selector also discovers valid project-slug directories/junctions under
`generated-scenarios`, even without portal run history. These appear as **local project**
read-only previews with available reference documents and package materials. Missing stage telemetry
is not invented; discovery does not create state, approve, run jobs or deploy resources.
Portal-managed scenarios take precedence over duplicate disk entries. Refresh discovers new folders.

Requests, input prompts, agent output and run metadata persist under the ignored
`.abcbuilder-portal/` directory (or the retained legacy directory). They may contain local environment information:
do not publish them. Recent runs are selectable after restarting the server.
Runs interrupted by shutdown are explicitly marked interrupted on restart.
The browser displays only a bounded log tail; full output remains in the run's
`output.log`. Use **Stop job** to stop the owned CLI process tree on Windows.
Partial files/resources are preserved, never automatically deleted.

The portal never serves arbitrary workspace files. Review readiness is checked
against the canonical approval helper, not inferred from a CLI success message.
The live review snapshot and exact fingerprint are required for composition.

The approval helper additionally supports explicit historical user attestations when a successful
reference was tested in a deleted, inaccessible one-off lab. Use the canonical workflow's
`attest-history` command with the actual user statement and unavailable-evidence reason, then snapshot
and record separate suitability approval. This is not automatic inference from local tests or an
agent-authored pass. The dashboard labels historical evidence, hides the unavailable app link and
does not display granular passed checks. Future deployments in permanent subscriptions should retain
actual endpoints, target details, timestamps and runtime logs. No historical record grants cloud consent.

## Project state and worker reports

Versioned project records live at `.abcbuilder-portal/projects/<projectSlug>.json`, separate
from scenario suitability evidence and individual run logs. Existing legacy runs have no inferred
progress; resuming creates a project record and asks the worker to reconcile actual evidence.
Launching a new brief with an existing slug is rejected; use its saved scenario instead.

Project status and process status are distinct. An exit code of zero without stage evidence means
`needs_attention`, not a successful scenario. Local validation can be complete while deployment and
live acceptance remain pending. Pending decisions survive server restart and are shown until answered.
The dashboard groups attempts by scenario and follows the latest attempt.

The backend supplies `ABCBUILDER_PROJECT_STATE`, `ABCBUILDER_PROJECT` and `ABCBUILDER_RUN_ID`.
Legacy `HACKBUILDER_*` variables remain accepted for running workers.
Workers read the latest revision and submit one JSON event file per transition:

```powershell
python scripts\portal_workflow.py read
python scripts\portal_workflow.py report --revision 3 --event stage-event.json
```

Optional VS Code engineering work must claim the same writer lease before editing an idle project.
Use a distinct owner identifier, the actual project directory and current revision; read/report use
the same explicit arguments when the backend environment variables are absent:

```powershell
python scripts\portal_workflow.py read --directory .abcbuilder-portal\projects --project finance-agent
python scripts\portal_workflow.py claim --directory .abcbuilder-portal\projects `
  --project finance-agent --owner vscode-repair-1 --revision 12
```

Finish that external lease using `finish` with the same directory/project/owner and an explicit
`--outcome completed`, `failed` or `cancelled`. Backend-launched workers must not claim/release their
own leases: the server owns their lifecycle. A conflicting claim fails without changing state.
Claiming a new external project additionally requires `--request` with normalized intake JSON.

An event contains `stage`, `status`, concise `summary` and `evidence` (artifact references or exact
command/results). Completed steps require evidence. Known stages are requirements, architecture,
diagrams, bicep, application, local-validation, deployment, live-validation and review.
Statuses are pending, running, completed, waiting_for_user, failed and cancelled.

To stop for user input, include a `decision` object with `kind`, `question`, `reason`, distinct
`choices`, and an explicit `acceptChoice` for design/cloud decisions. The decision blocks further work
until the backend records the user's answer against its ID and project revision. The worker cannot
record user consent or suitability approval through reports.

```json
{
  "stage": "architecture",
  "status": "waiting_for_user",
  "summary": "Private managed-identity backend with public anonymous chat.",
  "evidence": ["02-architecture-assessment.md"],
  "decision": {
    "kind": "design",
    "question": "Confirm this architecture for local implementation?",
    "reason": "Review the proposed security boundaries and dependencies.",
    "choices": ["Confirm design", "Revise design"],
    "acceptChoice": "Confirm design"
  }
}
```

Cloud decision kinds are `deployment-preparation` and `deployment`, attached to the deployment stage.
Their `scope` contains account, subscriptionId, tenantId, resourceGroup, environment and region.
Deployment additionally includes actual `whatIfEvidence` and `estimatedCost`; its target scope must
match prior preparation permission. A new permission request invalidates superseded consent.
Revisions invalidate design confirmation and all cloud authorizations. Architecture confirmation
never unlocks hack composition; only the existing live-evidence/fingerprint approval helper does.

On restart, jobs whose owning server and worker have exited become interrupted and release their lease.
A surviving worker retains its lease. Inspect/stop it locally first; **Stop job** then recovers the
orphaned run. A new server never kills a potentially reused, unowned process ID.
Jobs belonging to a still-live server are not silently reclaimed. No worker process is automatically
restarted and no cloud mutation is retried.

## Validation

From the repository root:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py"
node --check portal\app.js
node --test scripts\tests\portal_dashboard.test.cjs
```

The tests cover intake validation, consent, host/origin/token checks, persisted
subprocess stage reports, decision replay, stale revisions, competing writers,
read-only refresh, dashboard actions, failure/interruption states and the explicit approval gate.
They use test fixtures and isolated local subprocesses, not real Azure deployments.
