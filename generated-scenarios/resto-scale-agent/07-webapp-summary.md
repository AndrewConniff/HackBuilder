# Fourth Coffee web application implementation checkpoint

## Application Overview

| Property | Value |
| --- | --- |
| App Name | `Restaurant.Web` |
| Framework | .NET 10, ASP.NET Core Razor Pages and typed HTTP APIs |
| Source Path | `src\Restaurant.Web` |
| Data Storage | Cosmos DB; no runtime in-memory data or agent success fallback |
| Auth | Key Vault-signed scoped guest sessions; verified Entra staff roles and floors |
| Status | Entra repair saved; local validation incomplete; no current Azure/runtime business acceptance |

The confirmed security and operational design takes precedence over minimal-demo guidance that omits
authentication, health probes or durable identifiers. Guest codes are hashed and session proofs are scoped.
Distributed visit, ticket and event IDs are strings; menu item IDs are integers.
The implementation uses the pinned SDK's documented Responses integration.
`OPENAI001` is suppressed only in that integration file because the referenced OpenAI surface remains annotated
evaluation-only. Compilation is not evidence that a deployed agent or model works.

## Business Industry Context

| Property | Value |
| --- | --- |
| Industry | Hospitality & Travel |
| Business Units | `["generic"]`, no department targeting |
| Company | Fourth Coffee; company CSV record 14 |
| Personas and Handoffs | Guest -> host/server -> kitchen -> server -> synthetic settlement -> survey |

The warm coffee/cream theme follows the restaurant story, with Fluent-style semantic tokens, visible text navigation,
keyboard focus, narrow-screen layouts and accessible form labels. No substitute icon artwork was generated.
Guest and staff screenshots at 1440px and 390px are retained in `evidence\browser`.
These show the real local application with an explicit missing-service state, not fabricated restaurant data.
The four recorded person mappings are preserved in catalog seed provenance and page text.

## Data Model

| Core model | Responsibility |
| --- | --- |
| `Slot` | Authoritative five-floor reservation capacity, ETag-checked allocation |
| `Visit` | Scoped visit state, captured ticket prices, synthetic settlement and survey |
| `MenuItem` | Versioned server-owned menu price, availability and vegetarian indicator |
| Operational records | Previews, receipts, audit, outbox/inbox, ticket sequences and replay requests |

`SeedData\catalog.json` contains twelve menu items and a versioned policy/provenance record.
The initializer reads that source into Cosmos; it is not a runtime JSON fallback.
`LegacyImport` validates schema version 1, synthetic-only records, catalog guest IDs and stable external identities.
It retains partial receipts locally and rejects changed source records; it never bypasses reservation capacity.
Reserved-only cancellation releases the separate slot partition through a durable compensating receipt.
An acknowledged cancellation remains visibly pending capacity release until the worker confirms compensation.
Dispatcher leases, durable inbox receipts and ticket sequence checks are authored but not cloud-tested.
Manager recovery/reconciliation code and UI are authored. Contention, bounded-DLQ recovery and failure reporting
still require actual broker evidence. A local domain check is not a broker race or recovery test.

## Pages and Endpoints

| Surface | Purpose |
| --- | --- |
| `/`, `/Staff` | Public shells; no protected restaurant data embedded |
| `/api/reservations`, `/api/session` | Capacity reservation and access-code verification |
| `/api/menu`, `/api/policy`, `/api/visits/{id}`, `/api/board` | Catalog and authorized visit/slot/floor data |
| `/api/previews`, `/api/confirm` | Caller-bound typed previews and explicit durable confirmation |
| `/api/reservation-previews`, `/api/reservation-confirm` | Agent-grounded capacity proposal and human allocation gate |
| `/api/management`, `/api/replay` | Manager-only synthetic reconciliation and audited recovery requests |
| `/api/chat` | Web proxy and separately authenticated internal Foundry invocation |
| `/health/live`, `/health/ready` | Role-specific local health/configuration probes |

The repaired staff shell uses Microsoft MSAL Browser 4.30.0 from same-origin vendored assets.
MSAL uses memory-only token caching and the scenario-owned SPA callback `/auth.html`.
Only the API access token, never an ID token, is exchanged for a secure HttpOnly host-only cookie after
JWT and antiforgery verification. It expires at the earlier of token expiry and 30 minutes.
The original proof is revalidated and propagated to internal chat; role/floor inputs from the browser are ignored.
Production has no synthetic staff fallback. Retained synthetic helpers require explicit isolated Testing mode.
Existing owned registration IDs are preserved; current directory configuration and real sign-in remain unverified.
Do not expose this partial reference as a production application.

Build browser assets from the web project using `npm ci --ignore-scripts`, then `npm run vendor`.
The dependency lock and retained license accompany the same-origin MSAL distribution.
The .NET Cosmos SDK also requires pinned Newtonsoft.Json at runtime despite using System.Text.Json for documents.

## Deployment Target

| Property | Value |
| --- | --- |
| Compute Target | Three independent Container Apps: web, chat, worker |
| Dockerfile | Multi-stage .NET 10; native SDK build, unchanged Linux x64 runtime, non-root user |
| azd services | `web`, `chat`, `worker` |
| Build context | Scenario root; scenario-local proxy-only `NuGet.Config` |
| Azure consent | None; no account, quota, what-if, deployment or live tests performed |

`azure.yaml` uses the shared source with role-specific configuration.
`infra\runtime.bicep` wires all three immutable versions from the initializer into the app module.
`scripts\prepare_runtime.py` rejects a mismatched tenant/subscription/region/environment, foreign identities,
mutable/foreign images, and a different Foundry endpoint before generating local runtime parameters.
The initializer uses explicit Azure CLI subscription and tenant options; runtime uses only its managed identity.
Its installation path is authored but has never been run against Azure.

Antiforgery protection keys are shared through Cosmos with platform encryption at rest and existing data RBAC.
They are not additionally Key Vault-wrapped. Guest JWT signatures still require the scoped Key Vault key.
Without Cosmos configuration, the public shell logs explicit shell-only mode and uses ephemeral antiforgery keys;
business APIs remain unavailable. No profile directory is used for the application's key ring.

## Build Validation

Current run `30bc1eeb`: targeted checks passed 50/50; full checks passed 51/52.
Chromium failed the staff board empty-state assertion after clearing an unauthenticated session;
it did not reach mobile validation. Python validation was denied by the CLI without a structured permission scope.
The repair is not complete or certified. Historical results below remain historical.

| Check | Actual result |
| --- | --- |
| Recorded k6/cache/SDK setup verification | Passed; prior blocker cleared at portal revision 110 |
| Required proxy-only test dependency restore | Passed |
| .NET build | Passed, zero warnings/errors |
| Domain/API/Chromium suite | Twenty-five passed; zero failed/skipped |
| Runtime parameter isolation and validation tooling | Eight local checks passed |
| Browser responsiveness | Real local server verified; desktop/mobile without horizontal overflow |
| First emulated SDK image build | Failed: QEMU signal 11 during restore; original log retained |
| Native SDK build, same Linux x64 runtime target | Passed; image exported locally |
| Recorded old-image setup verification | Passed; health/homepage HTTP 200, marker and cleanup verified |
| Updated final image build and liveness | Passed; Linux amd64, user 1654, marker and cleanup verified |
| Cosmos/broker race, replay and fault behavior | Not live-tested |
| Normal/burst/soak load thresholds | Definitions inspected at 50/150/25 req/s; not measured |
| Deployed model, agents and complete business journey | Not performed; no Azure authorization |

Exact restore/build/test/container logs and TRX evidence are under `evidence`.
The temporary local browser-test server was stopped through its owned process handle.
The recorded helper was retried exactly under existing permissions and passed in run `cc61b383`.
No host permission, shared tool, PATH, Azure target or existing user decision was changed.
`validation\load.js` is an explicitly limited menu/reservation microbenchmark, not the complete guest/staff load mix.
Its 250 read and 30 write VU ceilings are generator bounds, not proof of 250 guests and 30 authenticated staff.
`validation\business_journey.py` exercises 1,000/1,250 real daily covers and durable confirmation retries only
when invoked later against an authorized deployed endpoint with a real manager token.
Neither authored definitions nor `k6 inspect` establish runtime performance, RU cost, fault recovery or agent success.
