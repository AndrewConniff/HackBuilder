# FBCBuilder DEV Guide

Technical handoff for engineers maintaining **FBC Builder**.
Implementation baseline: the working checkout reviewed on **October 29, 2026**.
This describes shipped code, not an aspirational service architecture.
Local state, generated deployments and historical screenshots are not included as evidence of a current live run.

Start with the [user HOWTO](FBC-Builder-HOWTO.md) for installation and the complete browser experience.
Use [AGENTS.md](AGENTS.md) for repository conventions and the [workflow contract][workflow] for phase rules.
If an implementation and a safety/approval contract disagree, fix the implementation;
do not reinterpret a display state as permission.

## Contents

- [1. Product and execution model](#1-product-and-execution-model)
- [2. Repository map and ownership](#2-repository-map-and-ownership)
- [3. Developer workstation and local operation](#3-developer-workstation-and-local-operation)
- [4. Agents, skills and instruction discovery](#4-agents-skills-and-instruction-discovery)
- [5. End-to-end request lifecycle](#5-end-to-end-request-lifecycle)
- [6. Portal backend and HTTP contracts](#6-portal-backend-and-http-contracts)
- [7. Frontend architecture and state](#7-frontend-architecture-and-state)
- [8. Persisted state and data contracts](#8-persisted-state-and-data-contracts)
- [9. Native chat discovery and editor bridge](#9-native-chat-discovery-and-editor-bridge)
- [10. Progress, approval and package integrity](#10-progress-approval-and-package-integrity)
- [11. Catalog matching and isolated adaptation](#11-catalog-matching-and-isolated-adaptation)
- [12. Diagnostics, setup and Azure context](#12-diagnostics-setup-and-azure-context)
- [13. Generated reference and authoring outputs](#13-generated-reference-and-authoring-outputs)
- [14. Security and operational boundaries](#14-security-and-operational-boundaries)
- [15. Testing and acceptance strategy](#15-testing-and-acceptance-strategy)
- [16. Change recipes and extension points](#16-change-recipes-and-extension-points)
- [17. Troubleshooting and handoff runbook](#17-troubleshooting-and-handoff-runbook)
- [18. Documentation consolidation and compatibility](#18-documentation-consolidation-and-compatibility)

## 1. Product and execution model

FBC Builder is a repository of Copilot customizations plus a small local Python/JavaScript portal.
It is not a hosted orchestration service, a learner progress application or an autonomous job scheduler.
There is no production portal database, web build pipeline or cloud deployment for the portal itself.

The product has three deliberately separate phases:

| Phase | Owner | Deliverable | Boundary |
| --- | --- | --- | --- |
| A: reference | `az-01-conductor` | Deployed, tested Foundry business scenario | Explicit suitability approval |
| B: composition | `HackCreator Agent` | Minimum starter and learner/private coach packages | Local validation receipt |
| C: optional event | Scenario orchestrator | Coach plus 1-20 isolated team deployments | Separate rollout request |

Publication is another explicit user choice, not a phase-completion side effect.
Deployment consent does not approve suitability. Suitability does not authorize an event or publication.
The agents implement their work directly through skills; neither delegates or launches nested orchestrators.
The portal opens real VS Code conversations and displays agent-authored reports.
It never calls a model endpoint itself.

```text
Browser: portal\visualizer.html + visualizer.js + visualizer.css
  |
  | loopback HTTP, explicit UI actions and read-only refresh
  v
Python: scripts\portal_visualizer.py / Studio
  |-- local briefs, reports, catalog, file previews and audience ZIP exports
  |-- explicit shared prerequisite and existing-identity diagnostics
  |-- initial handoff: code chat --mode <canonical-agent>
  `-- existing-chat operations: vscode URI -> local Scenario Chat extension
                                            |
                                            v
                                Existing native VS Code chat
                                  |-- agent + skills + native tools
                                  |-- writes generated reference/packages
                                  |-- writes portal_status.py reports
                                  `-- authorized Azure/Foundry runtime work
```

The generated business application may itself use one or several Foundry agents.
That runtime architecture is independent of the two Copilot implementation contexts.
Selecting an agentic pattern does not request additional Copilot build agents.

## 2. Repository map and ownership

The repository is Windows-first for the documented end-to-end local experience.
Keep executable paths in PowerShell examples Windows-compatible.
Some helpers have cross-platform branches; that alone does not establish full remote-host support.

```text
HackBuilder\
  FBC-Builder-HOWTO.md              Primary user manual
  FBCBuilder-DEV-Guide.md            This technical handoff
  AGENTS.md                        Repository conventions and validation
  AGENTSEXPLAINED.md                Customization inventory and dated findings
  PREREQUISITES.md                  Detailed setup and diagnostic reference
  Start-FBCBuilder.cmd              Product launcher
  requirements.txt                 Shared Python dependency minimums
  NuGet.Config                     Approved package source
  microsoft_industry_verticals.csv  Intake industries
  fictitious_company_names.csv      Synthetic company identities
  fictitious_people_names.csv       Synthetic people identities
  .github\
    agents\                        Exactly two canonical custom agents
    skills\                        Canonical procedures, references and templates
    instructions\                  File-scoped standards
    copilot-instructions.md         Repository Copilot defaults
    ISSUE_TEMPLATE\                GitHub issue templates
    PULL_REQUEST_TEMPLATE\         GitHub contribution templates
  .agents\skills\                   Manual launchers and scenario inputs
  .vscode\                         Shared editor configuration and portal task
  portal\                          Static local UI and intake catalog
  scripts\                         Local runtime, guards and maintenance CLIs
    tests\                         Python and frontend regression tests
  tools\vscode-chat-bridge\         Native editor extension and tests
  system-tools\                    Opt-in native installer and version catalog
  scenarios\                       Portable catalog/index/profile metadata
  docs\images\fbc-builder\          Historical walkthrough screenshots
  generated-scenarios\              Ignored logical scenario workspaces
  .fbcbuilder-portal\               Ignored local portal/session state
```

Key source modules:

| Source | Responsibility |
| --- | --- |
| [start_portal.py][startup] | Start/reuse, health/version matching, browser opening |
| [portal_visualizer.py][backend] | `Studio` operations, HTTP routing, file/export policies |
| [portal_status.py][status] | Atomic display reports and bounded intermediate events |
| [scenario_chat.py][chat] | Associate scenario/phase with verified native session identity |
| [hack_workflow.py][guard] | Reference validation, review fingerprints, approval, package receipts |
| [scenario_catalog.py][catalog] | Manifest validation, inference, discovery, portable catalog index |
| [scenario_match.py][matching] | Technical sidecars, freshness, deterministic matching, curation |
| [scenario_adapt.py][adapt] | Source snapshots, late selection, allowlisted copy, reconciliation |
| [check_prerequisites.py][checker] | Tool/package/probe observations and process environment |
| [prerequisite_profiles.py][profiles] | Shared System profile and conditional stage requirements |
| [check_container_runtime.py][containers] | Docker installation versus responsive Linux engine |
| [azure_context.py][azure-context] | Existing CLI identity, local targets and regional evidence helpers |
| [New-AzdScenarioWorkspace.ps1][workspace-helper] | Adjacent physical workspace and repository junction |

The [artifact template library][artifacts] lives under the skills directory but has no `SKILL.md`.
It is not a discoverable skill.
Historical procedural agent bodies in skill references are research/history, not executable agent definitions.
The supplied PDF is background for scenario-pattern guidance, not a runtime dependency.

New scenario work normally lives physically in the adjacent `azd-projects` directory.
For a clone at `C:\work\HackBuilder`, the logical path can be
`C:\work\HackBuilder\generated-scenarios\example` and the physical path `C:\work\azd-projects\example`.
Existing legacy directories stay in place; do not migrate them simply to match this example.
Use the [workspace helper][workspace-helper] for new work, not to relocate populated scenarios.

## 3. Developer workstation and local operation

Follow the [HOWTO setup sequence][howto-setup] before generating or deploying references.
The portal uses the Python standard library, but full reference work requires the wider toolchain.
The shared baseline includes Python 3.10+, repository `.venv`, Git, PowerShell 7+, .NET 10 SDK,
Graphviz, Azure CLI, azd, Bicep, a running Linux Docker engine, Functions Core Tools and k6.
The complete native setup also includes Node.js 22+, GitHub CLI and VS Code.

There is no root npm application and no portal `npm install`, `npm start` or bundle build.
The bridge has its own [package manifest][bridge-package] and `npm test` command.
Python dependencies are minimum-version requirements, not a fully reproducible transitive lock.
The native [tool catalog][tool-catalog] separately locks installer versions, URLs and SHA256 hashes.

Useful read-only checks from the repository root:

```powershell
.\system-tools\Install-SystemTools.ps1 -Mode Check
.\.venv\Scripts\python.exe -B scripts\check_prerequisites.py --system --json --contributor
az account show --output table
azd auth login --check-status --no-prompt
```

Use the documented installer only as an explicit opt-in operation.
Do not install packages to validate a prose-only change.
Do not run an Azure diagnostic/deployment merely because unit tests are being maintained.
The Python source instructions include broader historical conventions;
the actual shipped local test runner is `unittest`, not a required new pytest harness.

For normal operation:

```powershell
.\Start-FBCBuilder.cmd
```

For foreground backend development, after confirming the normal server is not using the selected port:

```powershell
python scripts\portal_visualizer.py --port 8766 --open-browser
```

The backend still writes the active state's `server.json`; do not run competing runtimes against shared state.
A different port avoids a socket collision, not scenario/state concurrency.
For tests, construct `Studio` or `make_server` with a temporary root as the shipped tests do.
Do not point mutation tests at real local scenario state.

The shared VS Code task is **FBC Builder: Open Portal** in [tasks.json](.vscode/tasks.json).
The [workspace settings](.vscode/settings.json) enable both skill locations and canonical agent discovery.
Settings may contain host-specific or historical tool approvals:
their presence does not create an executable npm task or authorize cloud work.
Do not copy another developer's broad tool-approval preferences as a setup requirement.

### Startup lifecycle

[start_portal.py][startup] reads the active `server.json`, then checks:

1. A valid recorded port and loopback `/api/health`.
1. Exact workspace identity in the health response.
1. Catalog workflow, backend engine, System controls, prerequisites and PATH-policy versions.
1. During new startup, the expected random startup identity rather than merely a responsive port.

The reviewed backend publishes engine **23**, workflow **5**, System controls **1**,
prerequisites surface **1**, and worker PATH policy **2**.
These are compatibility markers, not deployment or approval versions.
The shared prerequisite profile separately uses version **2**.

A matching server is reused without replacing its interpreter/environment.
For a new server, the helper prefers the repository virtual environment, sets the process environment,
redirects output to `server.log`, and waits up to ten seconds for identified readiness.
On Windows it creates a dedicated runtime console and process group.
Failure is explicit; an incompatible live server is not silently replaced.
`--hook` returns hook JSON after browser startup.
Legacy portal-job environment flags suppress recursive startup for compatibility.

## 4. Agents, skills and instruction discovery

Canonical agents:

| Definition | Stable name | Scope |
| --- | --- | --- |
| [az-01-conductor.agent.md][conductor] | `az-01-conductor` | Reference and separately requested rollout |
| [az-09-hackcreator.agent.md][creator] | `HackCreator Agent` | Approved-reference authoring only |

Both use `agents: []`, expose read/search/edit/execute/web/todo tools, and inherit the host model preference.
The numeric filename of HackCreator is not a third lifecycle stage or an agent registry ID.
The conductor's inline `sessionStart` hook opens the portal; there is no separate shipped hooks directory.
Hosts that do not execute scoped hooks use the documented first-interactive-action fallback.
Portal handoffs skip redundant startup because the browser is already open.

Canonical skills live in [`.github/skills`](.github/skills).
A discoverable skill has `<folder>\SKILL.md` and discovery frontmatter.
Its description drives matching; references/assets are loaded as needed.
A skill file existing in Git is not proof that a session actually invoked it.
Use dated execution evidence when documenting observed behavior.

| Skill | Owned procedure |
| --- | --- |
| `hack-builder-workflow` | Scope, sequencing, evidence and approvals |
| `az-consolidated` | Shared defaults, AVM patterns, identities and templates |
| `az-scenario-requirements` | Story, adaptive scoping, business units, agentic-pattern selection |
| `az-scenario-adapt` | Source-based preparation and change reconciliation |
| `az-scenario-architecture` | Design, identity/network paths, WAF trade-offs and cost |
| `az-azure-diagrams` | Architecture and runtime diagrams |
| `az-scenario-bicep` | AVM-first Bicep, policy/RBAC and azd wiring |
| `az-webapp-development` | Real .NET application, fixtures and tests |
| `az-azure-validate` | Authorized readiness and runtime acceptance |
| `az-azure-deploy` | Authorized provisioning, deployment and recovery |
| `az-scenario-demonstration` | Walkthrough and failure/recovery evidence |
| `azure-foundry-hack-builder` | Post-approval hack structure and composition procedure |
| `skillable-lod-authoring` | Learner pages, private Finale, templates and validator |
| `az-multi-team-deployment` | Explicit event manifest and isolated rollout |
| `az-scenario-contribution` | Explicit GitHub publication/contribution |

The seven entries under [`.agents/skills`](.agents/skills) are manual compatibility launchers or scenario inputs.
They are not parallel agents or independent procedural authorities.
For example, `/run-conductor` enters the canonical workflow.
The `az-webapp-development` companion `app-creation-SKILL.md` is explicitly read, not another discoverable skill.

Instruction ownership:

- [AGENTS.md](AGENTS.md): repository conventions and validation.
- [Copilot defaults](.github/copilot-instructions.md): entry-point and workflow guidance.
- [File-scoped instructions](.github/instructions): Markdown, Python, PowerShell, Bicep, .NET and generated artifacts.
- [Foundry instructions][foundry]: current resources, projects, region/model evidence and acceptance.
- [Research instructions][research]: bounded evidence-first implementation and reuse.
- [Hack-authoring instructions][authoring]: learner/coach boundaries and post-approval content.
- [Customization inventory](AGENTSEXPLAINED.md): full discovery map and dated execution findings.

When modifying customizations, preserve stable names and phase boundaries.
Do not copy implementation rules into compatibility launchers or activate historical agent bodies.
Reload customizations/start a new chat when testing discovery changes.
Do not assume host-specific settings prove a skill loaded.

## 5. End-to-end request lifecycle

### Intake and scoping

1. The browser loads catalog data and renders validated choices.
1. `POST /api/scenarios` validates the request and saves immutable original intake in local state.
1. `POST /api/handoff` prepares the phase handoff and opens the repository with `code`.
1. A second `code chat --mode` invocation attaches the handoff and launches the chosen canonical context.
1. A unique trace and launch receipt establish later session association, not proof of agent execution.
1. The agent reads the saved request and existing evidence and reports through [portal_status.py][status].

Intake mode `scope` prohibits workspace creation, architecture, tool audits, Azure discovery and implementation.
The requirements skill asks only material prompt-specific questions and records actual answers in `scoping.md`.
Normal build mode uses the same bounded gap review without forcing an interview when the brief is sufficient.
Adaptation intake is forced into scoping regardless of which submit button the user chose.

**Confirm brief** and **Save changes** post a fingerprint-bound scoping response.
Confirmation dispatches a fixed normal-workflow continuation to the existing native chat.
Changes dispatch a scoping-only revision.
Neither writes cloud authorization or suitability approval.
Changing brief text requires a fresh confirmation.
Late source selection adds an explicit reviewed-selection step before confirmation becomes available again.

### Reference implementation and deployment

The conductor creates requirements, architecture, diagrams, Bicep, app, fixtures and local tests.
It reuses valid existing observations and actual same-scenario authorization.
It prepares local repairs and cost/security proposals without a preliminary cloud-permission questionnaire.
Unauthorized Azure/Entra reads/writes remain pending.

In the existing VS Code chat it presents one consolidated architecture/deployment review:
exact identity and targets, operations, authorized what-if/readiness, costs, access paths and limitations.
Only missing authority or materially new scope needs a new decision.
After authorization it deploys and repairs in-scope issues, proves runtime behavior and operator access,
then prepares a review snapshot and demonstration.
It stops for explicit suitability approval.

### Composition, exports and optional rollout

HackCreator checks approval before either planning or packaging.
It derives the minimum starter and sanitized coach solution from the approved reference.
It authors five outcome-led challenges with 150 build minutes in a three-hour event.
Full architecture, detailed answers and Finale coaching remain private.

Successful local package checks are recorded, then the workflow helper issues a bound validation receipt.
Only current validation with no reported build in progress enables portal exports.
Creating folders, reporting a completed stage or opening File Explorer does not validate packages.
Coach/team deployment and publication remain separate explicit requests.

### Existing scenarios and authorization continuity

Resume saved work, not a newly invented replacement deployment.
The portal reads answered-decision/authorization history from both current and legacy project records
and attaches provenance to same-scenario handoffs.
An expired worker receipt, migration or newer agent-authored summary does not revoke an actual user grant.
Only actual user restrictions and exact target/operation scope govern that continuity.
No authorization, approval, deployment state or runtime success transfers to an adapted target.
A recorded legacy writer blocks conflicting handoff/continuation/message operations.
There is no portal process-termination or old-worker execution endpoint.

## 6. Portal backend and HTTP contracts

[portal_visualizer.py][backend] uses `ThreadingHTTPServer`, `BaseHTTPRequestHandler` and one `Studio` instance.
`Studio` handles domain operations; `Handler` maps HTTP, validates transport and serializes responses.
`RLock` serializes selected handoff/continuation/message operations.
A separate nonblocking System-check lock rejects overlapping prerequisite/identity checks.
This is process-local locking, not a multi-process queue or distributed concurrency protocol.

### Read endpoints

| GET route | Parameters | Result |
| --- | --- | --- |
| `/api/health` | None | `status` and exact workspace |
| `/api/catalog` | None | Catalog choices plus compatibility versions |
| `/api/reuse-sources` | None | Local/portable discovered source entries and errors |
| `/api/reuse-source` | `project` | Inspected source snapshot and reusable inventory |
| `/api/prerequisites/plan` | None | Fixed profile, planned checks, saved observations |
| `/api/scenarios` | None | Computed scenario summaries, stages, actions and approvals |
| `/api/files` | `project` | Allowlisted reference/learner/coach file inventory |
| `/api/review` | `project` | Safe current deployment review and stale-display fingerprint |
| `/api/conversation` | `project`, `phase` | Last 100 entries and send availability |
| `/api/file` | `project`, `path` | Listed-file preview, subject to size/path rules |
| `/api/export` | `project`, `audience` | Current validated learner or coach ZIP |

Static routes are `/`, `/visualizer.js`, `/visualizer.css` and `/markdown.js`.
No arbitrary static-file root is exposed.
Some GET operations resolve/save chat association metadata while calculating the view.
"Read-only polling" means no message dispatch, agent execution or deployment;
it is not a promise that every implementation path is filesystem-write-free.

### Explicit action endpoints

All POST bodies must be JSON objects of 1-32,768 bytes.

| POST route | Primary fields | Effect |
| --- | --- | --- |
| `/api/scenarios` | Intake fields | Save a new original brief; returns 201 |
| `/api/prerequisites/plan` | Empty/System-compatible object | Read fixed plan; reject scenario overrides |
| `/api/prerequisites/check` | `toolConsent: true` | Run local shared checks and persist observations |
| `/api/system/identity` | `toolConsent: true` | Verify existing CLI identities and persist metadata |
| `/api/handoff` | `projectSlug`, `phase` | Open/reopen canonical context |
| `/api/scoping-response` | Slug, fingerprint, decision, changes | Persist brief response and explicit continuation |
| `/api/reuse-recommendations` | Draft intake, or bound brief | Local deterministic catalog comparison |
| `/api/reuse-selection` | Slug, fingerprint, `reuseSource` | Save explicit late choice and request revision |
| `/api/chat-open` | Slug, phase | Reopen existing native conversation |
| `/api/chat-link` | Slug, phase | Compatibility alias for reopening, not arbitrary link registration |
| `/api/conversation/send` | Slug, phase, text, request ID | Relay one explicit message to existing chat |
| `/api/open-package-folder` | Slug | Open verified packages directory in Windows Explorer |

Handoff phases are `scenario`, `scoping`, `composition` and `deployment-review`.
Conversation phases are only `scenario` and `composition`; scoping/review belong to the scenario conversation.
Composition handoff checks approval in the backend.
Deployment-review handoff additionally requires the displayed `reviewFingerprint`.
`newChat` is an explicit backend option, not an automatic recovery fallback.
Normal saved-session handoffs reopen the verified existing conversation.

Known input/path errors return JSON `error` responses:
400 for validation, 403 for origin/host policy, 404 for missing routes/files,
504 for a handoff subprocess timeout and logged 500 errors for filesystem failures.
Uncertain message delivery may instead return a persisted `unknown` record;
the frontend must inspect status, not treat HTTP 200 as successful agent execution.

### Transport protection

The server binds to `127.0.0.1` only.
It requires the exact `Host` value `127.0.0.1:<port>`,
an absent or matching loopback `Origin`, and acceptable Fetch Metadata.
Use the numeric loopback URL, not an arbitrary hostname alias.
Responses include no-store, nosniff, no-referrer and a restrictive same-origin CSP.
There is no user login/session authorization layer for remote hosting.
These checks do not isolate the portal from other trusted local processes/users with filesystem access.
Never expose it through a public interface, tunnel or reverse proxy as a supported deployment.

## 7. Frontend architecture and state

The UI is plain JavaScript with native DOM APIs, not a SPA framework.
[visualizer.html][html] owns semantic layout and controls,
[visualizer.js][frontend] owns state/rendering/actions,
[visualizer.css][css] owns responsive/theme styling,
and [markdown.js][markdown] provides the shared inert Markdown renderer.

The four hash views are `create`, `build`, `hack` and `system`.
Navigation retains the draft and selection without submitting anything.
Back/forward uses hash navigation.
System is workspace-wide; only Build/Create hack expose the working-scenario selector.
At narrow widths navigation becomes compact; the conversation pane stacks below content.
At 1,200 pixels and above the conversation pane is a sticky right-hand column.

`hackEligible` requires current approval and all nine reference stages completed.
The compatibility path accepts a current package receipt when granular reports are missing,
but only if reference stages are completed/available/unreported, not explicitly running/failed/pending.
Eligible scenarios appear in Create hack rather than duplicated on both boards.
Eligibility is a frontend presentation rule; backend approval/export guards must remain independent.
Never rely only on a hidden button to enforce a security or phase boundary.

Frontend state includes:

- Selected slug, scenario list, view and selection generations.
- Busy/polling guards and file/review signatures.
- Scoping draft state and current review context.
- Matching timers, input fingerprints and asynchronous result generations.
- Per-scenario/per-phase conversation caches and in-page unsent drafts.

The four-second refresh reads current scenario/report data; it does not dispatch work.
Generation checks prevent late results from replacing another scenario's preview, source or conversation.
Preserve these checks when adding asynchronous UI.
An input edit invalidates pending recommendation results.
Suggestions start after at least 35 characters/six words and a 900 ms pause, or prompt blur.
These thresholds reduce noise; they are not semantic acceptance criteria for a scenario brief.

**Your scenario brief** renders expanded in a paper-style box only when notes exist.
Confirmation/revision display cues are bound to the matching response fingerprint.
They must not hide newer failed/running/completed implementation reports.
Milestone icons retain text labels; reduced-motion behavior disables spinner animation.

Appearance supports System/Light/Dark.
Explicit choices use `fbcbuilder-theme`; System removes the override.
The first visit after migration uses the system theme until a new explicit preference is selected.
Storage failure produces a notice while leaving the current tab usable.
Conversation drafts are not persisted across browser reloads.

## 8. Persisted state and data contracts

There are three separate storage domains; do not merge them:

| Domain | Location | Intended contents |
| --- | --- | --- |
| Source-controlled metadata | `portal`, `scenarios`, catalogs | Portable choices, manifests/profiles/indexes |
| Local portal state | `.fbcbuilder-portal` | Briefs, dispatch records, reports, session associations |
| Generated reference | `generated-scenarios\<slug>` | App/IaC/docs, technical evidence, approval/packages |

[state_directory][status] selects `.hackbuilder-portal` only when it exists and the current directory does not.
Otherwise it selects `.fbcbuilder-portal`.
History continuity may inspect both. The FBC migration renames the current portal directory in place,
without merging independent histories or changing native session IDs.
Original authorization/scoping JSON, generated references and approval fingerprints remain unchanged.

Workspace-local state includes:

```text
.fbcbuilder-portal\
  server.json
  server.log
  system-prerequisites.json
  system-identity.json
  scenarios\<slug>\
    request.json
    scoping.md
    scoping-response.json
    reuse-candidates.json
    reuse-selection.json
    status.json
    handoff.json
    <phase>-handoff.txt
    <phase>-handoff.json
    scenario-chat-started.json
    composition-chat-started.json
    chat-sessions.json
    chat-open\<request-id>.json
    chat-continuations\<ledger-key>.json
    messages\scenario\<request-id>.json
    messages\composition\<request-id>.json
```

Not every scenario creates every file.
Bridge locks/receipts are transient where the implementation cleans them up.
Historical `projects\<slug>.json` records can also exist; they are not a current scheduler queue.

### Original intake

`request.json` has schema version 1 and contains:

| Field | Contract |
| --- | --- |
| `projectSlug` | At most 40 lowercase letters/digits/single hyphens; no leading/trailing/double hyphen |
| `prompt` | Trimmed, nonempty, 1-6,000 characters |
| `industry` | Exact repository CSV industry label |
| `intakeMode` | `build` or `scope` |
| `businessUnits` | Nonempty unique known IDs; Generic exclusive |
| `agenticPattern` | Valid catalog ID; default `ai-decides` |
| `services` | Unique known IDs; Foundry inserted as baseline |
| `pillars`, `domains` | Unique known catalog IDs |
| `reuseSource` | Optional validated source snapshot; forces scoping |

Creation rejects an existing brief or existing target workspace.
Refined scope belongs in scoping notes/responses, not destructive edits to original intake.
Business-unit IDs are `generic`, `executives`, `it`, `operations`, `communications`,
`executive-assistant`, `legal`, `hr`, `business-manager`, `finance`, `sales` and `marketing`.
Generic means industry-typical workflow without unit targeting, not every specific unit selected.

### Scoping and messages

Scoping text is limited to 64 KiB.
The fingerprint hashes decoded UTF-8 text with BOM removed and line endings normalized by text reading.
The extension implements matching normalization before hashing.
A response records decision, requested changes, timestamp, fingerprint and continuation request/status.
Requested changes accept up to 8,000 characters.
Confirmation requires the current requirements-stage input wait and exact brief fingerprint.
Late reuse must be reviewed against that brief too.

Message records include schema version, slug, phase, request ID, exact saved native resource,
text, creation timestamp and delivery status/error.
Request IDs are 32 lowercase hexadecimal characters; text is nonempty and at most 8,000 characters.
The request ID cannot be reused for different text.
Statuses distinguish dispatching, dispatched, failed and unknown.
These are delivery facts, not model completion states.

### Progress reports

`status.json` schema version 1 contains slug, latest stage/status/summary/time,
a latest-per-stage `steps` map and a bounded `events` list.
Each new report appends an ID-bearing event; only the last 100 events remain.
Older records without events are seeded from their existing steps rather than invented activity.
Summaries must contain 1-1,200 characters and no secrets.
Writes use a unique temporary file followed by replacement.
Atomic replacement prevents partial JSON reads; it does not make concurrent read/modify/write agents safe.
Maintain one active writer per scenario.

## 9. Native chat discovery and editor bridge

Initial handoff uses the installed `code chat` custom-agent launcher.
Existing-session navigation, brief continuation and messages use the local
[Scenario Chat extension][bridge].
Its version is **0.4.0**, installed identity `fbcbuilder.scenario-chat`,
minimum editor `^1.143.0`, and activation event `onUri`.
Untrusted workspaces are unsupported.

### Session association

[scenario_chat.py][chat] resolves **editor session ID**, **SDK session ID** and exact workspace separately.
It reads native editor `agentSessionData` SQLite databases in read-only mode for identity metadata.
On Windows the default catalog is under `%APPDATA%\Code\agentSessionData`.
The helper also examines local SDK `events.jsonl` evidence under the user's Copilot session-state directory
to match original handoff traces and successful progress-report calls.
It does not stream those transcripts into the browser.
Do not describe identity discovery as never reading local event history.

New handoffs include an exact FBC trace marker; historical trace labels remain recognized.
Without a trace, verified handoff/progress or reference-attachment/progress evidence supports older sessions.
Candidates must match workspace and phase.
Successful latest progress can disambiguate older continuations; tied/ambiguous matches fail explicitly.
Titles are not identity.

The saved native link is:

```text
agent-host-session://ahp-session/<editorSessionId>?connectionAuthority=local
```

It does not contain the SDK session ID as the editor resource.
Older automatically discovered `copilot` links can be repaired only after the same identity is verified.
Manually linked sessions are not silently replaced.
Missing catalogs/history/profile matches produce errors, never a new replacement conversation.
The command **FBC Builder: Link Existing Chat to Scenario** is an explicit repair path.

### URI and dispatch contracts

The portal sends a URI under `vscode://fbcbuilder.scenario-chat/` with action
`open`, `ping`, `continue` or `message`, plus root, slug, phase and request ID.
Message bodies live in bounded local JSON files, not URI query text.
The extension validates trusted workspace, safe paths, request/phase/session identity and current delivery state.

For a continuation/message, it:

1. Acquires the per-request dispatch lock/ledger.
1. Validates the exact saved response or message resource.
1. Opens the linked session as an editor via `_workbench.open` with `sideBySide`.
1. Waits for the native chat editor to become active and verifies the intended session.
1. Calls `workbench.action.chat.submit` with `inputValue` and preserved input options.
1. Persists dispatched/failed/unknown and writes a local acknowledgement.

The sidebar `chat.open` command is not an equivalent targeted-submit API.
`vscode.open` with text-document options can incorrectly open a session URI as a text file.
These are sensitive editor integration contracts; mock tests alone cannot prove a new VS Code build supports them.

The portal waits up to 60 seconds for an acknowledgement and removes the consumed acknowledgement file.
The durable dispatch ledger remains under `chat-continuations`.
Message ledger keys include phase to avoid collision with scenario brief continuations.
An error before attempted submit can be safely marked failed.
An exception after submit may have delivered the prompt and must remain unknown.
Never replay from a timer, reconnect, poll or missing acknowledgement.
A receipt proves only editor-command dispatch, not AI execution.

The backend's feature-version guards require at least 0.3.0 for messaging and 0.2.3 for brief continuation.
This checkout additionally uses the new extension identity/routes from 0.4.0, so install the current 0.4.0 build;
an older publisher's extension cannot handle those routes even if its feature version passes a numeric threshold.
Restart the extension host after installation: installed version and activated version can differ.
Packaging and manual setup are documented in the [bridge README][bridge].

## 10. Progress, approval and package integrity

### Display reports are not workflow authority

The ordered stages are:

```text
requirements -> architecture -> diagrams -> bicep -> application -> local-validation
-> deployment -> live-validation -> review
hack-content -> hack-starter -> hack-coach -> hack-validation
```

This is display order, not an executable dependency scheduler.
The report helper accepts running, completed, waiting_for_user, blocked, failed and handed_off.
Agents normally use the first five for actual phase work.

```powershell
python scripts\portal_status.py example --stage architecture --status running `
    --summary "Comparing identity and private management paths"
```

Per-stage artifacts without a report are **available**, never automatically completed.
Outstanding failed/blocked/waiting steps can override an unrelated latest completion.
Review completion derives from current approval, and package validation from current receipts.
Do not mark all stages complete just to move a card between boards.

### Reference review guard

[hack_workflow.py][guard] validates required artifacts and real app source before a review snapshot.
Required reference files include region evidence, requirements, architecture, both diagrams,
azd wiring, main Bicep, deployment summary, runtime evidence and demo guide.

Normal `scenario-validation.json` must have:

- `status: "passed"` and runtime-validation evidence type, explicit or default.
- Boolean-true deployment, modelInference, agentInvocation, applicationChat and negativeCase checks.
- Every additional supplied check true, not merely the required subset.
- A deployed HTTPS application URL.
- A timezone-aware `checkedAtUtc`.

The helper checks the evidence shape and integrity; it does not perform those runtime tests.
Agents must actually run and retain the evidence.
Workflow requirements such as grounding/tool behavior and full deployment-user access remain mandatory
even where the helper's minimum boolean set cannot independently verify them.

The reference fingerprint hashes sorted relative paths and file content digests.
It excludes package/build/cache directories and specific root metadata/authoring files.
It excludes environment files by name.
See the exact exclusion constants in [hack_workflow.py][guard] before changing fingerprint coverage.
A fingerprint is a change guard, not a credential scrubber, signature or tamper-proof approval service.

After actual validation, the conductor uses `snapshot`.
Only after the user's actual affirmative suitability response does it use `approve --message`.
`check-approval` revalidates the reference, matching snapshot, phase and recorded decision.
Material covered-file changes require revalidation, snapshot and renewed user review.
Do not automate affirmative approval text or manufacture a decision in a test against real state.

The exceptional `attest-history` path supports an explicitly user-confirmed working deployment
whose one-off resources were deleted and cannot be rechecked.
It preserves null unavailable URL/test time and an empty checks object,
records the actual user statement/reason, and labels evidence `historical-user-attestation`.
It does not manufacture runtime success, remove the suitability gate or authorize future deployment.

### Package validation receipt

Composition persists `packages\validation\local-checks.json` with real command names, commands and exit codes.
Required check names are:

```text
coach-bicep-build       coach-bicep-lint       participant-bicep-build
participant-bicep-lint  coach-build            coach-tests
coach-script-guards    starter-status         package-boundaries
skillable              release-archives
```

`record-packages` requires `allCommandsPassed: true`, every recorded exit code exactly integer zero,
all required names, all four package directories and current reference approval.
It writes `composition-status.json` with reference/package fingerprints and `eventDeployed: false`.
The package fingerprint covers contract, inventory, planned event manifest and package files,
excluding the receipt itself and standard build directories.
Changing package evidence/content can invalidate the receipt as well as changing the reference.
`current_packages` checks both fingerprints; stale validation blocks export rather than silently accepting it.

## 11. Catalog matching and isolated adaptation

### Three different catalogs

- [portal/catalog.json][intake-catalog]: allowed services, patterns, WAF pillars and technical domains.
- [scenarios/catalog.json][scenario-index]: portable reference metadata/index, not deployment state.
- [scenarios/registry.json](scenarios/registry.json): separate scenario registry; not portal execution authority.

Industry choices are read from [the repository CSV][industries], and business units from catalog code.
Discovery reads local manifests, infers visibly unreviewed metadata for older local references,
and supplements them with portable catalog entries when the source is absent locally.
Inference/discovery does not curate or deploy anything.
Local availability requires actual allowed reference artifacts including `infra` and `src`.
Catalog-only entries stay unavailable/inspiration-only.

Manifest v1 includes ID, title, summary, exact industry, units, services, pillars, domains,
allowlisted artifacts, optional source provenance and `metadataStatus`.
Curated metadata must be explicitly maintained through the CLI:

```powershell
python scripts\scenario_catalog.py refresh generated-scenarios\example --metadata reviewed-metadata.json
```

Here `reviewed-metadata.json` is a developer/agent-prepared input, not a file shipped by that name.
The CLI also refreshes the portable index.
Inference remains `needs-review`; source selection grants no consent.
Manifest metadata is deliberately excluded from reference approval fingerprints.

### Technical profiles and recommendation behavior

Technical sidecars live in [scenarios/reuse-profiles](scenarios/reuse-profiles),
outside approved reference folders.
The [reuse-profile index](scenarios/reuse-profiles.json) is rebuildable metadata.
[scenario_match.py][matching] supports `enrich`, `review`, `index` and `recommend`.
Browsing does not enrich or rewrite profiles.

Enrichment extracts bounded safe text/code evidence, per-file hashes, feature references,
dimensions and design/code mentions. It sets `needs-review` and unknown implemented-pattern status.
Explicit curation binds the current profile digest, retained features, inspected code-backed patterns
and a portable architecture summary.
Code mentions are not proof of runtime execution; unknown is not unsupported.
Do not place URLs, subscription IDs, credentials or host paths in public summaries.

Recommendations compare workflow/action/data/human-gate/identity-network signals and lexical overlap.
Foundry alone does not make a useful match.
Scores reward shared signals and inspected code references and penalize conflicting constraints.
The result contains at most three matches above the absolute/relative cutoff, explanations,
freshness/review status, warnings, digests and per-source errors.
It is deterministic local retrieval, not a model verdict or cross-industry authorization.

### Snapshot selection and adaptation

[scenario_adapt.py][adapt] snapshots manifest, brief and reusable file hashes.
Initial source selection preserves target inputs for automatic suggestions;
the manual existing-source picker intentionally prefills them.
Both routes enter scoping.
Late choice records `reuse-selection.json`, asks the same scenario chat for assessment,
and requires `review-selection` plus a new fingerprint-matched confirmation.
`effective-request` resolves the late choice without mutating original intake.

After confirmation, the conductor creates an empty new workspace using the workspace helper.
`prepare` copies only allowlisted source design/code and reserves an adaptation baseline before writing.
It never overwrites a populated target or silently retries over an interrupted partial copy.
An interrupted baseline is an explicit recovery case, not an excuse to delete unknown target work.

Excluded reuse inputs include credentials/environment settings, parameter-value files,
packages, build outputs, deployment/runtime evidence, consent and approval state.
Nested links/escapes and credential-pattern matches block reuse.
Source files stay read-only.
Reconciliation requires one explicit action/reason for every baseline file:

- `keep`: current bytes still match the baseline hash.
- `change`: the file exists and its hash changed.
- `remove`: the target file no longer exists.

The reconciliation report hashes the resulting files and explicitly states `runtimeValidated: false`.
Regenerate target-domain app/data only as needed while preserving fitting implementation.
Then obtain target design confirmation, fresh cloud evidence, runtime validation and suitability approval.

## 12. Diagnostics, setup and Azure context

### Diagnostics are explicit observations

System uses one fixed profile across all catalog services with local image builds,
local Functions hosting and load testing.
There is no scenario/service/build-mode selector in System.
Readiness requires both full-profile tools and existing Azure CLI/azd authentication.
Older narrower reports are not reinterpreted as complete readiness.

The checker verifies executable versions, stable .NET 10 SDK, Python package minimums,
`pip check`, a real Graphviz/diagrams PNG and approved NuGet metadata HTTPS.
Docker checks distinguish installed CLI from a responsive Linux engine.
Installed-but-stopped Docker needs manual engine startup/repair, not automatic reinstall.
The NuGet probe checks approved-feed Azure.Identity metadata, not every generated app restore.

`execution_environment` prefers repository `.venv` and finds certain existing standard tool locations
on the child process PATH. It does not repair shared machine defaults.
New runtime processes inherit this environment; a reused server keeps its prior environment.
After tool installation, restart affected processes and rerun checks rather than trusting stale PATH.

The backend validates report profile, expected check coverage, readiness consistency and exit-code agreement.
Results persist with timestamps.
They have no lease expiry, timed scenario receipt or authority to resume a build.
Scenario agents still check only the dependencies needed by their design.

### Native installation is a separate consented operation

[Install-SystemTools.ps1][installer] defaults to downloading all pinned native baseline tools.
`-Install` adds installation of missing/failed tools after verifying the complete cache.
`-Mode Check` is read-only. `-WhatIf` previews.
`-UseCachedInstallers` forbids new native downloads; missing/corrupt cache entries fail.

The catalog pins URL/version/hash and validates signatures/publishers where applicable.
Catalogued unsigned open-source exceptions still require the pinned hash.
Receipts are local evidence, not signed publisher manifests.
Compatible installed tools are preserved rather than forcibly downgraded.
Docker installation requires separate `-AcceptDockerLicense`; OS virtualization/WSL setup remains manual.
Setup does not elevate itself, reboot, sign in, enable Windows features or start Docker.

Native installation is Windows x64 only.
The cache is not a fully offline bundle: Python packages, WSL images, extensions,
vendor dependencies and generated NuGet packages are not all supplied.
Do not redistribute the ignored cache/report directories with source.
Read [system-tools/README.md](system-tools/README.md) for exit codes, custom paths and recovery.
The legacy [Install-Prerequisites.ps1](scripts/Install-Prerequisites.ps1) remains a narrower compatibility entry.

### Azure identity and readiness

System identity checks reuse `az account show`, token expiry/identity metadata and
`azd auth login --check-status --no-prompt`.
Tokens are not retained in portal reports.
No sign-in, subscription switch, provider registration, resource discovery or deployment occurs from System.
Matching account labels do not establish all target-tenant rights.

[azure_context.py][azure-context] also contains scenario target-resolution and detailed regional-evidence helpers.
Do not confuse those callable helpers with an automatic System cloud-read pipeline.
Exact target readiness includes actual subscription/SKU/region/quota evidence and applicable infrastructure binding;
public availability pages alone are insufficient.
Azure/Entra queries and writes still require the user's actual authorization.
Local target proposal resolution does not grant that authority.

[NuGet.Config](NuGet.Config) clears inherited feeds and uses MicrosoftPackageFeedProxy.
Junctioned external workspaces may not inherit the root configuration:
verify effective restore configuration where the generated app actually runs.
Never disable TLS verification or add an unapproved feed to make a smoke test green.

## 13. Generated reference and authoring outputs

Reference output belongs under the exact handed-off `generated-scenarios\<slug>`.
Typical contract artifacts include:

```text
00-region-availability.json
01-requirements.md
02-architecture-assessment.md
03-architect-diagram.png
04-runtime-diagram.png
04-implementation-plan.md
05-implementation-reference.md
06-deployment-summary.md
azure.yaml
infra\main.bicep
src\<application>.csproj
demoguide\demoguide.md
scenario-validation.json
workflow-state.json
scenario-manifest.json
```

Use the [artifact templates][artifacts] and applicable instructions rather than inventing competing skeletons.
The application must use real Foundry invocation with managed identity and explicit errors.
A deployed resource, homepage or mock response is not runtime proof.
The operator must have both administrative control-plane and full required data-plane access
for every scenario component; workload identity access alone is insufficient.

Private architectures must establish the actual publishing/initialization/test host,
DNS/network connectivity and a usable human browser/CLI administration path before provisioning.
Do not relax network security merely to make deployment tooling work.
Local sample app accounts do not authenticate Azure resource calls.
Keep live participant/coach passwords in private deployment-specific access files and placeholders in public templates.

After approval, composition adds:

```text
08-hack-package-contract.md
09-hack-event-manifest.json
nextsteps.MD
packages\
  coach\                  Sanitized full reference
  participant\            Minimum deployable learner starter
  hack\                   Public learner instructions
  coach-guide\            Private solution guidance and Finale
  validation\
    local-checks.json
    composition-status.json
```

The starter contains indispensable access/isolation/fixtures/prerequisites, not automatically
all non-Foundry infrastructure from the completed reference.
The event manifest is a plan, not proof that any team environment exists.
Rollout uses a coach environment and distinct zero-padded team IDs, resource groups and azd environments.
Every requested target needs real acceptance; an app-less starter needs no invented URL.

Industry intake and Skillable support are separate.
The current [authoring catalog][authoring-industries] supports eight canonical industry slugs.
Unsupported intake blocks composition pending explicit support extension or revised/reapproved scope.
Do not silently map another industry or broaden Generic into every business unit.

## 14. Security and operational boundaries

Preserve these invariants during maintenance:

1. No arbitrary shell/process/Azure execution API in the portal.
1. No token retention or automatic login/default switching.
1. No suitability-approval endpoint, automatic affirmative response or composition scheduling.
1. No replacement native conversation on missing/ambiguous identity.
1. No automatic replay after uncertain delivery.
1. No learner access to private coach files.
1. No source-to-target inheritance of credentials, evidence, consent, approval or deployment state.
1. No weakening private networking, identity or RBAC to work around an external denial.

File previews require inventory membership and are limited to 5 MiB.
The path policy supports top-level repository-managed scenario junctions,
but rejects nested links/escapes and hidden/runtime/secret paths.
Sensitive filenames and common credential extensions are excluded.
Raw HTML remains inert in Markdown previews and no remote scripts/styles are loaded.
SVG/source previews are served as text, not arbitrary executable browser content.

Learner ZIP includes only `packages\hack` and `packages\participant`.
Coach ZIP includes only `packages\coach` and `packages\coach-guide`.
Export totals are limited to 200 MiB of selected source-file sizes before compression,
not a 200 MiB compressed-output guarantee.
ZIP generation is in memory; this is a local bounded convenience, not a streaming release service.
Allowlisted extensions/path filters are defense in depth, not a complete content secret scanner.
Agents must sanitize packages and validate audience boundaries before issuing a receipt.

Source-only sharing must exclude state, ignored generated junctions/physical workspaces,
`.azure`, `.private`, caches, virtual environments, build artifacts and local session history.
Use [`.gitignore`](.gitignore) as a starting policy, not proof a whole-directory ZIP is safe.
Never force-add ignored state for a handoff.
Git does not back up local generated references or their adjacent physical directories.

The native bridge operates with local editor privileges.
Workspace trust and exact session checks matter even on loopback.
Tool permission such as **Allow all** is a user/editor setting, not Azure consent.
The portal cannot inherit a prior chat's session-only approval or bypass organization policy.

## 15. Testing and acceptance strategy

Run the smallest existing checks covering a change.
No absent artifact-template npm lint task, root package manifest or automatic CI pipeline should be assumed.
The Markdown instructions request linting, but no repository Markdown lint command/configuration is shipped.
Use an already available approved Markdown linter when present;
do not claim a missing one ran or install a new tool merely to validate prose.

### Targeted regression commands

From the repository root:

```powershell
python -m unittest scripts.tests.test_portal_visualizer scripts.tests.test_portal_conversation
python -m unittest scripts.tests.test_scenario_chat scripts.tests.test_start_portal
python -m unittest scripts.tests.test_scenario_catalog scripts.tests.test_scenario_match `
    scripts.tests.test_scenario_adapt
python -m unittest scripts.tests.test_hack_workflow scripts.tests.test_branding
python -m unittest scripts.tests.test_prerequisites scripts.tests.test_prerequisite_profiles
python -m unittest scripts.tests.test_container_runtime scripts.tests.test_azure_context
python -m unittest scripts.tests.test_system_tools scripts.tests.test_system_lifecycle
node --check portal\visualizer.js
node --check portal\markdown.js
node --test scripts\tests\portal_visualizer.test.cjs
node --test tools\vscode-chat-bridge\bridge.test.cjs
```

The extension's documented `npm test` runs the same bridge Node tests from its directory.
These tests use mocked editor APIs and temporary fixtures, not real approval or Azure operations.
Frontend tests check DOM/state behavior and asynchronous isolation without establishing live chat success.
Python tests cover request validation, filesystem boundaries, lifecycle/receipt guards,
diagnostics and source-reuse contracts.
Read the relevant test fixtures before changing output shapes.

For a broad cross-cutting change:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py"
python .github\skills\skillable-lod-authoring\scripts\validate_skillable_package.py --check-skill
```

For generated packages, run the validator with package path and canonical industry:
use its `--help` for the actual CLI, then run relevant Bicep builds/lints,
application builds/tests, script guards and package-boundary/release checks.
Persist exact commands and results before recording the package receipt.
No Azure deployment is needed simply to rerun composition's local checks.

### Manual acceptance that automated tests cannot replace

For portal/editor changes, use a disposable scenario and the supported trusted local VS Code profile:

- Verify initial handoff opens the correct repository, agent and trace.
- Reopen the original session and confirm retained history, rather than a new chat.
- Refine a brief; test confirmation, revision and fresh confirmation after text changes.
- Send one message in each existing phase and verify it reaches only the correct native session.
- Exercise unavailable bridge, wrong active editor and uncertain acknowledgement without replay.
- Switch scenarios/phases while responses are pending; confirm no cross-scenario UI overwrite.
- Verify milestones, conversation history, responsive layout, keyboard navigation and appearance.
- Confirm export gates and audience separation against a disposable validated package fixture.

Live Foundry acceptance is separate and requires actual authorized cloud scope.
It must prove inference, invocation, app behavior, required tools/grounding, negative cases
and deployment-user access, not merely homepage reachability.
Unit tests cannot certify the quality of an AI scoping interview or current region/model availability.

## 16. Change recipes and extension points

### Add a portal capability

1. Define whether it is read-only display, explicit local mutation or an agent-owned operation.
1. Keep cloud/model execution and approvals in the existing native context.
1. Implement validation/domain behavior in `Studio`, then a narrowly scoped handler route.
1. Add frontend state/rendering with busy and asynchronous-generation guards.
1. Test rejected inputs, unsafe paths, errors and uncertain delivery, not only the happy path.
1. Update HOWTO and portal/developer references.
1. If old live servers cannot safely support the contract, update the backend compatibility marker.
1. Restart the backend for manual acceptance; a new source checkout does not reload running Python modules.

Do not add another agent, queue, runner, cloud sign-in flow or approval engine as an incidental UI feature.

### Add a service, pattern, industry or business unit

- Services: update [intake catalog][intake-catalog], prerequisite service mapping, relevant skills/templates
  and tests; preserve Foundry baseline and unknown-ID rejection.
- Patterns: update the catalog, [pattern guide][patterns], handoff rationale/runtime-acceptance instructions,
  matching feature extraction where relevant and tests.
- Industries: update exact intake catalog evidence and separately extend Skillable templates/validator support
  if composition is required. Do not equate adding a card with complete authoring support.
- Units: update stable IDs/validation, intake, manifest contracts, matching/brief behavior and scope propagation.
  Keep Generic exclusive and carry targeting through data, tests and authored materials.

Existing decisions, manifests and approval evidence must not be silently rewritten when choices expand.

### Change the bridge or native API integration

1. Preserve extension publisher/name, URI scheme and command IDs.
1. Update validation/dispatch behavior and bridge mock tests together.
1. Bump extension version and, if required, portal running-version checks.
1. Package a VSIX, install it into the target local profile and restart the extension host.
1. Manually prove retained-session targeting and non-replay on the supported editor version.
1. Record the editor version and limitations without copying private session transcripts.

Never replace an uncertain targeted API with a generic sidebar submit as a fallback.

### Change approval or fingerprint rules

Treat this as a workflow/security change, not a display refactor.
Inspect inclusion/exclusion rules, historical evidence support, direct HackCreator invocation,
backend composition checks, phase eligibility, export guards and receipt tests together.
Do not migrate existing approvals by synthesizing user responses.
If new coverage invalidates old records, explain the revalidation/review path explicitly.
Keep the distinction between syntactically valid evidence and independently observed runtime tests.

### Update the native installer baseline

Change the reviewed tool catalog's versions, immutable official URLs, SHA256 and install arguments together.
Test a separate cache rather than editing receipts to accept different bytes.
Preserve signature policy, explicit agreement/Docker consent, offline-native limits and compatible-tool reuse.
Update System/profile/checker coverage when adding dependencies.
Keep setup separate from diagnostics and scenario execution.

### Maintain documentation and customization

The HOWTO is the single primary user document; do not recreate a competing overview.
Keep focused component READMEs for operational/API detail.
Use this guide for cross-component developer architecture, and AGENTSEXPLAINED for dated discovery findings.
Follow the applicable file-scoped instructions and the 120-character Markdown line limit.
Prefer relative documentation links, meaningful image alt text and plain headings.
Preserve historical screenshot dates instead of claiming they show current controls.

## 17. Troubleshooting and handoff runbook

| Symptom | Likely investigation | Safe response |
| --- | --- | --- |
| Launcher rejects server | Health/workspace/version and recorded PID | Stop only the verified stale server when safe |
| Browser disconnects | Runtime console or server log | Restart the portal; preserve state |
| Installed tools fail checks | Process PATH, `.venv`, probe output | Restart affected process; fix dependency |
| Docker pipe unavailable | Engine mode/startup/virtualization | Start/repair Linux engine, not reinstall blindly |
| NuGet failure | Approved proxy, TLS, effective config | Use approved IT/feed fix; retain TLS |
| Handoff stays Starting | Native chat, trust, permissions, first report | Inspect original session; no duplicate |
| Reopen cannot resolve chat | Trace, workspace/profile, IDs/history | Repair known existing association explicitly |
| Bridge installed but too old | Activated versus installed version | Restart extension host; recheck |
| Message unknown | Native chat and durable ledger | Inspect before any explicit resend |
| Brief confirmation stale | Current text hash/response/selection | Review revised brief and confirm anew |
| Reuse source changed | Manifest, brief and file digests | Reload source; do not override hashes |
| Adaptation partially copied | Baseline state and target inventory | Preserve work; reconcile controlled recovery |
| Approval fails | Evidence shape and reference fingerprint | Revalidate and obtain real renewed review |
| Export blocked | Package/current reference receipt and build state | Fix checks and record current receipt |
| Running after interruption | Report time and actual VS Code state | Resume/report actual results, not a heartbeat |

For an engineering handoff:

1. Record source revision, intended local editor version and which components were tested.
1. Provide the HOWTO, this guide, workflow contract and relevant component references.
1. Share source-only content, not a directory dump.
1. Separately inventory local generated references and physical junction targets if transfer is required.
1. Securely transfer only explicitly approved private deployment/access material.
1. Preserve approval provenance, evidence limitations and actual authorization scope.
1. Have the recipient install/check tools and authenticate their own identities.
1. Confirm real editor handoff/bridge operation before troubleshooting scenario implementation.
1. Run targeted local tests for the changed surfaces.
1. Treat cloud validation, event rollout, cleanup and publication as separate scoped operations.

Stopping the browser/server does not clean up Azure resources.
Never use broad process-name termination or recursive root deletion to resolve local runtime issues.
Do not edit a scenario concurrently with another chat or legacy writer.

## 18. Documentation consolidation and compatibility

The former user README overlapped with the HOWTO on purpose, startup, two-window operation,
phases, approvals, prerequisites, outputs, industry scope and optional rollout.
Those topics now have one primary home in [FBC-Builder-HOWTO.md](FBC-Builder-HOWTO.md).
Unique overview details about source sharing, compatibility, direct invocation and scope were merged there.
The obsolete FBC-named overview was removed.
Duplicate legacy guide and launcher entry points have been removed rather than retained as redirects.

The HOWTO also adds current features missing from the historical illustrated sequence:
automatic catalog comparison, manual/late source reuse, isolated adaptation, expanded brief review,
phase-local portal conversation, delivery uncertainty and the dedicated runtime console lifecycle.
Its old screenshots remain explicitly dated.

Keep stable workflow and evidence surfaces:

- Agent names and canonical skill folder IDs.
- Existing executable script names and environment variables.
- Recognition of historical chat traces and retained approvals/evidence.

Current product identifiers are `.fbcbuilder-portal`, `fbcbuilder-theme`, extension
`fbcbuilder.scenario-chat` and command `fbcbuilder.linkChat`.
The state directory is moved, not copied. Install the 0.4.0 bridge and restart the extension host
before using its new URI routes; the old publisher's installed extension is not a route alias.
For another existing checkout, stop its portal and rename its previous product-state directory to
`.fbcbuilder-portal` before launching this version. Never merge two existing state directories.
Keep the original JSON records byte-for-byte intact during that move.
Theme preferences start with the system default because the browser storage key has changed.
This migration does not rename deployed resources, identity ownership markers, original generated
scenario files, consent records or approval fingerprints. Historical references inside those retained
artifacts are evidence, not current portal paths. Cryptographic hashes and third-party code are unchanged.

[workflow]: .github/skills/hack-builder-workflow/SKILL.md
[startup]: scripts/start_portal.py
[backend]: scripts/portal_visualizer.py
[status]: scripts/portal_status.py
[chat]: scripts/scenario_chat.py
[guard]: scripts/hack_workflow.py
[catalog]: scripts/scenario_catalog.py
[matching]: scripts/scenario_match.py
[adapt]: scripts/scenario_adapt.py
[checker]: scripts/check_prerequisites.py
[profiles]: scripts/prerequisite_profiles.py
[containers]: scripts/check_container_runtime.py
[azure-context]: scripts/azure_context.py
[workspace-helper]: scripts/New-AzdScenarioWorkspace.ps1
[artifacts]: .github/skills/az-azure-artifacts/templates
[howto-setup]: FBC-Builder-HOWTO.md#prepare-your-machine-and-open-fbc-builder
[bridge]: tools/vscode-chat-bridge/README.md
[bridge-package]: tools/vscode-chat-bridge/package.json
[tool-catalog]: system-tools/tool-catalog.json
[installer]: system-tools/Install-SystemTools.ps1
[conductor]: .github/agents/az-01-conductor.agent.md
[creator]: .github/agents/az-09-hackcreator.agent.md
[foundry]: .github/instructions/az-foundry.instructions.md
[research]: .github/instructions/az-agent-research-first.instructions.md
[authoring]: .github/instructions/hack-authoring.instructions.md
[html]: portal/visualizer.html
[frontend]: portal/visualizer.js
[css]: portal/visualizer.css
[markdown]: portal/markdown.js
[intake-catalog]: portal/catalog.json
[scenario-index]: scenarios/catalog.json
[industries]: microsoft_industry_verticals.csv
[patterns]: .github/skills/az-scenario-requirements/references/agentic-patterns.md
[authoring-industries]: .github/skills/skillable-lod-authoring/references/industry-catalog.md
