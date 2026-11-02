# Web application summary: equip-ai

## Application Overview

The .NET 10 Razor Pages app uses real Blob and Foundry SDKs with managed identity.
Static inventory is synthetic metadata; runtime measurements come only from routed telemetry.
The forest-green Operations theme preserves keyboard focus, responsive layout and visible errors.
Missing account storage disables sign-in; no measurements or agent answers are simulated.

The user-approved restoration replaces Microsoft/Entra sample sign-in with local accounts.
Salted Identity password hashes, role records and lockout counters persist in the private `accounts` container.
Framework session keys persist there across restarts. Azure Storage provides encryption at rest;
this is not customer-managed key wrapping. No local password is an Azure credential.
The web identity can write accounts/session keys but can only read telemetry.
The private cleaner cannot access accounts.

## Business Industry Context

Manufacturing & Mobility, `["operations"]`, synthetic Adatum Corporation.
Airi Ilves and Hasan Ibrahimov retain their exact requirements/catalog provenance.
The `tacoma-support` account can read Tacoma only; `statewide-lead` can read all five Washington sites.
The separate `coach` account has statewide visibility and an explicit coach role.
No account can actuate machines or certify mechanical safety.

## Data Model

Inventory has 25 immutable device/site records. Routed events carry measurements, device/message identity and UTC time.
IoT connection identity, not payload assertions, determines the device.
Typed tools independently authorize sites, validate inputs, deduplicate readings and calculate exact metrics.
Coverage exposes scoped expired-record exclusion counts without leaking other sites.
The 30-second bounded cache never overrides the two-hour tool and final-citation freshness checks.
Chat and raw telemetry are not persisted by the app or written into diagnostic logs.

## Pages and Endpoints

| Route | Boundary |
| --- | --- |
| `/` | Public sign-in shell; no measurements |
| `/api/config` | Session state and anti-CSRF token; no credentials |
| `/api/login` | Same-origin HTTPS/CSRF; IP rate limit; salted password check; durable lockout |
| `/api/logout` | Authenticated session and same-origin CSRF |
| `/api/equipment` | Current local session and server-assigned Operations role |
| `/api/chat` | Same role/session plus CSRF, rate limit and 30-second real agent deadline |
| `/api/evidence/{siteId}/{deviceId}` | Same session plus independent device/site authorization |
| `/health` | Process liveness only; never evidence of cloud runtime success |

Cookies are Secure, HttpOnly and SameSite Strict, expire after two hours and do not slide.
Every authenticated request validates the durable security stamp and assigned roles.
Account changes use conditional ETags with bounded conflict retries to avoid lost failed-login updates.
Five failures lock sign-in for 15 minutes; existing valid sessions are not invalidated by an attacker's bad passwords.

## Installation and private access

Use the guarded azd lifecycle, not the retained historical Entra installer.
Preprovision protects the private credential directory and generates deployment-specific access files.
Postprovision publishes self-contained Linux x64 output, verifies private DNS, installs a real versioned agent,
and seeds only salted account records using the private VM's managed identity.
Artifacts use authenticated SCM `/data`, never public `wwwroot`; exact staged files are removed after success.
`services: {}` prevents a second workstation deployment to the private cleaner.

Bootstrap switches are removed before configuration parsing, so adjacent CLI settings remain intact.
CLI-only operations prepare private accounts/certificates, initialize accounts/agent, publish X.509 events
and reset a provisioned account's lockout through the management identity.
None is exposed as a public administrative HTTP endpoint.

Private credential files are `.private/participant-access.json` and `.private/coach-access.json`.
The participant file contains no coach password; the coach file contains only coach access.
Keep both out of Git, catalogs, source archives and published application assets.
For a new destination deployment, generate new credentials rather than copying these files.

## Validation

Use the executable test harness, not `dotnet test`, for deterministic, HTTP and browser checks.
The restoration adds local password/lockout/stamp checks and actual publisher fixture/expiry diagnostics.
The separately guarded `scripts/validate_live.py` performs real login, certified MQTT ingress,
Blob grounding, Foundry invocation, cross-site denial, dependency failure/recovery and measured load checks.
Receipts distinguish local checks, real runtime calls and historical evidence.
No provisioned resource, homepage, agent definition or screenshot alone establishes successful acceptance.
