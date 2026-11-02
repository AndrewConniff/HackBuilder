# Fourth Coffee reference deployment summary

## Deployment Details

| Property | Observed value |
| --- | --- |
| Environment | `coffee-shop-ref` |
| Deployment | Approved `azd up --no-prompt`, followed by endpoint repair with `azd deploy --no-prompt` |
| Evidence date | 24-25 October 2026 UTC |
| Operator | `petender@microsoft.com`; CLI and azd identities matched |
| Subscription | `efd64343-6ef4-4926-951f-d3229f38bd76` |
| Tenant | `16b3c013-d300-468d-ac64-7eda0820b6d3` |
| Resource group | `rg-coffee-shop-ref` |
| Region | Sweden Central |
| Duration | Successful `azd up` retry: 3m24s; endpoint-repair publication: 57s |
| Status | Deployed; functional runtime and browser checks passed; performance targets not met |
| Suitability approval | Not requested/recorded before this review; no hack composition started |

The original creation what-if succeeded with **16 creates and no deletes**.
See [creation preview](evidence/what-if-rest-swedencentral.json).
The [latest corrective preview](evidence/what-if.json) is a later deployed-state comparison,
not another claim of 16 new resources. No resource deletion was performed.
East US 2 was rejected by actual ARM P0v3 validation; Sweden Central was explicitly approved.
Original authorization is retained in [the deployment receipt](evidence/deployment-authorization.json).

### In-scope failures and repairs

1. Readiness initially passed `--subscription` to a directory-only command. The helper was corrected and rerun.
1. First provisioning succeeded, but initialization failed with Table 403:
   the storage AVM defaulted its network ACL to Deny.
   IaC now explicitly uses the reviewed authenticated-public Allow configuration with bypass None.
   Shared keys and anonymous blobs remain disabled; no private-only requirement was bypassed.
   Bootstrap now uses the verified operator's `AzureCliCredential`.
1. The successful retry installed accounts, fixtures and three agents, then published the application.
   See [successful lifecycle result](evidence/azd-up-retry1-result.json).
1. Initial application agent calls returned 403 because they used the project developer Responses API.
   Bootstrap now configures each Responses endpoint with 100% routing to its installed immutable version.
   Runtime uses `GetProjectResponsesClientForAgentEndpoint`, preserving project-scoped Agent Consumer.
   No broader runtime role, API key or SDK upgrade was introduced.
   See [endpoint repair](evidence/agent-endpoint-repair.json).
1. The first fault-injection attempt reached the old process before settings applied.
   Its unsuccessful test remains in `evidence/live-branch-transition-not-applied.json`.
   Explicit restart, then the real missing-margin fault, returned 503.
   Correct settings were restored in `finally`; another restart and complete live acceptance proved recovery.
1. Browser assertions initially used the test library's five-second default for a real multi-agent call.
   The receipt assertion now waits within the actual 90-second application budget; the browser rerun passed.

No Graph writes, end-user Entra registrations/consent, shared tool installations or Azure default changes were made.
Existing scenario content, unrelated repository changes and durable stock/orders were preserved.

## Deployed Resources

| Resource | Configuration | Actual evidence |
| --- | --- | --- |
| `fc-coffee-shop-keegvmxo` | Foundry AIServices S0 | Real model inference passed |
| `backoffice` | Direct child Foundry project | Three installed agent endpoints invoked |
| `gpt-4.1-mini` | Version 2025-04-14; GlobalStandard; capacity 30 | Real Responses inference completed |
| `plan-fc-keegvmxonq3wc` | Linux P0v3; baseline 1; elastic cap 3 | Web publication and runtime succeeded |
| `web-fc-keegvmxonq3wc` | .NET 10; system identity; public HTTPS | Real cookie login, chat and browser passed |
| `stfckeegvmxonq3wc` | Standard_LRS; Table `CoffeeBackOffice` | Account checks, snapshots and order replay passed |
| Three prompt agents | `coffee-shop-stock`, `coffee-shop-margin`, `coffee-shop-close`; all v1 | Real response IDs |

Application MI: `a03f1a03-1b4b-402d-a807-0334996b560e`.
Its roles remain Foundry Agent Consumer at project scope and Table Data Contributor on this scenario's storage.
Storage permissions span all stores; server-controlled entitlements remain a critical authorization boundary.

### Actual acceptance

| Check | Observed result |
| --- | --- |
| Local build/test/lint | 31 tests passed; build 0 warnings/errors; Bicep build/lints and publish passed |
| Local authentication | All three accounts signed in; secure cookie, CSRF and logout verified |
| Authorization negatives | Anonymous denied; cross-store and store 003 denied; missing CSRF denied |
| Direct model inference | Completed; `COFFEE_MODEL_OK`; actual response ID retained |
| Application agent close | Stock + margin, then coordinator; all three real v1 response IDs retained |
| Structured grounding | Stores 001/002 only; net sales 4200 and profit 1485; no store 003 persona leakage |
| Internal order | 230.35 total; no oat-milk shortfall; same approved receipt across managers |
| Actual branch fault | Missing margin endpoint returned HTTP 503; no completed-close payload |
| Recovery | Original agent restored; full functional acceptance passed again |
| Browser | Login, scoped store, order view, area comparison and three real receipts; screenshots captured |
| Single area close | 9.50 seconds; not a ten-user p95 measurement |
| Ten concurrent HTTPS reads | p95 2.41 seconds; **1-second target not met** |
| Ten simultaneous closes | 2 completed, 8 explicit HTTP 409 busy responses; **ten-user target not met** |

The ten-request samples use three configured identities, not ten distinct users or sustained load.
No actual three-worker scale-out was exercised. Rejections are not counted as successful fast closes.
Functional passed status in the evidence index does not assert complete non-functional acceptance.

## Outputs (Expected)

| Output | Actual value |
| --- | --- |
| App URL | https://web-fc-keegvmxonq3wc.azurewebsites.net/ |
| Foundry project endpoint | https://fc-coffee-shop-keegvmxo.services.ai.azure.com/api/projects/backoffice |
| Storage endpoint | https://stfckeegvmxonq3wc.table.core.windows.net/ |
| Store logins | `storeman001` / store 001; `storeman002` / store 002 |
| Area login | `petender` / stores 001 and 002 |
| Agent configuration receipt | [Installed agent names/versions](src/CoffeeShop.Web/agent-installation.json) |
| Runtime evidence index | [Functional checks and performance limitations](scenario-validation.json) |
| Demonstration | [Executed walkthrough, screenshots and recovery](demoguide/demoguide.md) |

Passwords are not published. Store passwords were supplied separately; the area password is in the original
operator's ignored Windows DPAPI-protected local receipt. See [sign-in instructions](README.md#sign-in).
The earlier directory-administrator question concerned Entra app registration/consent and no longer applies.

### Cost, limits and review boundary

Estimated USD **120-270/month**, not a budget cap.
One P0v3 worker at the fetched retail USD 0.089/hour is USD 64.97/month at 730 hours;
three continuously active workers would be USD 194.91 before inference/storage.
Public authenticated endpoints, no WAF/private networking, one non-HA baseline worker,
shared demo credentials, preview SDK/service and legacy model are explicit limitations.
Reported model inference deprecation is 14 April 2027; migration requires planning.
Agent prose is advisory; structured totals are authoritative. No supplier transmission or ledger posting occurs.

Azure Portal screenshots were not captured. The actual ARM/azd receipts and live service evidence above
are the labeled resource-evidence fallback, not invented portal screenshots.
Actual application screenshots are available in the demonstration guide.

### Cleanup instructions

Stopping the app does not stop App Service plan charges.
Resource cleanup is a separate explicit user decision; **no cleanup was run**.
After reviewing and authorizing deletion of this scenario environment, `azd down` removes its resources.
There are no scenario-created user-login directory applications or users to remove.

Present this deployed reference and its unmet performance targets for explicit suitability review.
Do not approve it, create hack plans/packages, roll out teams or publish on the user's behalf.
