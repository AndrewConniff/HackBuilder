# Approved reference deployment scope

## User decision

On 24 October 2026 the user explicitly said **approved deployment** and confirmed petender as area manager.
The same response requested application-local dummy store logins and **no Entra user authentication**.
The [authorization receipt](evidence/deployment-authorization.json) deliberately omits the supplied password.
This is deployment consent, not working-scenario suitability approval.

## Exact target

| Field | Value |
| --- | --- |
| Azure operator | petender@microsoft.com; current CLI and azd names match |
| Tenant | `16b3c013-d300-468d-ac64-7eda0820b6d3` |
| Subscription | `efd64343-6ef4-4926-951f-d3229f38bd76` |
| Environment | `coffee-shop-ref` |
| Resource group | `rg-coffee-shop-ref` |
| Region | **swedencentral** |

Resources remain the reviewed Foundry S0 account/direct child project, capacity-30 GlobalStandard
gpt-4.1-mini / 2025-04-14 deployment, three agents, Linux P0v3 plan (1-3 workers), .NET 10 app,
Standard_LRS Table storage, synthetic fixtures and least-privilege managed-identity/installer RBAC.
Public TLS endpoints, no WAF/private networking, GlobalStandard processing, non-HA baseline
and model deprecation/preview-SDK limitations remain disclosed in the architecture.

## Revised authentication

- `storeman001`: StoreManager, only store 001.
- `storeman002`: StoreManager, only store 002.
- `petender`: AreaManager, stores 001 and 002.
- Installation uses the supplied store password without committing or logging it.
  The area password is independently generated and saved in an operator-local Windows-protected credential file.
- Only independently salted PBKDF2 hashes are persisted in Table Storage.
- Secure HttpOnly SameSite cookies, 30-minute expiry, POST antiforgery and shared five-failure lockout.
- Data Protection keys persist on App Service shared HOME for restart/scale-out continuity.
- **No Entra browser sign-in, application registration, user creation, consent or Graph write.**
  The earlier directory-administrator question therefore no longer applies.
- Azure system-assigned managed identities still authenticate the backend to Foundry and Tables.
  They are not interactive user accounts and require no application-login directory installation.

## Actual preparation evidence

Sweden Central what-if succeeded with **16 Create, 0 Delete, 0 Modify**.
The revised no-directory Bicep was compiled/linted and its what-if rerun successfully.
A read-only in-memory three-worker ARM validation passed; source baseline remains one.
Quota and validation cannot reserve worker/model capacity or prove runtime behavior.
Required providers are registered; the operator has subscription Owner and Foundry User.
Model quota is shared globally: observed usage 0, limit 5000, demand 30.
Immediately before rollout, [affected identity/quota observations](evidence/readiness/predeploy-quotas.json)
were refreshed. Model lifecycle is Legacy with reported inference deprecation on 14 April 2027.

East US 2 was rejected: ARM validation reports P0v3 limit 0 despite usage metadata showing 360;
actual denial takes precedence. Its failed what-if is retained, not called successful.

Evidence: [region matrix](00-region-availability.json), [current what-if](evidence/what-if.json),
[three-worker preflight](evidence/arm-validation-swedencentral-scale.json),
and [local build/test output](evidence/local-checks.json).
The full revised local run passed 31 tests, locked build/publish, both Bicep lints, browser checks
and parser checks for five PowerShell scripts.

## Cost and remaining proof

Fetched Sweden Central Linux P0v3 retail price is USD 0.089/hour:
USD 64.97/month for one continuously active worker, USD 194.91 for three at 730 hours.
With illustrative inference/storage assumptions, the estimate remains **USD 120-270/month**,
not a cap, negotiated quote or production scaling guarantee.

Authorized lifecycle: exact-target assertion -> provisioning/RBAC -> hashed account/fixture/agent installation ->
app publishing -> real authentication, model/agent/chat/grounding/order/negative/performance acceptance.
No event rollout, publication or hack composition is authorized.
After runtime proof, present the actual working scenario and wait for explicit suitability approval.
