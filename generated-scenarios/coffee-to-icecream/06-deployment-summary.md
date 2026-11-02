# Coffee-to-icecream deployment and acceptance summary

> Updated by az-01-conductor agent | 2026-10-30

## Deployment Details

| Property | Actual result |
| --- | --- |
| Status | Deployed; latest read-latency and narrative-grounding acceptance failed |
| Workspace | Isolated target under adjacent azd-projects, exposed through generated-scenarios junction |
| Industry / units | Hospitality & Travel / operations |
| Target account | Existing CLI and azd identity matched the user-selected account |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76 |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Region | Sweden Central; exact-target read-only preflight passed |
| Environment / RG | coffee-to-icecream-ref / rg-coffee-to-icecream-ref |
| What-if / cloud changes | Reviewed 22 creates, 0 modifications/deletions, including five role assignments; installed |
| Application URL | https://web-ic-gyhmp4vgxvkwy.azurewebsites.net/ |
| Consent | Actual user response: "Approve reviewed deployment and runtime validation" |

This deployment decision did not approve working-scenario suitability, composition, event rollout,
directory writes, shared-default changes, publication or resource cleanup.
No passed validation index or suitability snapshot exists; the current validation index explicitly says failed.

### Executed local checks

Commands below ran from repository root unless stated otherwise.

```powershell
python scripts\scenario_adapt.py prepare coffee-to-icecream
python generated-scenarios\coffee-to-icecream\scripts\create_fixtures.py --repository C:\HackBuilder
dotnet build generated-scenarios\coffee-to-icecream\src\CoffeeShop.Web\CoffeeShop.Web.csproj --configuration Release
dotnet run --project generated-scenarios\coffee-to-icecream\tests\Operations.Tests\Operations.Tests.csproj `
    --configuration Release
node --check generated-scenarios\coffee-to-icecream\src\CoffeeShop.Web\wwwroot\js\workspace.js
az bicep build --file generated-scenarios\coffee-to-icecream\infra\main.bicep `
    --outfile generated-scenarios\coffee-to-icecream\infra\local-build.json
az bicep lint --file generated-scenarios\coffee-to-icecream\infra\main.bicep
```

- Preparation: passed; source manifest and artifact digests matched confirmed intake.
- Fixture generation: passed; ten stores, two areas, ten complete CSV packets, exact catalog provenance.
  Malformed company records 7, 11, 25 and 33 were rejected without catalog edits.
- .NET build: passed with zero warnings/errors on initial compilation; final assertion run rebuilt successfully.
- Focused executable suite: **50 assertions passed**, including all ten deterministic fixtures,
  exact money/units, invalid recipes/units/negative stock, store/area isolation before reads/inference,
  variable worker counts, bounded concurrency, failed/missing evidence, duplicate receipt, cancellation,
  persisted human review, stale/repeated order/import safety and login lockout.
- The ten-manager test uses an explicit test-only gateway; no fake implementation is registered in the app.
  It proves the local scheduler accepts ten requests, not Foundry inference or live latency.
- JavaScript syntax: passed.
- Bicep build/lint: passed after correcting Log Analytics AVM parameter and role-assignment dependency wiring.
  Local template compilation made no Azure subscription queries.
- Lifecycle scripts: PowerShell AST parse passed. Guard refused absent target approval before any cloud command.
- Architecture/runtime PNGs: rendered; PNG integrity verified with repository Pillow.
- Target catalog metadata: curated through scenario_catalog.py, with source provenance and local-only summary.
- Baseline file decisions: validated through scenario_adapt.py reconcile; rerun after final artifact changes.
- Added exact scoped synthesis-ledger, waste, profit, closing-stock and area-isolation assertions.

Diagram command:

```powershell
$env:PATH = 'C:\Program Files\Graphviz\bin;' + $env:PATH
.\.venv\Scripts\python.exe generated-scenarios\coffee-to-icecream\03-architect-diagram.py
```

Graphviz was already installed but absent from this process PATH; only command-local PATH changed.
No package or system tooling installation was performed.

### Local UI and failure/recovery observations

- The unauthenticated local homepage rendered HTTP 200 in the integrated browser.
- HTTP session creation failed because secure antiforgery cookies require HTTPS; no TLS control was relaxed.
- An explicit Development HTTPS host using the existing developer certificate passed test-client checks:
  session authenticated false with CSRF token; anonymous store access 401; missing-CSRF login 400.
- Integrated-browser HTTPS navigation rejected the local certificate. No shared trust settings changed.
  Authenticated responsive/browser screenshots remain pending; no screenshots or Azure browser proof fabricated.
- A local preview initially started as Production and correctly rejected missing App Service HOME.
  It was rerun with explicit Development configuration, not a production bypass.
- A repeat build encountered apphost locks from owned preview children. Those exact PIDs were identified,
  stopped and the full focused suite reran successfully. Temporary hosts were not left running.
- A Pillow check initially used system Python; rerunning with the existing repository venv passed.
- CSV/fixture equality initially compared serialized decimal formatting; changed to value/sequence equality.
  Exact decimal arithmetic is preserved; no numerical acceptance threshold was loosened.
- Catalog refresh initially rejected an unsupported editable artifacts field.
  Removed that field; the helper now derives allowlisted artifacts itself and refresh/reconciliation pass.

These are local construction results, not substitutes for the separate deployed evidence below.

### Authorized readiness on 30 October 2026

This section records the earlier read-only preparation, not the current installation authority.
The later explicit deployment response above superseded the earlier no-write boundary for the reviewed scope.

Actual review responses: `designReview=Accept this design for readiness preparation`,
`authorizePreparation=true`.
The grant covers exact-target CLI/azd identity, own deploying principal, region/model/SKU/quota,
effective access, policies, prices and ARM what-if.
It does not authorize provisioning, role grants, Entra writes, shared-default changes or suitability approval.
At that earlier stage, no destination environment or deployment-scope approval had been created.

The final collector retained 23 successful observations at `2026-10-30T03:50:35.563030+00:00`.
It compares identity before subscription discovery, records command failures explicitly and exits unsuccessfully
if any required collection command fails. Token material is not retained.

| Readiness gate | Result |
| --- | --- |
| CLI / azd identity | Matched selected account, subscription and tenant; no sign-in/default changes |
| Own principal | Resolved 214d672b-df87-4f3b-94fd-7863032546c1; no other Entra user lookup |
| Existing grants | Inherited Owner and Foundry User verified and reused, not duplicated |
| Providers | CognitiveServices, Web, Storage, OperationalInsights, Insights, Authorization all Registered |
| Foundry/project | Readiness metadata/what-if passed; real invocation was tested later |
| Exact model | gpt-4.1-mini / 2025-04-14 / GlobalStandard; Responses and agentsV2 supported |
| Lifecycle | Legacy; API reports inference deprecation 2027-04-14; explicit deployment acceptance required |
| Model quota | Global 20/5,000 units; capacity API reports 4,980 available against requested 300 |
| Model capacity unit | 1,000 TPM/unit; requested 300,000 TPM; observation does not reserve allocation |
| Linux P0v3 | Listed in Sweden Central; Web total regional VMs 0/11 covers maximum three workers |
| .NET runtime | DOTNETCORE\|10.0, Active LTS, listed end of life 2028-11-14 |
| Storage/logs | Regional provider/SKU metadata and exact-target what-if passed; LRS restrictions empty |
| Effective policy | 20 direct/inherited assignments inspected; no blocking what-if denial observed |
| Final what-if | Succeeded: 22 creates, 0 modifications, 0 deletions, including five role assignments |
| Allocation/runtime | Not attempted during readiness; later actual results are recorded below |

West Europe and UK South have the same model capacity observation and supporting provider/SKU metadata.
West Europe reports Web total regional VMs 0/10; UK South reports P0v3 VMs 0/360.
Neither alternative received a complete target what-if; Sweden Central is the selected common region.
Global quota is shared, not three separate allocations.

The five proposed role assignments are deployer Table Data Contributor and Log Analytics Contributor,
app Table Data Contributor and project Agent Consumer, and project-identity account Foundry User.
Redundant new human Contributor and Foundry User grants were removed after observing inherited access.
Resolved Agent Consumer GUID: `eed3b665-ab3a-47b6-8f48-c9382fb1dad6`.
No role assignment was executed during read-only readiness.

Effective policies include governance deny/modify controls and mandatory MFA for user resource writes.
Classic resources and ProvisionedManaged deployments are prohibited; neither occurs in the target template.
The storage public-network modification policy has an explicit `SecurityControl=Ignore` tag exclusion.
The reviewed template already carries that repository-standard tag; deployment review must explicitly accept
this public-network security exception alongside public TLS/no WAF, rather than implying private-only compliance.
No new policy exemption, policy modification, tenant consent or security-control relaxation was executed.
Future MFA/policy denials stop affected work; no alternate identity or network bypass is authorized.

Evidence: `evidence/readiness.json`, `evidence/what-if.json`, `evidence/prices.json`,
`evidence/policy-definitions.json`, `evidence/policy-rule-details.json` and `evidence/web-runtimes.json`.
The collector includes inherited policy and exact deployable-capacity checks, not only public model listings.

Executed final commands:

```powershell
python generated-scenarios\coffee-to-icecream\scripts\check_readiness.py --repository C:\HackBuilder
python -m unittest discover -s generated-scenarios\coffee-to-icecream\tests -p test_readiness.py
az bicep lint --file generated-scenarios\coffee-to-icecream\infra\main.bicep
az deployment sub what-if --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --location swedencentral --name icecream-reference-preview `
  --template-file generated-scenarios\coffee-to-icecream\infra\main.bicep `
  --parameters environmentName=coffee-to-icecream-ref location=swedencentral `
    principalId=214d672b-df87-4f3b-94fd-7863032546c1 `
    agentConsumerRoleId=eed3b665-ab3a-47b6-8f48-c9382fb1dad6 `
    modelName=gpt-4.1-mini modelVersion=2025-04-14 modelCapacity=300 `
  --result-format FullResourcePayloads --no-pretty-print --output json
```

Results: collector passed all 23 queries; two fail-closed collector tests passed using mocked failures;
Bicep lint passed; final ARM what-if succeeded with the counts above.
An earlier preview predicted 24 creates; final 22 reflects removal of two redundant human grants.
These readiness results predate deployment and subsequent grounding repairs; they do not prove live latency.

Readiness recovery notes:

- The initial exact quota search used `gpt-4.1-mini`, but the actual standard quota key is `gpt4.1-mini`.
  Correcting that exact key revealed available GlobalStandard quota; no quota was created or increased.
- This CLI has no `az storage account list-skus`; the collector now uses the documented Storage SKUs ARM API.
- Windows CMD split multi-parameter URLs and unquoted parentheses.
  The collector now invokes the already-installed Azure CLI Python runtime, using separate URL parameters.
  No CLI installation or shared shell/security setting changed.
- The runtime-list API now returns structured records; querying its actual runtime/version fields confirmed .NET 10.
- Retail meters distinguish spaces from hyphens and separate Log Analytics from Azure Monitor.
  Final costs use exact base-model GlobalStandard and Analytics Logs meters, not fine-tuning or Basic Logs rates.

Final source recheck: the manifest digest still matches, but the current preview no longer includes
the source's compiled `infra/main.json`; therefore its artifact digest has changed.
Every remaining baseline file hash matches, with no changed or added source paths.
Do not claim the current aggregate source fingerprint is unchanged.
The confirmed request and original baseline remain intact; no source restoration or recopy was performed.
The target already intentionally removed that copied compiled JSON and independently rebuilt/previewed its Bicep.
See `evidence/source-recheck.json`; any future recopy must review the then-current source fingerprint.

### Approved installation and repair history

From the destination workspace:

```powershell
azd up --no-prompt
.\scripts\Initialize-Scenario.ps1
azd deploy web --no-prompt
```

- The first `azd up` stopped before provisioning: azd added a destination-owned UserSecretsId to the csproj.
  The scope guard detected it; the parallel package step was cancelled. No guard was bypassed.
  Verified this was the only reviewed input change, retained destination metadata and recorded a technical amendment.
- Retried `azd up`: succeeded in 7 minutes 16 seconds, including reviewed resources, roles, initialization and publish.
  Twelve unique private local accounts and three real version-1 agents were installed without overwriting live stock.
- Semantic inspection found version-1 waste explanations contradicted deterministic ledgers.
  Preserved those immutable reports and runtime evidence; did not delete or rewrite historical reviewed artifacts.
- Version 2 supplied authoritative ledgers and revised prompts; guarded initialization and app publish succeeded.
  All 73 HTTP checks passed, but narrative review still found unsupported variance and ambiguous spoilage wording.
- Version 3 supplies scoped authoritative ledger AND final-stock snapshots and tighter prompts.
  Fifty local assertions passed; guarded initialization and `azd deploy web --no-prompt` succeeded.
  The final publish took 30 seconds. All three owned agent endpoints now select version 3.
- These were in-scope corrective changes, not new infrastructure, model, role, network or spending permissions.
  The private deployment receipt preserves the actual user response, original digest and technical amendments.
  Subsequent documentation updates do not assert that the installation-time digest is the latest document fingerprint.

### Actual HTTP, performance and semantic acceptance

The session-owned `verify_live_reference.py` uses verified HTTPS and an independent persistent connection
per manager. It reads private credentials internally and does not log passwords, cookies or CSRF tokens.
Ten store logins precede 100 reads and ten concurrent complete real closes.
Both area managers then perform five-store closes. Failed operations remain in measurements.

| Retained run | Read p95 / failures | Close p95 / failures | Overall result |
| --- | --- | --- | --- |
| First fresh-connection attempt | 4.5267 s / 0 | 11.2629 s / 0 | Failed read target |
| Version 1, persistent HTTPS | 0.3631 s / 0 | 6.3387 s / 0 | HTTP/performance passed; semantics later failed |
| Version 2, persistent HTTPS | 0.3284 s / 0 | 9.1784 s / 0 | HTTP/performance passed; semantics still failed |
| Version 3, persistent HTTPS | 3.4644 s / 0 | 7.4583 s / 0 | Failed read target; semantic issues remain |

The final version-3 run completed at `2026-10-30T04:40:04.220568+00:00`.
All 73 HTTP business/security assertions passed; overall run status remains failed, not conditionally passed.
Area closes took 9.0754 and 8.5878 seconds; all worker/synthesis receipts identify version 3.
Server HTTP diagnostics independently show 80 successful store requests in the affected ten-second bucket,
server p95 3,242 ms and maximum 3,285 ms. The client spike cannot be dismissed as TLS-only overhead.
Root cause remains unresolved. No samples were removed, thresholds loosened or passing retry substituted.

The business checks include anonymous/CSRF denial, secure cookies, store/area isolation, unique real responses,
human report review and replay, CSV import/duplicate, stale order/report conflicts and human order approval/replay.
The original CSV was already committed by an earlier test. Revalidation used the identical business packet
with one additional newline for version 2 and two for version 3, changing raw packet identity only.
Each duplicate check reused that exact new packet; no quantities, business dates or expectations were changed.

Store 001 remains exact: final vanilla 11.3 L, net sales 598.50, COGS 99.40,
separate waste 3.00, labor 142.00, occupancy 45.00 and profit 309.10.
Version 3 correctly describes waste as separately expensed and already removed from closing stock.
However, both margin and synthesis still describe costs as steady without historical evidence.
Stock commentary also mentions hypothetical profit variance without a supplied profit baseline.
These are residual grounding defects, not certified business explanations.
Structured figures remain authoritative; human review is not presented as fixing those model errors.

### Actual operator, account and coordination proof

The deploying user's own Entra credentials, not the app identity, passed:

- Table listing and disposable entity create/read/update/delete.
- Foundry disposable agent create/list/read/update, actual model invocation and delete.
- App control-plane atomic probe-tag merge/read/remove, preserving existing tags.
- Log Analytics saved-search create/read/update/delete and actual diagnostic queries.
  One retained diagnostic observation counted 5,439 rows across eight tables.

All disposable operator entities, agent, saved search, probe tags and private test account were cleaned up.
The real lockout test denied five bad passwords, then denied the correct password and revoked a prior session.
Private probe credentials were removed; reference accounts remain available only in the restricted access file.

Final version-3 worker recovery completed at `2026-10-30T04:43:14.336928+00:00`:
temporarily pointed the stock agent setting to a nonexistent test name, restarted and performed a real close.
HTTP 503 trace `0HNPM80BDQCV8:00000004`; close count stayed 47 -> 47.
The `finally` path restored the actual agent name and restarted; a real successful close increased the count to 48.
No incomplete report was persisted. Do not repeat this disruptive test during somebody else's demonstration.

An attempted optional CLI log query required an absent extension and failed without installation.
The existing REST API then returned actual server timing evidence; no CLI settings or tools changed.
The bounded console warning query returned no matching rows, not a diagnosed root cause.
Model/token aggregate queries returned no rows.
No measured token charges, total bill or billed per-close cost is claimed.

Evidence: [latest HTTP run](evidence/http-acceptance.json),
[worker recovery](evidence/worker-recovery-acceptance.json),
[server latency](evidence/read-latency-server-observation.json),
[operator SDK checks](evidence/operator-sdk-acceptance.json),
[operator ARM checks](evidence/operator-arm-acceptance.json)
and [lockout](evidence/lockout-acceptance.json).
Earlier failed and version-1/version-2 runs are retained separately in the evidence directory.

## Deployed Resources

| Actual resource | Configuration |
| --- | --- |
| rg-coffee-to-icecream-ref | Reviewed target resource group, Sweden Central |
| ic-coffee-to-i-gyhmp4vg | Foundry S0, direct child project backoffice |
| gpt-4.1-mini | 2025-04-14, GlobalStandard, 300 units / 300,000 TPM |
| web-ic-gyhmp4vgxvkwy | .NET 10 application, system-assigned managed identity |
| plan-ic-gyhmp4vgxvkwy | Linux P0v3, baseline one, maximum three |
| sticgyhmp4vgxvkwy | Standard LRS, IceCreamBackOffice Table |
| log-ic-gyhmp4vgxvkwy | PerGB2018, 30 days, 1 GB/day configured ingestion cap |

No directory app, tenant permission, private network, management VM, supplier connection or payment integration.

### Management access and remaining acceptance

The actual Windows operator host used the deploying user for installation and own-user control/data CRUD.
The deployed App Service uses its own managed identity for Table and Foundry calls.
Private-host/outside-private-network tests are not applicable to this reviewed public-TLS architecture.
Local app accounts grant no Azure administration rights.

Remaining: diagnose/remediate read latency, eliminate unsupported narrative claims, then fresh runtime acceptance.
The integrated browser shows the actual Azure HTTPS sign-in page; authenticated UI/responsive captures remain unrun.
Do not expose passwords/cookies to bridge the browser boundary. Secure manual sign-in may be needed.
Only after required checks pass should a fingerprinted suitability review be created and explicitly approved.

## Outputs (Expected)

These are actual target outputs, not future event or package defaults.

| Output | Producer |
| --- | --- |
| AZURE_RESOURCE_GROUP | rg-coffee-to-icecream-ref |
| AZURE_WEB_NAME | web-ic-gyhmp4vgxvkwy |
| AZURE_WEB_URL | https://web-ic-gyhmp4vgxvkwy.azurewebsites.net/ |
| FOUNDRY_MODEL | gpt-4.1-mini |
| STORAGE_ENDPOINT | https://sticgyhmp4vgxvkwy.table.core.windows.net |
| Actual agent names/versions | coffee-to-icecream-stock, -margin, -close; each version 3 |
| Local app passwords | Twelve unique destination credentials, restricted .private file only |

Foundry project endpoint:

```text
https://ic-coffee-to-i-gyhmp4vg.services.ai.azure.com/api/projects/backoffice
```

Official USD retail rates observed on 30 October: Linux P0v3 $0.089/hour, global base-model input/output
$0.40/$1.60 per million tokens, Analytics Logs $2.99/GB, LRS Tables $0.045/GB-month and
$0.00036 per 10,000 transaction operations.
At 10,000 five-store closes/month, assumed 12,000 input/3,000 output tokens each, ten GB of logs,
one GB Table data and one million Table operations: approximately **$191-321/month** for one-to-three workers.
Thirty GB logs instead: approximately **$251-381/month**.
These are workload estimates, not quotes or monetary caps; tax/support, unusual egress, additional retries
and external governance charges are excluded. The 1 GB/day log cap is not a hard spending ceiling.
Public endpoints/no WAF, the policy tag exception, Legacy model retirement and preview SDK runtime
compatibility are explicit deployment review items.
The reviewed deployment/runtime scope was explicitly authorized.
Scenario suitability, hack composition, event rollout, cleanup and publishing remain unauthorized.
