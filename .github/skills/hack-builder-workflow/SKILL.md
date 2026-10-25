---
name: hack-builder-workflow
description: >
  Use when asked to build a hack, create a Foundry scenario, resume ABC Builder,
  approve a scenario, author hack packages, or deploy a hack event. Defines the
  scenario-first workflow, explicit approval boundary, minimal learner starter,
  and separate optional team rollout.
---

# ABC Builder workflow contract

The user first needs proof that the story and technology work. A hack is derived
from an approved deployed reference solution, not built in parallel with it.
Exactly two Copilot agents own the workflow: `az-01-conductor` is the scenario
orchestrator and `HackCreator Agent` is the hack composition agent. Each performs
all implementation in its own context through skills. Neither delegates to
specialists, invokes the other agent, or starts a subagent fanout.

## Intake and local portal

The portal is a visualization and handoff layer, not an execution engine.
It saves the brief and opens the real interactive VS Code custom agent using
`code chat --mode <agent> --add-file <handoff>`. It never launches Copilot CLI workers,
schedules stages, runs scenario tests/deployments or answers decisions.
Its optional System panel runs the existing read-only local prerequisite checker and verifies already-authenticated
CLI identity metadata on explicit request. It never installs tools, signs in, retains tokens or changes Azure defaults.
The agent performs the entire technical flow in VS Code through the existing skills.
Use `generated-scenarios\{projectSlug}` without silently changing the slug.

The normal user flow is:

1. Enter the scenario brief in the portal and hand it to `az-01-conductor` in VS Code.
1. The agent builds requirements, architecture, diagrams, Bicep, real app and tests.
1. In that VS Code chat, approve the architecture and reviewed deployment scope once.
1. The agent deploys, repairs in-scope errors and proves real application behavior.
1. Approve the working scenario's suitability in chat; record the reviewed fingerprint.
   Open the separate `HackCreator Agent` context to produce and validate hack materials.
1. View files and export separate learner/private coach ZIPs in the portal. Done.

Permissions and approvals belong to the actual VS Code session. The portal neither grants them nor
creates another permission/decision queue. No repeated preflight, target, build or deployment approval
cards. Required checks remain agent work; only genuine blockers or material changes outside the
approved design require another decision. Preserve existing explicitly restricted instructions.
Never bypass actual host, tenant or Azure restrictions.

### Authorization continuity and consolidated review

Separate local preparation, authorized cloud reads, installation writes and working-scenario suitability approval.
Permission to use tools is not permission to change Azure or Entra, and a deployment approval is not hack approval.

- Continue local analysis, public-documentation research, design/cost proposals, code and tests within the user's
  existing local scope. Do not ask permission merely to prepare a repair or price an unapproved addition.
  A local-only instruction still prohibits cloud operations; it does not block this local preparation.
- Reconcile actual user responses for the same scenario by target and operation, across current and legacy records.
  A later read-only grant does not revoke an earlier deployment grant unless the user explicitly withdraws or
  restricts it. An initial false intake flag, expired worker receipt or portal migration is not a revocation.
  Agent-written summaries, status reports and derived authorization files cannot create or revoke user consent.
  Trace a claimed restriction to its actual user response, not merely a newer artifact timestamp.
  Honor actual explicit restrictions and host/tenant denials. If user responses genuinely conflict, defer only
  affected cloud operations and ask one focused clarification; continue independent authorized local work.
- Reuse matching approval for its exact targets, resources, directory operations and reviewed cost scope.
  Do not request routine reapproval for a build, unchanged readiness check, in-scope repair or installation step.
  Azure readiness reads and Entra ownership reads are distinct: run only those covered by actual authority.
  Missing read permission is not permission to query; mark the affected check pending and keep preparing locally.
- Before asking about a missing private execution host, prepare a concrete preferred access-path repair and cost.
  Use saved evidence and authorized discovery where available; otherwise label reuse/connectivity unverified.
  Do not require a preliminary choice between "discover a runner" and "design a runner" just to prepare the review.
  Carry the proposed host, artifact transfer, identity, DNS, execution wiring and lifecycle into local artifacts.
  Do not create it, alter networking or relax private access before the required approval.
- Present one consolidated new-scope review: what was already approved, the exact addition or conflict,
  account/tenant/subscription and resource targets, Azure reads/writes versus Entra reads/writes,
  security impact, incremental and total estimated cost, evidence and pending dependent checks.
  Explain each requested permission by the operation it enables and state what it does not authorize.
  Request only missing authority or the material change, not the entire previously approved deployment again.
  Genuine business choices and observed permission failures still require a decision; never invent their answers.

Use `waiting_for_user` only when local preparation is complete or a genuine missing decision blocks further work.
Report a cloud step as blocked without implying all local work must stop. Once the scoped response is recorded,
continue matching authorized work in the same context. Event rollout, publication and suitability remain separate.

### Display-only progress

At stage start, completion, a real blocker and a user review boundary, write a short report:

```powershell
python scripts\portal_status.py <projectSlug> --stage bicep --status running --summary "Creating infrastructure"
```

Stages are requirements, architecture, diagrams, bicep, application, local-validation,
deployment, live-validation, review, hack-content, hack-starter, hack-coach and hack-validation.
Statuses are running, completed, waiting_for_user, blocked and failed.
The helper writes `.abcbuilder-portal\scenarios\<projectSlug>\status.json` atomically
(or the existing legacy state directory). It has no leases, revisions, authorization or execution gates.
Write truthful summaries without secrets. A completed step is not completion of the entire scenario.
The portal shows the reported step and timestamp, not an inferred live process state.
Validated package receipts establish package completion; a handoff alone never means an agent started.

The retired CLI runner has been removed. Its saved state and diagnostics remain historical,
not current instructions or a reason to reproduce background-worker errors.
Before continuing an old scenario, ensure no legacy worker still owns it; never edit concurrently.

### Service-aware prerequisites

Reuse the user's configured CLI/azd identity and existing prerequisite observations in VS Code.
Do not ask each scenario to configure credentials or repeat the whole machine audit.
Resolve tenant/subscription/account from `az account show` and verify `azd auth login --check-status`,
using `scripts/azure_context.py` helpers. Do not request manual IDs available from the authenticated CLIs.
Ask only for missing authentication, conflicting intended targets or an actual sign-in mismatch.
The System panel's sign-in metadata is an observation, not permission for cloud resource queries or writes.
Recheck affected tools after actual failure, changed environment or newly required capabilities.
Keep RBAC, region/quota, what-if and runtime checks in the agent's technical flow, not portal checkpoints.

Use the shared profiles in `scripts\prerequisite_profiles.py` and the checker, not per-scenario guessed install lists.
The scenario agent owns prerequisite checks through the existing skills. Check the tools needed for the
current work, reuse unchanged results, and stop before an affected step if its dependency is unavailable.
The optional portal System audit prepares shared tools before scenarios; it is not a stage scheduler,
deployment-readiness gate or second scenario approval pipeline. Reuse matching saved results without a timed renewal.
When a service-aware audit is needed, run:

```powershell
python scripts\check_prerequisites.py --services foundry --stage requirements --json
```

Include the scenario's selected service IDs and confirmed build mode when needed.
These are standalone diagnostics, not worker leases or timed execution gates; the System page records its own report.

The checker allows requirements/design while later gates fail. Do not require a browser launch or a temporary
.NET build before writing a story. After architecture confirmation, update manifest services and check
new dependencies before using them. Actual scenario builds/tests remain required, but the portal does not
repeat them after the agent has run them. Dashboard reports do not require a separate timed machine-audit receipt.
Report all failed checks and affected stages together in chat; block only before an affected operation.
Docker is needed for confirmed local image builds, not Bicep/Dockerfile authoring.
Check the running Linux engine, not just executable discovery.
Use `--build-mode remote` only for an explicitly chosen remote-build design, never as a failure/permission fallback.
Use `--local-functions` only for a planned local Functions host; do not require emulators or optional tools by default.
Verify new design-specific packages with real restore/build. Unknown dependencies require explicit additional checks.
No preflight grants Azure/host permission, starts engines, installs software or replaces deployment acceptance.
See [the prerequisite guide](../../../PREREQUISITES.md) for the service/stage matrix and System checklist.

Status refresh is read-only. Agents own execution, evidence and decisions in VS Code.
Continue between technical steps in the same context; reporting status is not a handoff or gate.
Never infer successful deployment or validation from existing files or a successful handoff.

For local-only work, account, subscription quota and budget are deferred deployment concerns.
Use current public evidence for provisional region/model choices and label unresolved live checks.
Complete local implementation and authorized preparation, then obtain a concise architecture/deployment approval in chat.
This checkpoint is not deployed-scenario suitability approval. Reuse answered choices and
continue backend implementation without unnecessary handoffs. Required service substitution,
material security exceptions or unresolved business requirements need explicit structured decisions.

Perform authorized readiness/what-if in the real VS Code session; the portal does not authorize commands.
Architecture approval includes deployment consent after actual what-if, estimated cost and target review.
Present one coherent end-to-end deployment scope, including necessary directory installation and cost.
Use azd lifecycle hooks for technical dependency ordering; do not turn foundation, image publication,
agent initialization and app rollout into separate routine user approvals.
Further consent is needed only for permissions or material scope/cost changes outside the approved design,
not each command or an in-scope corrective retry. Technical bugs are agent-owned work, not user decisions.
Do not label generated configuration conflicts or correctable script errors as workstation setup.
An existing explicitly restricted approval is not broadened by this rule; consolidate any remaining scope honestly.

### Subscription regional readiness

Regional validation belongs to architecture, not a trial deployment. Public service locations support only
provisional local design. At the first authorized exact-target read-only preparation, validate the actual
subscription before deployment consent or provisioning. If that scope was already authorized during design,
perform these checks then; do not ask again. Authentication alone is not subscription-query authorization.

Build a candidate matrix for the complete resource set, exact SKUs, models, feature requirements and scale limits.
Query only candidates covered by the authorization; otherwise present proposed alternatives for consolidated
target review. Do not pin a failing preferred region merely because a public service table lists it.
Preserve residency, security, zone redundancy and selected services when ranking alternatives.
Only recommend a common region where all required checks pass; missing/denied data is unknown, not available.
Never silently change targets or require a quota/support ticket before evaluating acceptable alternatives.

- Cosmos DB: query subscription-scoped location properties. `supportsAvailabilityZone` does not prove access.
  For zone-redundant accounts require `isSubscriptionRegionAccessAllowedForAz: true`; nonzonal accounts require
  `isSubscriptionRegionAccessAllowedForRegular: true`. Require `status: Online` and applicable feature support.
  Record rejected regions and the actual access flags; do not disable zones as a workaround.
- Compute VMs/VMSS: query `az vm list-skus --all` and `az vm list-usage` with explicit subscription and region.
  Verify exact SKU/family, subscription restrictions and requested zones, plus both total regional and family
  vCPU headroom and VM-count quota. Aggregate all instances, maximum scale and rollout/surge demand.
  Require `currentValue + required <= limit`; a zero limit with positive demand fails.
- App Service/Functions plans: identify the actual ARM resource type before interpreting a size/quota error.
  An App Service B2 worker quota is Microsoft.Web, not a Microsoft.Compute B-family VM quota.
  Validate its exact SKU/worker quota and hosting requirements using the correct provider.
- Foundry and dependencies: validate exact model/version/deployment type, quota, required tools/features,
  provider registration, policy and each supporting service's restrictions. Provider registration is not quota.

The agent records actual regional results in `00-region-availability.json` and the deployment summary.
Use the validation skill and service-specific checks; do not introduce a second portal-specific evidence
schema or repeat unchanged checks merely to satisfy a timed dashboard receipt.
Missing, denied or insufficient eligibility remains a real blocker, never a passing default.
Clearly distinguish actual failures from checks dependent on resources/identities created during installation.
Disclose those dependencies, planned installation changes, what-if limits and cost in the consolidated review.
Only actual user authorization for the reviewed targets permits deployment; preparation is not provisioning consent.

Refresh after provider/capacity failure and immediately before deployment when stale. ARM what-if, quota and
region metadata cannot reserve capacity or guarantee allocation; distinguish checked eligibility from capacity
that Azure only resolves at deployment. Do not submit quota requests, change shared defaults or allocate probes.
Keep each scenario's evidence, targets and approvals separate, even when two scenarios encounter similar errors.

Official references:
[Cosmos location properties][cosmos-locations] and [Compute quota and capacity][compute-quota].

[cosmos-locations]: https://learn.microsoft.com/rest/api/cosmos-db-resource-provider/locations/list
[compute-quota]: https://learn.microsoft.com/azure/virtual-machines/quotas

### Private-workload management access

Private networking must include a usable operator and automation path in the architecture, not a surprise
workstation prerequisite after provisioning. During design, inventory both control-plane and data-plane access
for provisioning, image publishing, fixture ingestion, agent initialization, runtime tests and troubleshooting.
An ARM deployment succeeding does not prove the execution host can reach private service endpoints.

- Reuse an existing authorized VPN/connected runner when available. Otherwise recommend the simplest viable
  path: a VNet-connected automation runner for unattended operations, and, when interactive administration is
  needed, a management VM without a public IP reached through Azure Bastion or an approved VPN.
  Bastion is interactive VM access, not automatic network connectivity for the local Copilot worker.
  Explain how scripts/artifacts reach the execution host and how results return; do not assume portal access
  or a jump VM makes local azd hooks run inside the VNet.
- Compare a public-IP exception only where the service supports it and the requirements permit restricted
  public access. A public-IP allowlist does not route to a private endpoint or work with public access disabled.
  Never silently relax private-only requirements. If chosen, parameterize a confirmed operator egress IP,
  restrict IPv4 rules to `/32` (or the equivalent narrow supported IPv6 rule), and document expiry/removal.
  Do not discover the user's public IP through an unsolicited external lookup or use unrestricted ingress.
- Plan routing, private DNS resolution/forwarding, NSGs/firewalls, required outbound build/package access,
  operator sign-in and least-privilege execution identities. Network reachability does not grant RBAC.
  Use managed identity for automation where supported; do not expose RDP/SSH to the Internet or embed credentials.
- Include management resources, exact SKUs/region constraints, compute quota, ongoing VM/disk/Bastion/VPN
  costs, patching, shutdown and cleanup in the architecture, diagrams and consolidated deployment review.
  VM shutdown does not remove disk or Bastion charges. Suggest a concrete preferred option and alternatives
  at the existing design checkpoint, not a new portal wizard or a routine prerequisite questionnaire.
- Wire the selected path into IaC and installation automation. Order provisioning so the execution host and
  private DNS exist before dependent publishing/initialization. Avoid a bootstrap dependency where installing
  the management path itself requires access that only that path provides.
  Validate DNS, TCP/TLS and an authenticated service operation from the actual execution host after provisioning,
  plus the expected unauthorized/outside-network denial. Route metadata alone is not acceptance evidence.
  Before provisioning, document planned checks without probing nonexistent endpoints or inventing success.
- For existing deployments, an absent management path is a design gap: propose one consolidated repair with
  cost/security impact. Create no VM, VPN, runner, peering or firewall exception outside recorded authorization.
  Actual host/tenant restrictions remain blockers; never bypass a denied execution environment.

Design evidence (reviewed 2026-10-23):
[Private Endpoint DNS](https://learn.microsoft.com/azure/private-link/private-endpoint-dns) and
[Azure Bastion](https://learn.microsoft.com/azure/bastion/bastion-overview).
Refresh service/SKU-specific evidence when selecting a concrete scenario option.

### Sample application accounts and Azure resource access

Sample application sign-in uses **local app accounts**, not participants' Microsoft/Entra identities.
Participants and coaches must not need directory roles, app registrations or consent-administrator access.
Never use Entra ID authentication for a sample app if admin consent is required; switching OAuth flows
or adding basic OpenID scopes does not remove tenant consent or assignment restrictions.
Do not weaken tenant policy, remove required authentication or add an anonymous/role-selector bypass.
An explicitly requested enterprise identity integration is a separate reviewed requirement, not the sample default.
If that integration needs admin consent, stop the affected integration and retain local app sign-in.

- Generate unique per-deployment passwords and separate participant and coach accounts with server-assigned roles.
  Store only salted password hashes in the configured durable backend. Use secure HttpOnly session cookies,
  CSRF protection, bounded sessions, login throttling/lockout and persistent session-key protection.
  No public registration, shared hard-coded passwords or client-selected privileged roles.
- Document login URL, usernames, role boundaries and credential delivery in both participant and coach guides.
  Write actual generated credentials only into private, gitignored deployment-specific guide/access files
  (for example `.private/participant-access.json` and `.private/coach-access.json`), with restrictive local access.
  The participant file contains only participant credentials; coach credentials stay coach-only.
  Public/GitHub-ready guides contain placeholders and private-file retrieval instructions, never live passwords.
  Exclude these files from catalogs, web publishing, source archives and public learner exports.
  Do not copy reference credentials to a new coach/team deployment; generate destination-specific credentials.
  Before suitability approval, produce private reference access notes only, not hack plans or packages.
- Azure resource-to-resource authentication always uses managed identities and least-privilege RBAC.
  Local app passwords are not Azure credentials. Never substitute service keys, connection-string secrets
  or shared service-principal secrets for the workload managed identity.
- Resolve the signed-in deploying admin user's object ID from the existing CLI context. Include the necessary
  scenario-scoped control-plane and data-plane RBAC assignments for that user in IaC/installation and what-if
  review, alongside separate workload managed-identity assignments. Subscription ownership alone does not
  imply data-plane access. Grant only roles needed to initialize, inspect and validate the complete scenario,
  including grounding ingestion and queue/tool operations required by acceptance; avoid broad tenant roles.
  Execute assignments only within authorized scope. Missing role-assignment rights are an explicit blocker,
  not permission to elevate or silently omit validation.
- Prove local login/logout, failed login/lockout, anonymous and wrong-role denial, and the real app-to-Azure
  managed-identity path. Deployer probes complement, but never replace, runtime managed-identity acceptance.

### Scenario-owned application identity setup

This section applies only to explicitly required non-default identity integrations, not sample-app login.
Apply [sample application accounts and Azure resource access](#sample-application-accounts-and-azure-resource-access)
first. Do not generate Entra registrations or consent dependencies merely to authenticate a sample app.

Treat Microsoft Entra application registrations, service principals, exposed API scopes, app roles,
redirect URIs and assignment requirements as technical deployment dependencies, not recurring business questions.
Resolve them during architecture and carry one identity installation plan through IaC, app configuration and deployment.

- Use managed identities for Azure backend communication. Add interactive-user SPA/API registrations only
  for the explicitly reviewed non-default integration, never as a local sample-account replacement.
- For a standalone scenario requiring registrations, default to new dedicated scenario-owned registrations
  when no existing IDs were supplied and no requirement mandates reuse. Record this implementation choice;
  do not ask "existing or new?" merely because IDs do not exist yet. Preserve an already answered choice.
- Generate idempotent scenario-local identity setup and validation automation with the reference assets.
  Persist tenant, stable scenario ownership markers, actual application/client and object IDs, scopes/roles,
  redirects, assignment policy and outputs consumed by azd. Names alone are not proof of ownership.
  Reuse only verified owned objects; do not adopt unrelated registrations or create duplicates on retries.
- **Deployment outputs are not user inputs.** Client IDs, service-principal object IDs, generated scope/role IDs,
  endpoint URLs and installation receipts for solution-created components belong to the deployment.
  Do not request them in a business decision, portal message or manual receipt questionnaire.
  A new registration having no ID before creation is expected, not evidence of a missing user prerequisite.
  Use existing IDs as inputs only when the user requires integration with externally managed components.
- Avoid a circular preparation gate: identity objects do not need to exist just to document their planned changes,
  estimate cost or inspect the independent ARM changes within authorized read-only scope.
  Identify which parameters are generated outputs and which checks genuinely depend on installed identities.
  Where exact ARM what-if needs a generated ID, report that dependent check as pending until authorized identity
  setup produces it; run independent checks now. Never invent an ID to claim an exact what-if passed,
  require the user to manufacture one, or create directory objects during read-only preparation.
  Present the planned directory changes and independent what-if with this limitation in the consolidated review.
- Distinguish Azure resource authorization from Microsoft Graph/directory operations. Read-only preparation
  and ARM what-if do not authorize directory writes or cover their changes. Include required directory writes,
  any admin consent, target tenant and exact permissions in one consolidated authorization/installation plan
  before the dependent operation. Reuse recorded authorization when it actually covers these operations.
  Do not split it into source-choice, installer-choice and client-ID questionnaires.
- Do not assume a tenant administrator is required merely to register an application. Member-user registration
  may be permitted by tenant policy; creation, API permission consent, role assignment and assignment policy
  have distinct requirements. Verify the current identity's applicable capabilities within authorized scope.
  Never elevate roles, weaken tenant policy or grant broad Graph/admin consent to avoid a blocker.
- Execute approved setup through the current authorized identity and azd lifecycle wiring when supported.
  Capture real outputs automatically; do not ask the user to copy client IDs that the tooling can retrieve.
  Keep local builds/tests running with explicit test configuration while live IDs are unresolved;
  never invent production IDs or present placeholder-dependent what-if/runtime checks as passed.
- If actual policy/permission evidence or a known tenant restriction prevents required setup, report one
  precise technical prerequisite with the failed operation, least-privilege remediation, prepared script
  and read-only verification. Request administrator assistance only for the operations that need it.
  Missing directory authorization is a scope checkpoint, not proof that administrator installation is required.
  Once the user explicitly chooses an administrator-managed route, honor it and consume verified outputs;
  do not silently switch to worker-managed installation or ask the same route question again.
  Administrator involvement, when genuinely necessary, should run the prepared installation automation;
  its structured non-secret output is consumed and verified by the deployment, not transcribed into a business answer.
  An earlier "arrange administrator installation" answer does not prove creation succeeded or confer write permission.
  If no installation occurred, show the unresolved technical dependency once; do not turn it into a succession
  of "which IDs were installed?" questions. A user correction that deployment must own setup changes the intended
  installation route, not the tenant's permissions or the required authorization scope.

Keep these dependencies visible in deployment status. Do not claim the scenario is deployed or authenticated
until the real configuration, sign-in/token validation and expected denial cases pass.
See [Microsoft Entra default permissions](https://learn.microsoft.com/en-us/entra/fundamentals/users-default-permissions).

In noninteractive jobs, missing business decisions, authentication or target authorization mean
persist progress, report **decision required** with the exact next action, and
stop. Do not guess consent because an interactive question tool is unavailable.
This customization work itself authorizes no Azure operations.
For technical prerequisite/host-permission failures, use the separate blocked protocol above.

Industry intake comes from repository `microsoft_industry_verticals.csv`.
Skillable currently supports eight slugs in its own authoring catalog:
`financial-services`, `healthcare`, `manufacturing`, `retail`, `energy-oil-gas`
`government-public-sector`, `hospitality-travel` and `media-communications`.
Do not silently map unsupported intake industries.
Before composition, block on an unsupported selection and request an explicit
decision to extend authoring support or revise/reapprove the scenario.

## Business-unit scope

`businessUnits` is a multi-select array of stable IDs. Use these exact IDs:

| ID | Display name |
| --- | --- |
| `generic` | Generic |
| `executives` | Executives |
| `it` | IT |
| `operations` | Operations |
| `communications` | Communications |
| `executive-assistant` | Executive assistant |
| `legal` | Legal |
| `hr` | HR |
| `business-manager` | Business manager |
| `finance` | Finance |
| `sales` | Sales |
| `marketing` | Marketing |

Generic is exclusive: `["generic"]` means a typical workflow for the selected
industry with no unit targeting. Never combine it with specific units or interpret
it as every unit. For older intake without this field, make the Generic fallback
visible; never infer a specific unit. Multiple specific units form one coherent
cross-unit scenario with explicit handoffs, not unrelated demos.

Record exact IDs and business meaning in requirements, personas, scenario narrative,
data ownership and access boundaries. Carry them into app pages/actions, seed data,
agent grounding/tools, evaluation prompts, demo acceptance and, after approval,
learner challenges and private coach notes. These business-unit choices are not
Azure deployment or authorization scopes.

## Agentic business workflow

Use the requirements skill's
[18-pattern guide](../az-scenario-requirements/references/agentic-patterns.md)
to choose a useful industry/unit workflow before selecting supporting infrastructure.
Record the simplest primary pattern, justified overlays, simpler alternative, runtime contract and measurable evidence
in requirements and architecture. Patterns concern deployed Foundry behavior, not additional Copilot contexts.
Carry the choice through app/data, runtime coordination checks, demonstration and only then approved hack composition.
Catalog reuse requires a fresh fit assessment. Existing scenarios and approval records are not automatically changed.

## Reusable scenario catalog

The portal catalog reads `generated-scenarios\*\scenario-manifest.json`.
Discovery is read-only: it must not refresh manifests, mutate source scenarios or
infer consent. A selected source is guidance, not approval or permission to deploy.

Each manifest uses this schema:

| Field | Contract |
| --- | --- |
| `schemaVersion` | Integer `1` |
| `id` | Scenario slug matching its folder |
| `title`, `summary` | Curated business title and concise outcome summary |
| `industry` | Exact intake catalog value; `null` for unclassified inferred metadata |
| `businessUnits` | Array of stable IDs, respecting Generic exclusivity |
| `services`, `pillars`, `domains` | Arrays of curated service, WAF and domain metadata |
| `artifacts` | Relative paths to reference documents, infrastructure and application only |
| `source` | `null` for an original; otherwise `{scenarioId, manifestDigest}` |
| `metadataStatus` | `needs-review` for inferred metadata; `curated` after review |

Initially inferred metadata
must be visibly marked `needs-review`, never presented as curated or validated.
Exclude packages, deployment/runtime state, credentials, secrets, environment files,
approval records and authorization scopes from catalog artifacts. Paths must resolve
inside the reference workspace; never include absolute paths or traversal.
`manifestDigest` identifies the selected source manifest, not a runtime-success receipt.

The worker maintains the target manifest explicitly at local preparation checkpoints
and after reference changes, honoring writer leases and revision checks:

```powershell
python scripts\scenario_catalog.py refresh generated-scenarios\<slug>
python scripts\scenario_catalog.py refresh generated-scenarios\<slug> --metadata reviewed-metadata.json
```

Write the reviewed metadata fields into `reviewed-metadata.json`, including business scope
and `metadataStatus: "curated"`. Source provenance is maintained from the normalized adaptation request.
The initial refresh can infer a
`needs-review` entry; the worker must review and complete it with `--metadata`,
then verify the saved manifest. Do not hand-edit catalog state or make discovery a writer.
The portable repository index is `scenarios/catalog.json`; rebuild it through the same helper.
Remote-only index entries remain unavailable until their reference folders and manifests are local.

For an adaptation, read the source architecture as read-only guidance. Regenerate
the business application, synthetic data, personas, grounding and tests for the
target industry and units; a rename of source branding is not an adaptation.
Refresh current technical evidence and obtain a new design confirmation, validation
and suitability approval. Never inherit deployment state, secrets, authorization
scopes, approvals, packages or runtime success. Source region/quota/runtime evidence
is not target deployment proof. Do not modify the source or auto-start composition.

## Phase A: scenario implementation and review

Create these artifacts at `generated-scenarios/{project}/`, using existing
templates where available:

- `00-region-availability.json`: dated subscription, feature, model and region evidence.
- `01-requirements.md`: scenario story, business outcome, personas, scope,
  fictitious company provenance, acceptance prompts and expected evidence.
- `scenario-manifest.json`: curated catalog metadata, business units and optional
  source provenance; it is not runtime validation or approval evidence.
- `02-architecture-assessment.md`: complete reference architecture, SKUs,
  Foundry setup choice, identity/data paths, cost and trade-offs.
- `infra/`, `azure.yaml`, `src/`, runtime data and installation scripts.
- `03-architect-diagram.png` and `04-runtime-diagram.png`.
- `06-deployment-summary.md`: commands, targets, real results and limitations.
- `demoguide/demoguide.md`: a usable walkthrough of the deployed story,
  with live app evidence and a documented screenshot fallback if needed.

For Foundry hacks, implement the real application and agent invocation path.
Choose the simplest supported architecture that meets the story and security
requirements. Explain Basic versus Standard and private-network requirements
before implementation. Do not expand into a complex multi-agent design unless
the business outcome needs it. Never weaken required security to meet a timer.

Deploy the root reference scenario once, only within explicit Azure authorization
and with user-confirmed targets after what-if.
Do not require any hack contract, Skillable content, package, or team manifest.
Existing legacy packages must not redirect this deployment.

Prove the deployed application invokes the real Foundry agent with managed
identity; test the model, grounding and tools where required by the story, plus
an observable negative/error case. A homepage or provisioning success alone is
insufficient. Verify runtime fixtures from the identity/network path that will
actually read them, including ingestion when applicable.

Write `scenario-validation.json` with `status: "passed"`, `checkedAtUtc`,
`applicationUrl`, and a `checks` object. Required boolean checks are `deployment`,
`modelInference`, `agentInvocation`, `applicationChat`, and `negativeCase`.
Add `grounding` and `tools` when requirements include those capabilities.
For a new pattern-scoped reference, add `agenticWorkflow` after real coordination-specific
success and failure tests pass; retain the exact traces/results in the deployment summary.
All supplied checks must be true. Record exact commands/results in the deployment
summary; this small JSON file is an evidence index, not a substitute for tests.

Create a review snapshot using:

```powershell
python scripts\hack_workflow.py snapshot generated-scenarios\{project}
```

Present the user with the story, diagrams, live application URL, acceptance
results, limitations, estimated cost and demo guide. Explicitly ask whether this
is workable and usable as the hack scenario. Offer approve, revise, or stop.
**Stop and wait.** Never infer approval from silence, initial intent to build a
hack, a deployment confirmation, or a request to repair the app.

## Approval record and invalidation

### Explicit historical deployment attestation

When the user explicitly reports that the full reference was deployed and worked, but the resources
were deleted and the one-off subscription/endpoint/logs cannot be recovered, accept a distinct
historical user attestation. Never ask for redeployment solely to keep resources running.
This exception requires the actual user statement, not an agent assumption or "assume it works".
Record it using:

```powershell
python scripts\hack_workflow.py attest-history generated-scenarios\{project} `
  --message "Exact user confirmation of successful deployment and complete scenario behavior" `
  --unavailable-reason "User-provided reason the historical endpoint and logs cannot be recovered"
```

The helper writes `scenario-validation.json` with `evidenceType: "historical-user-attestation"`,
`status: "user-attested"`, null URL/test time and an empty checks object. Preserve the statement,
capture time, deleted-resource state and missing evidence. Do not invent per-check results, former
URLs, deployment time, quota, targets or an independently observed success. Do not overwrite existing
runtime evidence with this fallback. Update the deployment summary to distinguish prior local checks,
user-reported deployment and currently deleted resources. Future permanent-subscription deployments
still require retained exact targets, actual logs, runtime acceptance and ordinary consent gates.

Create a fingerprinted review snapshot as normal. Separate explicit suitability approval is still
required; historical attestation alone does not authorize composition. With the user's actual approval
recorded against that snapshot, `check-approval` permits local composition from the attested reference.
Carry the evidence limitation into private coach/release notes; do not present a running demo URL.
This permits authoring, not future deployment, event rollout, publication or runtime certification.

After the user explicitly approves the presented scenario and its reviewed
fingerprint is unchanged, the interactive owner or portal backend records:

```powershell
python scripts\hack_workflow.py approve generated-scenarios\{project} `
  --message "Exact affirmative user response to the scenario review"
```

The helper records the response, timestamp and reference fingerprint in
`workflow-state.json`. Do not call `approve` on behalf of the user. This is an
audit guard against accidental progression, not an authentication boundary.
Keep operational state out of public learner packages.

The scenario process must not start composition automatically. Record the user's actual suitability response
in VS Code against the reviewed fingerprint. The portal's HackCreator handoff checks approval but never records
or invents it. Open the separate composition context only after approval.

If the user requests revision or stops the scenario, record that response with
the `reject` command and `--message`. This clears any previous authorization;
resume in Phase A, not authoring.

Before either composition mode:

```powershell
python scripts\hack_workflow.py check-approval generated-scenarios\{project}
```

Missing, rejected, unreviewed, or stale evidence blocks authoring. A change to
the story, architecture, templates, application, runtime fixtures, validation,
or walkthrough invalidates the snapshot. Revalidate, present a new review, and
obtain new approval. Do not edit the approved reference while deriving packages.

## Phase B: derive the hack

Only after `check-approval` passes:

1. The composition context `plan` creates `08-hack-package-contract.md` and `nextsteps.MD`.
   Reuse reference data and tests instead of regenerating them. Record which
   runtime resources are preprovided, learner-built, or coach-only, and why.
1. The composition context `package` creates `packages/coach/`, `packages/participant/`,
   `packages/hack/`, and `packages/coach-guide/`, plus the event manifest.
1. Build/lint both IaC projects, test the starter's intended incomplete state,
   and run the Skillable validator. The approved reference tests remain the
   complete-solution baseline.
1. Present **packages validated; event not deployed** and stop.

The coach is a sanitized deployable copy of the approved solution, not a second
independently designed implementation. Do not redeploy an identical copy merely
to finish authoring. State clearly that a new coach environment has not been
deployed yet.

Reference validation targets are not hack/event defaults. Parameterize region and any service-specific
locations in coach and participant IaC; require explicit destination azd environment values.
Do not copy the reference `.azure`, region parameter values, subscription/tenant IDs, capacity evidence or
authorization into packages. Retain required region colocation constraints and document them without pinning
the validation region. Event subscriptions can differ from each other and from the reference subscription.
Validate the complete resource/model/SKU set afresh against each destination subscription and chosen region;
never reuse reference quota or regional-access results as event readiness.

The participant starter is the **scenario-specific minimum**: isolation/access
and only indispensable synthetic fixtures or prerequisites that cannot fit the
learning budget. It need not contain an app, Search, Cosmos, networking, or other
supporting services just because the reference does. No prebuilt Foundry
resources or completed agent implementation. Empty starter resource groups are
valid if their setup/access is documented and validated.

Require a private reference-to-starter resource matrix with each omission,
learner decision, challenge dependency, and checkpoint. Learners determine the
components/resources and build the solution; public milestones describe
observable outcomes and constraints, not a pasted reference architecture.
Portal-first and collapsed SDK routes are options and progressive hints, not
mandatory click-by-click solution disclosure. Keep complete answers in Finale.

## Phase C: optional event deployment

Creating a manifest or specifying a future team count is not deployment consent.
Only a **separate explicit event-deployment request** authorizes this phase.
The scenario orchestrator executes the deployment and multi-team skills directly
in its own context and confirms actual targets after what-if.
Validate coach once and each requested team independently. Report rollout
completion separately from scenario and package completion.

`planned` team statuses and null app URLs are valid during authoring.
After requested rollout, all deployments must pass; URLs are required only for
packages that actually include a deployed application.

## Resumption and execution budget

- No state file on a legacy project means **unreviewed**, even if packages exist.
  Reuse its reference artifacts, prove live behavior, then seek approval.
- Reject changes: stay in Phase A. Approval: enter Phase B. Package validation:
  stop. Explicit rollout: enter Phase C. Never resume from filenames alone.
- Research each open technical question once and persist evidence in its owning
  artifact. Refresh subscription capacity before deployment and after capacity
  failures; do not repeat unchanged templates/docs at every stage.
- Each of the two agents performs its phase directly using skills. No nested
  conductor, specialist subagents, agent fanout or automatic cross-agent handoff.
  Independent local commands may run in parallel only when safe.
- Report completed artifacts/checks at each phase change. Record step start/end,
  tool/deployment waits, failures and retries in the scenario README or summary.
- At 15 minutes without a persisted result, report the blocker and next action;
  this is a progress checkpoint, not a deadline or permission to skip validation.
- Diagnose failures before retry. Never change subscription, region, model,
  security constraints or resource ownership silently.
