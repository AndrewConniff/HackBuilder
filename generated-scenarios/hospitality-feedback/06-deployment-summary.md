# Deployment Summary — hospitality-feedback

### Current resume result - 2026-10-24

**Preserved design confirmed; local validation passed. Decision required for Azure preparation.**
Canonical portal history records the exact design confirmation at 17:42:42 UTC.
Current cloud authorizations remain empty. The 2026-10-22 consent/target sections below are historical,
not current permission or readiness; no Azure/resource/Graph operation was executed during this resume.

| Current local check | Actual result |
| --- | --- |
| Required local tool/profile and approved NuGet HTTPS probe | Passed at 17:43:21 UTC |
| Web/test/operator restore via MicrosoftPackageFeedProxy | Passed |
| Bicep build/lint of preserved main/workload | Exit 0 |
| Web and operator Release builds | Zero warnings/errors |
| Complete .NET suite | 40 passed, 0 failed/skipped; includes 8 real Azurite and 10 JWT middleware cases |
| Python identity consent/ownership suite | 11 passed; isolated Graph fixtures only |
| Published local app and queued fixture ingestion | All 12 completed; original text, languages and names retained |
| Idempotency, conflict and invalid input | Duplicate accepted; HTTP 409 conflict; HTTP 400 invalid feedback |
| Missing Foundry configuration | Explicit HTTP 503, `mockFallback: false` |
| Playwright and artifact integrity | Passed; local screenshot refreshed, no page errors |
| Preserved diagrams | PNGs decode at 1700 by 1120; SVG/source hashes recorded, no regeneration |
| Cleanup | Only owned temporary emulator/app processes stopped; no listeners left on their four ports |

Evidence: `evidence/resume-local-validation-2026-10-24.json`,
`evidence/resume-installation-validation-2026-10-24.json`,
`evidence/tests/resume-all-2026-10-24.trx`, `evidence/resume-diagrams-2026-10-24.json`,
`evidence/local-application.json`, `evidence/browser-local.json` and `evidence/artifact-integrity.json`.
The legacy `evidence/local-validation.json` remains dated historical evidence; use the new resume receipt.

The JWT role branch previously used the default claim type while inbound mapping was disabled.
Explicit `RoleClaimType = "roles"` now recognizes `Feedback.Operator` without weakening signature, issuer,
audience, lifetime, tenant, operator allowlist or permission checks.
The first new test harness attempts failed because early settings and static signing configuration were incomplete;
the corrected harness exercises the actual middleware with local keys, not a bypass authentication handler.
The first emulator startup exceeded a 40-second wait; owned-process cleanup succeeded.
A bounded 120-second retry with emulator telemetry disabled started successfully and all tests passed.
No denial was bypassed, tool installed, shared default changed or fixture regenerated.

### Consolidated deployment preparation review - not authorization

Use the portal Azure context card to confirm or replace the historical target proposal.
Do not request design confirmation again or ask users to manufacture solution-created client/object IDs.
After exact-target read-only preparation is authorized, refresh subscription eligibility, policies, model lifecycle,
capacity, independent ARM preview and full estimated cost. Historical West US 3/SKU/model evidence is not current proof.

The complete proposed installation comprises the existing RG, UAMI, Storage, project/model/Foundry and Linux B1 app,
six reviewed RBAC grants, plus dedicated scenario-owned API/public-client applications and their service principals.
Expose only delegated `access_as_user`, request v2 access tokens, use loopback PKCE and preserve the operator allowlist.
No Graph application permission, secret, automatic admin consent, app-role assignment
or tenant-policy change is planned.
User-consent policy and actual installer rights remain unknown; administrator involvement is not assumed.
`directoryActions` in a preparation proposal describes future changes only; only an explicit deployment grant
covering those actions permits installation.

Prepared azd hooks perform ownership-checked identity installation/output capture, final-identity ARM what-if,
provisioning/publication ordering and authenticated fixture/chat smoke. Graph operations are not covered by ARM what-if.
Dependent final-identity checks remain pending until authorized installation generates real IDs.
The operator helper builds, but real PKCE, tenant consent, Graph calls and hook execution have not run.
It requires explicit interactive invocation or an approved process-local token; noninteractive jobs never open sign-in.
Its smoke receipt deliberately does not create `scenario-validation.json`.

Historical planning allowance remains USD 15-30/month before model tokens, Storage variability and possible egress.
The historical B1 figure was USD 0.017/hour, USD 12.41 at 730 hours; neither is a refreshed quote.
No additional hosted compute is introduced by the local operator helper or registrations.
Applicable identity licensing, model token rates/workload and final total cost still require preparation review.
No spend cap is enforced. Present one consolidated post-what-if deployment/directory/cost decision,
not foundation/image/initialization/app-rollout cards.

Real model inference, persisted agent invocation, grounded deployed chat, managed-identity access,
live ingestion/idempotency/recovery/poison behavior, authentication denials and semantic negative cases remain pending.
No suitability snapshot, approval, packages, event deployment or publication was created.

## Continuation — Authentication Gate, 2026-10-22 18:36 UTC

**Decision required. Deployment consent received and recognized; no deployment attempted.**
The previous missing deployment-consent statement is superseded by the user's explicit continuation.
Conditional authorization covers only the reviewed reference target/SKUs and expected grants,
provided valid intended existing authentication is established and the repeated what-if stays within scope.

Read-only discovery returned 12 applications and 29 service principals matching scenario-name prefixes.
None exposes enabled `access_as_user` or `Feedback.Operator`. The existing **Feedback API (local dev)**
uses different permissions and is not selected for reuse. No intended registration or consent readiness established.
CLI signed-in object ID and azd ARM-token identity both match
`214d672b-df87-4f3b-94fd-7863032546c1` in the confirmed tenant; the RG is still absent.
All six persisted read-only commands exited 0. No bearer tokens were logged.

Full results, limitations and exact next action:
[authentication gate report](evidence/auth-blocker-2026-10-22.md);
`evidence/auth-discovery-2026-10-22.json` contains dated commands and results.
Provide the intended existing registration/client ID, v2 audience, approved scope/role and consent/token flow,
and confirm the deployer object ID as operator. Otherwise separately authorize a narrow Entra setup.
No directory changes, preview-audience deployment, auth weakening or unrelated registration reuse was attempted.
No new what-if, resource deployment, fixture ingestion or live acceptance ran because the auth gate remains closed.
The earlier capacity and 30-test evidence is inherited, not refreshed.
No validation success JSON, live URL or review snapshot was produced.

## Current Status — Authorized Preflight and What-If, 2026-10-22

**Decision required. No deployment occurred.**

| Target | Actual verified/recommended value |
| --- | --- |
| Account | `petender@microsoft.com` |
| Subscription | `MCAPS-Hybrid-REQ-152516-2026-petender` |
| Subscription ID | `efd64343-6ef4-4926-951f-d3229f38bd76` |
| Tenant ID | `16b3c013-d300-468d-ac64-7eda0820b6d3` |
| New RG / local azd environment | `rg-hospitality-feedback` / `hospitality-feedback` |
| Final recommended region | `westus3` |
| Foundry | Basic, S0, direct child project `hotel-feedback` |
| Model | `gpt-4.1-mini`, `2025-04-14`, Standard, capacity 10; deployment `hotel-analysis` |
| Hosting / Storage | Linux B1 × 1, DOTNETCORE 10.0 / Standard_LRS StorageV2 Hot |
| Final what-if | Provider validation Succeeded, exit 0; 24 Create, 0 Modify, 0 Delete, 2 Unsupported |
| Cloud writes / deployment attempts | 0 / 0 |
| What-if attempts | 2: East US 2 blocked; West US 3 succeeded |
| Live application / inference | None / not performed |

Consent is recorded in `evidence/preflight-consent.json` from the user's current exact scoped instructions.
CLI and azd identity claims match the target tenant and deployer object
`214d672b-df87-4f3b-94fd-7863032546c1`; no bearer token was logged or persisted.
The local azd environment was created and configured; `API_AUDIENCE` is intentionally absent.
The resource group was checked absent before and after previews; no temporary cloud RG was created.
The existing root template already has subscription scope, so no wrapper was necessary.

The first provider what-if failed with `InternalSubscriptionIsOverQuotaForSku`:
B1 VMs current limit 0, usage 0, required 1, minimum requested limit 1.
Tracking ID: `c3d4195b-4daf-418b-99eb-63a8e5c6e579`.
The complete response is preserved in `evidence/what-if-eastus2-blocked.json`.
Read-only regional quota checks supported trying West US 3; no quota increase or SKU change was performed.

All 24 concrete creates are confined to the intended new RG, including the RG itself.
Two expected Storage assignments for the new runtime identity are `Unsupported` because their GUIDs depend
on the future principal ID. No unrelated changes were identified, but those assignments are not fully previewed.
There are six intended RBAC grants overall: Blob and Queue contributor for deployer/runtime, plus two Foundry User.
No RBAC grant was executed. Exact create IDs and limitations are in `evidence/what-if.json`.

Planning cost: Linux B1 USD 0.017/hour, USD 12.41 at 730 hours, plus low-volume Storage allowance USD 1–10/month,
model tokens, and possible egress. Reserve approximately USD 15–30/month before model usage, not a billing quote.
Official dated pricing is saved in `evidence/preflight/retail-web-b1-westus3.json`.
The live catalog labels this model Legacy with inference deprecation `2027-04-14`; disclose before long-term use.

### Exact Final Preview Command

```powershell
.\scripts\Invoke-TargetWhatIf.ps1 `
  -AuthorizationFile evidence/preflight-consent.json `
  -ResolvedParametersFile infra/preview.parameters.json `
  -ExpectedEnvironment hospitality-feedback -PreviewOnly
```

This runs subscription-scope `az deployment sub what-if` with Provider validation and no deployment.
The actual invocation, start/end times, payload and return code are retained in `evidence/what-if.json`.
Local Bicep build and lint passed again after the previews. The application was not changed.
The previous 30-test result is inherited evidence, not a newly rerun suite.

### Required Next Action and Deployment Boundary

1. Supply the existing Entra API registration's exact access-token audience and confirm delegated
   `access_as_user` or application role `Feedback.Operator`, including its tenant/consent readiness.
   No registration may be created implicitly. Confirm the deployer object ID is the intended operator allowlist.
1. Replace the preview-only audience and rerun target-scoped what-if. Review its exact results and final inputs.
1. Only then explicitly authorize reference provisioning, application deployment, fixture ingestion,
   real model/agent/chat acceptance and the negative case for the exact account, subscription, tenant,
   `rg-hospitality-feedback`, azd `hospitality-feedback`, West US 3, and the model/SKUs above.
   Explicitly acknowledge the two what-if-unsupported runtime Storage grants if they remain unresolved.

A general "ok to deploy" does not override the current preflight-only restriction.
No suitability approval, review snapshot, packages, participant deployments, publication or commits were created.
See `evidence/preflight-report.md` for the compact handoff and complete limitations.

## Historical Local Implementation Record

The original local-only record below is preserved; its missing-target/not-run statements describe the earlier phase,
not the current preflight results above.

## Deployment Details

**Local reference implemented and validated. Decision required only for live Azure scope and deployment gates.**

Portable code does not depend on target selection. This corrects the initial design-only stop.
No customer Cosmos resource is generated; Foundry Basic uses Microsoft-managed state as a service caveat.

| Property | Actual result |
| --- | --- |
| Workspace | `C:\HackBuilder\generated-scenarios\hospitality-feedback` |
| Physical workspace | `C:\azd-projects\hospitality-feedback` |
| Azure account/subscription/tenant | Missing; no local default-account instructions found |
| Reference resource group / azd environment | Missing |
| Region/model/version/SKU/capacity | Unresolved parameters; no live query |
| Azure provisioning attempts / retries | 0 / 0 |
| Actual what-if | Not executed |
| Live Azure URL | None |
| Local URL used for bounded checks | `http://127.0.0.1:5080`, not a deployed endpoint |
| Local check result | Build, publish, Bicep build/lint, 30 tests, API and Playwright checks passed |

### What-If Summary

Not run. No create/modify/delete counts exist. Public documentation and local compilation do not prove capacity,
policy compatibility, authorization, what-if safety or deployment success.

## Deployed Resources

None created by this job. No assertion is made about other subscriptions or existing resources.
No Azure login, account switch, target enumeration, provider registration, resource mutation or deletion was run.
`az bicep build`, `az bicep lint` and public module restore were local compilation/research, not target operations.

### Implemented Local Artifacts

- Requirements, cost/WAF/Basic-versus-Standard decisions and implementation/resource mapping.
- Subscription-scoped, target-parameterized Bicep and azd service wiring.
- Six pinned AVM modules: RG, identity, Storage, Foundry, App Service plan and web app.
- Native direct child Foundry project and its role assignments; no published standalone AVM for those paths.
- .NET 10 Razor Pages application, Entra JWT policy and safe-text browser UI.
- Real Blob repository, Queue Storage consumer, outbox reconciliation, idempotency, retries and poison handling.
- Real persisted Foundry prompt-agent registration and invocation over current documented REST `v1`.
- Twelve multilingual fixtures with exact company/person CSV provenance.
- Architecture/runtime PNG and SVG diagrams, matching Python sources and rendering helper.
- Unit, isolated HTTP protocol-contract and real Azurite Blob/Queue tests.
- Fixture import, local validation, API/browser checks and guarded future what-if helpers.
- Demo guide with local walkthrough, future live acceptance, recovery and screenshot fallback.

### Actual Local Checks and Evidence

| Check | Actual result | Persisted evidence |
| --- | --- | --- |
| .NET Release build | Passed; 0 warnings, 0 errors | `evidence/local-validation.json` |
| Bicep build | Exit 0, including AVM restore | Same |
| Bicep lint | Exit 0 | Same |
| .NET tests | 30 passed, 0 failed, 0 skipped | `evidence/tests/local-tests.trx` |
| .NET publish | Exit 0; framework-dependent deployable output | `.local/publish/` |
| Diagram rendering | Both PNG/SVG pairs generated and visually inspected | Root diagram files |
| API/emulator ingestion | All 12 completed; Unicode/names preserved | `evidence/local-application.json` |
| Duplicate and conflict | Identical duplicate accepted; changed payload HTTP 409 | Same |
| Invalid input | HTTP 400 | Same |
| Missing Foundry configuration | HTTP 503, mockFallback=false | Same |
| Playwright | Status table, branding, explicit error and no page errors passed | `evidence/browser-local.json` |
| Screenshot | Actual rendered local page, not a fabricated cloud result | `evidence/local-browser.png` |
| Helper syntax | Five PowerShell scripts parsed; JS syntax/Python compilation passed | Command record below |

The 30 tests comprise 22 domain/protocol-contract checks and 8 actual Azurite integration tests.
The protocol tests use synthetic in-process HTTP fixtures, clearly labeled **not** live agent acceptance.
Actual emulator tests cover Unicode/correlation, duplicate/collision safety, poison handling, correlation isolation,
filtered evidence, interrupted-enqueue reconciliation, five-delivery retry exhaustion and explicit dataset limits.

The application initially accepted HF-0001–HF-0012 as queued.
The worker completed all twelve with attempt=1 and retained stable correlations, as observed in its actual logs.
HF-0001 correlation: `0b65973f6b2b43fea1ffae0fc7071eac`.
HF-0012 correlation: `201f1706c86a40d498530d0358e5a5db`.
The final API check repeated ingestion idempotently and verified all twelve original-language evidence records.

### Exact Commands Executed

From the repository root, the required creation command succeeded:

```powershell
.\scripts\New-AzdScenarioWorkspace.ps1 -ProjectName 'hospitality-feedback'
git --no-pager status --short
```

The working tree already contained user customization changes. They were not reverted, committed or published.
All scenario writes stayed within the requested workspace.

From the scenario workspace:

```powershell
# .NET runtime was present, but no SDK. Installed workspace-local SDK via official dotnet-install.ps1:
# -Channel 10.0 -Architecture arm64 -InstallDir .tools/dotnet -NoPath
# Actual installed SDK: 10.0.402.
npm install --prefix .tools/azurite azurite --no-audit --no-fund
npm install --prefix .tools/render @resvg/resvg-js playwright --no-audit --no-fund
node .tools/render/node_modules/playwright/cli.js install chromium
python scripts/generate_fixtures.py --catalog-root C:\HackBuilder
node .tools/azurite/node_modules/azurite/dist/src/azurite.js `
  --silent --skipApiVersionCheck --location .local/azurite `
  --blobHost 127.0.0.1 --queueHost 127.0.0.1 --tableHost 127.0.0.1
.\scripts\Validate-Local.ps1 -Dotnet "$PWD\.tools\dotnet\dotnet.exe" -WithAzurite
.\.tools\dotnet\dotnet.exe publish src/HospitalityFeedback.Web `
  -c Release --no-restore --nologo -o .local/publish
```

For the bounded application check, the real app was started with Development, UseAzurite=true,
LocalAnonymous=true and ASPNETCORE_URLS=http://127.0.0.1:5080:

```powershell
.\.tools\dotnet\dotnet.exe run --project src/HospitalityFeedback.Web `
  -c Release --no-build --no-launch-profile
.\scripts\Test-LocalApplication.ps1
node scripts/browser-local.cjs
python 03-architect-diagram.py
```

Additional successful syntax checks:

```powershell
# Each scripts/*.ps1 was parsed with System.Management.Automation.Language.Parser.ParseFile.
node --check src/HospitalityFeedback.Web/wwwroot/js/app.js
python -m compileall -q scripts 03-architect-diagram.py 04-runtime-diagram.py
python scripts/validate_artifacts.py
```

### Timing, Failure and Retry Record

Final measured core validation, `2026-10-22T17:37:48Z`–`17:38:12Z`:

| Command phase | Seconds | Exit |
| --- | --- | --- |
| .NET build | 1.360 | 0 |
| Bicep build | 11.620 | 0 |
| Bicep lint | 5.657 | 0 |
| Tests | 3.539 | 0 |
| Architecture rendering | 1.063 | 0 |
| Runtime rendering | 1.161 | 0 |

Publish completed at `2026-10-22T17:38:13.9840993Z`.
Final local API check completed at `17:41:46Z` (0.5 seconds, repeating already-processed fixture IDs).
Playwright completed at `17:41:49.613Z`.
Dependency installation and earlier research were not stopwatch-measured; their durations are not invented.

Course corrections:

1. Initial default-account search found no target; first attempt stopped too broadly.
   User clarified portable local implementation should continue; no Azure gate was bypassed.
1. Host lacked an SDK and Graphviz/Python diagram packages.
   Installed SDK locally; used source-preserving SVG/resvg rendering instead of global Graphviz.
1. Direct NuGet TLS queries failed in Python and PowerShell.
   Switched to the official Microsoft public package mirror; no TLS verification was disabled.
1. Several guessed public documentation paths returned 404.
   Followed the actual current `agents/quickstarts/prompt-agent` and Responses API documentation.
1. First build failed on an obsolete ManagedIdentityCredential constructor.
   Changed to explicit ManagedIdentityId for the user-assigned runtime identity; clean rebuild passed.
1. First Bicep build failed on runtime-dependent parent/role-assignment names.
   Used deterministic names and explicit dependencies; subsequent build and lint passed.
1. A newline-ID unit test failed. Corrected regex anchors to absolute `\A`/`\z`.
   A clean non-incremental recompile removed stale output; all tests passed.
1. Initial API harness timed out despite the worker completing all records.
   Inspection showed twelve completed statuses; fixed PowerShell's nested-array enumeration in the harness.
   Rerun passed API and browser checks. This was not an ingestion failure.
1. A final Git status probe from the external physical workspace returned exit 128 (not a Git repository).
   Repeated with `git -C C:\HackBuilder --no-pager status --short -- generated-scenarios/hospitality-feedback`;
   the repository-root probe completed with no tracked scenario changes.

See `evidence/initial-deployment-summary.md` for the preserved, superseded first-attempt log.
Final artifact-integrity checks passed at `2026-10-22T17:44:51.378830Z`.
They verified exact catalog mappings, the compiled Foundry direct project, no customer Cosmos/hub footprint,
valid PNG files and separation from live acceptance/approval/composition.
Both temporary local processes were stopped after those checks: web shell 33 and Azurite shell 21.
Listener inspection found no listening sockets on ports 5080, 10000, 10001 or 10002.
The unfilled authorization example was tested against `Invoke-TargetWhatIf.ps1`.
It refused execution with the expected explicit-authorization error before any Azure command.
The helper was reparsed successfully. Artifact integrity was rechecked at `2026-10-22T17:45:24.301470Z`.

## Outputs and Live Acceptance Boundary

Local evidence is explicitly scoped and does not substitute for:

| Required live check | Current state |
| --- | --- |
| Account/project/model deployment | Not executed |
| Model inference | Not executed |
| Real persisted agent invocation | Not executed |
| Grounded application chat | Not executed |
| Runtime MI/RBAC | Not executed in Azure |
| Azure queuing/processing and negative case | Not executed; emulator-only evidence exists |
| Live URL and browser acceptance | Not available |

No passed `scenario-validation.json`, review snapshot, suitability approval record, hack plan,
`nextsteps.MD`, package, composition launch or participant deployment is created.
Temporary local servers are stopped before return; use the README to restart them.

### Exact Remaining Authorization

One follow-up must explicitly identify and authorize live preflight for:

1. Selected account, subscription name/ID and tenant ID.
1. Exact reference RG names, permission to create them if needed, and exact azd environment.
1. Target-scoped read-only policy/provider/region/model/quota/capacity checks and actual what-if.

Region/model selection remains evidence-driven; no live capacity is inferred from documentation.
Supply the existing API audience and operator object IDs as deployment configuration.
After actual what-if review, separately confirm deployment to that exact target.
The filled example file, a build request, permissive CLI flags or existing packages are not consent by themselves.
No further clarification of Microsoft's internal Basic persistence is requested or required.

### Costs and Limitations

Planning allowance: USD 20–70/month hosting and USD 1–10/month low-volume Storage/diagnostics, plus model tokens.
This is not a live regional quote. Exact model cost, quota/capacity and Azure Policy compatibility remain unverified.
One B1 instance/LRS is modest reference infrastructure, not production HA.
Public TLS service endpoints, token-input UI, 100-record bound and agent-registration privileges
are documented trade-offs.
Quote/source validation cannot establish semantic entailment or language accuracy without live review.
No Azure spend was incurred by this job's operations.

After authorized deployment and full live acceptance, present the reference and stop for explicit suitability approval.
Hospitality composition support must be decided explicitly later; never silently map to another industry.
