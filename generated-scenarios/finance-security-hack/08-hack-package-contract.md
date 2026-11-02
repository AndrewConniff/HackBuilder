# Adatum brokerage education agent — private package contract

## Approval and unchanged scope

Phase B plan started 2026-10-22. `check-approval` passed before planning.
Approved reference fingerprint: `63e39364ad4e4ba55aea25ab5d1e1052d263fe7878ad83a4eecc81206b4d85b6`.
Financial Services / `financial-services` matches both intake CSV and Skillable catalog.
Adatum Corporation / adatum.com / `adatum-corporation` is company catalog data record 1.
No people occur in the reused fixtures; no new identities will be generated.

Adatum Corporation is a synthetic investment brokerage. Its anonymous public education
assistant explains investment concepts and approved FAQs, refuses trading and account
access, and protects private keyless backends with least privilege.
Security and Operational Excellence remain the priorities.

Historical evidence is explicit user attestation, not independent runtime verification.
The lab was deleted and is inaccessible; former URL, exact test time and logs are unavailable.
No current capacity, live URL, per-check success or new deployment is inferred.
Root reference source, infrastructure, fixtures and evidence remain untouched.

## Four deliverables

| Root | Boundary |
| --- | --- |
| `packages/coach/` | Private sanitized copy of approved app, IaC, scripts, fixtures and tests |
| `packages/participant/` | Public empty resource-group starter, access contract and FAQ only; no app |
| `packages/hack/` | Public outcome-led Skillable challenges and safe payloads |
| `packages/coach-guide/` | Private full architecture, deployment guide, exact challenge copies and Finale |

Only these roots and root contract, inventory, manifest and README may change.
Do not copy `.azure`, operational evidence, local caches, credentials or concrete endpoints.

## Minimum starter architecture

Team operator -> separately authorized team resource group -> no service resources.
The only indispensable business fixture is the small approved synthetic FAQ.
Access is assigned by the event operator to the team group; no broad subscription grants
or automated role escalation are supplied. A private-capable operator environment and
service/model quota are future event prerequisites, not preprovided resources.

Starter placeholders are environment name, location and separately selected target.
No application or URL exists. A local status script must say `not-configured` and
list learner-built capabilities; it must never simulate successful chat.

## Private reference-to-starter resource omission matrix

All learner-built entries are omitted from starter source and compiled ARM.
Coach retains the exact approved implementations; learners choose implementation from outcomes.

| Reference resource/capability | Disposition | Dependency/rationale | Checkpoint |
| --- | --- | --- | --- |
| Team group/access | Preprovided | Isolation only | C0 team allowed; coach denied |
| Twelve-topic FAQ | Preprovided | Stable approved facts | C2 citations and unknown question |
| Foundry account/project/model/agent | Learner-built | Core learning | C0 model; C1 real agent/version |
| Instructions and installation | Learner-built | No answer handout | C1 refusal; explicit failure |
| VNet/subnets/NSG/endpoints/DNS | Learner-built | Private Standard | C0 operator route; C4 public denial |
| Storage/Cosmos/Search/capability host | Learner-built | Platform persistence | C1 real agent runtime |
| FAQ blob and Blob Reader | Learner-built | Bounded context | C2 authorized read; denied identity |
| App/gateway/project MIs and RBAC | Learner-built | Least privilege | C0 access; C3 wrong-identity denial |
| Entra backend audience | Learner-built | No shared secret | C3 wrong-audience denial |
| Internal ACA/app/ACR/image | Learner-built | No starter app | C1 direct MVP; C3 integration |
| APIM/token/rate policy | Learner-built | Anonymous edge | C3 edge succeeds; backend denies |
| Key Vault/key/crypto RBAC | Learner-built | Signed digest | C3 verify; tamper and identity denial |
| Logs/correlation/limits/diagnostics | Learner-built | Operations | C4 redaction; bounded errors |
| Full tests/diagrams/architecture | Coach-only | Private answers | Local tests; future runtime checks |
| Complete deployment scripts | Coach-only | Guarded private install | Local guards; future readback |

Coach retains complete implementations for every learner-built entry.
Standard setup requires Storage/Cosmos/Search for persistence, not additional business tools.
The app uses container-scoped Blob Reader and key-scoped Crypto User; runtime is Agent Consumer, not agent creator.
App, gateway and project identities stay distinct; gateway has no model, source or signing roles.
Full reference installation scripts and instructions remain private even though learners implement those outcomes.

## Learning contract and time budget

10-minute kickoff + 150-minute build + 20-minute wrap = 180 minutes.

| Challenge | Minutes | Cumulative build | Observable increment and regression |
| --- | --- | --- | --- |
| 0 — Secure Foundation | 25 | 25 | Team isolation, private-capable access, identity-backed model request |
| 1 — Build the Agent | 30 | 55 | Real versioned agent response in first 15 minutes; refuse trade requests |
| 2 — Ground the Answer | 30 | 85 | FAQ citations; retain MVP and unknown-question response |
| 3 — Sign the Receipt | 40 | 125 | Authenticated signing and public/private boundary; retain citations |
| 4 — Harden and Demo | 25 | 150 | Regression, negative cases, sanitized correlation and controlled failure |

Challenge 3 adapts the generic authenticated-action slot to the approved application's
Key Vault signing operation. It does NOT add an agent tool, trading API or multi-agent design.
Portal-first routes cover exploration and configuration; private networking, host integration
and signing require SDK/operator work. Mixed teams pair for those steps; no false all-portal claim.
Optional customer authentication is a post-core stretch, never a core prerequisite.

Public pages describe constraints, evidence and learner decisions, not full architecture.
Fallbacks preserve the last checkpoint, use one synthetic source/answer for isolated next-step
testing, and label any deferred integration. A partial team must not claim end-to-end success.
Private Finale supplies exact reference answers, recovery and acceptance expectations.

## Isolation and future deployment

Coach environment `finance-security-hack-coach`, group `rg-finance-security-hack-coach`.
Default team `01`: environment `01-finance-security-hack-hack`,
group `rg-01-finance-security-hack-hack`. These are distinct planned names, not deployed state.
No shared backend, coach resource reuse, Azure operations or event deployment is authorized.
Staged private coach initialization preserves the approved guarded operator process;
there is no misleading one-shot deployment or automatic cloud-mutating hook.

## Validation and release gate

Before packaging: recheck approval. Compile and lint both IaC roots using cached standalone
Bicep offline. Build and run copied coach tests using the available .NET 10 SDK.
Parse guarded scripts; test intended-incomplete starter and omitted-resource denylist.
Validate all deployment-critical inventory placements, safe release allowlist, absence of
operational state, byte parity of challenges/payloads and Skillable structure/frontmatter.
Recheck approval at end. Persist exact results under `packages/validation/`.

Private networking and multi-service provisioning may exceed the timer in a fresh subscription.
The schedule is a build target for prepared, quota-enabled teams, not a measured completion claim.
Future event owner must confirm quota, target permissions, private operator access and costs
before accepting the event. Do not weaken private/keyless controls to meet the timer.

Completion is **packages validated; event not deployed**, only after saved checks pass.
Publication and event rollout require separate decisions.

## Saved completion evidence

The four package roots and separated source ZIPs are saved.
Both standalone Bicep build/lint pairs passed offline; the copied .NET app built with zero warnings/errors.
All 18 deterministic app tests and 17 script syntax/consent checks passed.
Starter, catalog, omission, parity and public/private boundary checks passed.
Skillable package and authoring-resource checks passed; approval remained valid at the release gate.
Exact commands, times, results, ARM and test evidence are private under `packages/validation/`.
Only the copied script's absolute example paths were sanitized; executable coach logic and fixtures are unchanged.
No Azure runtime test, live Skillable import, publication or event deployment occurred.
