# Local ABC Builder scenario studio

The intake portal launches real local Copilot CLI jobs, using the current user's
Copilot authentication. It is not a hosted agent service or an Azure deployment.
There are no browser-side Azure/GitHub credentials. Backend readiness uses the repository
Python environment and Playwright/Chromium; the HTTP server itself uses the standard library.

## Execution ownership

The portal is a friendly interface to the same two canonical agents, not an additional approval workflow.
The Python backend checks tools, the actual browser runtime, approved-proxy .NET restore/build and existing
Azure CLI/azd sign-ins before launching a scenario worker. Its collapsed **Backend readiness** card shows
the consolidated result and a fixed local setup/recheck action. The user normally prepares the machine once.

Python assigns one bounded scenario operation at a time, verifies completion evidence and relevant builds,
then automatically schedules the next operation without a stage-by-stage approval.
Each scenario retains its own workspace, writer, inputs and evidence.
CLI exit zero without the assigned result is an error, never scenario success.
Failures preserve partial work; no hidden retry loop changes permissions or cloud targets.
Design, exact-target cloud consent and deployed-scenario suitability remain the existing explicit checkpoints.
Composition remains a separate approved-reference job producing the minimum starter, guides and release archives.

## Resume and pause controls

The Build view exposes **Play / Resume**, **Pause** and **Cancel run** without opening instructions.
Play resumes cancelled, paused, failed or needs-attention attempts using their saved request and evidence.
It requires retained local consent, a free worker slot and no unresolved decision or setup blocker.
Granting consent alone does not start a worker; the status text explicitly distinguishes idle from running.

Pause stops the current owned process and releases its writer after cleanup, preserving partial files and evidence.
It is checkpoint-based resumption, not suspension of the process or its memory.
Cancel also stops the current attempt and preserves work; Play can recover it later.
Neither action deletes files or Azure resources, revokes consent or rolls back an in-flight cloud operation.
The older Stop job action remains compatible with cancellation.

### Resume local projects

Folders found on disk without a managed execution appear as **local project**.
Select one, authorize local execution once, and choose **Resume existing scenario**.
The backend adopts that exact workspace and first recovers the business scope and dependency inventory
from its requirements, architecture and implementation. No new brief or duplicate project is needed.
Incomplete or inferred manifests are reviewed against the actual reference, not treated as validated intake.
The documented Generic business-unit fallback is explicit when older artifacts lack unit targeting.

Recovered intake is checked against current catalogs, then the full recovered dependency scope is audited.
Existing assets are reused and revalidated operation by operation; file presence does not mark a stage complete.
The project then uses the same progress, Pause, Cancel and Resume controls as portal-created scenarios.
If discovery lacks enough evidence to recover genuine business scope, the failed attempt explains what is missing.
Already-managed projects and active writers cannot be imported again.
Import does not carry over Azure permissions, infer deployment success, approve suitability or start composition.
Existing reference/package files are preserved; normal design and subsequent cloud/review checkpoints still apply.

Cancel also works while a project is idle or waiting for a question. It preserves unanswered decisions;
resuming does not silently answer them.

## Backend-owned question handling

Authorized deployment preparation must validate subscription-specific regional eligibility for the complete
resource/SKU/feature set. Public service availability and successful what-if do not establish deployability.
The backend checks the scenario's fresh, scope-bound `regionalReadiness` evidence before accepting preparation,
starting deployment consent or launching provisioning. Cosmos zone access flags, VM SKU restrictions and
family/total vCPU plus instance quota, and App Service worker quotas are distinct checks.
Missing, denied, unknown, insufficient or stale results block deployment. Failed checks invalidate active
deployment grants with an audit record; Resume returns to read-only preparation rather than repeating provisioning.
Candidate recommendations retain the scenario's security/reliability requirements and authorized region scope.
Quota and eligibility checks cannot reserve regional allocation capacity.

Proposed business questions remain internal until a bounded backend review reads intake, answered decisions
and relevant evidence. Users never classify or withdraw questions themselves.
Routine implementation choices and solution-created IDs, endpoints and receipts become recorded backend actions,
not user questionnaires. Already-answered input is reused. No user answer or deployment output is fabricated.
Genuinely unresolved business/security decisions require a documented gap in saved input and a distinct impact
for every choice before appearing in the portal. Verified external failures become actionable setup blockers.
Insufficient classification evidence fails the job visibly instead of exposing an unclassified question.

A CLI denial without structured metadata identifying the missing permission is a backend diagnostic failure,
not an actionable host setup request. The portal shows **Backend needs attention**, retains the denial and
offers no setup-retry button for that failure. It never asks the user to inspect execution logs or invent a
permission scope. Per-operation CLI diagnostics are retained privately with the run for investigation.
No alternate shell, Python wrapper, SDK, direct HTTP or backend route may be used to bypass the denied operation.
This handling does not repair the underlying CLI approval failure or prove Azure policy access.

### CLI runner reliability checks

Each assigned operation retains its full prompt and separate private CLI diagnostic directory with the run.
Child Python tools use UTF-8 output rather than the Windows legacy code page. Assigned-operation variables
are rebuilt for each child instead of inheriting an unrelated parent job.
Readiness verifies every CLI flag used by the runner, including output format and diagnostic logging.
This checks compatibility, not Copilot authentication, model access or enterprise permission rules.

The runner rejects Windows commands exceeding the executable's launch limit before starting a process.
It counts UTF-16 units, including quoting, and uses the lower limit for batch-file launchers.
Oversized prompts are preserved, not truncated or silently launched through another execution route.
Each CLI operation has a two-hour deadline. On timeout the owned local process tree is stopped without
automatic retry. Submitted Azure operations may continue remotely; inspect actual cloud state before resuming.
If local process termination cannot be confirmed, the writer lease and owned Stop control remain reserved.
Server restart and another writer are blocked until cleanup succeeds.

A reported stage or preparation failure stays a failure even when the CLI exits zero.
Its saved provider/build explanation is preserved rather than replaced by a generic missing-contract error.
Conversely, a zero exit or a prose success claim without the assigned report cannot complete a stage.
Existing artifact/build, regional-readiness and explicit consent gates still apply.

Local fault-injection tests cover stalled children, failed termination, no-report zero exits, reported
failures, nonzero exits, parent-environment leakage, Unicode output, incompatible flags and Windows limits.
These are deterministic runner tests, not proof of a successful real Copilot/Azure end-to-end flow.
Before release, separately prove Copilot login/model access and exact tool/path/URL permissions under the
intended user's enterprise policy; cancellation/recovery during real operations; and a complete deployed,
runtime-validated scenario followed by explicit suitability approval and validated hack composition.
Do not upgrade CLI versions, disable enterprise restrictions or broaden access as an automatic recovery.

Legacy pending business questions undergo the same review. On startup and when capacity becomes free, the server
resumes eligible waiting scenarios with retained local consent, no writer, and no other approval/setup blocker.
Paused, cancelled and failed attempts are not restarted automatically; Play resumes their saved review.
Review reports are revision/writer checked and audited. They preserve completed work, confirmed decisions and
authorization scopes. They cannot approve design, cloud/directory operations, suitability or composition.
Repeated identical technical questions are rejected using the recorded resolution.
For a technical question interrupting a cloud stage, an older deployment grant is retained as history,
not reused as recovery/retry consent. Preparation evidence must be refreshed under existing preparation scope,
then renewed exact-target consent is required before further cloud execution.

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
Local Copilot execution consent is highlighted in a teal-accented box in both intake and workspace views,
with a bolder label, larger checkbox and keyboard-focus outline. Styling never selects the checkbox automatically.

## Run

Complete the [prerequisite checklist and optional automated setup](../PREREQUISITES.md)
before starting scenario workers. Check-only installs nothing; installation requires explicit opt-in
and an idle, closed portal. New servers prefer the repository `.venv` and expose its Python on worker PATH.
After installing tools, reopen the terminal/VS Code before starting a new server; browser refresh cannot update PATH.

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
The **System** page shows the server PID, uptime, interpreter, workspace/state paths and active workers.
Each owned worker has its own confirmation and **Stop worker** action; no arbitrary PID termination is exposed.
Server **Stop** and **Restart** require confirmation and are rejected while any worker or saved writer lease is active,
including workers from another scenario. Wait for cancellation cleanup before trying again.
Restart shuts down the listener, reloads the Python backend and rotates local authentication;
the requesting tab waits for authenticated health and reloads. Other tabs must reopen through the launcher.
After **Stop**, the loaded page keeps recovery instructions visible, but cannot start an offline server.
Use `Start-ABCBuilder.cmd` or `python scripts\start_portal.py` locally to start/open it again.
No persistent supervisor or system service is installed.
Restart does not refresh inherited Windows environment variables; use a fresh terminal after PATH changes.
The **System** prerequisite checklist lists the end-to-end local toolchain with unchecked, ready and failed states.
Read-only checks require explicit local command authorization; they do not consume a scenario worker slot.
Server stop/restart also waits for active audits, so their child processes are not abandoned.
Green checks mean real version/dependency/render/engine probes passed, not just executable discovery.
Failures list affected stages and fixes, including **Docker installed: start the Linux engine**,
without auto-starting it.
Audit all catalog services or the selected saved scenario plus its current manifest.
Intake also previews the selected-service dependency union and can check it before launch.
Requirements/design are never blocked by future build-tool failures.
New/resumed scenario workers must record fresh owner-bound audits before affected implementation/validation stages.
Receipt scope follows manifest changes and expires after 15 minutes; UI diagnostics never fabricate worker receipts.
Build-mode/Functions-host selections on System are diagnostic only, not architecture changes or Azure authorization.
See [the service/stage matrix](../PREREQUISITES.md#service-aware-preflight-and-system-checklist).
When starting a replacement, readiness waits for the new process's connection record before authenticating,
so a previous server's per-start token is not sent to a newly bound listener.
A random per-launch identifier verifies ownership even when Windows virtual-environment Python hands off
to a different PID. A stale connection record never satisfies that identifier.

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
Local execution consent is stored once per scenario and reused for steps, resumptions, revisions and
separately approved composition, including after browser/server restarts. Intake authorization never transfers
to another selected project. The workspace shows the saved authorization and an idle-only revoke action.
Older projects without a recorded grant require one explicit workspace confirmation; no approval is inferred
from prior decisions, history, CLI flags or existing files. Revocation blocks new jobs until explicitly reauthorized.

Missing tooling/PATH and execution-host denials have a separate **Setup required** card, not an approval choice.
Workers report `blocked` with `blocker: {kind, action, verification}`; kind is `prerequisite` or `host-permission`.
**Verify setup & retry** starts a worker that first checks the recorded blocker using existing host permissions.
The blocker remains active during retry and after a failed/denied check.
Only a revision/owner-checked report for the blocked stage, with `status: "pending"`,
`setupVerification: {blockerId, passed: true}` and actual command/result evidence clears it.
The worker can then continue automatically. The retry does not install tools, change PATH, grant host permissions,
approve an Azure target or change suitability approval. Existing business/design/cloud decisions remain separate.
Older pending business decisions are not silently answered or reclassified.

This installation explicitly trusts the worker account's NuGet package and Playwright browser caches
through scoped `--add-dir` arguments, not unrestricted filesystem access. See
[worker cache policy](../PREREQUISITES.md#worker-package-and-browser-cache-access).
This is configuration trust as well as filesystem access; it grants neither shared installation nor
cloud permission. Packages within these locations share the approved scope. Custom cache locations
outside approved roots require review. Worker instructions require separate dependency probes and an
up-front inventory of design-specific browser/load tools; optional tools cannot block unrelated authoring.
`/api/catalog` exposes `workerPathPolicyVersion` and `workerCacheDirectories`.
The launcher refuses stale policy versions; a retry never clears a blocker without actual evidence.

Read-only Azure preparation progress uses `stage: deployment`, `operation: deployment-preparation`
and the exact authorized `scope`. The backend stores it in `deploymentPreparation`, not the actual
deployment stage; completing what-if cannot mark resources deployed or unlock live validation/review.
Current preparation consent is reused across attempts. Mismatched targets require a new scope review.
Repository/workflow defects use `blocker.kind: workflow-error` and are labeled portal errors,
not user tooling or permission deficiencies. Switching CLI/SDK transports does not change these gates.

The **Azure readiness and proposed targets** disclosure resolves current Azure CLI/azd sign-ins and
local scenario configuration only after read-only identity-discovery consent. It reuses saved targets,
existing azd environments, architecture region evidence and environment/resource-group conventions.
The card displays values and provenance, allows naming/region edits, and creates a prefilled
exact-scope preparation decision without authorizing it. A legacy business question asking for all
target IDs is superseded explicitly by this review; unrelated decisions are never overwritten.
Accepting preparation rechecks current identity; deployment consent remains separate after what-if/cost.
Private `deploymentContext` is passed to later workers, not included in the public catalog.

Local container shell/liveness verification uses
[`check_container_runtime.py`](../scripts/check_container_runtime.py), rather than generated multi-command
PowerShell. The helper validates an owned nonroot Linux x64 image, starts a read-only loopback-only container,
waits for health, checks the expected homepage text, captures logs and cleans up only its container.
It never pulls images, mounts host directories or accesses Azure. Startup/HTTP failures remain application
diagnostics, not permission requests. Earlier checks that assigned an HTTP response to the read-only `$HOME`
variable are corrected on retry without granting profile access. New setup reports reject obvious assignments
to `$HOME`, `$PID` or `$Host`; workers must diagnose CLI approval metadata before requesting broader scope.

This version changes the workflow protocol. Let active workers finish before restarting the portal,
then open its newly authenticated entry page. Existing jobs keep their original instructions until they end.
**Refresh status** only reads persisted state and never starts another agent.
The collapsed-by-default **Worker activity** card shows process liveness, attempt elapsed time,
last log-write age and up to 12 observed tool-action headings from the bounded output tail.
It refreshes with the existing run polling and preserves the user's expanded/collapsed choice.
After three minutes without output it reports a quiet worker, not an inferred hang.
Headings are observations, not completion evidence or internal reasoning; individual action times
are not available. Raw technical output remains separately expandable. URLs are omitted from activity
headings; this is not a general-purpose secret scrubber, and authenticated local logs remain private.
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
