# Local Hack Builder scenario studio

The intake portal launches real local Copilot CLI jobs, using the current user's
Copilot authentication. It is not a hosted agent service or an Azure deployment.
There are no browser-side Azure/GitHub credentials and no new runtime packages.

## Run

**Easiest on Windows:** double-click [`Start-HackBuilder.cmd`](../Start-HackBuilder.cmd)
in the repository root. It starts or reuses the local server and opens the authenticated browser page.
You can create a Windows shortcut to this file for desktop access. Python must be on PATH.

**In VS Code:** select **Terminal > Run Task > Hack Builder: Open Portal**.
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
Portal-launched CLI jobs inherit `HACKBUILDER_PORTAL_JOB=1` and skip startup.
This prevents recursive portal/browser launches. It does not change Azure
deployment or scenario-approval gates.

Open the **private URL printed by the server**, including its token fragment.
The browser removes the fragment after putting the token in session storage.
Do not share the URL. The server binds only to `127.0.0.1`; API requests require
the random per-start token and reject foreign origins/hosts.
Use `--port 8766` if the default port is busy. Stop with Ctrl+C.

After updating backend code, stop the existing portal server and run the helper again, then reload
the page. A stale backend is detected by the dashboard protocol version; refreshing alone does not
reload Python modules. Finish/stop active workers before a planned server restart.

No server is installed as a system service. Automatic startup leaves the local
process available after the chat turn. Connection details (including the private
token) are saved in ignored `.hackbuilder-portal/server.json`; never publish it.
Background diagnostics are in `.hackbuilder-portal/server.log`, without the launch
URL. For a foreground server, use the original command and Ctrl+C to stop.
To stop a background server on Windows, inspect the PID in `server.json` and
verify that it belongs to this workspace's `portal_server.py`, then use
`Stop-Process -Id <PID>`. Never terminate by process name. Re-running the helper
reuses a responsive instance; it does not kill another process occupying the port.
Use a trusted personal/local machine: this version is not designed for multiple
users, remote hosting or untrusted local accounts.

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

For older jobs lacking stage telemetry, a valid approved snapshot labels constituent reference
artifacts **reviewed**, not pending or newly tested. Runtime and local test outcomes are not invented.

1. Describe a scenario or select Azure building blocks. Choose one industry,
   optional Well-Architected priorities and technical domains, and a project slug.
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
Only one job runs per portal instance. A durable project writer lease also rejects competing
workers across portal instances; every state update checks its expected revision under a kernel lock.
This coordinates cooperating tools, not arbitrary filesystem editors. VS Code work must check the
same project state and must not edit a scenario with an active writer. Never manually clear a live lease.
Path access additionally allows only the adjacent `azd-projects` workspace
directory; it does not enable unrestricted filesystem access.

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

## Local data and recovery

The scenario selector also discovers valid project-slug directories/junctions under
`generated-scenarios`, even without portal run history. These appear as **local project**
read-only previews with available reference documents and package materials. Missing stage telemetry
is not invented; discovery does not create state, approve, run jobs or deploy resources.
Portal-managed scenarios take precedence over duplicate disk entries. Refresh discovers new folders.

Requests, input prompts, agent output and run metadata persist under the ignored
`.hackbuilder-portal/` directory. They may contain local environment information:
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

Versioned project records live at `.hackbuilder-portal/projects/<projectSlug>.json`, separate
from scenario suitability evidence and individual run logs. Existing legacy runs have no inferred
progress; resuming creates a project record and asks the worker to reconcile actual evidence.
Launching a new brief with an existing slug is rejected; use its saved scenario instead.

Project status and process status are distinct. An exit code of zero without stage evidence means
`needs_attention`, not a successful scenario. Local validation can be complete while deployment and
live acceptance remain pending. Pending decisions survive server restart and are shown until answered.
The dashboard groups attempts by scenario and follows the latest attempt.

The backend supplies `HACKBUILDER_PROJECT_STATE`, `HACKBUILDER_PROJECT` and `HACKBUILDER_RUN_ID`.
Workers read the latest revision and submit one JSON event file per transition:

```powershell
python scripts\portal_workflow.py read
python scripts\portal_workflow.py report --revision 3 --event stage-event.json
```

Optional VS Code engineering work must claim the same writer lease before editing an idle project.
Use a distinct owner identifier, the actual project directory and current revision; read/report use
the same explicit arguments when the backend environment variables are absent:

```powershell
python scripts\portal_workflow.py read --directory .hackbuilder-portal\projects --project finance-agent
python scripts\portal_workflow.py claim --directory .hackbuilder-portal\projects `
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
