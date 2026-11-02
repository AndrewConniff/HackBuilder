<!-- markdownlint-disable MD033 -->

# Next steps — Fourth Coffee sales readiness and daily close

Use this scenario-level file to plan, create, package, upload, and validate every
supporting artifact. Keep it at `generated-scenarios/coffee-shop/nextsteps.MD`.

## Scenario context

Scenario: Fourth Coffee sales readiness and daily close.
Industry: Hospitality & Travel; slug `hospitality-travel`.
Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.
Owner: composition author. Updated 2026-10-25.
Company identity: Fourth Coffee, fourthcoffee.com, fourth-coffee; company CSV data record 14.
People CSV uses exact FullName values in data records 1–4; mapping is fixed, not regenerated.
Malformed company records 7, 11, 25 and 33 are rejected and left unchanged.

## Delivery rules

Classify every artifact before work begins:

- `deployment-critical` supports a deployed application path or an acceptance
  test. It must reach `packaged` before deployment handoff.
- `release-enrichment` improves the lab or release but is not required for the
  deployed acceptance path. It may remain `planned` after deployment testing.

Use one of these statuses:

| Status | Meaning |
| --- | --- |
| `planned` | The detailed specification exists, but the file does not. |
| `created` | The file exists in a working location. |
| `validated` | Local schema, safety, and content checks pass. |
| `packaged` | Every listed repository destination exists. |
| `azure-verified` | Azure load or installation and its acceptance check pass. |

> [!IMPORTANT]
> A missing `deployment-critical` artifact blocks package handoff. It does not
> authorize a dry run or omission of deployment testing.

## Artifact inventory

| ID | Proposed file or file set | Challenge use | Azure target | Classification | Status |
| --- | --- | --- | --- | --- | --- |
| ART-001 | stores.json | 0–4 | See detail | `deployment-critical` | `packaged` |
| ART-002 | workflow-contract.md | 0–4 | See detail | `deployment-critical` | `packaged` |
| ART-003 | evaluation-cases.json | 0–4 | See detail | `deployment-critical` | `packaged` |
| ART-004 | stock.md, margin.md, close.md | 0–4 | See detail | `deployment-critical` | `packaged` |
| ART-005 | Installation file set 5 | 0–4 | See detail | `deployment-critical` | `packaged` |

## Detailed artifact specifications

### ART-001 — File set 1

- **Purpose and challenge use:** Exact reference grounding, scoped access and negative fixture for challenges 2–4.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** stores.json
- **Repository destinations:** `packages/coach/src/CoffeeShop.Web/SeedData/stores.json`,
  `packages/participant/data/stores.json`, `packages/hack/Allfiles/stores.json`,
  `packages/coach-guide/Allfiles/stores.json`
- **Package visibility:** Learner-safe except the explicitly private coach installation and instruction files.
- **Synthetic content requirements:** Fourth Coffee only; fixed synthetic fixture date; no real customers, contact
  details or credentials.
- **Business scope coverage:** Hospitality & Travel; businessUnits ["sales"]; reviewed finance handoff only.
- **Owner and creation priority:** Composition author; P0 before package handoff.
- **Artifact type and format:** UTF-8 JSON array of StoreSnapshot objects.
- **Target Azure service and destination:** Coach Table CoffeeBackOffice; PartitionKey Store.StoreId; RowKey
  snapshot; Payload JSON string.
- **Schema or document structure:** Three objects: Store {Id,StoreId,Name,Area,Manager}, Version, Stock array and
  Ledger object.
- **Required fields or sections:** StoreId 001/002/003, Version string; Stock Id/Sku/Unit/OnHand/Target/UnitCost;
  Ledger Id/Date/NetSales/Cogs/Labor/Occupancy/Waste/Complete. Decimal arithmetic; date YYYY-MM-DD.
- **Expected quantity or size:** 3 stores, 12 stock rows, 3 daily ledgers; approximately 2.6 KB.
- **Generation method and dependencies:** Byte-copy approved SeedData/stores.json. Company CSV data record 14;
  people data records 1/2/4 map to 001/002/003; record 3 is north-area manager. Preserve exact FullName column.
- **Upload or installation method:** Coach Bootstrap via postprovision Initialize-Scenario.ps1 adds snapshots;
  existing 409 is retained, not overwritten. Participant loads only through learner-chosen challenge 2 component.
- **Identity and access:** Coach installer AzureCliCredential and Table Data Contributor; runtime system MI. Server
  store grants filter all reads; no keys or user-supplied scope.
- **Local validation:** Boundary check compares all four copies; verifies schema/counts/catalog mapping.
- **Azure validation:** Future authorized rollout: 3 snapshot entities, point read 001/snapshot and 001 partition
  query; rerun keeps stock; store 001 request for 002 denied. Timestamp server-managed, never seeded.
- **Acceptance criteria:** Twelve stock records and incomplete 003 ledger retained; keys contain no forbidden key
  characters.

### ART-002 — File set 2

- **Purpose and challenge use:** Challenge 3 read/draft/approve behavior and action safety constraints.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** workflow-contract.md
- **Repository destinations:** `packages/participant/data/workflow-contract.md`,
  `packages/hack/Allfiles/workflow-contract.md`, `packages/coach-guide/Allfiles/workflow-contract.md`
- **Package visibility:** Learner-safe except the explicitly private coach installation and instruction files.
- **Synthetic content requirements:** Fourth Coffee only; fixed synthetic fixture date; no real customers, contact
  details or credentials.
- **Business scope coverage:** Hospitality & Travel; businessUnits ["sales"]; reviewed finance handoff only.
- **Owner and creation priority:** Composition author; P0 before package handoff.
- **Artifact type and format:** UTF-8 Markdown integration contract.
- **Target Azure service and destination:** Learner-chosen authenticated application boundary; no starter service.
- **Schema or document structure:** Scope, evidence, internal order, failure and integration sections.
- **Required fields or sections:** storeId, snapshotVersion, source IDs, draftId, idempotencyKey, approvedBy,
  approvedAt and ETag.
- **Expected quantity or size:** One document, approximately 2 KB.
- **Generation method and dependencies:** Distill approved domain/API rules without exporting implementation.
- **Upload or installation method:** Local download; learner implements adapter in challenge 3. No azd load hook.
- **Identity and access:** Authenticated local sales session; backend MI or DefaultAzureCredential.
- **Local validation:** Parity and sensitive-data checks; no completed implementation.
- **Azure validation:** Future learner test: deny cross-store, repeat same approval, reject stale snapshot.
- **Acceptance criteria:** No autonomous spending, supplier transmission or finance ledger posting.

### ART-003 — File set 3

- **Purpose and challenge use:** Challenge 4 repeatable positive, denied, failure, stale and replay probes.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** evaluation-cases.json
- **Repository destinations:** `packages/participant/data/evaluation-cases.json`,
  `packages/hack/Allfiles/evaluation-cases.json`, `packages/coach-guide/Allfiles/evaluation-cases.json`
- **Package visibility:** Learner-safe except the explicitly private coach installation and instruction files.
- **Synthetic content requirements:** Fourth Coffee only; fixed synthetic fixture date; no real customers, contact
  details or credentials.
- **Business scope coverage:** Hospitality & Travel; businessUnits ["sales"]; reviewed finance handoff only.
- **Owner and creation priority:** Composition author; P0 before package handoff.
- **Artifact type and format:** UTF-8 JSON object with industry, businessUnits and cases array.
- **Target Azure service and destination:** Local learner evaluation runner; no starter Azure target.
- **Schema or document structure:** Each case has id, actor, stores, prompt and assertion.
- **Required fields or sections:** Stable case IDs, string actor, store ID array, prompt and observable assertion.
- **Expected quantity or size:** 6 cases; approximately 2 KB.
- **Generation method and dependencies:** Derive approved acceptance prompts and failure contract; no answer code.
- **Upload or installation method:** Local download; run against selected implementation, never auto-load.
- **Identity and access:** Use isolated synthetic accounts; keep passwords outside files and evidence.
- **Local validation:** JSON parse, six IDs unique, exact industry/units, byte parity.
- **Azure validation:** Future event: record real receipts, denied scope and dependency failure before success.
- **Acceptance criteria:** Pass/fail evidence distinguishes test doubles from real model/agent calls.

### ART-004 — File set 4

- **Purpose and challenge use:** Private full-solution baseline for all five challenges; not public answers.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** stock.md, margin.md, close.md
- **Repository destinations:** `packages/coach/src/CoffeeShop.Web/Agents/stock.md`,
  `packages/coach/src/CoffeeShop.Web/Agents/margin.md`, `packages/coach/src/CoffeeShop.Web/Agents/close.md`
- **Package visibility:** Private deployable coach only.
- **Synthetic content requirements:** Fourth Coffee only; fixed synthetic fixture date; no real customers, contact
  details or credentials.
- **Business scope coverage:** Hospitality & Travel; businessUnits ["sales"]; reviewed finance handoff only.
- **Owner and creation priority:** Composition author; P0 before package handoff.
- **Artifact type and format:** Three UTF-8 Markdown instruction files.
- **Target Azure service and destination:** Three persisted prompt agents in destination Foundry project.
- **Schema or document structure:** Approved role instructions, scoped evidence and advisory-output constraints.
- **Required fields or sections:** Reference instruction contents retained byte-for-byte.
- **Expected quantity or size:** Three small text files, each below 4 KB.
- **Generation method and dependencies:** Byte-copy reference Agents directory; pinned Foundry SDK.
- **Upload or installation method:** Bootstrap postprovision: reuse owner/digest-matching version or create;
  configure endpoint selector.
- **Identity and access:** Installer Foundry User; runtime project-scoped Agent Consumer via agent endpoint.
- **Local validation:** Coach build/tests; digest equality against approved instruction files.
- **Azure validation:** Future event: three real version/response receipts and failing-branch negative.
- **Acceptance criteria:** No project developer Responses route for runtime Consumer; no write tool.

### ART-005 — File set 5

- **Purpose and challenge use:** Deployable coach initialization; local guards block unreviewed future deployment.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** Assert-DeploymentScope.ps1, Initialize-Scenario.ps1, Build-Assets.ps1, Bootstrap.cs
- **Repository destinations:** `packages/coach/scripts/Assert-DeploymentScope.ps1`,
  `packages/coach/scripts/Initialize-Scenario.ps1`, `packages/coach/scripts/Build-Assets.ps1`,
  `packages/coach/src/CoffeeShop.Web/Services/Bootstrap.cs`
- **Package visibility:** Private coach only.
- **Synthetic content requirements:** Fourth Coffee only; fixed synthetic fixture date; no real customers, contact
  details or credentials.
- **Business scope coverage:** Hospitality & Travel; businessUnits ["sales"]; reviewed finance handoff only.
- **Owner and creation priority:** Composition author; P0 before package handoff.
- **Artifact type and format:** Three PowerShell scripts with native-command exit checks and one C# initializer.
- **Target Azure service and destination:** Destination ARM/web settings, Table fixtures and Foundry agents.
- **Schema or document structure:** Preprovision target guard; postprovision bootstrap; prepackage pinned assets.
- **Required fields or sections:** Separate destination consent and exact environment/group/subscription/tenant;
  process-only passwords.
- **Expected quantity or size:** Three scripts plus one C# initializer, approximately 10 KB total.
- **Generation method and dependencies:** Sanitize only reference deployment target guard; retain bootstrap
  semantics, .NET, npm, azd and CLI.
- **Upload or installation method:** azure.yaml preprovision/postprovision/prepackage hooks. Postprovision validates
  target again.
- **Identity and access:** Existing authorized installer; no interactive login, defaults change or directory writes.
- **Local validation:** Parse all scripts; execute no-consent and wrong-target guard negatives before CLI calls.
- **Azure validation:** Future event: fresh what-if, azd up, idempotent rerun and complete authenticated acceptance.
- **Acceptance criteria:** No reference destination is accepted or inherited; failures stop publication.


## Creation and review sequence

1. Reuse approved fixtures and catalog mapping.
1. Sanitize only package copies, preserving the reference.
1. Parse schemas, compare copies and run focused tests.
1. Package all critical files; verify public/private boundaries and separate archives.

## Package and GitHub publication

All four roots remain local. Learner source and starter are public-safe; coach solution and guide are private.
No repository, branch, license change, push, publication or event rollout is requested.
Select publication destinations and obtain separate permission before publishing.

## Azure load and installation plan

Only the coach has ingestion hooks: postprovision initializes the CoffeeBackOffice table and agents.
Prepackage restores pinned browser assets; preprovision asserts separately reviewed destination scope.
No participant ingestion hook exists because no storage or app is preprovided.
Learners load local fixtures only into components they choose. See per-artifact identity and checks above.
Table Timestamp is server-managed; snapshot keys are safe fixed IDs. Existing stock is never overwritten.
A future event requires fresh destination regional/model/SKU/quota and role checks, not reference evidence.

## Deployment and test gate

Package authoring ends with local validation and does not authorize event rollout.
After a separate explicit event-deployment request, `azd up` is mandatory for
`packages/coach/` and every manifest entry using `packages/participant/`.
Planned follow-up work never replaces acceptance for an authorized deployment.

Before deployment handoff:

- [ ] Every `deployment-critical` artifact has status `packaged`.
- [ ] Every listed destination for a packaged artifact exists.
- [ ] Load scripts are idempotent and fail on schema or count mismatches.
- [ ] Coach and participant Bicep build and lint checks pass.
- [ ] Application and focused integration tests pass locally.

During and after separately requested event deployment:

- [ ] Run the configured data load and installation hooks as part of `azd up`.
- [ ] Verify the coach application uses the real supporting artifacts.
- [ ] Verify each participant environment receives its required synthetic data.
- [ ] Run every artifact's Azure validation and application acceptance check.
- [ ] Update successful artifact statuses to `azure-verified`.
- [ ] Record failures and remediation without marking deployment as skipped.

If a critical artifact or deployment fails, fix and retry or ask the user for a
decision. Do not silently remove the artifact, bypass the test, or claim success.

## Completion tracking

Inventory state: packaged. Local commands and outputs: `packages/validation/local-checks.json`.
No artifact is azure-verified by composition. Azure installation, publication and rollout remain unrequested.
The receipt is recorded only after real local validation, not merely because files exist.
