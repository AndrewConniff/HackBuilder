# Authentication Gate — 2026-10-22 Continuation

**Decision required. Deployment authorization received; authentication prerequisite unresolved.**

Checked at `2026-10-22T18:36:06.466400+00:00`.
Machine-readable commands, timestamps, exits and safe results: `auth-discovery-2026-10-22.json`.

## Authorization Recognized

The continuation explicitly relays the user's response, **"ok to run the deployment"**, to the reviewed what-if.
It authorizes reference provisioning, app deployment, fixture ingestion and live acceptance for:

- Account `petender@microsoft.com`.
- Subscription `efd64343-6ef4-4926-951f-d3229f38bd76`
  (`MCAPS-Hybrid-REQ-152516-2026-petender`).
- Tenant `16b3c013-d300-468d-ac64-7eda0820b6d3`.
- New `rg-hospitality-feedback`, azd environment `hospitality-feedback`, `westus3`.
- Foundry Basic S0; `gpt-4.1-mini` version `2025-04-14`, regional Standard capacity 10.
- Linux App Service B1 × 1, .NET 10; Standard_LRS Hot Storage.
- Reviewed 24 Create / 0 Modify / 0 Delete / 2 Unsupported expected runtime Storage grants.

Authorization is conditional on establishing valid intended existing authentication and repeating what-if.
It does not authorize Entra registration creation/modification, unrelated registration reuse,
additional material permissions, auth bypass, participant deployment, composition or publication.
Missing deployment consent is no longer the blocker.

## Actual Read-Only Results

All six persisted query commands exited 0:

- `az account show`: exact enabled subscription, tenant and account match.
- `az ad signed-in-user show`: actual guest user object ID
  `214d672b-df87-4f3b-94fd-7863032546c1`.
- `azd auth token`: safe decoded ARM token claims match the same tenant and object ID.
  Decoding is identity alignment, not signature verification or application API acceptance.
  No token was printed or persisted.
- `az ad app list` and `az ad sp list`, filtered to display-name prefixes
  `hospitality`, `hotel`, `Margie`, `feedback`: 12 applications and 29 service principals returned.
- `az group exists`: `rg-hospitality-feedback` remains absent.

None of the returned objects exposes enabled delegated `access_as_user` or role `Feedback.Operator`.
The superficially relevant **Feedback API (local dev)** application
(`2cca1d9d-2ce5-4d21-8598-84c542834a84`) requests v2 tokens, but exposes
`user_impersonation` and roles `Feedback.Read` / `Feedback.Ingest` instead.
It is **not selected or authorized for reuse**. Other hotel/travel-named registrations do not establish intent.

`src/HospitalityFeedback.Web/Program.cs` requires the configured tenant, exact audience,
allowlisted `oid`, and `access_as_user` or `Feedback.Operator`.
The discovered permissions therefore cannot satisfy the existing application policy.
Consent discovery for these unrelated/incompatible registrations was deliberately not expanded.

This is prefix-filtered discovery, not a claim that no suitable registration exists anywhere in the tenant.
No intended registration ID exists in the reviewed configuration/evidence.
No custom API token was requested, and no scope consent or role assignment was invented.

## Exact Next Action

Supply the **intended existing** registration's application/client ID and tenant,
its v2 access-token audience, and either enabled delegated `access_as_user` with the approved
client ID, scope URI and existing consent, or an enabled `Feedback.Operator` application role
with the approved caller identity and existing assignment.
Confirm that object ID `214d672b-df87-4f3b-94fd-7863032546c1` is the intended operator allowlist entry.
Do not send bearer tokens, client secrets or certificates in chat or source.

If no such registration exists, a separate explicit authorization for a narrowly specified Entra
registration/permission setup is required; this continuation grants no directory-write authority.

Then verify the supplied registration and approved token acquisition path, set real local parameters,
refresh time-sensitive capacity evidence, rerun what-if, and compare the exact resource and RBAC scope.
Proceed under the recorded conditional deployment consent only if the new preview stays within
the reviewed creates/expected grants and has no material new permissions or unrelated modifies/deletes.
Otherwise obtain confirmation of the changed scope.

## State Preserved and Work Not Performed

- Preview audience left unchanged; azd `API_AUDIENCE` remains unset.
- No Entra, Azure resource, RBAC, provider or quota writes; no provisioning/deployment attempt.
- No application code, fixtures, region, model, networking or security settings changed.
- Existing 30 passing local tests remain inherited evidence, not rerun or claimed as live acceptance.
- Capacity 5000 remains the earlier point-in-time evidence; not refreshed because authentication blocks deployment.
- No functional live URL, cloud model inference, deployed chat, browser acceptance or validation success claimed.
- No `scenario-validation.json`, review snapshot, suitability approval or hack package created.

Official references checked during this continuation:

- [Access token claims, including exact v2 audience][claims]
- [Read-only application listing and permissions][applications]

[claims]: https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
[applications]: https://learn.microsoft.com/en-us/graph/api/application-list?view=graph-rest-1.0
