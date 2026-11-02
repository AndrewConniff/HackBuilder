# Web Application Summary - Manufacturing Sales-to-Marketing

## Application Overview

| Property | Value |
| --- | --- |
| App Name | `MobilityCommercial.Web` |
| Framework | .NET 10, ASP.NET Core Razor Pages |
| Language | C# |
| Source Path | `src\MobilityCommercial.Web` |
| Data Storage | Private versioned Azure Blob; no runtime local-file fallback |
| Auth | Anonymous synthetic APIM entry; every private backend route requires gateway JWT |

The confirmed private backend security contract takes precedence over the generic unauthenticated demo template.
There is no staff sign-in or business-unit entitlement claim. Persona navigation does not authenticate a user.
Production registers only real Foundry, Blob and Key Vault implementations.
Test doubles live exclusively in `tests\MobilityCommercial.Tests`; no runtime mock-success switch exists.
Missing endpoint, model, pinned version, hash, key or identity configuration fails startup explicitly.

The visual direction follows mobility manufacturing: forest-green brand, warm neutral canvas and restrained
industrial typography, using Fluent 2 semantic color/spacing/focus/state tokens rather than Azure-blue branding.
An official Fluent System Icons arrow is embedded in navigation; its Microsoft MIT notice ships with the app.
No CDN, external JavaScript, tracking, decorative emoji or third-party browser dependency is required.
Keyboard focus, skip navigation, live status, visible current navigation and narrow-screen layout are provided.

## Business Industry Context

| Property | Value |
| --- | --- |
| Industry | Manufacturing & Mobility |
| Description | Evidence-backed commuter product fit and safe campaign handoff |
| Business Units | `["sales", "marketing"]` |
| Personas and Handoffs | Airi Ilves / Sales -> Hasan Ibrahimov / Marketing -> human review |
| Company | Adventure Works Cycles; company catalog record 2 |
| People provenance | Exact `FullName` from people catalog records 1 and 2 |

The finance source remains read-only architectural guidance. This application, prompts, data and tests are new.
The confirmed three-product/four-opportunity/three-claim corpus intentionally replaces generic 10-20-record advice.
`opp-001` requests an unsupported range guarantee; `opp-002` fits; `opp-003` needs clarification;
`opp-004` contains an unapproved product and injection-like text and fails before inference.
All values, commercial numbers and contact sentinels are synthetic; catalog domains are never contacted.

## Data Model

| Entity | Fields and purpose | Seed count |
| --- | --- | --- |
| Product | Integer `Id`, stable `SourceId`, version, category, qualified range statement | 3 |
| Opportunity | Integer `Id`, product reference, audience, needs, range, owners and excluded commercial fields | 4 |
| ApprovedClaim | Integer `Id`, source/version, product reference, permitted wording and required caveat | 3 |

PascalCase seed files are in `SeedData`; HTTP/tool JSON uses camelCase with strict constructor/schema checks.
No fourth business entity or business database is added. Cosmos/Search support private Standard platform state,
not business record access from the application.

The installer uploads versioned blobs and a content-addressed manifest containing actual agent IDs/versions/model.
Runtime checks the configured manifest SHA-256, each blob's exact version/hash, installed pins and schema.
It never creates a container, changes a firewall, downloads arbitrary paths or reads platform state.
Even Sales tools project away margin, discount and contact before model invocation.
Marketing receives validated structures, never the original user prompt or Sales conversation.
Public wording is selected deterministically from allowlisted claims; arbitrary agent prose is not published.

Sales Fit gets only `get_opportunity` and `get_product`; Marketing Claims gets only `get_approved_claims`.
Coordinator has no tools. Separate version-pinned Responses contexts prevent accidental conversation handoff.
Tool arguments, product/source IDs, citations, required unknowns and coordinator reconciliation are validated.
No agent can publish, order, recurse or select another agent.

Four in-flight handoffs per replica, 4,000 input characters, 800 output tokens per response, seven inference
requests, 30,000 cumulative tokens and a 90-second total deadline enforce the confirmed bounds.
Conservative next-call input/history/instruction allowances are checked before inference; actual usage is reconciled.
SDK inference retries are disabled, so failures are visible and do not consume unaccounted model requests.
Routine logs contain correlation, stage, response ID and token totals, never prompts/tool payloads or credentials.

Canonical receipt JSON sorts object keys ordinally, preserves array order and uses compact UTF-8 JSON.
SHA-256 and PS256 cover the full packet, source versions and actual installed/response provenance.
The envelope includes base64 canonical bytes, digest, signature and exact versioned key URI.
Verification recomputes packet bytes and refuses another key/algorithm, altered content or invalid signature.
Integrity is neither factual certification nor human business approval.

## Pages and Endpoints

| Page or API | Route | Contract |
| --- | --- | --- |
| Dashboard/workflow | `/` | Opportunities, Sales evidence, Marketing brief and trace sections |
| Styles/script | `/app.css`, `/app.js` | Explicit authenticated routes; no static-file bypass |
| Opportunities | `GET /api/opportunities` | Minimal needs projection only |
| Products | `GET /api/products` | Versioned synthetic evidence |
| Claims | `GET /api/claims` | Approved wording/caveats |
| Handoff | `POST /api/handoffs` | Known opportunity ID, request; signed review-required packet |
| Verify | `POST /api/receipts/verify` | Whole returned receipt; explicit rejection of tampering |

Every route validates JWT signature, tenant v2 issuer, GUID audience, lifetime and gateway object ID.
The app does not trust incoming identity headers. APIM supplies the backend token; the browser never receives it.
Errors return safe codes and correlation IDs with non-success status; unavailable dependencies never return a packet.
400/404/429/502/503/504 represent invalid requests, missing evidence, admission, invalid output,
dependency and deadline.
401/403 distinguish authentication and gateway identity. CSP, no-store and anti-sniffing headers apply to all routes.

## Deployment Target

| Property | Value |
| --- | --- |
| Compute Target | Internal Azure Container Apps behind APIM |
| Dockerfile | Multi-stage .NET 10, nonroot `APP_UID`, port 8080 |
| azd Service Name / Host | `web` / `containerapp` |
| Docker build context | Scenario root; includes scenario-local proxy-only `NuGet.Config` |
| Proposed distinct environment | `manu-multi-agent-ref`; not initialized |

`azure.yaml` points at the existing project. It adds no deployment hook and does not bypass staged provisioning.
Do not run `azd up`, initialize an environment, push an image or execute installation without exact-scope consent.
Immutable image digest, manifest hash, installed versions and `SIGNING_KEY_VERSION` remain workload inputs.
The foundation key URI is versionless; installation resolves its actual version before runtime configuration.
The app will reject a versionless key, protecting against sign/verify drift after key rotation.

Local application checks, from the repository root:

```powershell
python generated-scenarios\manu-multi-agent\scripts\validate_application.py `
  --nuget-config C:\HackBuilder\NuGet.Config
```

The runner restores locked packages only through the approved proxy, compiles, tests and publishes.
It also checks the narrowly coupled key-version/route IaC contract and exercises offline browser fixtures.
It does not build/start a container, invoke an agent, install an identity or contact Azure.

Later authorized installation uses `tools\MobilityCommercial.Installer` with
`--execute-authorized-installation <scenario-root>`, from a private-network-capable operator context.
Set process-local `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `FOUNDRY_PROJECT_ENDPOINT`,
`FOUNDRY_MODEL_DEPLOYMENT`, `FIXTURE_BLOB_ENDPOINT` and `SIGNING_KEY_URI` from the verified authorized foundation.
Map `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_AI_MODEL_DEPLOYMENT` outputs to those installer names.
No account default is changed. The installer uses the specified tenant's CLI credential.
Azure commands used by the deployment operation must additionally pass the authorized subscription explicitly.

The installer reuses owned agent versions by scenario/definition/model hash, verifies versioned fixtures,
captures actual agent IDs, and writes ignored private `.installation\installation.json`.
That receipt supplies agent versions, manifest SHA-256 and actual key URI/version to workload parameters.
`scripts\Initialize-BackendIdentity.ps1` separately creates/reuses one tagged, dedicated, single-tenant API
application/service principal, sets its unique resource URI and token version 2, and records actual IDs privately.
It creates no secret, Graph permission grants, user sign-in, redirect or admin role.
Directory writes need their own authorized mutation scope; resource preparation consent is insufficient.
The script checks the exact account/subscription/tenant, never adopts by name and never changes shared defaults.
No installer has been executed; no generated local receipt should be treated as live success.

## Build Validation

| Check | Status / evidence |
| --- | --- |
| Locked proxy restore, solution build, publish | `.application-evidence\validation.json` and command logs |
| Unit/persona/coordination/authentication checks | 35 offline tests; actual JWT middleware and request pipeline |
| Chromium desktop/mobile | 8 intercepted offline UI cases at 1280 and 390 pixels |
| Seed data and published output | Three JSON files; test assemblies excluded |
| Dockerfile and azd wiring | Native SDK build passed; nonroot `linux/amd64` runtime retained |
| Offline container configuration | Passed with isolated test settings; real installation outputs still pending |
| Container authentication | Six protected routes return correlated HTTP 401; no network, mounts or published ports |
| Key-version IaC integration | Local Bicep compilation/lint and 12 structural checks |
| Identity installer | Parsed locally only; not executed |
| Real Foundry/Blob/Key Vault/private networking | Not run; requires separate authorized cloud work |

Browser screenshots and `browser-checks.json` are explicit offline UI evidence, not a running reference URL.
The early mobile digest overflow was fixed by wrapping receipt text and retaining horizontal trace-table scrolling.
Original infrastructure evidence is preserved; application evidence owns subsequent integration changes.
Phase A remains incomplete until authorized deployment, live model/agent/application negatives and suitability review.
No hack plan, participant starter, coach package, scenario approval, team rollout or publication was created.

Local validation is recorded in `local-validation.json` and `.local-validation-evidence`.
The shared generic helper fails as expected without required production configuration; this is a negative startup
assertion, not a passed anonymous health/homepage check. No backend routes were weakened to satisfy that helper.
Configured container checks use explicit syntax-only fixture values with Docker networking disabled.
These checks prove startup and anonymous denial, not live configuration, Foundry inference or identity installation.
Read-only startup uses ephemeral ASP.NET Data Protection keys; persistent cookie state was not validated.
