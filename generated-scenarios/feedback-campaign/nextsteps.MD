# Supporting-artifact inventory

## Scenario context

Adatum Corporation, Media & Communications, canonical slug media-communications.
Exact businessUnits: `["sales", "marketing"]`. Marketing campaign/product review hands
subscriber recovery to Sales. No Generic or additional unit is selected.
Company provenance: fictitious_company_names.csv line 2, domain adatum.com,
derived slug adatum-corporation. People provenance: fictitious_people_names.csv
lines 2–7, first six data records (first Eesha entry).
Airi Ilves/subscriber1, Hasan Ibrahimov/subscriber2, Nemanja Milatovic/subscriber3;
Nino Kapanadze/campaign operator, Petra Bartosova/Product Manager,
Eesha Chatterjee/Conflict Resolution Specialist. Contacts use example.test only.

## Delivery rules

Keep approved reference bytes unchanged. Copy only allowlisted source and fixtures.
No credentials, deployment state, operational receipts or reference endpoint are packaged.
Every runtime dependency below is deployment-critical and locally packaged, not azure-verified.
No optional release-enrichment artifact is required for this event.

## Artifact inventory

| ID | Artifact | Purpose | Visibility | Classification | Status |
| --- | --- | --- | --- | --- | --- |
| ART-001 | Campaign posts | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |
| ART-002 | Grounding policy | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |
| ART-003 | Prompt instructions | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |
| ART-004 | Destination installation | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |
| ART-005 | Starter isolation and status | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |
| ART-006 | Incomplete integration contract | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |
| ART-007 | Access guides | Runtime/challenge input | Scoped | `deployment-critical` | `packaged` |

## Detailed artifact specifications

### ART-001 — Campaign posts

- **Purpose and challenge use:** Campaign posts; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `posts.json`
- **Repository destinations:**
  - `packages/coach/src/FeedbackCampaign.Web/SeedData/posts.json`
  - `packages/participant/fixtures/posts.json`
  - `packages/hack/Allfiles/posts.json`
  - `packages/coach-guide/Allfiles/posts.json`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** JSON UTF-8 array; 10 records.
- **Target Azure service and destination:** Local fixture; explicit authenticated intake into posts queue;
  SHA256(sourceId) case key.
- **Schema or document structure:** sourceId, posterName, contact, campaign, subject, body: required strings; unique
  stable sourceId.
- **Required fields or sections:** sourceId, posterName, contact, campaign, subject, body: required strings; unique
  stable sourceId.
- **Expected quantity or size:** JSON UTF-8 array; 10 records; exact file list above, no hidden dependency.
- **Synthetic content requirements:** Reuse exact reference bytes. Synthetic catalog people; example.test contacts only.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** Operator submits selected posts; app publish carries SeedData. No automatic
  external transmission.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

### ART-002 — Grounding policy

- **Purpose and challenge use:** Grounding policy; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `campaign-policy.md`
- **Repository destinations:**
  - `packages/coach/src/FeedbackCampaign.Web/Policy/campaign-policy.md`
  - `packages/participant/fixtures/campaign-policy.md`
  - `packages/hack/Allfiles/campaign-policy.md`
  - `packages/coach-guide/Allfiles/campaign-policy.md`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** Markdown UTF-8 document; one policy.
- **Target Azure service and destination:** Prompt context on every native agent invocation, with source and exact
  rule snapshot.
- **Schema or document structure:** campaign-policy-v1 heading, offers, Marketing/Sales ownership, no refund
  promises, grounding boundaries.
- **Required fields or sections:** campaign-policy-v1 heading, offers, Marketing/Sales ownership, no refund
  promises, grounding boundaries.
- **Expected quantity or size:** Markdown UTF-8 document; one policy; exact file list above, no hidden dependency.
- **Synthetic content requirements:** Reuse unchanged policy bytes; Adatum Corporation CSV first data record.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** csproj copies Policy into build/publish; application supplies it per inference;
  no Search ingestion.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

### ART-003 — Prompt instructions

- **Purpose and challenge use:** Prompt instructions; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `agent-instructions.txt`
- **Repository destinations:**
  - `packages/coach/src/FeedbackCampaign.Web/Policy/agent-instructions.txt`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** UTF-8 text; one bounded instruction document.
- **Target Azure service and destination:** Foundry campaign-listener prompt-agent version.
- **Schema or document structure:** Interpretation/draft contract, normalized vectors, untrusted text, no
  self-authorization.
- **Required fields or sections:** Interpretation/draft contract, normalized vectors, untrusted text, no
  self-authorization.
- **Expected quantity or size:** UTF-8 text; one bounded instruction document; exact file list above, no hidden
  dependency.
- **Synthetic content requirements:** Reuse exact approved runtime instructions; no new pattern or native tool.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** initialize_foundry.py postdeploy compares definition, creates only changed
  version and pins returned version.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

### ART-004 — Destination installation

- **Purpose and challenge use:** Destination installation; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `cloud_io.py`, `setup_lab_accounts.py`, `initialize_foundry.py`, `azure.yaml`
- **Repository destinations:**
  - `packages/coach/scripts/cloud_io.py`
  - `packages/coach/scripts/setup_lab_accounts.py`
  - `packages/coach/scripts/initialize_foundry.py`
  - `packages/coach/azure.yaml`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** Python UTF-8 modules and YAML hooks; four files.
- **Target Azure service and destination:** Destination project, campaignstate rules/config/accounts partitions,
  protected private access files.
- **Schema or document structure:** Explicit destination guard; private account hash setup; idempotent agent/rule
  initialization.
- **Required fields or sections:** Explicit destination guard; private account hash setup; idempotent agent/rule
  initialization.
- **Expected quantity or size:** Python UTF-8 modules and YAML hooks; four files; exact file list above, no hidden
  dependency.
- **Synthetic content requirements:** Copy active hooks; parameterize source target binding; no access values or
  receipts copied.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** azd preprovision prepare, postprovision install, postdeploy initialize;
  preserve promoted rules on rerun.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

### ART-005 — Starter isolation and status

- **Purpose and challenge use:** Starter isolation and status; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `main.bicep`, `main.parameters.json`, `azure.yaml`, `cloud_io.py`, `verify_destination.py`,
  `status.py`
- **Repository destinations:**
  - `packages/participant/infra/main.bicep`
  - `packages/participant/infra/main.parameters.json`
  - `packages/participant/azure.yaml`
  - `packages/participant/scripts/cloud_io.py`
  - `packages/participant/scripts/verify_destination.py`
  - `packages/participant/scripts/status.py`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** Bicep/JSON/YAML/Python; six files.
- **Target Azure service and destination:** Isolated participant resource group only; no service fixture load hook.
- **Schema or document structure:** Environment, location required; tags only; guard requires explicit
  subscription/tenant/group.
- **Required fields or sections:** Environment, location required; tags only; guard requires explicit
  subscription/tenant/group.
- **Expected quantity or size:** Bicep/JSON/YAML/Python; six files; exact file list above, no hidden dependency.
- **Synthetic content requirements:** Locally authored minimum; no completed runtime logic, Foundry or source target
  values.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** Preprovision checks explicit destination; status runs offline and reports
  not-configured.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

### ART-006 — Incomplete integration contract

- **Purpose and challenge use:** Incomplete integration contract; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `integration.json`
- **Repository destinations:**
  - `packages/participant/contracts/integration.json`
  - `packages/hack/Allfiles/integration.json`
  - `packages/coach-guide/Allfiles/integration.json`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** JSON object UTF-8; one contract.
- **Target Azure service and destination:** Learner-selected adapter; no installed action or Foundry tool.
- **Schema or document structure:** Industry, exact businessUnits, null endpoints/agent, interpretation/action
  request/evidence fields.
- **Required fields or sections:** Industry, exact businessUnits, null endpoints/agent, interpretation/action
  request/evidence fields.
- **Expected quantity or size:** JSON object UTF-8; one contract; exact file list above, no hidden dependency.
- **Synthetic content requirements:** Unconfigured schema, not an implementation or successful receipt.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** Learners implement the bounded contract in C1–C3; never provision an omitted
  service in starter hooks.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

### ART-007 — Access guides

- **Purpose and challenge use:** Access guides; C0–C4 as listed in the package contract.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `participant-access.md`, `coach-access.md`
- **Repository destinations:**
  - `packages/coach/docs/participant-access.md`
  - `packages/coach/docs/coach-access.md`
  - `packages/participant/docs/participant-access.md`
  - `packages/hack/Allfiles/participant-access.md`
  - `packages/coach-guide/Allfiles/participant-access.md`
- **Package visibility:** Source package only unless explicitly placed in public Allfiles.
- **Artifact type and format:** Markdown UTF-8; two logical role guides.
- **Target Azure service and destination:** Private destination account setup only; guides are not Azure identities.
- **Schema or document structure:** Participant usernames/roles, placeholders, separate coach delivery and runtime
  MI distinction.
- **Required fields or sections:** Participant usernames/roles, placeholders, separate coach delivery and runtime MI
  distinction.
- **Expected quantity or size:** Markdown UTF-8; two logical role guides; exact file list above, no hidden dependency.
- **Synthetic content requirements:** No real credential values. Coach role never included in participant material.
- **Generation method and dependencies:** Reference reuse or explicit local minimum; Python 3 and .NET 10 as applicable.
- **Upload or installation method:** Fresh destination passwords generated during authorized installation; privately
  delivered separately.
- **Identity and access:** Managed identity for workload; separate scoped installer data/control roles.
- **Local validation:** Package-boundary/hash checks, Bicep build/lint, app and script tests as applicable.
- **Azure validation:** Pending separate authorized rollout; verify loaded content, real access and idempotent rerun.
- **Acceptance criteria:** All listed destinations exist, local checks pass and reference approval remains unchanged.
- **Owner and creation priority:** Composition owner; required before package release, destination installer at rollout.

## Creation and review sequence

Verify approval and exact industry support, copy safe source, strip target state,
package fixtures/hooks, validate locally, recheck approval and record package-bound receipt.
No new names, datasets or architecture replace the approved implementation.

## Package and GitHub publication

Four self-contained roots: coach, participant, hack and coach-guide.
Release ZIPs remain separate; public learner output never includes completed coach source or Finale.
Learner challenge, resources, Allfiles and media copies in coach-guide are hash-identical.
GitHub publication is not authorized and has not been performed.

## Azure load and installation plan

Coach hooks generate destination-only credentials, install hashes in campaignstate,
initialize campaign-listener and insert rules/v1 plus config/active only if absent.
State entities have PartitionKey, RowKey and string Payload; Timestamp is server-managed.
Cases use SHA256(sourceId) and ETag transitions; immutable rule versions retain author/reason.
No key contains slash, backslash, hash, question mark or controls.
Runtime reads with MI; installer has separate scoped data roles.
Participant preprovision only checks destination; no nonexistent service ingestion is wired.
Learner-installed components and policy invocation belong to the matching challenge.

## Deployment and test gate

`azd up` is mandatory for later destination acceptance of `packages/coach/`
and `packages/participant/`; neither is executed during this local composition.
Run fresh destination region/model/SKU/quota checks and exact what-if after separate rollout consent.
No reference region, shared default, tenant, subscription or runtime receipt proves event readiness.
Verify actual grounding, queue acceptance, both edited human replies, restart, wrong-role,
CSRF, stale/duplicate denials and promotion/rollback in the new destination.
Live provider outage/DLQ injection remains unrun in the reference; local failure/retry tests exist.

## Completion tracking

All seven deployment-critical groups are packaged and locally tested.
Exact command results belong in packages/validation/local-checks.json.
Deployment-specific loads, identities, credentials and runtime acceptance remain pending rollout.
No artifact is marked azure-verified based on local tests.
