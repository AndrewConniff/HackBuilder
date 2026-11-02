# Deployment summary: Fourth Coffee restaurant agents

## Deployment Details

### Current local repair: 2026-10-24, run 30bc1eeb

**Local repair is saved but validation is incomplete. No cloud operation ran in this attempt.**
All canonical decisions/history were read. The recorded answer "Confirm design for local repair" confirms only
the existing design and local implementation; the current authorization list remains empty.
Shared identity observations were reused without sign-in, target changes or a new identity questionnaire.
The old Graph denial was neither retried nor reclassified as a fresh observation.

The same reference now has Entra JWT middleware, scoped API-token cookie exchange and MSAL browser sign-in.
Synthetic staff helpers remain only for explicit isolated Testing hosts; runtime IaC contains no staff passwords,
HMAC signing secrets or deployed synthetic fallback.
Guest sessions, deterministic transaction APIs, domain data/seed assets and shared resource definitions are retained.
The restored identity helper preserves the historical ownership marker, role IDs and installed object IDs.
Its read-only verifier is prepared but has not run against Azure/Graph.
Only the scenario-owned SPA callback repair is an available directory write; consent POSTs remain prohibited.

`azure.yaml` now has one ordered postprovision runtime hook.
It checks the current canonical writer and exact deployment authorization bound to the installation-plan digest,
then verifies the owned identities, installed quota, immutable image, fixtures/agent versions and runtime preview.
The complete proposal is `scripts\reference-installation-plan.json`, not a hack package plan or a grant.
No hook, initializer, image publication or runtime rollout was executed.
The retained historical operator-specific consent remediation still needs actual authorized read-only verification.

| Actual local command/check | Result |
| --- | --- |
| `npm install --ignore-scripts --no-audit --no-fund`, then `npm run vendor` in the web project | Passed |
| Approved-proxy `dotnet restore` after adding required Cosmos runtime dependency | Passed |
| Targeted authentication/API/domain test run | Passed: 50/50 |
| Full .NET suite, including new proxy propagation and Chromium checks | Failed: 51 passed, 1 browser failure |
| Runtime Bicep build and runtime/shared Bicep lint | Passed, exit 0 |
| `docker info --format '{{json .OSType}}'` | Passed: `linux`; no new image build |
| Python validation suite | CLI permission denial before execution; not passed |
| Optional Ruff module | Not installed; no shared tooling installed |

The initial targeted .NET run exposed two local defects: test hosts inherited Development configuration,
and Cosmos SDK initialization requires its Newtonsoft.Json assembly even with System.Text.Json serialization.
Test hosts now explicitly select isolated Testing configuration. Newtonsoft.Json 13.0.4 is a pinned dependency;
the prior missing-dependency suppression is removed and both lock files were refreshed using the approved feed.
The corrected targeted run passed. Original failing results remain in the evidence directory.

The full browser run successfully started and queried its owned local app, rendered the guest/staff shells,
loaded same-origin MSAL, showed the explicit unconfigured-Entra error and rejected anonymous staff data access.
It then failed on `#board`: expected "No staff data loaded", actual empty text after `clearStaff()`.
The real Chromium process and owned app were cleaned up by the test's existing `finally` path.
The mobile iteration was not reached; do not claim full browser acceptance.
That empty-state mismatch still requires a local fix and rerun after the execution blocker is resolved.

The denied command was the Python unittest discovery invocation with TEMP/TMP scoped to this run directory,
redirecting output to `evidence\local-entra-repair-30bc1eeb\python-tests.txt`.
The CLI returned:

```text
Permission denied because no interactive user response was available.
Retry in an interactive session so the user can approve it,
or try an alternative that does not require this permission.
```

No permission scope, request ID or structured approval metadata accompanied the denial.
No alternative route or retry was attempted. This is `workflow-error`, not an inferred workstation problem.
Backend diagnosis must identify and resolve the missing execution permission under the same restrictions.
Do not widen consent, install shared tools or ask for an unidentified business approval.
Only then rerun the original validation and finish the browser correction.

Actual .NET TRX/logs, browser output and runtime ARM compilation are retained in
`evidence\local-entra-repair-30bc1eeb\`.
No current region/quota/ownership/what-if, Entra sign-in, real model/agent/business/load/fault result is claimed.
The six-service design, supporting dependencies and historical Central US candidates/costs remain unchanged.
After local validation, obtain the missing exact-target preparation scope before resource/directory reads,
then present one consolidated end-to-end deployment review with actual incremental what-if, identity scope and cost.
No suitability approval, snapshot, composition, event deployment or publication is authorized.

### Earlier local resume boundary: 2026-10-24, run 34a01313

The same existing reference was recovered without replacing runtime, infrastructure, diagrams or seed assets.
The current portal state has retained local tool consent, no design confirmation and no cloud authorizations.
The table and installation reports below describe earlier attempts only; their grants are not imported.
No Azure/resource/directory query or write ran in this attempt.
The historical denied consent write was not retried, and shared CLI defaults were not changed.

Local intake validation passed 25 catalog, provenance, scope, template and acceptance-contract checks.
Evidence: `evidence\resume-34a01313-intake-validation.json`.
The architecture assessment now records the synthetic-runtime/Entra-requirements discrepancy and proposes
repairing the existing surfaces to satisfy Entra requirements without a deployed synthetic fallback.
Historical verification automation imports retired installer symbols and requires local repair before use.
No application build, current authentication, model/agent invocation, runtime or load result is claimed.

Next boundary: portal design confirmation of that repair and the preserved end-to-end architecture.
After confirmation, complete local implementation/validation, then exact-target preparation and one consolidated
deployment review including identity dependencies, actual incremental what-if and costs.
Do not split technical deployment ordering into routine foundation/image/initialization/app approval cards.
No suitability snapshot, composition, event deployment or publication is authorized.

| Property | Observed value |
| --- | --- |
| Status | Shared infrastructure deployed; stopped on actual operator delegated-consent denial |
| Evidence date | 2026-10-24 UTC |
| Account | `petender@microsoft.com` |
| Subscription | `efd64343-6ef4-4926-951f-d3229f38bd76` |
| Tenant | `16b3c013-d300-468d-ac64-7eda0820b6d3` |
| Resource group | `rg-resto-scale-agent`; 14 resources listed at `2026-10-24T17:42 UTC` |
| Distinct azd environment | `resto-scale-agent`; initialized locally with explicit target values |
| Current validation target | `centralus`; shared provisioning succeeded; runtime validation not started |
| Preparation authorization | Canonical Central US read-only scope recorded `2026-10-23T23:31:37.857139Z` |
| Installation authorization | Decision `3f3d19a20079404991c95dfe6d23b93f`; consent denial stops execution |

### Current consolidated installation: 2026-10-24, 17:42 UTC

**Shared infrastructure is deployed successfully; the full reference remains incomplete.**
The recorded consolidated grant was consumed in its exact Central US scope, without changing shared defaults.
Fresh identity, ownership/name availability, provider, policy/RBAC, exact-model/quota/capacity and regional
checks preceded writes. Bicep build/lint passed; the fresh full preview matched the reviewed
**33 creates, zero modifies/deletes and 13 unresolved identity-dependent expansions**.
The infrastructure fingerprint remains
`2371ff53fd0c9ff35ca3e337f30911f0bd4b4bf019dcd27f13cb0456dfb25ed7`.

The group was recreated with the reviewed ownership tags.
`azd provision` used the existing environment with explicit subscription and region:

```powershell
azd provision --environment resto-scale-agent `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 --location centralus `
  --cwd C:\HackBuilder\generated-scenarios\resto-scale-agent --no-prompt
```

The command exited **0**. Root deployment `resto-scale-agent-1792863260` and all listed nested deployments
are **Succeeded**. ARM recorded `PT4M20.805905S`; azd reported four minutes 52 seconds.
The corrected three Cosmos grants are installed at the full account/database scope.
The replacement vault and signing key are installed, retaining their security controls.
The newly created environment's actual Consumption quota is **0/500 cores**; **0 + 28 <= 500** passes.
This is installed quota evidence, not a performance result or reserved allocation.

The authorized installer created and verified exactly two marker-owned staff applications/service principals.
It captured real object/client IDs, roles, v2 configuration and assignment-required access automatically.
Read-only reconciliation verifies the approved operator's **Manager** API assignment and default client assignment.
No other users/groups were assigned.
The final consent write failed:

```text
POST https://graph.microsoft.com/v1.0/oauth2PermissionGrants
Forbidden: Authorization_RequestDenied
Insufficient privileges to complete the operation.
2026-10-24T17:42:00Z
request-id: da04fa78-673a-4464-a535-17151194801c
```

**Stopped immediately after the actual authorization denial.**
The exact owned client/API grant list subsequently returned `value: []`.
No denied command was retried through another route. No elevation, broad Graph permission,
tenant-wide consent, security relaxation or alternate credentials were attempted.
No image publication, fixture/agent initialization, runtime apps, live business/agent/load tests,
suitability snapshot, hack packages or team deployment ran.
The shared resources and directory objects are retained and may incur charges; no cleanup is authorized.

Two earlier setup-harness defects were corrected before this denial:
the verified tenant object ID, not a B2B guest UPN string, identifies the approved operator;
the owned principal's assignment collection is enumerated without an unsupported `principalId` filter.
The original failures remain recorded. These were local/API-query defects, not permission denials.
Five offline tests now cover idempotency, exact operator/ownership, fail-fast denial and read-only consent verification.

All actual commands, UTC timestamps, exit codes, infrastructure outputs, grants and failure text are retained
under `evidence\installation-e13812c5\`. The identity receipt is `evidence\identity-installation.json`.
Output names are normalized case-insensitively to uppercase without changing their actual deployed values.
The discovered project endpoint comes from the real direct child project's `properties.endpoints`.
No endpoint, digest, agent version or authentication success was invented.

**Required external remediation:** a tenant-authorized consent operator must complete only the exact
operator-specific `Principal` / `access_as_user` grant described by
`evidence\installation-e13812c5\operator-consent-request.json`.
This file already contains the actual installed principal IDs; no user ID transcription is required.
Do not grant `AllPrincipals` consent, new broad Graph rights or tenant roles to this worker.
The [Graph consent API][graph-consent] documents `DelegatedPermissionGrant.ReadWrite.All` plus an applicable
Entra capability for its POST. The observed 403 does not distinguish a missing installer scope from user capability.
Use the tenant's approved consent process with an already authorized operator, not self-elevation.
Then select **Verify setup & retry** in the portal. The prepared verifier makes GETs only:

```powershell
python generated-scenarios\resto-scale-agent\evidence\installation-e13812c5\operator_access.py --verify-only
```

The actual current check exits **1**, reports `passed: false` and zero grants.
A correction assertion is insufficient: clearing the blocker requires actual `passed: true`.
After verification, reuse the installed infrastructure/identities rather than recreate them.
Continue only through the portal's current lease and retained applicable scope; the stopped denial is not
permission to retry the denied write, broaden consent or bypass a new scope requirement.

Reviewed costs and SKUs are unchanged: **$745-$1,150/month shared** and **$900-$1,650/month typical full reference**.
The shared allowance now describes provisioned resources; the full allowance remains a future runtime estimate.
The Premium broker alone is **$677.08/month** at 730 hours. Charges continue while retained.
Rates retain their original `2026-10-24T00:01:36.245550Z` observation; these are not a quote, cap or current invoice.

### Historical repair and consolidated installation review: 2026-10-24 UTC

**Local defects are repaired, but the reference is not deployed.**
This resume read all canonical decisions/history and retained local execution and Central US preparation consent.
The former foundation grant stopped on failure and cannot authorize a retry or any directory/runtime writes.
The first exact-subscription resource enumeration returned `ResourceGroupNotFound`.
Two subsequent group-existence checks returned **false**, last observed at `01:26:45.816296 UTC`.
The former 13 resources are historical observations, not current inventory.
Removal time, actor and reason are unknown; this worker performed no deletion or other cloud mutation.
Consequently this is a full recreation preview, **not an incremental repair of existing resources**.
The scenario-local azd environment remains, but its old outputs cannot establish current resources.

`infra\main.bicep` now uses a fully qualified account resource ID followed by `/dbs/restaurant`
for all three Cosmos grants. Web/worker and initializer retain database-only access; chat has no Cosmos grant.
The account name, zones, local-authentication prohibition, throughput and backup configuration are unchanged.
The conflicting absent vault alone gets stable replacement `kv-resto-dc9a173f4d0b5f6`.
Its legal 24-character label derives from subscription, full environment, scenario and naming generation.
RBAC, purge protection, soft delete, RSA-3072, sign/verify, 180-day expiry and 90-day rotation are unchanged.
No unrelated resource name, SKU, network boundary or Foundry model changed.
Regression checks compare compiled inputs with the actual prior foundation template.

| Fresh exact-scope result | Observation |
| --- | --- |
| Identity | Exact saved account/subscription/tenant; Enabled; azd signed in as the same account |
| Cosmos Central US | Online; subscription AZ and regular access true; zones retained |
| Model quota/capacity | GlobalStandard quota 100/1,000; additional 100; regional capacity 900, not reserved |
| Provider registrations | All twelve checked resource/control-plane namespaces Registered |
| Environment count | Current 0, limit 50; demand 1; not a Consumption core limit |
| New environment Consumption cores | Unknown until installation; former environment's 0/500 is historical only |
| VNet count | Current 0, limit 1,000; demand 1 |
| RBAC/policy | Owner and Foundry User retained; policy metadata inspected, not compliance certification |
| Replacement vault availability | `nameAvailable: true` before preview; not a reservation |
| Unchanged Foundry subdomain | `isSubdomainAvailable: true` before preview; not a reservation |
| Full repaired shared what-if | Succeeded: 33 creates, zero modifies/deletes, 13 unresolved grant expansions |
| Full validation | Succeeded; eight identity/output-dependent modules skipped |
| Independent replacement vault | Succeeded: 3 creates, including group and key; grants/diagnostics excluded |
| Independent Cosmos | Succeeded: 7 creates, including group and actual deployer database-scoped grant |

The independent Cosmos preview now includes the real initializer principal and the corrected exact scope.
It excludes only the two uncreated managed identities and diagnostics; no synthetic principal was invented.
The full preview still has 13 Unsupported identity-dependent expansions, not 13 proven unsupported resources.
Validation skipped insights, registry, cosmos, broker, vault, foundry, project and environment.
Provider allocation, policy enforcement and installed access therefore remain dependent checks.
Unchanged same-day service/feature evidence is reused with its original timestamps.
Independent previews contain the same group and must not be added together.

The final infrastructure fingerprint, after the repairs, is:

```text
2371ff53fd0c9ff35ca3e337f30911f0bd4b4bf019dcd27f13cb0456dfb25ed7
```

Actual command strings, UTC times, exit codes and responses are in `evidence\repair-6f748869\`.
Main Bicep build/lint exited 0. Three compiled infrastructure regression tests passed.
Two test-harness issues were corrected without changing permissions: Windows subprocess discovery needed
the existing `az.CMD` path, and order-independent `dependsOn` arrays needed set-equivalent comparison.
The initial enumeration failure remains retained; it was not relabeled as a setup/host denial.
Existing application/image evidence is reused, not re-certified as live business or agent behavior.
The exact Cosmos ARM schema and retained AVM 0.21.1 interface were reviewed for this scope correction:
[Cosmos SQL role assignment schema][cosmos-role-schema].

### Historical remaining end-to-end authorization boundary

`evidence\repair-6f748869\installation-review.json` consolidates the remaining installation.
This is a **new proposed scope**, not an expansion of the stopped foundation-only grant.
It includes recreation of the exact reviewed shared resources, two dedicated marker-owned Entra registrations
and service principals, the API's business/floor roles and delegated scope, assignment-required access,
the current deployment operator's Manager/client assignments, scenario image publication,
synthetic fixture and three agent-version initialization, three runtime apps and bounded live acceptance.
No other users/groups, Graph application permissions, tenant-wide consent, credentials, policy changes,
provider registration, quota requests, purge/recovery, unrelated resources, cleanup or hack/event work is included.
Registration/assignment permissions and tenant user-consent policy have **not** been verified.
Subscription Owner does not prove those directory capabilities.
Only API-specific delegated consent for the operator is in the proposal, subject to actual tenant permission.
A real permission failure must stop without self-granting access or weakening assignment requirements.
The registration installer is prepared; operator assignment must use actual verified generated principals,
with idempotent assignment preparation before execution. No IDs are requested from the user.

After a genuinely recorded consolidated grant, one context performs the ordered azd/shared-resource installation,
directory setup/output capture, image publication, initializer and runtime rollout.
The existing azd predeploy hook consumes the verified identity receipt; it does not create registrations.
Shared and runtime templates remain separate technical dependency passes, **not separate user approval stages**.
Capture actual infrastructure outputs, current Consumption quota, immutable image digest and agent versions.
Require actual environment quota to cover 28 rollout vCPU before runtime rollout.
Run the dependent exact runtime/grant preview with those real outputs under the same grant.
Stop for a materially different preview/cost, new permission, ownership/provider/policy/capacity failure
or real host restriction; do not invent a completed runtime preview before those outputs exist.
Staff sign-in may need an actual operator authentication interaction; no token or login success is fabricated.
Only real inference, agents/tools/grounding, guest/staff journeys, negatives and load/recovery evidence
can enable the later suitability snapshot.

Reused Central US retail observations remain dated `2026-10-24T00:01:36.245550Z` in
`evidence\centralus-189819a8\cost-review.json`; local repairs do not change resource SKUs or estimated rates.
Shared allowance remains **$745-$1,150/month**; typical full reference **$900-$1,650/month**.
Premium broker alone is $677.08/month; the model example is $50.40/month.
At sustained configured maxima, app compute alone is $1,103.76/month, or $2,207.52 at the conservative
56-replica rollout envelope. Storage, telemetry, requests, zone treatment, egress and taxes can add charges.
These are planning estimates, not a quote, cap, approved budget, current invoice or capacity reservation.
No new Azure/directory resources, images, agents, application rollout, live tests or hack packages were created.

### Historical Central US foundation attempt: 2026-10-24 UTC

The following inventory, retained-resource costs and quota describe the `00:11-00:19 UTC` attempt only.
Current read-only reconciliation above supersedes those resource-existence statements.

**The shared foundation is incomplete. The exact model, Foundry project, zonal Cosmos account,
Premium broker and zonal Container Apps environment were created, but two modules failed.**
The recorded foundation-only decision `00637ba454ef44d3b84d700f57017e3d` was used once.
No repair deployment, purge, recovery, directory write, image publication, initialization or runtime rollout ran.
Existing resources are retained and may incur charges; cleanup requires separate authorization.
This is not a working scenario, live acceptance result or suitability review.

All 16 canonical decisions and 35 history entries were reviewed before execution.
The unchanged infrastructure fingerprint matched the reviewed
`1aa0c0f7d9f7518ece839c1edb8578142a922edb9ac482d2462b8fd6aa0feffc`.
Fresh exact-subscription checks verified identity, providers, model/SKU/quota/capacity,
Cosmos zonal access, environment-count eligibility, policy/RBAC and the repaired Foundry name.
The fresh full preview again returned **33 creates, zero modifies/deletes and 13 Unsupported grant expansions**.
Actual Bicep build/lint passed. Same-day regional prices and unchanged cost estimates were reused.
An initial local provider comparison mishandled `microsoft.insights` capitalization;
the retained response proves it Registered. Case-insensitive comparison corrected that local check,
without repeating the query or treating it as a provider failure.

The scenario-only azd environment was initialized and configured with explicit subscription, tenant,
resource group, region, principal and exact model values. No shared Azure CLI defaults were changed.
The authorized group was created with the reviewed tags.
Only `azd provision` ran, not `azd up` or `azd deploy`; the `predeploy` identity hook did not execute.

```powershell
azd provision --environment resto-scale-agent `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 --location centralus `
  --cwd C:\HackBuilder\generated-scenarios\resto-scale-agent --no-prompt
```

The command ran from `00:11:59.652305` to `00:15:56.984567` UTC and exited **1**.
The ARM deployment `resto-scale-agent-1792800732` finished **Failed** after `PT3M30.086858S`.
Azure completed already-submitted independent resources; no second deployment was submitted.
Full command output, provider errors, operation details and dated observations are retained under
`evidence\foundation-47a34228\`.

| Actual failure | Evidence and consequence |
| --- | --- |
| Key Vault `VaultAlreadyExists` | `kv-resto-4tvlzr5zf2rxi` cannot be created; guest signing key is absent |
| Cosmos grants `BadRequest` | Three grants reject relative `/dbs/restaurant`; account creation succeeded |

Cosmos requires the fully qualified account resource ID followed by `/dbs/restaurant` for these ARM grants.
The error explicitly expected `subscriptions` as the first segment, but received `dbs`.
Actual role-assignment enumeration is empty: neither application identity nor initializer has its intended grant.
The implementation-owned repair must retain database-only access and the chat identity's lack of direct data access.
The independent earlier Cosmos preview excluded these grants; its success never certified their payload.

The vault is absent from the authorized group (`ResourceNotFound`).
An exact-name deleted-vault lookup in **Central US only** returns `DeletedVaultNotFound`.
Those results do not identify the globally conflicting owner's tenant, subscription, region or deletion state.
The azd soft-delete suggestion is not proof of a recoverable scenario-owned vault.
No cross-region lookup, adoption, recovery, purge or weaker retention/security setting was attempted.
Prepare a stable legal scenario/subscription/environment-specific replacement name and availability check
for a future review rather than acting on the CLI's destructive purge suggestion.

The real environment now exposes **Consumption cores: current 0, limit 500**.
The conservative rollout check is **0 + 28 <= 500**, so this specific quota dependency now passes.
This is actual environment quota, not the Consumption profile's machine size or the regional environment count.
It is not reserved capacity, application-scale performance evidence or runtime authorization.
The environment is zone-redundant with peer traffic encryption enabled.
Cosmos is zonal in Central US with local authentication disabled.
The model is the exact reviewed `gpt-5.4-mini` / `2026-03-17`, GlobalStandard capacity 100.
The Premium broker retains zones; its Active kitchen queue retains sessions and duplicate detection.

**Stopped at the consent's new-provider-failure boundary.**
Next work is technical repair of the Cosmos grant payload and vault naming, preserving the existing resources,
followed by ownership-aware incremental previews/cost review and **renewed exact-target deployment consent**.
Do not retry this stopped grant or reprovision successful resources.
Do not request generated IDs or create a business questionnaire.
Directory installation and runtime publication/initialization/rollout still need their separate permissions.
No live model inference, agents, business transactions or application chat were invoked.

### Historical Central US repair preparation: 2026-10-23 UTC

**The Foundry naming defect is repaired; no resource was deployed.**
The prior repair ran under the saved exact Central US read-only preparation scope.
All canonical decisions/history, prior Central US evidence and summaries were read; the confirmed design was reused.
The fresh backend prerequisite receipt was reused, not replaced by another machine audit.
No shared account defaults, other scenarios, hack/event parameters or canonical repository files were changed.

The exact target resource group is absent. Its account-list query returns `ResourceGroupNotFound`,
so there is no verified scenario-owned account to reuse. No conflicting global resource was adopted or purged.
`infra\main.bicep` now derives Foundry account and custom domain from the same stable GUID function,
bound to the full subscription, environment, scenario ID and naming generation `foundry-v2`.
The legal 41-character name is `ai-resto-6f6767a4ef6b5c6bb82c4a11edebfdec`.
The provider's `checkDomainAvailability` response was **true before** any repaired preview.
The subsequent independent account/model what-if succeeds; availability is not a reservation.
All other names, confirmed Cosmos zones, model/version, SKUs and identity/network controls remain unchanged.

| Repaired Central US preview/check | Actual result |
| --- | --- |
| Full production shared what-if | Succeeded; 33 creates, 13 Unsupported expansions, zero modifies/deletes |
| Full subscription validation | Succeeded; eight nested modules short-circuited |
| Independent Basic registry | Succeeded; 2 creates including the same group |
| Independent zonal Cosmos | Succeeded; 6 creates; AZ/regular access both true, Online |
| Independent Premium broker | Succeeded; 3 creates; exact sessions/dedup/zones retained |
| Independent standard vault/key | Succeeded; 3 creates; RBAC/purge protection/signing controls retained |
| Independent repaired Foundry | Succeeded; 3 creates: group, account and exact model deployment |
| Exact Central US model | `gpt-5.4-mini` / `2026-03-17` / GlobalStandard; quota 100/1,000; additional 100 |
| Exact regional model capacity | availableCapacity 900; metadata, not reserved capacity or inference |
| Subscription managed environments | Current 0, limit 50, additional demand 1 |
| Actual Consumption core quota | **Unknown**, not zero, not passed; details below |
| Group after preparation | Absent; no provisioning, directory writes or provider registration |

The thirteen Unsupported entries all reference principal IDs of new managed identities.
ARM says their resource IDs cannot be calculated until deployment is under way.
This is **unsupported what-if expansion**, not proof that role assignments or the underlying services are unsupported.
They remain pending real installation outputs; no synthetic principal was supplied to claim success.
The full what-if expanded account/project/environment/diagnostic resources, unlike the earlier nine-create previews.
However, provider validation still skips `insights`, `registry`, `cosmos`, `broker`, `vault`, `foundry`,
`project` and `environment`. Expanded what-if is not complete provider/policy certification.
Independent previews exclude only the documented grants/diagnostics; production security is unchanged.
Their counts include the same group and must not be summed into a deployment count.
Runtime what-if was not run: real environment outputs, image digest, installed agent versions and staff receipt
do not yet exist. These are generated installation outputs, not values the user must supply.

### Correct Consumption quota diagnosis

Both supported direct regional usage APIs, `2025-07-01` and current `2026-07-01`, returned the same five quotas:
ManagedEnvironmentCount, SubscriptionDedicatedNCA100Gpus, SessionPools, ExpressEnvironmentCount and SandboxCores.
Neither returned a Consumption core limit. GPU and Sandbox quotas are not substitutes.
Provider metadata advertises `locations/usages`, not a separate Microsoft.App quota resource.
The supported generic regional Microsoft.Quota limit **and** usage GETs were attempted explicitly:

```text
GET /subscriptions/{authorized-subscription}/providers/Microsoft.App/locations/centralus/
    providers/Microsoft.Quota/quotas?api-version=2025-09-01
GET /subscriptions/{authorized-subscription}/providers/Microsoft.App/locations/centralus/
    providers/Microsoft.Quota/usages?api-version=2025-09-01
```

Both failed `MissingRegistrationForResourceProvider`; `Microsoft.Quota` is actually **NotRegistered**.
That is a provider/service response, not a host permission denial or missing SDK.
No provider was registered and no alternate credentials, quota writes or test allocation were attempted.
The result does not establish whether this provider would expose the future environment's Consumption quota
after separately authorized registration. Current Learn scopes that core quota to a managed environment.
No subscription default, absent-environment zero or guaranteed core limit is inferred.
Demand remains 14 vCPU/28 replicas at maximum scale and conservatively 28 vCPU/56 replicas during rollout.
The exact environment quota must be established before runtime scale/rollout; unknown is not a passing check.
The prior missing-environment query is historical and was not pointlessly repeated.

### Prepared identity installation and generated output consumption

`scripts\setup_identity.py` is now idempotent, scenario-local installation automation.
It discovers by stable identity name **and** scope-derived ownership marker, verifies tenant/principal ownership,
rejects ambiguous/unowned objects, and checkpoints actual generated IDs after each step.
It creates two single-tenant registrations and their principals: API and secretless native/public token client.
The API exposes only `access_as_user`, requires v2 tokens and defines the four existing business roles
plus Floor.1-Floor.5 user roles. Both principals require assignments; no role/tenant policy is weakened.
The application accepts signed assigned floor roles while retaining existing verified `floors` claims.
Business-role-only, floor-role-only and cross-floor negative cases remain denied.

No Graph read/write, application creation, user assignment or consent grant ran.
`evidence\centralus-189819a8\installation-plan.json` specifies exact directory operations and permissions,
including the distinction between member registration, application updates, principal creation,
staff assignment and delegated consent. Azure subscription Owner does not prove directory capability.
The installer grants no Graph application permissions or tenant-wide consent and creates no credentials.
No administrator-only route or new source/installer/generated-ID questionnaire is assumed.
An installed registration receipt is not a live authenticated workload.

The installer emits actual client/object/principal IDs and audience automatically.
`prepare_runtime.py --identity-receipt` consumes and validates those outputs against the exact target;
the user no longer needs to supply an audience. The compatibility audience option can only verify a match.
The azd `predeploy` hook performs only receipt consumption into the exact **existing** environment,
using explicit `--environment` after subscription/tenant/group/region verification.
It never creates an environment, calls Graph, installs identities or grants deployment consent.
The two-pass infrastructure/initializer/runtime sequence remains mandatory.
Actual endpoints, image digest, agent versions and grants are captured only during separately authorized installation.
The changed app must be rebuilt into a reviewed immutable image before any future publication/runtime rollout.

### Consolidated installation review and explicit foundation consent

The earlier draft's mandatory backend review-gate claim was stale.
Current `portal_server.execute_operations` runs the canonical agent through its authorized flow;
it does not invoke the standalone all-passed readiness validator before presenting a deployment decision.
`portal_workflow.Store.report` supports the normal exact-target consent decision after preparation.
Actual source/AST inspection is retained in `evidence\centralus-189819a8\controller-review-check.json`.
No canonical backend code was edited, no readiness gate was bypassed and no unknown result was marked passed.
The standalone readiness validator still rejects incomplete or stale evidence; full runtime readiness remains false.

This resume finalizes the prior unfinished preparation rather than repeating cloud queries or rebuilding the scenario.
Original Azure observation timestamps remain attached to the evidence.
Finalization time is not a fresh quota, name-availability, ownership, capacity or policy observation.
Independent eligibility must be rechecked within the authorized scope before any future provisioning.
The repaired templates, actual independent what-if, consolidated directory installation plan and costs are ready
for a narrowly scoped **Central US shared-foundation deployment decision**, not full application rollout.

The proposed first installation creates only `rg-resto-scale-agent` and the reviewed `infra\main.bicep` resources:
four managed identities, network/subnet, telemetry, Basic registry, zonal Cosmos/database/containers,
Premium broker/queue, RBAC vault/signing key, Foundry account/project/model, Container Apps environment,
and their declared tags, diagnostics and scoped grants.
The retained production preview has 33 creates, zero modifies/deletes and 13 unresolved identity-dependent grants.
Eight nested modules were skipped by validation; independent previews narrow, but do not eliminate, that limitation.
Azure can still reject allocation, provider/policy enforcement or dependent grants during installation.
Stop on a new ownership, capacity, policy or provider failure; no silent retry or weaker fallback is permitted.

The complete later identity plan remains `evidence\centralus-189819a8\installation-plan.json`:
two dedicated marker-owned registrations/principals, only the scenario delegated scope, business/floor roles
and assignment-required access, with generated IDs captured by the prepared installer.
Required directory capabilities and later staff assignment/consent permissions are disclosed there.
**This foundation-only consent excludes all Graph writes, staff assignment and admin/delegated consent grants.**
It also excludes provider registration, quota changes, image publication, agent/data initialization,
runtime application rollout, cleanup and modifications outside the exact target.
No generated client IDs, endpoints or identity values are requested from the user.

After separately authorized foundation installation, capture actual outputs and query actual environment quota.
Require at least 28 rollout vCPU, resolve grants/project/policy checks and independently validate the identity receipt
before any app rollout. Directory installation needs explicit permission for its documented operations.
Runtime needs its actual-output preview and separate exact-target consent, followed by real acceptance tests.
If any dependency fails, preserve the failed state and stop; do not imply a working scenario or request hack approval.
The normal portal decision is the next boundary. No deployment or directory consent has yet been granted.

### Fresh commands, validation, cost and retained evidence

Exact command strings, arguments, UTC timestamps, exit codes, stdout/stderr and structured responses are in
`evidence\centralus-189819a8\*.json`; earlier regional failures remain separate history.
The collector reuses the scenario's saved Central US and Azure command helpers.
A local PowerShell quoting error in an inspection command was diagnosed as syntax, not a profile/path/host denial;
the corrected scenario collector records the actual API results. No trust or permissions were broadened.

```powershell
python generated-scenarios\resto-scale-agent\evidence\centralus-189819a8\prepare.py discover
python generated-scenarios\resto-scale-agent\evidence\centralus-189819a8\prepare.py name
python generated-scenarios\resto-scale-agent\evidence\centralus-189819a8\prepare.py collect
python generated-scenarios\resto-scale-agent\evidence\centralus-189819a8\prepare.py quota
python generated-scenarios\resto-scale-agent\evidence\centralus-189819a8\prepare.py preview
python generated-scenarios\resto-scale-agent\evidence\centralus-189819a8\prepare.py prices
```

Each collector command exited 0 after retaining individual provider failures as failures in its records.
Collector exit success does not mean quota/readiness success.
Both main/runtime Bicep builds and main lint passed without diagnostics.
The saved runtime-lint attempt exited `4294967295` with no diagnostic; it was not a passing check.
This resume executed its exact command under unchanged restrictions: exit 0, empty stdout/stderr.
The original failure remains retained; its cause is unestablished, not assumed to be a permission denial.
The separate retry result is `evidence\resume-cbd218af-verification.json`.
Focused .NET domain tests passed 15/15 after building the changed app.
Final Python identity/runtime wiring and broader local application results are in `local-checks.json`.
Offline installer tests cover repeat installation without duplicate objects, ownership rejection, default-deny
floor scopes, incomplete/foreign receipts and explicitly environment-scoped azd output export.
They are not directory installation or live authentication evidence.

Central US public retail meters were refreshed. At 730 hours/month, Premium 1 MU is **$677.08**,
Cosmos autoscale 400-4,000 RU/s **$35.04-$350.40**, nine warm replicas idle-to-active **$106.43-$354.78**,
and example 24M input/7.2M output model tokens **$50.40**.
Retained planning allowances are **$745-$1,150/month shared**, **$900-$1,650/month typical full reference**.
Maximum 28 active replicas cost **$1,103.76/month** app compute alone;
conservative 56-replica overlap sustained all month costs **$2,207.52/month** app compute alone.
Ancillary allowance is not individually requoted; storage, requests, telemetry, restore, egress and taxes add costs.
These are estimates, not a cap, quote, approved budget, capacity reservation or deployment consent.
Fresh raw prices and exact-meter calculations are in `cost-review.json`.

`00-region-availability.json` contains the complete current 26-check inventory and preserved rejection history.
`scope-and-fingerprint-final.json` is computed **after** final IaC/azd edits.
The resumed finalization preserves dated Azure observations instead of refreshing their timestamps.
Only this scenario's manifest was refreshed using the repository catalog API; no shared catalog was exported.
No tool installation/upgrade, default-account change, external resource adoption, cloud mutation or fallback region ran.

### Historical West US 2 preparation: 2026-10-23 UTC

**West US 2 does not pass the unchanged reference's complete regional readiness gate.**
Fresh Cosmos subscription metadata denies the required availability-zone access.
The exact Foundry subdomain also returns `CustomDomainInUse`.
The required `gpt-5.4-mini` / `2026-03-17` is absent from the regional AIServices model list;
the exact regional model-capacity response is empty, not a zero-demand or passing capacity observation.
Global model quota headroom does not establish regional eligibility.
Agent feature support, actual ACA Consumption core quota and output-dependent checks remain unverified.

This bounded attempt performed only `deployment-preparation` under the exact saved West US 2 authorization.
All canonical decisions/history, existing implementation and earlier rejection evidence were reused.
The fresh owner-bound backend prerequisite receipt was reused without repeating the machine audit.
Identity matched the authorized account, subscription and tenant; subscription state was Enabled.
Every Azure query/what-if explicitly supplied the authorized subscription.
The exact group was absent before and after preparation; the distinct azd environment was not initialized.
No shared defaults, production templates, security, names, identities, zones or targets were changed.
No resource/directory mutations, quota requests, purge, adoption, image push or runtime calls occurred.
No other candidate or scenario was evaluated, and no deployment-consent review, hack composition or event ran.

| Fresh West US 2 dependency finding | Actual result |
| --- | --- |
| Required provider namespaces | Registered; provider metadata retained with every resource check |
| Cosmos access | Online; zones supported; subscription AZ **false**, regular **true** |
| Cosmos exact configuration | Standard NoSQL; zones; shared autoscale 4,000 RU/s; Continuous7Days retained |
| Cosmos partial preview | Accepted configuration shape, but does **not** override AZ subscription denial |
| Foundry account | AIServices S0 listed without restrictions; exact-name preflight fails |
| Foundry exact subdomain | `ai-resto-4tvlzr5zf2rxi`: `CustomDomainInUse`; no rename, purge or adoption |
| Required model/version | No matching AIServices `gpt-5.4-mini` / `2026-03-17` in West US 2 list |
| Required model capacity | Exact regional query returns `value: []`; usable capacity **unknown** |
| Model quota | Global scope 100/1,000; additional demand 100; not regional eligibility |
| Agents/Responses/Functions | West US 2 absent from current official region tables; support **unverified** |
| Container Apps | Consumption listed; environment count 0/50; logical zones 1/2/3 |
| Consumption core quota | Actual environment usage query fails `ResourceGroupNotFound`; limit **unknown** |
| Aggregate app demand | 28 max replicas / 14 vCPU; conservative rollout 56 replicas / 28 vCPU / 56 GiB |
| Service Bus | Premium 1 MU / 1 partition; regional SKU/zones/partitions supported |
| ACR/vault | Exact Basic registry and standard RBAC/purge-protected RSA vault/key partial previews accepted |
| Network | VirtualNetworks 0/1,000; demand 1; delegated /23 subnet and encrypted environment retained |
| Identity/observability/policy | Four identities and workspace evaluated; dependent grants/Insights/policy incomplete |

West US and West US 3 are different regions; their agent/tool table rows do not establish West US 2 support.
The Learn page's West US 2 mention for Bing grounding is not support for this required agent configuration.
The model-level Functions support row does not establish regional model availability.
Fresh official feature/quota observations are in `evidence\westus2-34cc5a27\public-feature-evidence.json`.
The Consumption profile core size and environment-count quota are not the environment's Consumption core quota.
No environment was created to discover that limit. No VM/VMSS or Microsoft.Web plan is in this reference;
Compute family quotas and App Service B2 worker quotas are therefore not applicable or substitutes.

| Actual West US 2 preview | Result |
| --- | --- |
| Unchanged full shared template | Succeeded: 9 evaluated creates, 0 modifies/deletes; 8 skipped modules |
| Full subscription validation | Succeeded with skipped-module warnings; not complete eligibility |
| Independent Basic registry | Succeeded: 2 creates including group; no diagnostics |
| Independent zonal Cosmos | Succeeded: 6 creates including group; AZ access flag still blocks deployment |
| Independent Premium broker | Succeeded: 3 creates including group; no diagnostics |
| Independent standard vault/key | Succeeded: 3 creates including group; no diagnostics |
| Independent Foundry | Failed: `CustomDomainInUse`; no successful change-count claim |

Skipped modules: `insights`, `registry`, `cosmos`, `broker`, `vault`, `foundry`, `project`, `environment`.
Independent preview copies exclude only output-dependent grants/diagnostics, as explicitly documented in
`evidence\westus2-34cc5a27\preview-exclusions.json`; production controls remain unchanged.
Partial counts include the same proposed group and cannot be summed into a full deployment count.
The full compiled template was compared with the preview's embedded production template before execution.
Fresh Bicep build/lint passed without diagnostics.
`location` remains required and supplied through `${AZURE_LOCATION}`; portable hack region inputs were untouched.
Runtime what-if awaits actual outputs, image digest, installed agent versions and staff audience.
No fabricated IDs or placeholders were used to claim runtime readiness.

`00-region-availability.json` records **26 checks: 11 limited passes, 5 blocked and 10 unknown**.
The current exact scope is bound to infrastructure fingerprint
`38b48adc1404bb2431f16c6cf72cfd0e4dc98c5e9c764d993320321bcaae81f0`.
The actual repository guard rejects the blocked Cosmos account; no deployable region is selected.
Prior Central US readiness is archived alongside East US readiness, and all candidate rejections remain.
Command/result/exit/timestamp evidence and the exact failed event are in `evidence\westus2-34cc5a27`.
The manifest was refreshed through the scenario catalog API only; its canonical index was not written.

Fresh West US 2 pricing is in `evidence\westus2-34cc5a27\cost-review.json`.
At 730 hours/month, Premium 1 MU is **$677.08** and autoscale 400-4,000 RU/s is **$35.04-$350.40**.
Nine warm replicas cost **$141.91-$496.69/month** idle-to-active using the current regional base meters.
All 28 max replicas active cost **$1,545.26/month** for app compute alone;
56-replica temporary overlap sustained all month would cost **$3,090.53/month** for app compute alone.
The required model's exact regional meters are absent; the three returned GPT 5 Chat meters were not substituted.
The former full-reference allowance is historical, not a refreshed West US 2 quote.
Ancillary usage, storage, requests, telemetry, egress and taxes may add costs.
No complete model-inclusive regional estimate, approved budget or capacity reservation is claimed.

Neither newly requested candidate passes the complete unchanged reference.
Central US passed Cosmos AZ access but failed exact-name/dependent checks; West US 2 additionally fails
Cosmos AZ access and does not establish the required model/capacity/agent features.
This operation ends as **failed preparation**, not a tooling approval or deployment decision.
There is no automatic target, model, name, service or security change and no quota/support request.

### Historical Central US preparation: 2026-10-23, 23:16 UTC

The following Central US findings are preserved rejected-candidate history, not the current West US 2 result.

**Central US passes Cosmos zone access, but the complete unchanged reference is not deployment-ready.**
The exact Foundry subdomain still returns `CustomDomainInUse`; this is a name conflict,
not evidence that Central US lacks Foundry support.
The required Container Apps Consumption core quota remains unknown for the nonexistent environment.
These findings block preparation completion and deployment-consent review.

Only the backend-assigned `deployment-preparation` operation ran under the saved exact Central US scope.
All canonical decisions/history were read and the fresh owner-bound backend prerequisite receipt was reused.
The current Azure identity matched the authorized account, subscription and tenant; subscription state is Enabled.
Every Azure query/preview explicitly supplied the subscription; no shared defaults or azd environment changed.
The resource group remained absent before and after preparation.
No resources or directory objects were created/updated, quotas requested, names changed or security weakened.
No deployment-consent review, provisioning, runtime initialization, composition or team rollout was started.
West US 2 remains a user-requested candidate, **not evaluated or selected in this current-region-only job**.

| Current Central US finding | Actual result |
| --- | --- |
| Providers | All eleven required namespaces Registered |
| Cosmos regional access | Online; zones supported; subscription AZ **true**, regular **true** |
| Cosmos exact features | Zones, provisioned autoscale max 4,000 RU/s, Continuous7Days accepted in partial preview |
| Foundry account | AIServices S0 listed without restrictions; exact subdomain preflight fails |
| Foundry conflict | `ai-resto-4tvlzr5zf2rxi`: `CustomDomainInUse`; no adoption, purge or rename |
| Exact model | `gpt-5.4-mini` / `2026-03-17` / GlobalStandard; GA; agentsV2/Responses true |
| Model quota | 100 used / 1,000 limit; additional demand 100; global-scope quota, not reserved |
| Model capacity | Central US exact model/version/GlobalStandard availableCapacity 900; not reserved |
| Agent features | Current Learn: Central US Agents, Responses and Function supported; runtime unverified |
| Container Apps | Consumption explicitly listed; environment count 0/50; logical zones 1/2/3 |
| Consumption core quota | Actual `env list-usages` fails `ResourceGroupNotFound`; limit **unknown** |
| Scale demand | 28 max replicas / 14 vCPU; conservative rollout overlap 56 replicas / 28 vCPU |
| Service Bus | Premium / 1 MU / 1 partition; regional SKU, zones and partitions supported |
| Network | VirtualNetworks 0/1,000; additional 1; delegated /23 subnet retained |
| Identity/policy | Owner and Foundry User observed; three policy assignments; dependent checks incomplete |

The fresh positive Cosmos flags are not copied from another region and do not erase prior rejections.
The actual partial Cosmos preview covers the selected zone/autoscale/backup configuration, not reserved capacity.
The profile's advertised core size and environment-count quota are **not** Consumption core quota.
Microsoft Learn confirms Consumption cores are a per-environment limit.
The worker did not create an environment to discover that limit or request a quota increase.
The planned design contains no Compute VM/VMSS or App Service plan:
VM-family quotas and Microsoft.Web B2 worker quotas are not substitutes for ACA quota.
Staff Entra registration and real project/runtime identities remain installation outputs/dependencies;
read-only preparation neither creates them nor invents IDs to complete a preview.

| Current Central US preview | Exact result |
| --- | --- |
| Unchanged full shared template | Succeeded: 9 evaluated creates, 0 modifies/deletes; 8 skipped modules |
| Full subscription validation | Succeeded; same eight skipped-module warnings, not full eligibility |
| Independent Basic registry | Succeeded: 2 creates including group; no diagnostics |
| Independent zone-redundant Cosmos | Succeeded: 6 creates including group; no diagnostics |
| Independent Premium broker/queue | Succeeded: 3 creates including group; no diagnostics |
| Independent standard vault/key | Succeeded: 3 creates including group; no diagnostics |
| Independent Foundry | Failed: `CustomDomainInUse`; no successful change-count claim |

Skipped modules are `insights`, `registry`, `cosmos`, `broker`, `vault`, `foundry`, `project`, `environment`.
Independent previews exclude identity-dependent grants and diagnostic routing only in their preview copies.
Their exact exclusions are retained in `evidence\centralus-91633e9e\preview-exclusions.json`;
production security, SKUs, identity boundaries, zones and networking remain unchanged.
Partial counts include the same proposed group and must not be summed into a whole-reference count.
No placeholder outputs, endpoints, agent versions, staff audience or image digest were used for runtime what-if.
Bicep build/lint passed with no diagnostics; `location` remains required and supplied by `${AZURE_LOCATION}`.
Portable hack/event region parameters and packages were not touched.

All commands, timestamps, exit codes, responses and failures are in `evidence\centralus-91633e9e`.
The collector's localized subscription-location response initially failed UTF8 decoding;
the same Azure CLI query was filtered to Central US and only unfinished checks resumed.
This was an evidence-collector encoding defect, not a host denial or missing profile access.
The original failure and correction are retained in `collection-encoding-failure.json`.
`public-feature-evidence.json` records the freshly read official feature/quota sources.

`00-region-availability.json` records **26 checks: 15 passed limited checks, 1 blocked and 10 unknown**,
with current exact scope and infrastructure fingerprint
`38b48adc1404bb2431f16c6cf72cfd0e4dc98c5e9c764d993320321bcaae81f0`.
The actual repository readiness guard rejects the blocked Foundry account.
Previous East US readiness is archived in `regionalReadinessHistory`; all earlier candidate rejections remain.
Nothing is marked deployment-ready, and no successful partial check overrides a blocked or unknown dependency.

Fresh Central US public retail meters and calculations are in `evidence\centralus-91633e9e\cost-review.json`.
At 730 hours/month: Premium 1 MU **$677.08**, autoscale 400-4,000 RU/s **$35.04-$350.40**,
nine warm app replicas idle-to-active **$106.43-$354.78**, and example model use **$50.40**.
Retained planning allowances are **$745-$1,150/month shared** and **$900-$1,650/month typical full reference**.
Ancillary allowance is not individually requoted; requests/storage/restore/telemetry/egress/taxes can add cost.
Max 28 replicas active all month cost **$1,103.76** for app compute alone;
56-replica conservative overlap sustained all month would cost **$2,207.52** for app compute alone.
These examples are not a quote, cap, approved budget, capacity reservation or deployment consent.

The bounded operation ends with exact-scope **failed preparation**, not a tooling/setup or business decision.
Any future naming resolution or separately assigned candidate check must retain ownership/security constraints.
Deployment-consent review requires complete fresh readiness and actual what-if/cost evidence first.

### Historical East US preparation: 2026-10-23, 22:52 UTC

The following East US findings are dated rejected-candidate history, not the current West US 2 result.

**The unchanged reference is not deployment-ready in East US.**
The user changed the read-only preparation target, not the reliability/security design.
The former East US 2 setup blocker was superseded, **not verified resolved**.
All earlier findings below remain dated history; do not apply their remediation or authorizations to East US.

Read all canonical decisions/history and current exact-scope authorization before querying Azure.
The authorized account, subscription, tenant, environment and group remain those in the table above.
The fresh backend prerequisite receipt was reused; no redundant full audit or shared installation ran.
Every Azure query and what-if passed the authorized subscription explicitly.
No defaults, azd environment, directory objects, resources, quota allocations or other scenarios were changed.
No provisioning, deployment retry, support/quota request, purge, image publication or runtime operation occurred.
No hack packages or future event targets were inspected or modified.

| Actual regional finding | Result |
| --- | --- |
| Identity | Exact authorized account/subscription/tenant match; Enabled; azd account matches |
| Providers | All eleven required namespaces Registered |
| Cosmos East US | Online; AZ support true; subscription **AZ access false and regular access false** |
| Cosmos configuration | Zones retained; NoSQL shared autoscale max 4,000 RU/s; Continuous7Days; no serverless |
| Foundry account | AIServices S0 listed, no SKU restrictions; exact custom domain unavailable |
| Foundry provider error | `CustomDomainInUse`: `ai-resto-4tvlzr5zf2rxi` |
| Exact model | `gpt-5.4-mini`, `2026-03-17`, GlobalStandard; GA; agentsV2/Responses true |
| Model quota/capacity | Global quota 100/1,000; additional 100; East US capacity 900, not reserved |
| Container Apps | Exact Consumption profile listed; managed environments 0/50; zones 1/2/3 |
| Container Apps cores | Environment-specific quota **unknown**, because the environment does not exist |
| Scale demand | 28 max replicas / 14 vCPU; conservative old/new overlap 56 replicas / 28 vCPU |
| Service Bus | Premium / 1 MU / 1 partition; regional SKU, zones and partition support true |
| Network | VirtualNetworks 0/1,000; additional 1; /23 delegated subnet retained |
| Policy | Three assignments enumerated; skipped/dependent resources not certified compliant |
| Target isolation | `rg-resto-scale-agent` absent before and after preparation |

The Cosmos response rules out this subscription's current East US eligibility even though the region is Online.
The independent Cosmos preview succeeded but **does not override those false access flags**.
Neither removing zones nor changing to nonzonal Cosmos is an accepted workaround.
There is no authorized alternative region to query in this job; a different target requires portal scope review.

The Foundry error is an actual independent provider-preflight result, not a quota inference.
Ownership and possible soft-deletion retention are unresolved; the provider's purge suggestion is **not permission**.
No purge, adoption, automatic rename or search outside the authorized target was attempted.
Any future naming/target resolution must preserve ownership and identity requirements.
The prior stopped East US 2 deployment grant is not reusable in East US.

**B2 diagnosis and actual recheck:** the subscription's East US `Microsoft.Web` usage API returns
`name.value: B2`, localized `B2 VMs`, `limit: 0`, `currentValue: 0`, unit Instances.
This is an App Service `Microsoft.Web/serverfarms` worker quota, **not** a Compute B-family vCPU quota.
Zero permits no positive B2 worker demand; a region change cannot be claimed to fix it.
The restaurant's actual IaC contains Container Apps, not an App Service plan or Compute VM/VMSS.
Consequently B2 demand here is zero and its quota neither blocks nor proves restaurant ACA readiness.
No `equip-ai` files/resources were inspected or changed and no readiness claim is made for that scenario.
The Microsoft.Web SKU-list response was empty, not an availability pass.
The restaurant's ACA Consumption core quota remains separately unknown.

### Historical East US what-if and limitations

Fresh `az bicep build` and `az bicep lint` exited 0 without diagnostics on unchanged `infra\main.bicep`.
The local preparation parameter file and new preview wrappers use `eastus`.
Bicep `location` remains **required**, and production `infra\main.parameters.json` still supplies
`${AZURE_LOCATION}`; no East US default or future hack target was introduced.

| Current East US preview | Exact result |
| --- | --- |
| Full shared template | Succeeded: 9 evaluated creates, 0 modifies/deletes; 8 skipped nested modules |
| Full subscription validation | Succeeded with the same eight skipped-module warnings |
| Independent Basic registry | Succeeded: 2 creates including group; no modifies/deletes or diagnostics |
| Independent Cosmos | Succeeded: 6 creates including group; no modifies/deletes or diagnostics |
| Independent Premium broker | Succeeded: 3 creates including group; no modifies/deletes or diagnostics |
| Independent standard vault/key | Succeeded: 3 creates including group; no modifies/deletes or diagnostics |
| Independent Foundry | Failed preflight: `CustomDomainInUse`; no successful change-count claim |

The full preview skipped `insights`, `registry`, `cosmos`, `broker`, `vault`, `foundry`, `project`, `environment`.
These nine evaluated creates are not a complete nine-resource design.
Independent previews use the current compiled AVM modules and exact proposed names while excluding
new-identity-dependent grants and diagnostic routing; exclusions are in `preview-exclusions.json`.
They do not weaken production configuration or validate excluded grants, diagnostics or project identities.
Partial counts each include the same proposed group and **must not be summed** into a full deployment count.
The registry preview retains Basic, authenticated public access and disabled admin/anonymous access;
the previously corrected Premium-only networkRuleSet remains omitted.
Runtime what-if remains pending actual infrastructure outputs, installed agent versions, staff audience
and a published image digest. No placeholder identity IDs, endpoints or runtime success were fabricated.

All exact Azure commands, timestamps, exit codes, stdout/stderr and responses are retained in
`evidence\eastus-c99de84d\*.json`.
The collector is `evidence\validate-eastus-c99de84d.py`; the corrected model-capacity query uses
the **regional** `locations/eastus/modelCapacities` endpoint and separate `--url-parameters`.
An earlier URL-argument parsing failure and unsupported regional SKU-capacity route remain recorded;
neither is a host denial or a passing capacity check.
Region-zone metadata was retrieved by explicit-subscription REST after the CLI location command rejected
`--subscription`; no shared CLI default was changed.

`00-region-availability.json` now contains exact-scope `regionalReadiness`, 26 actual resource/SKU/feature checks,
timezone-aware timestamps and fingerprint
`38b48adc1404bb2431f16c6cf72cfd0e4dc98c5e9c764d993320321bcaae81f0`.
There are **12 passed limited checks, 4 blocked and 10 unknown**; no deployable region is selected.
The repository readiness guard was executed and correctly rejected the blocked Cosmos check.
Both the evidence and the portal report preserve failures rather than marking deployment/preparation complete.
Refresh checks after resolving blockers and whenever evidence is stale or infrastructure changes.
What-if and quota metadata never reserve allocation capacity.

### Historical East US retail planning cost

Fresh East US meters and calculations are in `evidence\eastus-c99de84d\cost-review.json`.
Model pricing uses the actual Foundry Models / Azure OpenAI GPT5 product and East US meter IDs,
not an empty query result or prices copied from East US 2.

| Example, 730 hours/month | USD/month |
| --- | --- |
| Premium broker, 1 MU | $677.08 |
| Cosmos autoscale billed at 400-4,000 RU/s | $35.04-$350.40, before storage/other charges |
| Nine warm ACA replicas, idle-to-active examples | $106.43-$354.78 |
| 24M input / 7.2M output model tokens | $50.40 |
| 28 replicas active all month, application compute alone | $1,103.76 |

Base refreshed rates support the retained rounded allowances:
**$745-$1,150/month shared**, **$900-$1,650/month typical full reference**.
The latter assumes nine warm replicas and about 200 turns/day, not sustained maximum scale.
Ancillary ACR/vault/network/telemetry retains a $30-$120 allowance, not individual new quotes.
Storage, requests, restore, zone-related billing, telemetry, egress, bursts and taxes may add cost.
Continuous7Days backup has a zero-priced backup meter; restore/storage are not thereby free.
No grant/discount/tax adjustment, spending cap, budget approval or deployment consent is implied.

Stop here: current eligibility, exact-name and unknown-quota findings prevent a later deployment-consent gate.
Any later deployment requires resolved target/name eligibility, fresh complete scoped readiness,
revised actual what-if/cost review and separate exact-target authorization.
No new business or setup approval was invented for this failed read-only operation.

### Historical East US 2 recovery preparation: 2026-10-23, 22:22 UTC

The following former access remediation is historical, superseded by the user's East US validation target.
It is not an instruction to request quota or alter the current target.

Resumed only backend-assigned `deployment-preparation`, using the saved local execution consent,
confirmed design and exact-scope read-only authorization. No resource creation, retry, support request,
directory write, image publication, initialization, application rollout or Azure-default change occurred.
Backend readiness dated `22:16:02 UTC` was reused; no redundant full machine audit ran.

**Current blocking finding:** Cosmos lists East US 2 Online with availability-zone support, but this subscription
has `isSubscriptionRegionAccessAllowedForAz: false`; non-zone access is true.
This is current service metadata, not merely the historical allocation failure or a missing local tool.
Do not downgrade reliability, change region or retry provisioning.
The operator must obtain zone-redundant Cosmos regional access for the saved subscription in East US 2 through
[Azure Cosmos DB regional access support](https://aka.ms/cosmosdbquota), then verify the live flag is true.
No access/capacity request was submitted by this worker.
The [official location-property definitions][cosmos-location-properties] distinguish zone support from
subscription access. Read-only access verification is:

```powershell
az cosmosdb locations list --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --query "[?name=='East US 2'].properties.isSubscriptionRegionAccessAllowedForAz | [0]" --output tsv
```

The full regional query returned the explicit false flag; retained in `evidence\cosmos-region-19f3d63e.json`.
An Online status or a successful ARM wrapper validation cannot override that denial.

The registry implementation defect is corrected without changing the approved design.
AVM registry 0.13.1 defaults `networkRuleSetDefaultAction` to Deny and therefore emits `networkRuleSet`
when public access is Enabled, even with no IP rules. Basic does not support those network restrictions.
`infra\main.bicep` now explicitly sets Allow and leaves IP rules null, making that AVM condition false.
Basic SKU, authenticated public TLS/Entra access, disabled admin/anonymous access and managed identities remain.
Current [official ACR SKU guidance][acr-skus] confirms the Premium-only IP/VNet rule boundary.
`evidence\registry-regression-19f3d63e.json` records compiled-input checks and exact template/wrapper hashes.
Cosmos and Container Apps zone redundancy remain enabled.

| Fresh read-only check | Observed result |
| --- | --- |
| Identity | Exact saved account/subscription/tenant match; Enabled |
| Target group | Absent before and after preparation; no owned target conflict observed |
| Providers | All eleven required providers Registered |
| RBAC/policy | Owner and Foundry User retained; three assignments inspected, not a compliance certification |
| Exact model quota | Limit 1,000, used 100, available 900; requested 100 capacity units |
| Exact model capacity | East US 2 GlobalStandard availableCapacity 900; not reserved or inference-tested |
| Full shared what-if | Succeeded; nine evaluated creates, zero modifies/deletes; eight skipped modules |
| Full shared validation | Succeeded with eight `NestedDeploymentShortCircuited` warnings |
| Independent registry what-if | Succeeded; two creates (group + registry), zero modifies/deletes; no diagnostics |
| Independent registry validation | Succeeded; no diagnostics; new-identity grants excluded |
| Public retail rate refresh | Eight retained regional meter rates unchanged; no pagination |

The latest full preview skipped `insights`, `registry`, `cosmos`, `broker`, `vault`, `foundry`, `project`
and `environment` because their parameters depend on unresolved new-resource outputs.
Nine evaluated creates are **not** a nine-resource design or a complete replacement for the older 33-create preview.
There are no reported potential changes; missing evaluations remain unknown, not zero-risk or accepted changes.
The independent registry wrapper uses the compiled AVM resource and the exact saved registry/group name,
excluding all four identity grants solely to validate the independent provider configuration.
Its actual preview has **no networkRuleSet**, Basic SKU, public access Enabled and admin/anonymous disabled.
It is neither a replacement production template nor a full reference acceptance result.

The renewed public-rate evidence is `evidence\prices-refreshed-19f3d63e.json`;
calculations and assumptions are in `evidence\cost-review-19f3d63e.json`.
Retained planning allowances remain **$745-$1,150/month shared** and **$900-$1,650/month full reference**.
Examples remain $677.08/month for the Premium broker, $106.43-$354.78 for nine warm replicas,
$35.04-$350.40 for 400-4,000 autoscale RU/s and $50.40 for 24M input/7.2M output tokens.
Ancillary services retain the earlier $30-$120 allowance, not fresh individual quotes.
Zones/storage/backup/telemetry/bursts/taxes can add charges; this is not a quote, budget approval or cap.

Commands executed, each exiting 0 for its defined limited operation:

```powershell
az bicep build --file generated-scenarios\resto-scale-agent\infra\main.bicep `
  --outfile generated-scenarios\resto-scale-agent\evidence\what-if-main-19f3d63e.arm.json
az bicep lint --file generated-scenarios\resto-scale-agent\infra\main.bicep
python generated-scenarios\resto-scale-agent\evidence\prepare-what-if-19f3d63e.py
python generated-scenarios\resto-scale-agent\evidence\prepare-registry-preview-19f3d63e.py
python generated-scenarios\resto-scale-agent\evidence\refresh-cost-19f3d63e.py
$subscriptionId = 'efd64343-6ef4-4926-951f-d3229f38bd76'
$evidence = 'generated-scenarios\resto-scale-agent\evidence'
az deployment sub what-if --subscription $subscriptionId --location eastus2 `
  --name resto-scale-agent-preflight-19f3d63e `
  --template-file "$evidence\what-if-subscription-19f3d63e.arm.json" --no-pretty-print --output json
az deployment sub validate --subscription $subscriptionId --location eastus2 `
  --name resto-scale-agent-validate-19f3d63e `
  --template-file "$evidence\what-if-subscription-19f3d63e.arm.json" --output json
az deployment sub what-if --subscription $subscriptionId --location eastus2 `
  --name registry-independent-19f3d63e `
  --template-file "$evidence\registry-independent-19f3d63e.arm.json" --no-pretty-print --output json
az deployment sub validate --subscription $subscriptionId --location eastus2 `
  --name registry-validate-19f3d63e `
  --template-file "$evidence\registry-independent-19f3d63e.arm.json" --output json
```

Matching JSON/stderr files retain actual preview/validation responses and their warnings.
An initial local inspection incorrectly assumed the registry was in the evaluated full preview and returned
`StopIteration`; inspecting diagnostics revealed its skipped evaluation, so an independent preview was used.
This parsing failure was not a host denial or an Azure failure.
No passing runtime result is inferred from any command exit.
After regional access is actually verified, refresh preparation and obtain **renewed exact-target deployment consent**
against current what-if/cost evidence; do not reuse the older stopped deployment grant.
Suitability approval, hack composition and team deployment remain untouched.

[cosmos-location-properties]: https://learn.microsoft.com/rest/api/cosmos-db-resource-provider/locations/list
[acr-skus]: https://learn.microsoft.com/azure/container-registry/container-registry-skus

### Historical resume reconciliation

The previous worker created shared resources but exited without reporting its final failure to the portal.
Its retained ARM result for `reference-shared-8608c198` is **Failed**, recorded at
`2026-10-23T18:59:00.786943+00:00`. Two provider errors prevented completion:

- Cosmos: `ServiceUnavailable`. East US 2 could not fulfill the zone-redundant account request.
  Azure directed a regional access/capacity request to <https://aka.ms/cosmosdbquota>.
- Registry: `NetworkRuleNotSupported`.
  The exact provider message is: "The requested feature virtual network rule is not supported for the SKU Basic."

Full nested errors, operation IDs and historical resource states remain in
`evidence\deployment-operations-final-8608c198.json`, `evidence\deployment-final-8608c198.json`
and `evidence\resources-final-8608c198.json`. These are historical partial creation, not current success.

This resume verified the exact authorized account/subscription/tenant and performed read-only reconciliation.
All three deployment/resource queries returned `ResourceGroupNotFound`;
`az group exists` returned **false**. The group is no longer present.
The reason for its disappearance is unknown; this worker performed no deletion or other cloud mutation.
Exact commands, exit codes and results are retained in `evidence\deployment-reconciliation-24079be7.json`.

The authorization explicitly requires stopping on new capacity/provider failures.
No recreation, retry, reliability downgrade, region/SKU change, image publication, agent installation,
runtime rollout or live validation was attempted.
The portal must resolve whether to retain the zone-redundant design pending capacity access,
revise deployment preparation, or keep the reference local only.
Retaining the design does not prove capacity has become available or authorize unresolved registry changes.
Any changed design/targets require their applicable review, fresh what-if/cost evidence and deployment consent.

The following preparation findings describe the **earlier read-only preparation**, not current deployment readiness.

Reused the confirmed design, existing application, images and prior local evidence; did not restart implementation.
No Azure resources, provider registrations, role assignments, agents or azd environments were created.
No login, subscription/default change, image publication, staff identity setup or runtime invocation was performed.
Read-only action APIs for name availability and ARM validation/what-if do not deploy the submitted templates.

### Actual what-if and validation

The authorized group-level what-if failed because the group does not exist.
The Azure CLI also printed a secondary response-consumption traceback; the underlying error is
`ResourceGroupNotFound`, not a host denial. Both outputs are retained.

Instead of creating the group, generated a subscription-scope **preview-only** wrapper containing that exact
group and the unchanged, freshly compiled main template with inner expression evaluation.
The wrapper adds no unrelated resource, region, subscription or environment.

| Change type | Actual count |
| --- | --- |
| Create | 33, including the group |
| Modify | 0 |
| Delete | 0 |
| Unsupported | 13 |

The subscription what-if returned `status: Succeeded`, `error: null`.
All 33 identifiable creates are inside the authorized group or are the group itself.
The 13 unsupported entries are role assignments whose IDs depend on not-yet-created managed identity principal IDs:
three telemetry, three registry, two Cosmos, three broker, one signing key and one Foundry project grant.
These are unresolved changes, **not thirteen independently validated grants or zero-risk changes**.
The exact expressions and reasons remain in `evidence\what-if-subscription-c3e1750f.json`.

ARM subscription validation returned `properties.provisioningState: Succeeded`, `error: null`.
Its validated-resource list includes the group, identities, network, workspace and deployment wrappers.
It does not establish that every nested resource provider, SKU, quota or policy will accept creation after
identity-dependent expressions resolve. Runtime.bicep was not previewed: actual outputs, installed agent versions
and a published image digest do not exist and were not fabricated.

Commands actually executed from the repository root:

```powershell
az bicep build --file generated-scenarios\resto-scale-agent\infra\main.bicep `
  --outfile generated-scenarios\resto-scale-agent\evidence\what-if-main-c3e1750f.arm.json
az bicep lint --file generated-scenarios\resto-scale-agent\infra\main.bicep
python generated-scenarios\resto-scale-agent\evidence\prepare-what-if-c3e1750f.py
```

Both Bicep commands and wrapper generation exited 0. With the exact authorized subscription:

```powershell
$subscriptionId = 'efd64343-6ef4-4926-951f-d3229f38bd76'
$evidence = 'generated-scenarios\resto-scale-agent\evidence'
az deployment group what-if --subscription $subscriptionId `
  --resource-group rg-resto-scale-agent --name reference-preflight-c3e1750f `
  --template-file generated-scenarios\resto-scale-agent\infra\main.bicep `
  --parameters "@$evidence\main-preflight.parameters.json" --no-pretty-print --output json
az deployment sub what-if --subscription $subscriptionId --location eastus2 `
  --name resto-scale-agent-preflight-c3e1750f `
  --template-file "$evidence\what-if-subscription-c3e1750f.arm.json" --no-pretty-print --output json
az deployment sub validate --subscription $subscriptionId --location eastus2 `
  --name resto-scale-agent-validate-c3e1750f `
  --template-file "$evidence\what-if-subscription-c3e1750f.arm.json" --output json
```

The group command exited 1; subscription what-if and validation each exited 0 with the structured results above.
Their JSON and stderr are retained under matching `what-if-*` and `validate-subscription-*` evidence filenames.
The parameters pin a preview key expiration; refresh it before any later deployment so expiry remains 180 days.
The compiled template/wrapper is evidence, not a replacement production deployment entry point.

### Read-only preflight findings

| Check | Actual result and retained evidence |
| --- | --- |
| Identity | Exact account/subscription/tenant match, subscription Enabled; `identity-c3e1750f.json` |
| azd | `azd auth login --check-status` reported the same account; no environment initialized |
| Providers | All eleven required namespaces Registered; `providers-c3e1750f.json` |
| Deployer RBAC | Subscription Owner and Foundry User; `rbac-c3e1750f.json` |
| Consumer role | `Foundry Agent Consumer`: `eed3b665-ab3a-47b6-8f48-c9382fb1dad6` |
| Policies | Three inherited/subscription assignments inspected; `policy-assignments-c3e1750f.json` |
| Model | Exact AIServices S0 GA model/version and GlobalStandard listed; `model-eligibility-c3e1750f.json` |
| Quota | Limit 1,000, used 1, available 999 capacity units; request 100; `model-quota-c3e1750f.json` |
| Model capacity | East US 2 GlobalStandard availableCapacity 999; `model-capacities-filtered-c3e1750f.json` |
| Broker | Premium supports SKU, zones and partitions in East US 2; `servicebus-skus-all-c3e1750f.json` |
| ACA | Regional resources listed; managed environments 0/50; `aca-regions/usage-c3e1750f.json` |
| Names | ACR/vault/broker/Foundry available; Cosmos name does not exist; matching `*-name-c3e1750f.json` |
| Target isolation | `az group exists --subscription $subscriptionId --name rg-resto-scale-agent`: false twice |

Quota units represent thousands of tokens/minute: the request is 100,000 TPM, not 100 tokens/minute.
Model SKU metadata reports one request and 1,000 tokens per 60 seconds per capacity unit.
The expected allocation is 100 RPM/100k TPM; actual allocation, throttling and function behavior remain untested.
Capacity is transient metadata, not a reservation or proof of an accepted inference.

All Azure management commands passed the explicit subscription; `az ad signed-in-user show` resolved the
tenant-specific setup principal without changing identity. No access tokens were displayed or retained.
The first capacity URL lost its ampersand parameters through Windows az.cmd parsing.
The corrected query used `az rest --url-parameters` and retained the complete structured response.
The initial unfiltered capacity result and incorrect top-level broker SKU filter were empty, not passing checks.
The corrected broker filter is `properties.skuName`, not the region-valued `name`.
An optional GET name probe used an unsupported route and failed; the proper read-only
`CheckNameAvailability` action subsequently confirmed the name. Earlier failures were not hidden.
Dedicated workload-profile enumeration is not independent proof of Consumption capacity.

The existing fourteen Checkov findings remain retained, not suppressed or relabeled as a clean scan.
Public endpoints and Basic/software-key choices match the confirmed synthetic-only design.
The actual preview confirms Key Vault purge protection, 90-day soft delete, RBAC, key expiry/rotation,
and Foundry SystemAssigned identity with local authentication disabled.
This narrows unresolved-expression findings but does not certify runtime enforcement or all policy compliance.
No production security, payment, regional-outage or measured scale guarantee is claimed.

### Regional cost review

USD retail meters were fetched from the public Azure Retail Prices API for East US 2.
Raw responses are `prices-servicebus/aca/cosmos/model-by-meter-c3e1750f.json`; no price pagination remained.
The old `Azure OpenAI` service filter returned no selected-model meters.
The corrected model meter query resolves current `Foundry Models` / `Azure OpenAI GPT5` pricing.

| Component | Observed rate and planning calculation |
| --- | --- |
| Premium broker 1 MU | $0.9275/hour; $677.08 for 730 hours |
| ACA active CPU | $0.000024/vCPU-second |
| ACA idle CPU and memory | CPU $0.000003/vCPU-second; memory $0.000003/GiB-second |
| Nine minimum replicas | 4.5 vCPU/9 GiB: approximately $106.43 idle to $354.78 active/month |
| ACA requests | $0.40/million; free grants not deducted |
| Cosmos autoscale | $0.012 per 100 RU/s-hour: $35.04-$350.40 for 400-4,000 RU/s over 730 hours |
| Cosmos data | $0.25/GB-month; backup/restore and other usage can add charges |
| Other infrastructure | $30-$120 planning allowance, not an independently quoted all-inclusive rate |
| GlobalStandard input | $0.75/million uncached input tokens; cached input discounts not assumed |
| GlobalStandard output | $4.50/million output/reasoning tokens; priority/batch meters not substituted |

**Shared-infrastructure-only planning allowance: about $745-$1,150/month**, before application/model usage.
**Full reference planning allowance: about $900-$1,650/month** at nine warm replicas and 200 chat turns/day.
The latter includes approximately $50.40 model usage for 24M input/7.2M output tokens per 30 days,
and rounded contingency for ancillary/zone/usage variation. It is not a quote, approved budget or spending cap.
These ranges exclude sustained burst replicas, high request/telemetry volume, taxes and negotiated discounts.
All 28 maximum replicas continuously active would add about $748.98/month beyond nine active replicas.
Environment/private endpoint/dedicated-plan meters returned by the API were not blindly added to Consumption.
Reconcile actual billed meters, zone treatment and available free grants after authorized provisioning.

## Deployed Resources

The current Central US enumeration lists **14 resources**, including the direct child Foundry project.
All shared deployment modules succeeded. Nested configuration/grants are not independently enumerated by
`az resource list`; its count must not be compared directly with preview create counts.

| Resource or module | Actual result |
| --- | --- |
| Four user-assigned identities | All four modules Succeeded |
| VNet/subnet, workspace and Application Insights | Modules Succeeded |
| Basic registry `acrresto4tvlzr5zf2rxi` | Module Succeeded; no image published |
| Cosmos `cosmos-resto-4tvlzr5zf2rxi` | Module Succeeded; all three database-scoped grants verified |
| Premium broker `sb-resto-4tvlzr5zf2rxi` and kitchen queue | Module Succeeded; messaging not runtime-tested |
| Vault `kv-resto-dc9a173f4d0b5f6` and signing key | Module Succeeded; purge protection and RBAC retained |
| Foundry `ai-resto-6f6767a4ef6b5c6bb82c4a11edebfdec` | Account and exact model Succeeded |
| Direct child project `restaurant` | Module Succeeded; no agents initialized |
| Container environment `cae-resto-4tvlzr5zf2rxi` | Succeeded; zonal Consumption environment |
| Two staff applications/service principals | Installed and verified; assignment-required retained |
| Operator Manager/API and default-client assignments | Installed and independently read back |
| Operator-specific delegated consent | Denied; no grant exists; portal setup blocker persisted |
| Three runtime Container Apps | Not deployed; stopped before rollout on the directory denial |

Current resource/module evidence is in `evidence\installation-e13812c5\resources-final.json`,
`deployments-after-provision.json` and `deployment-final.json`.
The successful root output set is retained in `infrastructure-outputs.json`.
The earlier failed attempt remains historical in `evidence\foundation-47a34228\`.
No application URL or live runtime result exists.

The earlier 25 application and eight Python checks, nonroot image checks, static findings and load-coverage limits
remain the local baseline described in `05-implementation-reference.md` and `07-webapp-summary.md`.
No model, agent, guest/staff chat, complete business journey, broker recovery or target load test ran in Azure.

## Outputs (Expected)

| Output | Current observed value or limitation |
| --- | --- |
| Complete infrastructure outputs | Captured from successful current root deployment |
| Registry | `acrresto4tvlzr5zf2rxi.azurecr.io`; provisioned, no scenario image published |
| Foundry project | Installed direct child `restaurant`; no agents initialized |
| Container environment domain | `proudsea-27880dc7.centralus.azurecontainerapps.io`; no runtime apps |
| Cosmos endpoint | `cosmos-resto-4tvlzr5zf2rxi.documents.azure.com`; provisioned, not data-plane tested |
| Key Vault/signing output | `kv-resto-dc9a173f4d0b5f6`; vault/key provisioned |
| Foundry project endpoint | Discovered from actual project properties; see `installation-e13812c5\project.json` |
| Staff API client ID | `4310055b-a107-4224-942c-01926f424ffd` |
| Staff native client ID | `9e01b233-2898-49c8-8e9e-1c8ffc2f8ad5` |
| Operator delegated consent | Absent; actual Graph 403; exact request and read-only verifier prepared |
| Image digest and agent versions | Not published/installed in Azure |
| Application URL | Unavailable |
| Runtime validation receipt | Not created; no fabricated `scenario-validation.json` |

The earlier East US 2 failure and other region rejection history remain retained.
The new consolidated Central US decision was explicitly answered and used for this installation.
Shared provisioning and owned directory setup succeeded; the exact operator consent write was denied.
The canonical portal blocker now requires external scoped consent remediation and actual read-only verification.
Preserve and reuse installed resources, generated receipts and prior answers.
No bypass, permission broadening, cleanup, destructive change, suitability approval or hack/event work is authorized.

[cosmos-role-schema]:
  https://learn.microsoft.com/azure/templates/microsoft.documentdb/databaseaccounts/sqlroleassignments
[graph-consent]:
  https://learn.microsoft.com/graph/api/oauth2permissiongrant-post?view=graph-rest-1.0
