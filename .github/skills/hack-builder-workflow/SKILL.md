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

The lightweight LOCAL web portal collects the prompt, a validated `projectSlug`,
industry, `businessUnits`, selected services and Well-Architected Framework priorities. Its local
authenticated backend launches actual Copilot CLI jobs, not simulated results.
Use `generated-scenarios\{projectSlug}` without silently changing the slug.

The backend uses `--agent az-01-conductor --prompt <text>` for scenario jobs and
the stable name `HackCreator Agent` for separately approved composition jobs.
The CLI supports `--output-format text/json`, `--allow-all-tools` and
`--no-ask-user`. These flags are not user consent and do not establish a sandbox.
Tool execution requires explicit portal permission. Initial jobs are local
preparation only by instruction: prepare reference code and what-if commands/
target previews, then stop before Azure operations unless explicitly authorized.
A separate user follow-up authorizes exact Azure targets; review actual what-if
before deployment. Service selections alone never authorize deployment.

The portal is the normal decision surface and scenario-level progress dashboard, not a CLI transcript.
Persist normalized intake, delegated preferences, resolved decisions and execution attempts in the
backend project store. Workers use `scripts\portal_workflow.py read` and revision-checked `report`
events; environment variables identify their project and writer lease. Status refresh is read-only.
Never use CLI exit success, existing files or guessed log parsing as stage-completion evidence.
Do not edit a portal-owned scenario concurrently from VS Code; the shared writer contract must be honored.

For local-only work, account, subscription quota and budget are deferred deployment concerns.
Use current public evidence for provisional region/model choices and label unresolved live checks.
Complete requirements/architecture, then obtain a concise portal design confirmation before implementation.
This design checkpoint is not deployed-scenario suitability approval. Reuse answered choices and
continue backend implementation without unnecessary handoffs. Required service substitution,
material security exceptions or unresolved business requirements need explicit structured decisions.

Cloud preparation and deployment use separate portal decisions with exact targets.
Preparation permission precedes Azure queries/what-if. Deployment consent follows actual what-if,
estimated cost and target review. Free-text continuation never grants cloud authorization.

In noninteractive jobs, missing decisions, authentication or permission mean
persist progress, report **decision required** with the exact next action, and
stop. Do not guess consent because an interactive question tool is unavailable.
This customization work itself authorizes no Azure operations.

Industry intake comes from repository `microsoft_industry_verticals.csv`.
Skillable currently supports six slugs in its own authoring catalog:
`financial-services`, `healthcare`, `manufacturing`, `retail`, `energy-oil-gas`
and `government-public-sector`. Do not silently map unsupported intake industries.
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

The scenario process must not start composition automatically. The portal's
approval action records the actual user response against the reviewed fingerprint,
runs `check-approval`, and only then launches a separate composition job. It never
auto-approves from job completion, selected services, or a deployment confirmation.

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
