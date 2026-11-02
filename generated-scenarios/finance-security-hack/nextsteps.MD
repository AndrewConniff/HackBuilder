# Next steps — Adatum brokerage education agent

## Scenario context

| Property | Value |
| --- | --- |
| Scenario | Adatum brokerage education agent |
| Industry | Financial Services |
| Industry slug | `financial-services` |
| Last updated | 2026-10-22 |
| Inventory owner | Composition owner |
| Package root | `generated-scenarios/finance-security-hack/packages/` |

## Delivery rules

All runtime/challenge dependencies below are `deployment-critical` and locally `packaged`.
No entry is `azure-verified`. No optional media, person data or business database seed is needed.
Adatum Corporation / adatum.com / adatum-corporation is company CSV record 1.
No people are introduced, so no person mapping or people-bearing artifact is required.
Private architecture and deployment answers stay in the private guide, not this delivery inventory.

## Artifact inventory

| ID | Proposed file or file set | Challenge use | Azure target | Classification | Status |
| --- | --- | --- | --- | --- | --- |
| ART-001 | Approved FAQ | Core support | See detail | `deployment-critical` | `packaged` |
| ART-002 | Private agent instructions | Core support | See detail | `deployment-critical` | `packaged` |
| ART-003 | Guarded operator scripts | Core support | See detail | `deployment-critical` | `packaged` |
| ART-004 | Evaluation prompts | Core support | See detail | `deployment-critical` | `packaged` |
| ART-005 | Interface evidence contract | Core support | See detail | `deployment-critical` | `packaged` |
| ART-006 | Private reference diagrams | Core support | See detail | `deployment-critical` | `packaged` |

## Detailed artifact specifications

### ART-001 — Approved FAQ

- **Purpose and challenge use:** C2 approved brokerage grounding and fee/unsupported-question evaluation.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `brokerage-faq.md`
- **Repository destinations:** `packages/coach/data/brokerage-faq.md`, `packages/participant/data/brokerage-faq.md`,
  `packages/hack/Allfiles/brokerage-faq.md`, `packages/coach-guide/Allfiles/brokerage-faq.md`
- **Package visibility:** Public learner-safe and deployable coach fixture.
- **Artifact type and format:** UTF-8 Markdown, English source document.
- **Target Azure service and destination:** Private Storage knowledge container, brokerage-faq.md blob; no learner
  starter cloud target.
- **Schema or document structure:** Title, synthetic disclaimer, version and twelve FAQ-01 through FAQ-12 topic
  headings.
- **Required fields or sections:** Market/limit orders, risk, brokerage role, fees, settlement, volatility, margin,
  privacy, advice, unknowns, incidents.
- **Expected quantity or size:** One file, twelve topics, 2914 bytes.
- **Synthetic content requirements:** Exact approved synthetic facts; hypothetical fee is 5 training units, not
  money; no person records.
- **Generation method and dependencies:** Byte-for-byte reference reuse; company catalog record 1 Adatum Corporation
  / adatum.com.
- **Upload or installation method:** Coach guarded Initialize-Reference.ps1 invokes installer upload overwrite and
  exact readback; no automatic azd hook.
- **Identity and access:** Installer Blob Contributor; runtime container-scoped Blob Reader via MI. Participant
  chooses authorized loader in C2.
- **Local validation:** Byte parity at all four destinations, unique FAQ IDs and deterministic coach fixture tests.
- **Azure validation:** Future authorized private readback equals file, correct fee citation, unsupported question
  and denied identity.
- **Acceptance criteria:** All twelve topics installed once per blob path; rerun overwrites the same source and
  verifies exact bytes.
- **Owner and creation priority:** Composition owner P0; event operator owns future installation.

### ART-002 — Private agent instructions

- **Purpose and challenge use:** C1 coach agent installation and education-only safety baseline.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `agent-instructions.txt`
- **Repository destinations:** `packages/coach/data/agent-instructions.txt`
- **Package visibility:** Private deployable coach only.
- **Artifact type and format:** UTF-8 plain text prompt instructions.
- **Target Azure service and destination:** Foundry versioned brokerage-educator agent definition.
- **Schema or document structure:** Education, approved source citation and refusal instructions.
- **Required fields or sections:** No trading, advice, account access or invented facts.
- **Expected quantity or size:** One file, 930 bytes.
- **Synthetic content requirements:** Synthetic brokerage only; no people, real accounts or tool schemas.
- **Generation method and dependencies:** Exact approved file, not regenerated from generic tool templates.
- **Upload or installation method:** Explicit guarded initializer creates/reuses identical model-and-instructions
  version; no automatic hook.
- **Identity and access:** Installer project Foundry User; runtime Agent Consumer only, target definition resolved
  before deployment.
- **Local validation:** Byte parity, app fixture test and review that no agent tool is introduced.
- **Azure validation:** Future real named/versioned agent invocation, response ID, trade refusal and
  credential-disclosure refusal.
- **Acceptance criteria:** Identical version reused on rerun; changed definitions produce explicit returned version,
  never guessed.
- **Owner and creation priority:** Composition owner P0; event operator installs.

### ART-003 — Guarded operator scripts

- **Purpose and challenge use:** Coach foundation preview, private fixture/agent installation and local guard
  validation.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `Initialize-Reference.ps1`, `Prepare-WhatIf.ps1`, `Test-LocalScripts.ps1`
- **Repository destinations:** `packages/coach/scripts/Initialize-Reference.ps1`,
  `packages/coach/scripts/Prepare-WhatIf.ps1`, `packages/coach/scripts/Test-LocalScripts.ps1`
- **Package visibility:** Private deployable coach only.
- **Artifact type and format:** PowerShell scripts with explicit parameters and consent guards.
- **Target Azure service and destination:** Confirmed target and private operator host; initialize FAQ and Foundry
  agent after foundation.
- **Schema or document structure:** CmdletBinding, explicit authorization, target verification, guarded WhatIf and
  local test doubles.
- **Required fields or sections:** Subscription/tenant/account arguments and required nonsecret output validation;
  no embedded concrete values.
- **Expected quantity or size:** Three scripts; exact approved implementation, no new cloud hooks.
- **Synthetic content requirements:** No generated business data; deterministic temporary fixtures confined to local
  tests.
- **Generation method and dependencies:** Exact reference reuse; requires PowerShell, .NET 10 and future authorized
  CLI context.
- **Upload or installation method:** Manual staged operator steps between foundation and workload. No automatic azd
  hook can assume private access.
- **Identity and access:** Explicit consent plus verified operator identity; runtime uses MI, never installer
  credentials.
- **Local validation:** PowerShell parse and Test-LocalScripts.ps1 local doubles/guards; no actual Azure invocation.
- **Azure validation:** Future confirmed-target initialization readback, immutable version capture and idempotent
  rerun.
- **Acceptance criteria:** Local guards block unconsented paths; future installation succeeds only after approved
  private foundation.
- **Owner and creation priority:** Composition owner P0; event operator executes only under separate authorization.

### ART-004 — Evaluation prompts

- **Purpose and challenge use:** C4 compact educational, safety and negative-case evidence set.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `evaluation.json`
- **Repository destinations:** `packages/hack/Allfiles/evaluation.json`,
  `packages/coach-guide/Allfiles/evaluation.json`
- **Package visibility:** Public learner-safe.
- **Artifact type and format:** UTF-8 JSON object.
- **Target Azure service and destination:** Local evaluator then future learner/coach app; no starter cloud
  installation.
- **Schema or document structure:** schemaVersion integer, cases array and infrastructureChecks array.
- **Required fields or sections:** Each case: id, prompt, expectation strings and sourceIds string array; unique
  IDs.
- **Expected quantity or size:** Six prompt cases and eight infrastructure checks.
- **Synthetic content requirements:** Approved requirement prompts, no people; one unsupported case and three
  safety/refusal cases.
- **Generation method and dependencies:** Extracted from approved requirements and existing deterministic test
  intent; no fabricated outcomes.
- **Upload or installation method:** Read locally in C4; send prompts only after authorized runtime exists. No azd
  load hook needed.
- **Identity and access:** Authorized tester; runtime identity remains scoped, never put tokens in result files.
- **Local validation:** JSON parse, unique IDs, count and citation-reference validation, exact Allfiles parity.
- **Azure validation:** Future actual answers checked against fact/refusal expectations and eight infrastructure
  checks.
- **Acceptance criteria:** All outcomes recorded as observed pass/fail or not evaluated; never prepopulate
  successful results.
- **Owner and creation priority:** Composition owner P0; team evidence reviewer executes.

### ART-005 — Interface evidence contract

- **Purpose and challenge use:** C1-C4 request/response evidence and sanitized error expectations.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `api-contract.md`
- **Repository destinations:** `packages/hack/Allfiles/api-contract.md`,
  `packages/coach-guide/Allfiles/api-contract.md`
- **Package visibility:** Public learner-safe, outcome contract without implementation.
- **Artifact type and format:** UTF-8 Markdown document.
- **Target Azure service and destination:** Learner-owned POST /api/chat interface; no starter app.
- **Schema or document structure:** Customer request, successful evidence and failure evidence sections.
- **Required fields or sections:** message length 1-2000; correlation/agent/source/receipt evidence; controlled
  400/401/403/429/502 failures.
- **Expected quantity or size:** One document, three substantive sections; no complete implementation.
- **Synthetic content requirements:** Only educational single-question examples; no personal data, endpoint values
  or trading operations.
- **Generation method and dependencies:** Derived from approved application request/response and failure boundary
  tests.
- **Upload or installation method:** Documentation only; learner implements during challenges. No azd hook or cloud
  ingestion.
- **Identity and access:** Anonymous educational edge, workload-authenticated private backend; no shared keys.
- **Local validation:** Section presence, byte parity and consistency with approved app tests.
- **Azure validation:** Future request, invalid input, unauthorized caller, overload and upstream-error
  observations.
- **Acceptance criteria:** Evidence can distinguish genuine agent success from missing configuration or fabricated
  fallback.
- **Owner and creation priority:** Composition owner P0; team API/evidence reviewer.

### ART-006 — Private reference diagrams

- **Purpose and challenge use:** Private architecture and runtime explanation for coach support.
- **Deployment classification:** `deployment-critical`
- **Status:** `packaged`
- **Proposed filename:** `03-architect-diagram.png`, `04-runtime-diagram.png`
- **Repository destinations:** `packages/coach-guide/media/03-architect-diagram.png`,
  `packages/coach-guide/media/04-runtime-diagram.png`
- **Package visibility:** Private coach only; never included in public source.
- **Artifact type and format:** PNG images.
- **Target Azure service and destination:** Documentation only, no Azure load target.
- **Schema or document structure:** Approved resource and identity-flow diagrams with placeholder suffixes.
- **Required fields or sections:** Complete reference identity/network boundaries, not public starter instructions.
- **Expected quantity or size:** Two PNG files; exact approved bytes.
- **Synthetic content requirements:** Synthetic Adatum branding, no people, resolved targets or real deployment
  identifiers.
- **Generation method and dependencies:** Exact reuse of approved rendered diagrams; no architecture redesign.
- **Upload or installation method:** Relative private image references; no cloud load or azd hook.
- **Identity and access:** Private repository access only.
- **Local validation:** PNG signature, exact byte parity and existing relative image references.
- **Azure validation:** Not applicable to image load; future operator compares actual deployed topology against
  approved reference.
- **Acceptance criteria:** Both diagrams render from existing private files, without broken links or public export.
- **Owner and creation priority:** Composition owner P0; coach reviewer.


## Creation and review sequence

1. Reuse approved files byte for byte and verify catalog provenance.
1. Create public evaluation/interface evidence without full implementation or personal data.
1. Validate structure, fixture counts, parity, placeholders and public/private boundaries locally.
1. Mark every destination packaged only when present; leave Azure acceptance for separately authorized rollout.

## Package and GitHub publication

| Content | Destination | Visibility | State |
| --- | --- | --- | --- |
| Scenario, contract and deployable coach | Owner-selected repository | Private | Not published |
| Learner instructions and starter | Separately reviewed repository | Public candidate | Not published |
| Coach guide and Finale | Separate restricted repository | Private | Not published |

No branch, commit, push, repository creation or publication is authorized by this job.
Future publisher must review exact release include lists and exclude all local build/validation caches.
Do not merge private files into a public release.

## Azure load and installation plan

Coach installation preserves the approved guarded staged operator process.
No automatic cloud-mutating azd hook is added: private connectivity and real image installation are required first.
The future authorized lifecycle must include explicit installation/readback and immutable-version capture.
Participant has no app or cloud data store; fixture delivery is local and source installation is learner work in C2.
Cosmos and Search are platform dependencies, not separate business seed/indexing tasks.
No custom search index, agent tool schema, person dataset or media enrichment is required.
Rerun overwrites the same FAQ blob and reuses an identical agent definition.
Clear only exact authorized event resources.

## Deployment and test gate

Local package validation does not authorize Azure operations.
After a separate explicit event request and exact-target review, `azd up` is mandatory for
`packages/coach/` and every manifest entry using `packages/participant/`.
Use the documented staged private coach installation rather than assuming a one-shot deployment.
Then verify real inference, agent invocation, grounding, receipt integrity, private paths, identity denial,
bounded errors and each artifact-specific check. Record actual outcomes and update successful entries to
`azure-verified` only after those runtime observations.
Future targets, quota, costs, consent and runtime results must be recorded separately.

## Completion tracking

| Workstream | Owner | Milestone | Evidence | Status |
| --- | --- | --- | --- | --- |
| Artifact creation/placement | Composition owner | Local package | Destinations above | Packaged |
| Safety/schema/parity | Composition owner | Release gate | packages/validation results | Passed locally |
| Azure load/runtime | Event owner | Separately authorized rollout | None | Not executed |
| Publication | Release owner | Separate decision | None | Not published |
