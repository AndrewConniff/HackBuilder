# Deployment preparation: equip-ai

## Current resumption: 2026-10-28 UTC

The user's **ok to progress** resumes technical acceptance, not scenario suitability or hack composition.
Existing account, subscription, tenant, private endpoints, model and agent version are unchanged.
The existing management VM was started; no new paid resource was allocated.

Private management-identity REST probes passed for agent listing, selected-model Responses and versioned-agent
Responses. The same application .NET SDK also completed a real versioned-agent response from that VM.
These results isolate the remaining application failure from a general model/agent or SDK outage;
they do not prove web-identity inference or deploying-user administration.
See [native REST probes](local-evidence/resume-20261028/private-runtime-probes.json)
and [same-SDK probe](local-evidence/resume-20261028/private-sdk-probe.json).
SCM has no workload identity endpoint, so it cannot substitute for the actual application container.
The temporary SCM probe was removed.

The web app's existing roles cover AIServices Responses and endpoint interaction.
The provider also publishes a distinct OpenAI Responses write action. A temporary project-scoped,
single-action permission diagnostic was inconclusive because the application timed out during sign-in;
its role and assignment were removed. No broader workload administrator role was retained.

The diagnostic CLI builds with zero warnings/errors and all 63 local app/browser checks pass.
The first local run lacked the existing browser path; rerunning with the installed Edge path passed.
Private republishing completed its installation steps, but the first exact-build readiness gate failed.
An explicit web restart subsequently encountered cold-start timeouts. The exact deployed assembly was then
verified at 15:02:54 UTC, together with real local-account login; the chat hit its explicit dependency deadline.
Warmup now uses the nondependent `/health` path with a bounded 600-second container startup allowance;
the intended always-on setting was restored. IaC build and lint pass with these persistent settings.
A nonpublic startup diagnostic at 15:09:08 UTC verified the actual web identity and ai.azure.com token audience;
the same SDK call then returned native HTTP 403. The original normal startup command was restored afterward.
See [web-container probe](local-evidence/resume-20261028/web-startup-probe.json).
Process readiness remains explicitly `cloudValidated: false`, not successful scenario acceptance.

### Proposed human administration repair, not deployed

The existing Run Command-only Ubuntu VM is not sufficient for the required human browser/CLI administration.
Propose reusing that VM with a lightweight desktop, xrdp and a browser, reached through Bastion Standard
native-client tunneling. Keep the VM without a public IP; permit RDP only from a new dedicated Bastion subnet.
The Bastion endpoint itself needs a Standard public IPv4 address and HTTPS, not public workload data access.
Add a nonoverlapping VNet address range and a /26 AzureBastionSubnet only after exact network validation and approval.
Retain managed-identity Run Command and authenticated artifact staging for unattended installation.
VM desktop sign-in is distinct from the deploying user's interactive Azure browser/CLI sign-in and MFA.
No Entra consent, tenant roles, credential copying or public Foundry/Blob exception is proposed.

Public Central US PAYG meters checked on 2026-10-28: Standard Gateway USD 0.29/hour;
Standard Static IP Addresses USD 0.006/hour. At 730 hours this adds USD 216.08/month,
for an illustrative USD 465.50/month total before extra outbound data/tax.
The existing VM/disk is already included; extra Bastion scale units are not proposed.
VM shutdown does not stop Bastion/IP/disk charges; delete the approved Bastion/IP when no longer needed.
This is a new paid management/security scope requiring explicit approval before provisioning.
Availability, exact what-if, desktop capacity and real deploying-user browser/data CRUD remain pending.
An already connected browser/CLI environment could avoid the addition only after equivalent access is verified.
SSH-only/Bastion Developer access is not represented as a working private browser path.

Sources: [Bastion native client][bastion-native], [Ubuntu desktop/xrdp][ubuntu-desktop]
and the [Azure Retail Prices API][retail-prices].
The full deploying-user matrix must cover Foundry agent/model administration, Blob safe CRUD,
IoT device/twin lifecycle, application/cleaner configuration and scenario monitoring/network resources.
Use scoped effective roles and the user's own credentials; workload-MI success cannot satisfy it.
IoT Hub Registry Contributor alone is not full twin/data administration.
No suitability review or hack composition can proceed while these requirements remain unverified.
The [structured access proposal](local-evidence/resume-20261028/deployer-access-plan.json)
separates inherited roles already observed from unverified own-user private lifecycle tests.

[bastion-native]: https://learn.microsoft.com/en-us/azure/bastion/native-client
[ubuntu-desktop]: https://learn.microsoft.com/en-us/azure/virtual-machines/linux/use-remote-desktop
[retail-prices]: https://prices.azure.com/api/retail/prices

## Current resumption: 2026-10-26 UTC

Restoration was explicitly approved by the user's reply **yes** at 00:26:11 UTC.
Current Central US eligibility and prices were refreshed; the estimate is USD 249.42/month,
including a USD 0.06 local-account operation allowance. Full-source what-if returned 22 creates,
no changes/deletes and 15 dependent nested-expansion warnings.
The local-account implementation passes 63 executable checks and 37 Python installer/acceptance checks.

Actual provisioning exposed a limitation hidden by those nested warnings: the original Foundry account
was soft-deleted at 2026-10-25T18:13:28.4730582Z and ARM requires `restore: true`.
The guarded preprovision hook now verifies the exact account/group/region and supplies the AVM restore flag.
It never purges or substitutes another account. Earlier partial resources are retained for idempotent retry.
The first bootstrap attempt also exposed a CLI parsing defect; standalone installation switches
are now removed before configuration parsing. Both failed attempts remain in dated diagnostics.
`azd up --environment equip-ai --no-prompt` succeeded at 00:58:21 UTC,
with ARM deployment `equip-ai-1792975951`. Both applications were published through the private VM.
Actual private DNS, managed-identity agent initialization and local-account hash installation passed.
Source-aligned republishing uses `azd hooks run postprovision --environment equip-ai --no-prompt`,
not another infrastructure allocation or public cleaner exception.

Live local login, five-device Tacoma scope, anonymous/cross-site/CSRF denials and real X.509 publishing passed.
An actual scoped role readback and authenticated outside-network Blob/cleaner denials also passed.
The first registry attempt exposed a token-audience defect: a trailing slash produces a different JWT audience.
The documented `https://iothubs.azure.net` audience immediately returned the expected device-not-found response
with the already installed Registry Contributor role; no additional permission was needed.
Windows Schannel then rejected an ephemeral private key. The publisher now imports into a transient user
key container on Windows, without `PersistKeySet`, and real TLS/certificate messages were acknowledged.
The first 3,000-message burst was acknowledged but failed the strict per-second offered cadence.
Warm-up and bounded outstanding sends were repaired; that failed receipt is retained, not called a pass.
The repaired burst passed: all 3,000 real messages acknowledged and exactly 50 offered in each of 60 seconds.
It warms the connection outside the measured window, uses bounded outstanding sends, and sends a paced cohort
within each second rather than scheduling an event against the next second's boundary.
One separately recorded warm-up message is not counted as part of the 3,000-message burst.
An actual routed-evidence read exposed that the bounded cache dropped expired payloads before their diagnostic
could be counted. Per-device counters now survive that filter without retaining expired payloads;
both direct evidence and agent tools use those scoped counters. The new cross-equipment isolation test passed.
Twenty live checks passed, including exact routed counts, metrics and expiry/stale/missing cases.
Actual app-managed-identity evidence matched the complete synthetic publication history after routing settled.

### Remaining native Foundry denial

The real application calls
`POST .../api/projects/equipment-operations/openai/v1/responses` with the pinned agent `equipment-operations/1`.
The service returns **HTTP 403 with no body**; the application reports a correlated 502, not a successful chat.
Latest observed correlation: `0HNPJ0J14LNRR:00000010` at 2026-10-26T02:06:24 UTC.
Web identity: `95e688cf-66f0-4d71-b361-8ab5cb20a890`.
Actual project assignments include Foundry Agent Consumer and Foundry Project Runtime User;
the latter's verified data actions are `Microsoft.CognitiveServices/accounts/AIServices/responses/*`.

The actual web execution environment resolved Foundry to private IP `10.247.0.72` and completed TLS.
Official [Foundry RBAC guidance][foundry-rbac] also requires the project's managed identity to have
Foundry User on its parent account. That previously absent prerequisite is now installed and declared in IaC.
Its exact preview had one create, three unchanged assignments and no resource deletion.
It did **not** resolve the web Responses denial, and is not represented as an inference pass.
An additional bounded diagnostic tried the same Responses-only role at the dedicated account scope.
All 12 probes still failed; that single diagnostic assignment was removed and the original project roles retained.
No broader developer/owner role was granted to the web app, no keys were substituted,
and no private endpoint or tenant consent setting was relaxed.
The denial's underlying cause is still unresolved and needs a Foundry access/service review.

Temporary private exception-capture code and files were removed.
Persistent diagnostics log only safe service status/code, endpoint and correlation, not chat/event bodies.
Publication now waits for a health response matching the actual published assembly SHA-256 and pinned agent version.
This replaces blind restart timing; health explicitly continues to say `cloudValidated: false`.
The invalid-version acceptance helper uses the same bounded configuration-readiness check.

| Exact command | Result |
| --- | --- |
| `azd up --environment equip-ai --no-prompt` | Passed; same-target restoration and private installation |
| `azd hooks run postprovision --environment equip-ai --no-prompt` | Passed; exact current build/configuration |
| `dotnet build tests\EquipAI.Tests\EquipAI.Tests.csproj --no-restore` | Passed; no warnings/errors |
| `dotnet run --project tests\EquipAI.Tests\EquipAI.Tests.csproj --no-build -- .` | Passed; 63 local checks |
| `python -m unittest discover -s tests -p "test_*.py"` | Passed; 37 tests |
| `python scripts\validate_live.py` | Failed at real chat after 20 passing checks |
| `az bicep build --file infra\main.bicep` and `az bicep lint --file infra\main.bicep` | Passed |
| `node --check src\EquipAI.Web\wwwroot\app.js` | Passed |

No real model/agent inference, agent-driven grounding/tools, complete coach/statewide flow, live lockout recovery,
invalid-version recovery, concurrent grounded latency or successful browser chat is claimed.
Full deploying-user administration and private data-plane CRUD remain unverified too:
installed scoped roles, registry operations and an expected outside-network storage denial are not that proof.
Do not substitute successful workload-identity access for the deploying user's own acceptance.
No suitability snapshot, approval, hack package, event deployment or publication was created.
The retained offline scan has 14 assessed findings and was not rerun or relabeled as passing.
See [the current validation index](scenario-validation.json) and [the real live checks][live-checks].

[foundry-rbac]: https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry
[live-checks]: local-evidence/resume-20261026/live-checks.json

### Historical observation before restoration consent

**The recorded reference is not currently deployed in its approved resource group.**
The authenticated CLI/azd identities still match the retained subscription and tenant,
but `az group exists` returned `false` for `rg-equip-ai`; the old app hostname fails DNS.
This resumption performed no Azure mutations or resource deletion.
All 29 Python installation tests passed locally. Complete live runtime validation remains unperformed.

See [the current-state receipt](local-evidence/resume-20261026/current-state.json)
and [the rebuild review](local-evidence/resume-20261026/deployment-review.md).
The review preserves private networking, managed identities and site isolation,
reconciles the older Entra login with the user's newer local-account requirement,
and carries the hub-scoped deployer RBAC correction into installation.
The last USD 249.36/month illustration must be refreshed before restoring paid resources.
The installation, endpoint and cost statements below are historical, not proof of current resources.

## Current installation and acceptance boundary: 2026-10-25 UTC

The user's "go for it" approved the presented D2als_v7 replacement and USD 249.36/month illustration.
Exact scope and response are retained in
`local-evidence/management-sku-substitution-20261024/deployment-approval.json`.
All targets remain Central US, `rg-equip-ai`, the retained subscription/tenant and environment `equip-ai`.

- Restored missing scenario-local azd inputs from actual identity and approved model/network values.
  No shared default changed. An initial system-Python process crash was avoided using the existing repository venv.
- Full-source ARM what-if: `Succeeded`, 21 creates, zero delete/modify, 14 `NestedDeploymentShortCircuited` warnings.
  This is not complete resource coverage. Full ARM validation then returned `Succeeded`.
- `azd up --environment equip-ai --no-prompt` provisioned deployment `equip-ai-1792886351` successfully.
  Its first postprovision transfer failed, so the overall command exited 1; this failure is retained.
- Actual VM: `Standard_D2als_v7`, `TrustedLaunch`, `StandardSSD_LRS`, provisioning `Succeeded`.
- Oversized 512 KiB inline Run Command payloads failed to execute; small diagnostic scripts succeeded.
  The in-scope repair stages the sanitized ZIP in the existing web site's authenticated SCM `/data`,
  not public `wwwroot`. The private VM downloads with its existing managed identity and verifies SHA-256.
  No new resource/permission, private-access relaxation or anonymous artifact URL was added.
- Actual SCM returned an HTTPS deployment Location with explicit port 443.
  URL validation now accepts equivalent same-origin HTTPS default ports and rejects other origins/ports,
  HTTP and userinfo. Initial failed retries and exact header-origin diagnostic are retained.
- `python scripts\private_lifecycle.py publish` finally exited 0; both sites were published,
  actual Foundry agent `equipment-operations` version `1` was installed/reused, and the SCM artifact was deleted.
  `private-installation.json` records actual private-DNS and installation evidence, not inference.
- All 29 Python installation/transport/URL/identity-cleanup tests passed.
- The approved current user was verified through Graph `/me` and received only nominated Tacoma/API and SPA access.
  Temporary Tacoma removal/final Statewide assignment remain pending the cross-site acceptance test.

Actual URL: <https://app-equip-web-equipai-kex72v.azurewebsites.net/>.
`/health` and configured `/api/config` returned 200; anonymous `/api/equipment` and `/api/chat` returned 401.
Outside-network private cleaner `/health` returned 403. These are not authenticated chat or grounding results.

The real browser is on Microsoft sign-in and requires the user's own interactive authentication.
The actual IoT device-registry read returned `401002 Unauthorized access`.
The operator's existing Owner and Foundry User roles do not grant IoT device-registry data access.
The proposed missing permission is **temporary IoT Hub Registry Contributor**
(`4ea46cd5-c1b2-4a8e-910b-273211f9ce47`) for the configured user only, at the single scenario hub scope.
It permits device registration needed for X.509 synthetic ingress/negative tests, not subscription/directory privileges.
No such assignment or device credentials were created. Its fixed incremental resource cost is zero.

Local installation correction, 2026-10-24: the hub AVM module now declares Registry Contributor for
`principalId`, the existing azd deployer identity, at the scenario hub scope.
This supersedes the proposed manual temporary assignment above: device-registry installation access belongs
in the reviewed Bicep deployment, alongside the existing installer Storage and Foundry roles.
The [pinned AVM hub module][hub-avm-rbac] supports this hub-scoped `roleAssignments` input.
The change is local only; the deployed role assignment and its propagation have not been verified.
The existing 401002 result is retained, not retroactively marked passed.

The Entra login pause originates from requirements capability 1 and the API's delegated `Equipment.Read`
policy, not a portal approval rule. Keep that security requirement and distinguish its human acceptance test
from independent technical work. Continue installation, fixtures, model/tool checks and local tests without
waiting for the browser login. Authenticated end-to-end chat remains unverified until real acceptance passes;
do not use an anonymous endpoint, fabricated token or synthetic user principal as proof of web authentication.

[hub-avm-rbac]: https://github.com/Azure/bicep-registry-modules/blob/avm/res/devices/iot-hub/0.4.0/avm/res/devices/iot-hub/main.bicep

Full command receipts, failure logs, exact roles, endpoint checks and current approval are in
`local-evidence/management-sku-substitution-20261024`.
Model inference, agent invocation, authenticated chat, tool grounding and IoT-to-Blob acceptance remain unverified.
No suitability approval, snapshot claiming success, hack composition or event rollout occurred.
Resources remain provisioned and incur the disclosed ongoing charges while acceptance is blocked.

## Current VM substitution: 2026-10-24

The user requested: "substitute the vm standard_b2s with a similar vm size that is available in that region".
Standard_D2als_v7 replaces the restricted Standard_B2s in Central US, with the same 2 vCPUs/4 GiB.
Live subscription SKU metadata has no restrictions; Dalsv7, total-vCPU and VM-count quotas have headroom.
The retained Ubuntu Gen2 image supports Trusted Launch and NVMe; Azure selects the size's default controller.
The runner does not depend on a local temporary disk. Private networking and managed identities are unchanged.
Linux PAYG is $0.0804/hour, or $58.69/month at 730 hours, versus $36.43/month previously.
Rounded management/combined estimates become $97.83/$249.36 per month, about $22.27 more than before.
See `local-evidence/management-sku-substitution-20261024` for exact SKU, usage, prices and check receipts.
This supersedes the historical B2s blocker and old estimates below, not the retained user authorization.
Full exact ARM what-if, conditional provisioning and runtime acceptance remain separate pending checks.

## Current authoritative continuation: concrete management addition prepared

The 00:05 UTC Central US ordered ARM/dedicated Entra approval remains valid for its reviewed scope.
Neither the actual later read-only answer nor local design confirmation explicitly revokes it.
The older summary below incorrectly promoted the derived `authorization.json` prohibited list to user restriction.
That inference is superseded, not used to request routine reapproval.
See [the consolidated addition review](local-evidence/management-repair-20261024/deployment-review.md)
and its `authorization-reconciliation.json`.

New local work: AVM private VM/NAT/IP/NSG, persistent management subnet in the core VNet declaration,
least-privilege site/project identity grants, serial hashed transfer, managed-identity SCM publishing and agent-version capture.
azd pre/postprovision hooks now run this actual private path rather than workstation deployment to the private cleaner.
Management execution is guarded and not enabled/provisioned. No new Azure/Graph queries or writes occurred.
Build/lint and all 24 Python tests pass; unchanged 49 app/browser checks/Linux publish evidence is reused.
Both diagrams were updated/rendered using installed Graphviz. Initial missing-shell-PATH failure was repaired per process.

Only new management scope ($75.56/month addition; $227.09/month combined illustration) and the named
current-user application-role assignments are submitted for review. NAT rates are disclosed planning assumptions.
New Compute quota/SKU checks and exact expanded what-if remain pending, not fabricated.
No live URL, actual model inference/agent/chat/grounding/negative-case pass or suitability approval exists.
The subsequent dated sections are history, not the current authorization interpretation.

## Current Central US continuation: 2026-10-24

The latest scenario handoff was reconciled against both attached consent-history records and the later
Central US continuation receipt. The earlier ordered ARM/dedicated-directory grant is retained as actual history.
It is not invalid merely because the portal migrated or a worker receipt expired.
However, the later continuation explicitly prohibits deployment and Entra writes; that restriction governs this resume.
New management resources were not included in the earlier grant either.
See [the handoff reconciliation](local-evidence/handoff-reconciliation.json) for the exact sources and remaining decision.
The brief was recovered from the existing legacy project record because the scenario `request.json` is absent.
The workspace junction was verified and no scenario worker was observed.
No Azure/Graph queries, deployment, directory changes or redundant build/test runs occurred during this handoff.
Existing local checks and Central US preparation remain dated evidence, not newly executed tests.

The user explicitly authorized **"Authorize Central US read-only checks and ARM what-if"**.
Only that scope was executed in subscription `efd64343-6ef4-4926-951f-d3229f38bd76`,
tenant `16b3c013-d300-468d-ac64-7eda0820b6d3`, group `rg-equip-ai`, azd environment `equip-ai`.
CLI/azd identity and explicit saved Central US targets matched; no saved target or shared default was changed.

- Current B2 and aggregate regional worker quotas: 0 used / 10 limit, demand 1.
- Exact retained model/version/GlobalStandard: quota 0/5,000 and available capacity 5,000, demand 10.
- All ten required providers Registered, including `microsoft.insights`; no provider registration was performed.
- Actual independent ARM what-if: CLI exit 0, `Succeeded`, 35 creates, no returned deletes or modifications.
- Nine nested-expansion/short-circuit warnings and omitted final app settings prevent a full-reference pass.
- Fresh public rates still match the USD 151.53 illustrative baseline; actual management path and full cost remain unknown.
- No provisioning, Graph call, quota request, suitability approval, composition or publication occurred.

The complete current dependency matrix, exact commands/timestamps/results, what-if coverage, costs,
directory/private-host gaps and precise next alternatives are in
[the consolidated read-only review](local-evidence/centralus-20261024T2240Z/deployment-review.md).
Machine-readable current results: `local-evidence/centralus-20261024T2240Z/regional-readiness.json`.
Actual reported user response/restrictions: `local-evidence/centralus-20261024T2240Z/authorization.json`.
The group remains nonexistent, with no live URL or runtime proof.
No deployment approval is requested until management access, directory review, coverage and costs are complete.

Everything below retains its historical date and authority boundary; it does not supersede this continuation.
The earlier statement about using the portal target card is obsolete; all decisions belong in this VS Code chat.

## Historical local-only VS Code resume: 2026-10-24 22:34 UTC

This session reused the same junction-backed workspace and the legacy brief at
`.abcbuilder-portal/projects/equip-ai.json`. No scenario-specific worker was observed before edits.
Unrelated repository changes were preserved. No Azure/Graph queries, deployment, directory changes,
shared-tool installation or shared-default changes occurred in this session.

All nine retained local validation commands passed again. Evidence, exact commands, timestamps and logs:
`local-evidence/resume-20261024T2233Z/local-checks.json`.
The 15 installer tests and 49 application/browser checks passed; build reported zero warnings/errors.
Self-contained Linux x64 publish passed and ELF64 x86-64 plus bundled runtime were verified.
The 120,000-event deterministic aggregate took 277.2 ms, not a live chat p95 measurement.
Both diagram sources parsed and PNG integrity passed using the existing repository Python environment.
The initial system-Python integrity probe lacked Pillow; no installation was needed.
Diagram label overlap, historical group labeling and the absent management host remain disclosed limitations.

Earlier local application evidence and screenshots were copied into the dated directory before rerunning.
The current copies are also retained there. Previous `.worker` command logs remain unchanged.
Catalog metadata was refreshed with `scripts.scenario_catalog.refresh` and reviewed metadata,
without invoking the CLI's unrelated shared-index export.
The earlier nonpassing Checkov assessment is retained, not relabeled or rerun.

The latest authorized cloud preparation is still the dated East US quota failure below, not a new observation.
Saved Central US settings were not changed to bypass it. No current full-reference what-if, complete cost,
directory ownership readback or connected execution path is proved.
See `local-evidence/resume-20261024T2233Z/resume-review.md` for the exact next authorization request.
`scenario-validation.json` records blocked live acceptance, with no passing runtime checks.
`demoguide/demoguide.md` is a preparation runbook, not a demonstrated live scenario.
A suitability snapshot and approval remain deferred until real runtime acceptance passes.

> [!IMPORTANT]
> Current resume, 2026-10-24: exact-target East US read-only preparation is authorized, but blocked by B2 quota.
> Deployment and directory writes remain unauthorized. The current result is recorded first below.
> Targets, permissions, installation and checks below retain their historical dates and are not current grants.
> No Azure or Graph operations were performed during intake recovery or the earlier local-validation run.
> Reuse existing identity outputs without replacement only after authorized ownership/readback verification.
> Private publishing/agent-runner access remains unverified; its cost is absent from the retained estimate.
> A future deployment review must consolidate that access path, directory changes, what-if limitations and costs.

## Deployment Details

### Current exact-target preparation: blocked

Run `.worker\674986e4ef5744bb97b15a88438a95ed`; last Azure result `2026-10-24T20:34:13.485454+00:00`.
All canonical decisions/history were read at revision 26.
Decision `ecf2d376abd84bbea662a9f547bcd1ca` permits read-only preparation for this scope only:

| Field | Authorized value |
| --- | --- |
| Account | petender@microsoft.com |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76 |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Group / environment / region | rg-equip-ai / equip-ai / eastus |
| Deployment / directory writes | Not authorized; none performed |

**Observed blocker:** Microsoft.Web reports B2 worker quota **0 used / 0 limit**, demand **1**.
Its aggregate regional worker quota is also **0 / 0**, demand **1**.
The actual independent ARM what-if rejected `Microsoft.Web/serverFarms` with
`InternalSubscriptionIsOverQuotaForSku`; tracking ID `3d48011c-6670-459e-a53f-f3be7c2ad2fd`.
This is App Service quota, not Compute B-family VM quota, a sign-in failure or a host-tool failure.
No quota request, alternative SKU, alternative-region query, provisioning or directory operation followed.

```powershell
python generated-scenarios\equip-ai\.worker\674986e4ef5744bb97b15a88438a95ed\prepare.py identity
# Exact account/subscription/tenant match; subscription Enabled.

python generated-scenarios\equip-ai\.worker\674986e4ef5744bb97b15a88438a95ed\prepare.py quotas
python generated-scenarios\equip-ai\.worker\674986e4ef5744bb97b15a88438a95ed\prepare.py support
# All recorded Azure read commands exit 0; failed quota eligibility remains failed.

python generated-scenarios\equip-ai\.worker\674986e4ef5744bb97b15a88438a95ed\prepare.py preview
# Current Bicep build exit 0; actual independent ARM what-if exit 1: B2 quota.
```

Each Azure command has a `*.command.json` record with exact command, timestamps and actual exit code.
The first preview wrapper returned exit 0 despite ARM failing; the recorded ARM exit was always 1.
The wrapper now propagates that exit; it was not rerun against Azure to relabel the failure.
There are no successful change counts or complete destructive-change/Policy assessment.
`independent-coverage.json` records the freshly compiled source hash and excluded `runtimeConfiguration`;
installer-specific grants intentionally use empty `principalId`, not an invented identity.
This partial preview does not certify the complete reference or any directory/private data-plane changes.

| Other observation | Bounded result |
| --- | --- |
| Target group | Does not exist; none created |
| Retained model | AIServices S0 / gpt-4.1-mini 2025-04-14 / GlobalStandard catalog match |
| Model quota / capacity | 0 / 5000 quota; available capacity 5000; planned 10; not reserved |
| Model lifecycle | Legacy; inference deprecation 2027-04-14; no substitution |
| IoT Hub | Paid-hub quota 0 / 50; exact B2 regional allocation and X.509 routing unproved |
| Storage | Account quota 0 / 250 and subscription SKU response read; private/routing acceptance pending |
| Providers | Nine returned Registered; Microsoft.Insights absent from response, not assumed ready |
| ARM / Policy | Management wildcard and three policy assignments read; not consent or full Policy validation |
| Local validation | Prior 15 installer / 49 app checks reused; no new runtime-success claim |

**Target review required:** the portal authorizes `eastus`, but `.azure\equip-ai\.env`,
`deployment-target-preview.json` and the identity receipt retain `centralus`.
All current cloud commands explicitly used authorized East US without modifying saved targets or shared defaults.
Use the portal Azure context card to reconcile this mismatch and authorize any alternative's read-only checks.
Central US has historical partial eligibility evidence only; it was not rechecked or selected in this attempt.
Do not recreate registrations, import a differently scoped ownership receipt or ask for generated client IDs.

`preparation-result.json` inventories every retained dependency, including uncataloged IoT Hub,
Entra installation and VNet-connected ZIP publishing/agent initialization/runtime execution.
No connected private execution path is evidenced, priced or newly authorized.
The complete deployment review therefore remains **incomplete**, not ready for deployment consent.
The old Central US **USD 151.53/month** illustration, including **USD 99.95 fixed charges**,
is not a current quote and excludes private runner/connectivity, egress, applicable Entra licensing,
taxes and support.
After target eligibility, consolidate verified identity reuse/redirects and any nominated role assignments,
directory authority, ARM changes, private execution path and complete costs into one installation review.
Keep technical ordering in the existing azd hooks; do not introduce successive infrastructure/app approval cards.
No deployment completion, live validation, suitability snapshot, composition, team rollout or publication occurred.

### Current local-validation checkpoint

Run: `.worker\637e1371f3b14e8d9aac9d95863a0e61`, 2026-10-24 UTC.
Canonical design decision `27f063435fdd48448544382139d45135` explicitly permits local validation only.
All canonical decisions/history were read. Cloud authorizations are empty; no deployment context is recorded.
Historical azd settings, installation receipts and target previews were not treated as permission or current readiness.
No shared defaults, tools, source architecture, app behavior, seeds or diagram images were changed.

The existing validator now accepts a scenario-contained output directory, preserving earlier command logs.
The installer contract test now compiles the current Bicep instead of reading a historical compiled fixture.
It also uses its own temporary directory rather than another run's directory.

```powershell
python scripts\check_prerequisites.py --for-project --record --stage local-validation --json
# Exit 0: local profile ready; approved NuGet metadata HTTPS/TLS and real PNG render passed.

python generated-scenarios\equip-ai\.worker\fa96363ef14f40ffa063aff3dcfd430c\validate_local.py `
  --output-directory generated-scenarios\equip-ai\.worker\637e1371f3b14e8d9aac9d95863a0e61
# Exit 0: all nine recorded commands passed.
```

`local-checks.json` retains exact commands, UTC times, exit codes and stdout/stderr paths:

| Check | Actual result |
| --- | --- |
| `az bicep build` / `az bicep lint` | Both exit 0; no diagnostics |
| Installer `unittest` suite | 15 passed, including current-template dependency ordering |
| `dotnet nuget list source --configfile ...\NuGet.Config` | Only MicrosoftPackageFeedProxy enabled |
| Test-project `dotnet restore` / `dotnet build --no-restore` | Exit 0; build has zero warnings/errors |
| Retained executable test harness | 49 deterministic, owned-loopback and Chromium checks passed |
| Linux RID restore / self-contained Release publish | Exit 0; no Docker or remote image build |
| Published artifact / ZIP inspection | ELF64 x86-64; bundled runtime, seeds and web assets; ZIP CRC valid |
| Retained diagram source/PNG checks | Both syntax/integrity checks passed; images not regenerated |

The 120,000-event deterministic aggregate took **290.4 ms**.
This is not five-concurrent-user live response p95, complete 1,000-device resource profiling or ingestion acceptance.
Browser checks prove only the branded missing-configuration shell, no horizontal overflow at 1440/390px,
and expected unauthenticated API rejection. Owned server/browser processes were closed by the harness.
`publish-checks.json` records the ZIP hash and 378 entries; Linux execution and Azure deployment were not performed.
`diagram-checks.json` records retained PNG hashes/dimensions and crossing-label readability limitations.

### Offline policy scan: nonpassing, with bounded applicability

```powershell
python -m checkov.main --directory generated-scenarios\equip-ai\infra `
  --framework bicep --skip-download --quiet --output json
# Exit 1: 5 passed, 14 failed, 0 skipped, 0 parsing errors; 37 resources reported.
```

Raw command/output is retained in this run's `checkov.*` files. No checks were suppressed or retried with skips.
All 14 findings apply seven rules twice to the two `appsettings` child resources in
`infra\modules\app-settings.bicep`. The installed scanner's rule implementations were inspected:
they inspect site/authsettings/web-config properties on all `Microsoft.Web/sites/config` objects.
These appsettings objects do not carry those properties.

| Rule | Assessment, not a passing scanner result |
| --- | --- |
| CKV_AZURE_13 | Tests platform authsettings; required JWT/tenant/scope/site checks live in the application |
| CKV_AZURE_65 / 66 / 63 | Detailed errors, request tracing and HTTP logs are not appsettings properties |
| CKV_AZURE_80 | Demands `netFrameworkVersion=v8.0`; design is self-contained Linux .NET 10 |
| CKV_AZURE_222 | Network setting belongs to parent sites; public authenticated web/private cleaner retained |
| CKV_AZURE_88 | Demands Azure Files; selected deployment is ZIP, not an Azure Files mount |

The parent AVM site explicitly configures TLS, public/private access, managed identity and sanitized console logs.
Adding raw request tracing or detailed payload logging to satisfy generic rules would contradict the privacy design.
This assessment is **not** Azure Policy validation, a comprehensive AVM scan or proof of deployed authentication.
The source scan does not establish complete coverage of registry-module resources.
Live Entra positive/negative token tests, effective settings, governance and private reachability remain required.
`policy-assessment.json` preserves rule-by-rule classifications while retaining the nonzero scanner result.

### Readiness and next authorization boundary

`dependency-readiness.json` inventories Foundry, Blob, IoT Hub, hosting, identities, networking, monitoring,
Entra installation, private publishing/agent initialization/runtime execution and their current evidence limits.
IoT Hub remains a required uncataloged B2 dependency, not a Service Bus/Functions substitution.
Local package restore proves SDK compatibility, not X.509 ingestion, managed-identity routing or live model support.
Exact 1,024-blob/128-MiB/eight-read runtime enforcement, cache behavior, ETag conflicts, five-user p95
and healthy-operation deletion timing need further targeted/live evidence; no blanket coverage claim is made.

**Decision required:** use the portal Azure context card to review the exact account/subscription/tenant,
resource group, environment and region, then separately authorize read-only preparation.
No historical target has been selected or imported as consent. Do not ask for generated identity IDs.
Within a later authorized scope, verify retained identity ownership before reuse and prepare one coherent
deployment review including directory changes, real what-if coverage, private execution path and complete costs.
The old USD 151.53/month illustration excludes that path and is not a current complete quote.
Preparation permission will not authorize directory writes, provisioning or suitability approval.
No snapshot, runtime-success record, hack content, team deployment or publication was created.

### Historical preparation chronology

| Property | Observed value |
| --- | --- |
| Date | 2026-10-24 UTC; earlier observations retain their dates |
| Account | petender@microsoft.com |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76 |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Authorized group / environment | rg-equip-ai / equip-ai |
| Authorized region | centralus |
| Authorization | Read-only preflight and what-if only |
| Deployment | Not authorized; not attempted |
| Preparation status | Ordered installation review prepared; full readiness remains unproved |

Current permission is the canonical read-only preparation scope refreshed at `2026-10-23T23:31:37.727625+00:00`.
Decision `14a2c19c1aa947f79680a7b130172581` is the historical preparation authorization.
The portal-selected environment supersedes the earlier `equip-ai-reference` naming proposal.
No shared CLI defaults were changed and no azd environment was initialized.

### Earlier read-only observations

Raw results reside in `.worker\2d77e6958d6f4ebd8d0f764234436eb3`.
All ARM queries supplied the authorized subscription explicitly.

| Check | Result / evidence file |
| --- | --- |
| Azure CLI account | Exact account, tenant and subscription match; subscription Enabled |
| Token metadata | Authorized tenant/subscription match; expiry returned; token never displayed or saved |
| azd authentication | Signed in as petender@microsoft.com; target-tenant deployment remains unverified |
| Resource group | `az group exists`: false; no group created |
| Provider registration | Nine required providers Registered; `providers.json`, `insights-provider.json` |
| Effective ARM permissions | Management wildcard allowed; `arm-permissions.json`; no RBAC mutations |
| Model catalog | Exact AIServices S0 / model version / GlobalStandard supported; `model-availability.json` |
| Model quota | 0 used of 5000 units, planned capacity 10; `model-quota.json` |
| Model lifecycle | Legacy; listed inference deprecation 2027-04-14; no model substitution |
| Linux B2 hosting | East US listed; `appservice-regions.json`; not a reservation |
| IoT quota | 0 paid hubs of limit 50; `iot-usage.json`; B2 allocation not proved |
| Policy | Three assignments retained in `policy-assignments.json`; full effects not evaluated |
| What-if | Not executed; no create/modify/delete counts exist |
| Pricing | Existing USD 150-400/month planning envelope only; not repriced or a spend authorization |

### Workflow blocker history and verified recovery

The preparation start report was rejected:

```text
python scripts\portal_workflow.py report --revision 18 --event
  generated-scenarios\equip-ai\.worker\2d77e6958d6f4ebd8d0f764234436eb3\deployment-running.json
Exit 1: Exact-target deployment consent is required for cloud stages.
```

That was a workflow defect, not an Azure RBAC or execution-host denial.
On the 2026-10-23 retry, the exact recorded isolated verification passed under unchanged permissions:

```powershell
python generated-scenarios\equip-ai\.worker\2d77e6958d6f4ebd8d0f764234436eb3\verify_preparation_reporting.py `
  --repository C:\HackBuilder
```

Exit 0: `PASS: scoped preparation reporting works; deployment and other targets remain denied.`
The worker did not repair repository files, install tools, change PATH or broaden trust.
Canonical revision 25 recorded the current blocker ID with `setupVerification.passed: true`
and returned deployment to pending. The existing preparation authorization was reused.
Revision 32 accepted the exact-scope `operation: deployment-preparation` running report,
separately from actual deployment progress.

### Resumed local verification

Current evidence is in `.worker\62a57487de8142ae9c39888e5f840385` and `local-evidence`.
Fresh owner-bound Bicep, application, local-validation and deployment prerequisite audits all passed.

| Command / check | Actual result |
| --- | --- |
| `az bicep build --file infra\main.bicep` with run-owned output | Exit 0; no diagnostics |
| `az bicep lint --file infra\main.bicep` | Exit 0; no diagnostics |
| Physical-workspace `dotnet nuget list source` | Only MicrosoftPackageFeedProxy enabled |
| Initial test-project `dotnet build --no-restore` | Failed: misplaced test separated `try` from `catch` |
| Build after relocating existing cache-budget assertion | Exit 0; zero warnings/errors |
| Test-project `dotnet run --no-build -- C:\azd-projects\equip-ai` | Exit 0; 49 local checks passed |
| 120,000-event aggregation | 265.3 ms; below 30-second threshold |
| Cache / security / browser | Budget rejection, malformed tools, 401s and both viewport checks passed |

The harness used the existing approved Chromium cache and cleaned up its own browser and loopback server.
`local-evidence\application-checks.json` records the new checks with `liveAzureTested: false`.
The catalog helper refreshed only this scenario's manifest; its CLI's unconditional shared-index export
was not used because worker writes are restricted to the owned scenario.

### Earlier preparation boundary (superseded parameter gate)

The selected Azure CLI account, tenant and subscription were rechecked and still exactly match authorization.
`azd auth login --check-status` still reports the authorized account.
`az group exists --name rg-equip-ai --subscription efd64343-6ef4-4926-951f-d3229f38bd76`
returned `false`; no group was created.

Read-only parameter verification failed: `EQUIP_API_CLIENT_ID` and `EQUIP_SPA_CLIENT_ID`
are not configured as nonempty GUIDs. `infra\main.parameters.json` still contains substitution placeholders.
No tenant application identity was invented and no registration was created or changed.
The portal answered the registration-source choice on 2026-10-23:
**Plan new dedicated scenario registrations**.
The [identity installation plan](entra-registration-plan.md) now specifies the two dedicated applications,
v2 API token format, read scope, site roles, permissions, redirect sequencing and verification gates.
This resolves the source choice without inventing client IDs or authorizing Entra mutations.
Installation still requires a separately authorized execution route and nominated real test principals.
What-if and final pricing remain incomplete; no readiness or deployment-completion claim is made.

### Checks still required

Resume rather than restart. Independent preparation does not require pre-created identity IDs:

- Bicep/application/local-validation are reconciled with fresh receipts and actual checks.
  The current application receipt records 49 local checks, not live Azure success.
- Resolve exact Entra SPA/API configuration without creating registrations under read-only permission.
- Complete live model allocation-capacity checks, whole-stack SKU checks and applicable Policy evaluation.
- Verify the installer principal in the authorized tenant and private deployment/agent-install execution path.
- Establish concrete scenario-only network parameters and check relevant conflicts.
- Run actual what-if for the exact target; the absent resource group must not be created without deployment consent.
  A subscription-scope preview wrapper can model that group without deploying it.
- Price the exact resource and token assumptions, then request separate matching-target deployment permission.

### Dedicated-registration planning continuation

Run-owned reports reside in `.worker\def8cd2bc0fc402fa709a83ea358b044`.
The initial owner-bound requirements audit passed on 2026-10-23 with no blocked stages.
All canonical decisions/history were read; confirmed design, local results and exact preparation permission reused.
No Azure account queries, Graph operations, what-if, resource changes or live tests were performed in this attempt.
The registration plan is local documentation; its verification checklist is not a passing runtime receipt.
The next portal decision selects administrator installation outside this worker or deferred local-only retention.
It grants this worker no new cloud permission and does not repeat registration-source selection.

### Diagnostic attempts, not passing checks

`az cognitiveservices model list` and `usage list` passed.
The separate `modelCapacities` attempt failed because required query filters were absent.
A filtered retry was malformed by Windows `az.cmd` ampersand handling and did not reach the intended API.
Neither attempt proves capacity or a permission denial; `model-capacity.json` is not a success receipt.
Correct argument quoting is required on resumption.

`az ad signed-in-user show --subscription ...` was rejected because that command does not support the flag.
The subsequent explicit-subscription Graph `/me` request returned an object ID, but its Graph tenant was not
independently confirmed; do not use that result as the final deployment principal.
The token-metadata retry with subscription alone passed; specifying tenant and subscription together was invalid.
No tokens, keys or secret-bearing configuration were retained.

### Previous bounded preparation result

Run-owned evidence: `.worker\f01a7c9b6f444a91afaeffec6d83b0c2`.
Canonical authorization `14a2c19c1aa947f79680a7b130172581` was reused without requesting it again.
The backend prerequisite receipt dated 2026-10-23 14:45:07 -07:00 was fresh at operation start.
Azure CLI account/subscription/tenant and azd account still match; the group still does not exist.
The later user correction withdraws the manual ID/receipt questionnaire.
Solution-created identifiers are deployment outputs; no Graph write permission was inferred.

| Current read-only check | Observed result |
| --- | --- |
| Retained Bicep compilation | Exit 0; output `main.json`, no diagnostics |
| Exact model capacity | East US / GlobalStandard / gpt-4.1-mini 2025-04-14: 5000 available, planned 10 |
| Exact model quota | Global usage 0 of 5000; not a reservation |
| Providers | Eight listed plus separately verified Microsoft.Insights: all nine Registered |
| Existing VNet prefixes | Empty subscription result; proposed isolated `10.247.0.0/24` has no listed conflict |
| Network proposal | Integration `10.247.0.0/26`; endpoints `10.247.0.64/26`; no networks created |
| Policy assignments | Three current initiatives retained; full rule/effect evaluation still pending |
| Actual partial what-if | Failed provider validation: `InternalSubscriptionIsOverQuotaForSku` |
| Hosting quota | B2 VMs: limit 0, usage 0, required 1, minimum requested new limit 1 |
| Full-reference what-if | Pending; no fake Entra IDs supplied |
| Directory/runtime | Not installed or verified; no consent for writes |

The successful capacity retry used `az rest --url-parameters @capacity-query.json` with the documented
2024-10-01 model-capacities API and exact filters. This avoids Windows command-line ampersand parsing.
`model-capacities.json` is an actual capacity response, unlike the earlier failed diagnostic.
The selected region remains unconfirmed for the whole stack because hosting validation failed.
Linux B2 appearing in a region catalog did not prove this subscription could allocate an instance.

The partial preview uses a subscription wrapper to preview the absent group without creating it.
It derives from the retained compiled reference, excluding `apps`, `appBlobAccess` and `agentAccess`.
`preview-coverage.json` records the source hash, exclusions and absence of identity placeholders.
This is not an alternate deployable solution and must never replace the full reference template.
Its exact command was:

```powershell
az deployment sub what-if --name equip-ai-preparation-f01a7c9b --location eastus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file generated-scenarios\equip-ai\.worker\f01a7c9b6f444a91afaeffec6d83b0c2\independent-preview.json `
  --no-pretty-print --output json
```

Exit 1. `independent-whatif.stderr.txt` retains the provider rejection and tracking ID.
No change list was returned: create/modify/delete counts are unavailable, not zero.
No lower validation level, alternate SKU/region, quota request or deployment was used to bypass this failure.
An authorized quota increase or a deliberate hosting-design revision is required before a passing retry.

Public retail pricing was also queried without sending source code or private scenario data.
`retail-prices.json` records the exact public queries and returned meters.
Linux B2 is USD 0.034/hour (USD 24.82 at 730 hours); IoT Hub B2 is USD 50/month.
These two fixed items alone total USD 74.82/month, not the solution's total.
Hot LRS block-blob meters include USD 0.0208/GB-month, USD 0.05/10,000 writes
and USD 0.004/10,000 reads; actual scans and batch counts affect cost.
The initial Private Link, private DNS and exact model filters returned no meters.
They are unresolved pricing queries, not free services.
Network processing, private endpoints/DNS, model tokens, diagnostics and bandwidth remain unpriced.
The earlier USD 150-400 planning allowance is not a refreshed complete quote or spend authorization.
No deployment-consent request can be based on a passing/full preview or final priced total from this run.

Future identity automation/output capture is specified in `entra-registration-plan.md`.
It is not implemented or executed by this preparation operation.
Real runtime configuration, tenant capability, directory consent, nominated access assignments and a private
installation path remain later gates, not requests to manufacture or manually transcribe generated IDs.
This operation does not perform the backend's next stage.

Official API/procedure references fetched on 2026-10-23:

- [Model capacities REST API][capacity-api]
- [ARM what-if behavior and validation][whatif-api]
- [Microsoft public retail pricing API][retail-api]

[capacity-api]: https://learn.microsoft.com/en-us/rest/api/aiservices/accountmanagement/model-capacities/list
[whatif-api]: https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/deploy-what-if
[retail-api]: https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices

### Current bounded preparation retry

Run-owned evidence: `.worker\93cf1a6a3a92425f9b99a50e2fbff68b`.
All canonical decisions/history were read at revision 61; existing exact-scope preparation consent was reused.
The backend readiness receipt at `2026-10-23T22:19:31.514330+00:00` passed; no full audit was repeated.
Azure CLI account, subscription and tenant still match the authorized scope; azd reports the same account.
The explicit-subscription `az group exists` check still returns `false`.

The retained reference compiled without diagnostics. Its SHA-256 remains
`da1b9ac421483a12c7ce6e87a5d50393e7eee4dc150d4aa74a9d794fac599257`,
matching the retained partial preview coverage. The unchanged preview and coverage were copied into this run.
No invented identity identifiers or alternate template design were introduced.

```powershell
az deployment sub what-if --name equip-ai-preparation-93cf1a6a --location eastus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file generated-scenarios\equip-ai\.worker\93cf1a6a3a92425f9b99a50e2fbff68b\independent-preview.json `
  --no-pretty-print --output json
```

Exit 1: Azure again reports `InternalSubscriptionIsOverQuotaForSku` for B2 hosting.
The selected East US preview requires 1 B2 VM; current limit and usage are both 0.
Tracking ID: `c979baad-1c85-4ed9-b380-927ca0d83ee2`.
`independent-whatif.stderr.txt` retains the exact provider failure.
No change list was returned; create/modify/delete counts remain unavailable, not zero.

Preparation remains failed, not completed or ready for deployment.
An authorized operator must arrange a B2 quota limit of at least 1 for this target,
or the user must explicitly choose a hosting-design revision through the portal.
This worker neither requests quota nor changes SKU, region, validation level or security.
Full-reference/identity-dependent preview and complete pricing remain pending; earlier capacity/pricing
observations retain their original timestamps and were not revalidated during this quota retry.
No resources, directory objects or azd environments were created; shared CLI defaults remain unchanged.
No manual identity-receipt question, deployment decision, live validation,
suitability approval or hack work was started.

### Latest bounded preparation attempt

Run-owned evidence: `.worker\76a361bdf80049829824419cc089ff62`.
Canonical revision 67 supplied all decisions/history and unchanged exact-scope preparation authorization.
The backend readiness receipt at `2026-10-23T15:27:19.218871-07:00` passed for this owner;
no redundant full audit was run. Revision 68 accepted the scoped preparation start.

Azure CLI account, subscription and tenant still match the authorized scope; azd reports the same account.
The explicit-subscription group-existence check returned `false`.
The retained Bicep compiled without diagnostics and its SHA-256 matched the retained partial preview:
`da1b9ac421483a12c7ce6e87a5d50393e7eee4dc150d4aa74a9d794fac599257`.
The unchanged preview and explicit exclusions were reused, without fabricated Entra IDs.

```powershell
az deployment sub what-if --name equip-ai-preparation-76a361bd --location eastus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file generated-scenarios\equip-ai\.worker\76a361bdf80049829824419cc089ff62\independent-preview.json `
  --no-pretty-print --output json
```

Exit 1: `InternalSubscriptionIsOverQuotaForSku`; B2 VM limit 0, usage 0, required 1, minimum new limit 1.
Tracking ID: `5beaa2dd-4aff-4a03-b3b8-c07fc1493fb3`.
The run's `independent-whatif.stderr.txt` retains the actual provider response.
No change list was returned; change counts remain unavailable, not zero.
This is a real cloud-capacity failure, not missing local tooling or a host-permission denial.

Preparation remains failed. An authorized operator must arrange the required B2 quota for the exact target,
or a hosting-design revision must be explicitly chosen through the portal.
No quota request, SKU/region change, reduced validation, resource mutation or directory write was attempted.
Identity-dependent preview, complete pricing and deployment authorization remain pending.
Earlier capacity and pricing evidence retain their own dates; none was refreshed or claimed as current here.
No deployment decision, live validation, review, suitability approval, hack composition or team rollout followed.

### East US revalidation: corrected provider diagnosis

Run-owned evidence: `.worker\04aeed2e81f44650b04cfe74fce03cd6`.
Canonical revision 74 supplied all decisions/history and the refreshed exact read-only preparation scope.
Revision 75 accepted the preparation-running report. The backend readiness receipt was current;
no completed implementation was restarted and no full tool audit was repeated.
The exact Azure CLI account/subscription/tenant matched authorization and remained Enabled.
`azd auth login --check-status` matched the same account. `rg-equip-ai` remains absent.

**East US was already the target.** The target change superseded the previous blocker state,
not the actual quota failure. The rejecting resource is **Microsoft.Web/serverFarms**, API `2025-03-01`.
Azure's label "B2 VMs" means App Service workers here, not a Microsoft.Compute B-family VM.
The distinct IoT Hub B2 SKU belongs to Microsoft.Devices and did not cause this rejection.

The actual subscription-scoped Microsoft.Web regional usage request was:

```powershell
$subscription = 'efd64343-6ef4-4926-951f-d3229f38bd76'
$endpoint = "https://management.azure.com/subscriptions/$subscription/providers"
$endpoint += '/Microsoft.Web/locations/eastus/usages'
az rest --method get --subscription $subscription --url $endpoint `
  --url-parameters api-version=2025-03-01 --output json
```

The command above is an exact executable evidence reference.
`web-usages.json` reports `B2`: limit **0**, current **0**, required **1**.
Its aggregate regional worker entry `*` also reports limit/current zero.
Demand is one fixed shared worker for both applications, with no autoscale, slots or rollout workers in this design.
No Compute quota query or quota request was made.

| Fresh check | Actual result |
| --- | --- |
| Providers | All ten queried namespaces Registered; no registration attempted |
| Foundry account | AIServices S0 East US: no SKU restrictions; diagnostic accepts account/project |
| Model | gpt-4.1-mini 2025-04-14 GlobalStandard; quota 0/5000, demand 10; capacity 5000, not reserved |
| Model features | Catalog advertises agentsV2 and Responses; live private agent/tool invocation remains unverified |
| Model lifecycle | Legacy; inference deprecation 2027-04-14; no substitution |
| IoT B2 | Exact one-unit, four-partition secured route accepted by diagnostic; paid hubs 0/50, demand 1 |
| Storage | Hot StorageV2 Standard_LRS East US, restrictions empty; accounts 0/250, demand 1 |
| Network | VNets 0/1000, demand 1; private endpoints 0/65536, aggregate demand 3 |
| Network conflicts | Subscription VNet list empty; retained scenario-only CIDRs unchanged |
| Linux runtime | DOTNETCORE\|10.0 listed Active; app-specific preview remains incomplete |
| Policy | Three SQL/relational initiatives and definitions read; full app evaluation incomplete |
| Identity/RBAC | ARM permissions read; IoT assignment preview Unsupported; generated Entra IDs still future outputs |

Neither a Cosmos DB account nor VM/VMSS is planned. No irrelevant Cosmos/Compute quota checks were substituted.
No requested zone redundancy was removed: Storage remains LRS and the fixed B2 plan remains nonzonal.
The private Foundry/Blob paths, Storage trusted-IoT exception, public Entra web ingress,
private cleaner and separate least-privilege identities are unchanged.
Bicep `location` still has no default and `main.parameters.json` still consumes `${AZURE_LOCATION}`.
Only the reference validation scope is East US; nothing was copied to hack/event defaults.

### Current what-if results and explicit limits

The unchanged reference compiled without diagnostics; its compiled SHA-256 remains
`da1b9ac421483a12c7ce6e87a5d50393e7eee4dc150d4aa74a9d794fac599257`.
Current infrastructure fingerprint from `azure_context.infrastructure_fingerprint`:
`c5affdab9498e2c92a476d8fcb299586d708f2477e870e74174121886ed759ac`.
`00-region-availability.json` now contains 28 scoped checks:
20 passed eligibility/preview checks, seven unknown and one blocked.
The earliest actual check time is `2026-10-23T22:45:23.727706+00:00`;
the normal 15-minute expiry still applies. `selectedRegion` remains null.

```powershell
az deployment sub what-if --name equip-ai-preparation-04aeed2e --location eastus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file generated-scenarios\equip-ai\.worker\04aeed2e81f44650b04cfe74fce03cd6\independent-preview.json `
  --no-pretty-print --output json
```

Exit **1**, `InternalSubscriptionIsOverQuotaForSku`, Microsoft.Web B2 limit 0, current 0, required 1.
Tracking ID `235bd609-8947-404d-9384-c6959e25508d`.
No change list was returned; the main preview's change counts are **unavailable**, not zero.
Coverage still excludes both apps and application RBAC because solution-created Entra IDs do not exist.
No identity placeholders were fabricated.

A separate **diagnostic-only** preview additionally omitted the failed hosting plan:

```powershell
$run = 'generated-scenarios\equip-ai\.worker\04aeed2e81f44650b04cfe74fce03cd6'
az deployment sub what-if --name equip-ai-nonhosting-04aeed2e --location eastus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file "$run\nonhosting-diagnostic-preview.json" `
  --no-pretty-print --output json
```

Exit **0**, status Succeeded: **33 Create, one Unsupported**, no Modify/Delete.
Unsupported is the IoT container role assignment; it is not a passing RBAC check.
These are proposed changes only. The absent group was not created.
This diagnostic isolates remaining resource validation; it is not a deployable replacement,
not a bypass of B2 quota, and not a whole-reference what-if pass.
Cleaner endpoint placement, app/identity policy, private installation and runtime behavior remain unresolved.

Earlier malformed/unsupported SKU queries remain recorded with their actual errors.
Storage was recovered with the subscription Storage SKUs REST API.
The standalone Microsoft.Web SKU list returned empty; its regional SKU endpoint returned 404.
IoT standalone SKU routes returned 404; exact unchanged IoT properties were instead accepted in the diagnostic.
Unknown results were not presented as subscription eligibility.

### Revised public retail estimate and scoped alternative

`retail-prices.json` and `cost-estimate.json` retain actual meters, filters and quantities.
Public rates were refreshed in this run; these are not negotiated prices or permission to spend.

| Reference item | USD/month or observed unit rate |
| --- | --- |
| One Linux B2 shared plan, 730 hours | 24.82 |
| One IoT B2 unit | 50.00 |
| Three private endpoints, 730 hours at 0.01/hour | 21.90 |
| Five private DNS zones at 0.50/month | 2.50 |
| Fixed subtotal | **99.22** |
| Model input/output | 0.40 / 1.60 per million tokens, GlobalStandard base inference |
| Hot LRS capacity / writes / reads | 0.0208/GB-month; 0.05/10k writes; 0.004/10k reads |
| Private endpoint data / DNS queries | 0.01/GB at first tier; 0.40/million queries |
| Log ingestion | 2.30/GB before any free allowance |

An explicit illustrative workload totals **USD 149.42/month**:
10,000 questions with 3,000 input/500 output tokens each; 5,760 Blob writes/day;
480 cold-read batches/question; two lists/question; 1 GB stored;
2,000 GB combined private endpoint traffic/month including repeated reads/overhead;
3 GB logs/month and one million DNS queries.
Actual caching, envelopes, routing and usage determine charges.
At 12,000 input and 4,500 output tokens/question, the same question count costs USD 120 for model usage alone.
The estimate excludes Internet/bandwidth charges, private installer connectivity/runner,
additional Entra licensing if applicable, taxes and support. It is not a final consent quote or spend ceiling.

Within the authorized East US scope, P0v3 Linux is listed and its per-SKU worker quota is 360/current 0.
Public hosting cost is **USD 56.58/month**, about **USD 31.76/month more** than B2.
However, aggregate `*` quota is still zero and no revised-design what-if was authorized or performed.
P0v3 is therefore an **unselected candidate**, not a verified deployable alternative.
No query evaluated West US 3 or any other unauthorized target region.

Preparation remains **failed**, with no deployment-consent request.
A future consolidated target/design review can consider a separately authorized alternative
or operator-managed quota remediation; neither is mandatory or executed by this worker.
Any changed SKU/region needs fresh scoped validation and revised costs before later deployment consent.
Directory changes, generated identity capture and private installation remain separately authorized work.
No provisioning, deletions, quota requests, directory mutations, live validation,
suitability approval, packages or team deployment occurred.

### Central US revalidation: historical bounded operation

Current evidence: `.worker\a3e940150ac44c76b8a6e9ec4ed97dee`.
Canonical revisions 81/82 retain all decisions/history and authorize only this saved Central US reference target.
The fresh backend prerequisite receipt was reused; no full machine audit or completed implementation was repeated.
Azure CLI identity exactly matches the authorized account/subscription/tenant and the subscription is Enabled.
The resource group remains absent; no shared defaults or azd environment were changed.
Earlier East US observations and rejection history above remain historical, not current Central US facts.

| Current check | Observed result |
| --- | --- |
| Microsoft.Web Linux B2 | Exact B2 and aggregate `*` worker quotas: each current 0, limit 10, demand 1 |
| Worker demand | One fixed worker shared by two apps; no autoscale, slots or temporary rollout instances |
| Foundry model | gpt-4.1-mini 2025-04-14 GlobalStandard: quota 0/5000, capacity 5000, demand 10 |
| Foundry features | Current official Central US table supports Agents, Responses, Functions and Private VNet |
| Foundry model lifecycle | Legacy; inference deprecation 2027-04-14; unchanged, capacity not reserved |
| Storage | Exact Hot StorageV2 Standard_LRS, restrictions empty; subscription account quota checked |
| IoT | Exact B2 one-unit/four-partition secure route accepted in preview; paid-hub quota checked |
| Network | Quotas include three endpoints and one VNet; existing subscription VNet list empty |
| Providers | All ten required namespaces Registered, including separately queried `microsoft.insights` |
| Identity/Policy | Definitions/permissions inspected; full identity-dependent app/RBAC coverage incomplete |

Unchanged infrastructure compiles with SHA-256
`da1b9ac421483a12c7ce6e87a5d50393e7eee4dc150d4aa74a9d794fac599257`.
The required location parameter still consumes `${AZURE_LOCATION}`.
No SKU, zone, private-network, identity or trusted-service firewall constraint was changed.
No Cosmos DB, Compute VM/VMSS or standalone broker is planned; unrelated quota checks were not substituted.
No West US 2 validation or hack/event region change was performed.

```powershell
$run = 'generated-scenarios\equip-ai\.worker\a3e940150ac44c76b8a6e9ec4ed97dee'
az deployment sub what-if --name equip-ai-preparation-a3e94015 --location centralus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file "$run\independent-preview.json" --no-pretty-print --output json
```

Exit **0**, Succeeded: **34 Create, one Unsupported**, no Delete/Modify.
This preview includes the unchanged B2 plan. Unsupported is the IoT container role assignment.
Both app modules, application RBAC and the cleaner endpoint remain excluded because generated Entra identifiers
do not yet exist. No fake identifiers were used and no directory write was performed.
The diagnostic-only nonhosting preview also succeeded; it does not expand full-reference coverage.
Do not count either preview as an exact full-reference pass, allocation reservation or runtime proof.

`00-region-availability.json` contains **29 current scoped checks: 22 passed, seven unknown**,
with the current infrastructure fingerprint and actual check times; the normal 15-minute expiry applies.
The backend guard rejects incomplete evidence as expected.
Central US is **not capacity-rejected** by these observations, but complete preparation is reported **failed**
because required identity-dependent/RBAC/Policy evidence is unresolved.
No deployment-consent decision was requested. Identity-generated outputs remain installation responsibilities,
not a request for the user to provide client IDs or an administrator receipt.
No additional tooling/host permission blocker was invented.

Current Central US retail meters yield **USD 99.95/month fixed** and **USD 151.53/month illustrative total**:
Linux B2 25.55, IoT B2 50.00, three private endpoints 21.90 and five DNS zones 2.50.
Usage assumptions remain 10,000 questions with 3,000 input/500 output tokens;
5,760 daily writes; 480 cold-read batches and two lists/question; 1 GB stored;
2,000 GB endpoint traffic; 3 GB logs and one million DNS queries.
Log ingestion uses the actual paid tier of 2.76/GB conservatively without subtracting the 5 GB free allowance.
The estimate excludes bandwidth/Internet egress, private installer connectivity/runner,
additional Entra licensing, taxes and support; it is not a final consent quote or spend ceiling.
`cost-estimate.json` retains observed meters, quantities and assumptions.

Malformed/unsupported diagnostic API attempts are preserved, not counted as eligibility failures.
The IoT query-file naming error was corrected; the actual regional SKU API then returned 404.
Storage uses its supported subscription SKUs REST response, not the unavailable CLI `list-skus` command.
These are not CLI approval/host denials and were not bypassed.
No provisioning, quota request, registration, directory mutation, live validation, suitability approval
or hack/team work occurred.

### West US 2 revalidation: historical bounded operation

Current evidence: `.worker\25a8ad7da41c44ef9428a7ec1ca7e71f`.
Canonical revision 88 and all persisted answers/history were read; revision 89 accepted preparation start.
The fresh backend owner-bound prerequisite receipt was reused without repeating the full machine audit.
Identity matches the unchanged authorized account/subscription/tenant; subscription Enabled; target group absent.
Only West US 2 was evaluated in this attempt. Prior East US and Central US evidence is preserved.
No defaults, environment, infrastructure, SKU, identity, private-network or zone constraints were changed.

| Check | Actual West US 2 result |
| --- | --- |
| Linux B2 workers | Microsoft.Web B2 and aggregate `*` quotas each current 0, limit 10, additional demand 1 |
| Worker demand | Two apps share one fixed worker; maximum one; zero temporary rollout instances |
| Exact model/version | No gpt-4.1-mini 2025-04-14 entry in live regional catalog |
| Exact model quota/capacity | Matching GlobalStandard quota and West US 2 capacity records absent; demand 10 |
| Foundry S0 | AIServices S0 SKU listed with no restrictions; nested account preview skipped |
| Required agent features | West US 2 omitted from official Agent Service/tool tables; eligibility unproved |
| Responses API | Separate OpenAI Responses page lists westus2; not proof of Agent Service support |
| Storage | Hot StorageV2 Standard_LRS listed, restrictions empty; accounts 1/250, demand 1 |
| Storage security preview | Nested account/firewall/private-endpoint evaluation skipped; not passed |
| IoT | Exact B2 unit/four partitions and secure route in preview; paid hub count 0/50, demand 1 |
| Network | VNet 0/1000, demand 1; private endpoints 0/65536, aggregate demand 3; VNet list empty |
| Providers | All ten required namespaces Registered |
| Policy/identity | Permissions/assignments inspected; omitted resources and identity-dependent apps not validated |

The real command, stdout, stderr, timestamps and exit code are retained in `*.command.json` files:

```powershell
$run = 'generated-scenarios\equip-ai\.worker\25a8ad7da41c44ef9428a7ec1ca7e71f'
az deployment sub what-if --name equip-ai-preparation-25a8ad7d --location westus2 `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file "$run\independent-preview.json" --no-pretty-print --output json
```

Exit **0**, status Succeeded: **23 Create**, no Delete/Modify.
However, `NestedDeploymentShortCircuited` skips telemetry-storage, iot-container-access and foundry-account.
`NestedDeploymentSkippedFromInternalExpansion` also reports a DNS nested expansion limit.
Those warnings make coverage incomplete; exit success and missing resources cannot be treated as a full pass.
The explicitly partial template still excludes identity-dependent apps/application RBAC without invented IDs.
No lower validation level, alternate SKU/model, quota request, probe allocation or directory write was used.

`00-region-availability.json` records the full retained resource inventory with current scope/fingerprint/time:
**29 checks: 12 passed, 16 unknown, one blocked**.
The exact model deployment check is blocked; absent quota/capacity entries remain unknown, not fabricated zeros.
The backend readiness guard rejects these results. Preparation is **failed**, not deployment completed,
and no deployment-consent review was requested. No new business or setup approval was invented.
Generated identity IDs remain future deployment outputs, not requested user inputs.

Refreshed public retail meters give **USD 99.22/month fixed**, **USD 149.42/month illustrative total**.
Fixed charges: Linux B2 24.82, IoT B2 50.00, three private endpoints 21.90, five private DNS zones 2.50.
Unchanged usage assumptions and exclusions are retained in `cost-estimate.json`;
the actual West US 2 paid log-ingestion tier is 2.30/GB before free allowances.
This is not a final consent quote, price guarantee, budget ceiling or reservation.

Current official feature evidence was refreshed from:

- [Agent Service regional and tool support][westus2-agent-regions].
- [OpenAI Responses support][westus2-responses].
- [Foundry private inbound networking][westus2-private-link].

[westus2-agent-regions]: https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/limits-quotas-regions
[westus2-responses]: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses
[westus2-private-link]: https://learn.microsoft.com/en-us/azure/foundry/how-to/configure-private-link

No provisioning, directory mutations, quota increases, live validation, suitability approval,
hack composition, team deployment or independent hack-region parameter changes occurred.

### Central US resumed preparation and consolidated installation review

Current run evidence: `.worker\fa96363ef14f40ffa063aff3dcfd430c`.
All canonical decisions/history at revision 99 were read; revision 100 accepted preparation resumption.
The current owner-bound deployment prerequisite audit passed.
The exact authorized account, subscription and tenant match; azd reports the same account.
The resource group remains absent. No shared defaults or azd environments were changed.

Retained repairs separate site/managed-identity creation from final Entra-dependent appsettings.
The cleaner private endpoint consumes the actual site resource ID.
The installer captures real owned registration/principal/scope/role IDs and sets the exact azd environment inputs.
Preprovision/postprovision hooks enforce separate directory authorization and use the generated web redirect.
Project-scoped Foundry Project Runtime User supplements Agent Consumer for the actual Responses API.
These are prepared implementation assets, not installed objects or passing live authentication.

Retained local receipts record Bicep build/lint, 13 identity tests, application build and 49 application/browser checks.
The 120,000-event aggregate took 281.8 ms against a 30-second bound.
The current retained reference recompiled without diagnostics; its compiled SHA-256 is
`7e61117802d1702d2b84dcd9b0e1109cc5084d441422e2011563e62d58cb9e3e`,
matching the repaired source tested by the interrupted run.
`00-region-availability.json` carries the final infrastructure fingerprint and actual cloud check timestamps.

| Refreshed Central US check | Actual result |
| --- | --- |
| Microsoft.Web B2 and aggregate workers | Each 0/10, one required; capacity not reserved |
| Exact model/version/GlobalStandard | Quota 0/5000, capacity 5000, demand 10; not reserved |
| Independent what-if | Exit 0, Succeeded, 35 Create, no Modify/Delete |
| Foundation what-if | Exit 0, Succeeded, 34 Create, one Unsupported, no Modify/Delete |
| IoT Unsupported | Generated managed-principal ID cannot be calculated before deployment |
| IoT role/scope/schema | Actual built-in Blob Contributor, container scope, supported 2022-04-01 API |
| Policy | Three initiatives, eleven live definitions; type predicates exclude planned ARM resources |
| Remaining dependencies | Final auth settings, app/installer assignments, directory capability and propagation |

Exact command, stdout, stderr, exit code and timestamps are retained in each `*.command.json` file.
The independent preview excludes only `runtimeConfiguration`; installer assignments use an intentionally empty
principal parameter, not an invented identity.
Its diagnostics skip Storage, Foundry, application/project assignments and some nested expansions.
The complementary foundation preview includes Storage, Foundry/model and their endpoints,
but excludes sites, cleaner endpoint and application/project assignments.
Its only Unsupported change is the IoT assignment with the exact unresolved generated-principal expression.
Neither preview proves actual role propagation; their create counts must not be summed as a resource total.
Both diagnostic lists and explicit exclusions remain available; no reduced validation level was used.

The refreshed public retail estimate is USD 99.95/month fixed and USD 151.53/month illustrative total.
The unchanged quantities, exact meters and exclusions are retained in `cost-estimate.json`.
Private installation runner/connectivity, Internet egress, extra Entra licensing, taxes and support are excluded.
This is neither a quote nor a spend ceiling.

The [identity installation review](entra-registration-plan.md) lists exact directory changes and permissions.
Dedicated IDs and HTTPS endpoints are generated installation outputs, not portal questionnaire inputs.
No actual installer directory capability, private deployment-runner connectivity or real user nomination is proved.
No access assignment is made by default. Verify these dependencies before their affected installation/runtime steps.
Any later approved installation must refresh the dependent full what-if/Policy/RBAC with real outputs,
and stop before affected provisioning on failure or material changes.

The earlier signature-only `verify_review_gate.py` failure was reproduced, then investigated.
It tests for a new function parameter, not an actual portal decision rejection.
The current agent-owned portal execution path no longer calls that validator before consent reporting.
The strict provisioning guard still rejects unknown IoT/identity checks; that is not a new workflow blocker.
A separate exact-target installation/deployment decision can truthfully present pending generated outputs.
Full preparation is therefore not marked completed; the portal receives the disclosed incomplete result
and a separate authorization decision, not fabricated all-passed evidence.

The portal subsequently recorded the exact-target ordered ARM/dedicated-directory authorization at
`2026-10-23T17:05:54.057966-07:00`, decision `157b9eb7c2f14f9e957e45e26826e35d`.
Suitability approval, live validation, hack composition, publication and teams remain separate and unstarted.

### Authorized identity installation and private-runner setup blocker

Run evidence: `.worker\7e73b648de00400c98f4ad9ef15eb880`.
Canonical revision 105, all history and resolved decisions were consumed; revision 106 recorded deployment start.
No prior story, design, model, SKU, security boundary or target was restarted or substituted.
Azure CLI and azd match the authorized account/tenant/subscription.
The scenario-only `equip-ai` azd environment was created; shared CLI defaults were not changed.

Read-only Graph checks succeeded: current installer object resolved, active directory-role memberships returned
an empty list, and tenant default-user policy permits application creation.
Those facts alone did not establish write permission. The approved installer performed actual writes successfully.
Its local authorization receipt references the accepted portal decision, exact scope and generated installer ID;
it permits registration/redirect operations only, with no user assignments or broader privileges.

The initial registration operation failed after creating both dedicated applications.
Graph returned `InvalidValue`, request ID `6ef3fcb5-aacd-49f3-9c09-f1d37a8b4611`:
`api.preAuthorizedApplications.delegatedPermissionIds` referenced a permission not yet persisted.
This was an installation ordering bug, not a tenant/host denial.
The fix writes and verifies `Equipment.Read` before the separate SPA-preauthorization request.
The local fake now enforces that same ordering. All 15 focused installer tests passed.
The authorized retry reused actual application/definition IDs, installed both service principals,
read back assignment-required policy and the API/SPA contract, and exported actual IDs into azd.
No duplicate registrations, credentials, user/group assignments, consent grants or tenant policy changes were made.

```powershell
python -m unittest discover -s generated-scenarios\equip-ai\tests -p test_preparation.py -v
# Exit 0: 15 tests.

# From the scenario directory, with the explicit authorized target environment:
python scripts\install_identity.py registrations
# Initial exit 1 retained; corrected retry exit 0; identity.json contains actual outputs.

python generated-scenarios\equip-ai\.worker\7e73b648de00400c98f4ad9ef15eb880\verify_installed_preview.py
# Exit 0; full template supplied, no symbolic resources excluded; actual generated IDs consumed.

Find-NetRoute -RemoteIPAddress 10.247.0.65
# Selected route: Wi-Fi, 0.0.0.0/0, next hop 10.0.0.1; no private route.
```

The dependent what-if returned `Succeeded`, **35 Create**, no Modify/Delete.
It still reports six `NestedDeploymentShortCircuited` diagnostics for Storage, IoT RBAC, Foundry,
runtime configuration, application Blob access and project access.
Four further expansion-limit diagnostics skip two DNS deployments and the web/cleaner app deployments.
These skips remain unresolved coverage, not a full-reference readiness pass.
Exact commands, timestamps and stdout/stderr are retained in the current run.

**Setup required:** the reviewed design requires an authorized VNet-connected runner for private cleaner SCM
publishing and Foundry agent installation. This host has only Wi-Fi/WSL adapters up and sends the reviewed
private endpoint range through its Internet default gateway. No approved connected runner is recorded.
No TCP probe was sent to an address without an allocated endpoint.
An operator must arrange an authorized private execution path and private DNS for the reviewed scenario.
The accepted installation scope does not provision a runner, VPN, peering or other connectivity.
Verify the selected route locally, then verify actual private endpoint DNS/TLS after authorized provisioning.
Do not expose private services, enable basic SCM credentials or widen network/role access as a workaround.

ARM provisioning was not started, avoiding paid resources that this worker cannot publish to or validate.
The current resource-group query still returns `false`.
Retain the installed owned identities for an idempotent continuation; no cleanup or deletion was attempted.
Exact redirect, principal nominations, dependent propagation checks, agent installation and all runtime
acceptance remain outstanding. No suitability snapshot or approval was created.

## Deployed Resources

No ARM resources created or deployed by this worker. The authorized resource group does not currently exist.
Two dedicated Entra applications and both assignment-required service principals are installed.
No runtime endpoint, Foundry agent, model inference, Entra login, ingestion or physical expiry was tested.

## Outputs (Expected)

Actual directory IDs are retained in `.installation\equip-ai\identity.json` and the scenario azd environment.
No ARM deployment outputs or live application URL exist.
Future outputs remain defined by `infra\main.bicep`; they are not observed values.
No suitability approval, review snapshot, hack package or team deployment was created.
Cleanup or cloud mutation is not authorized by this document.
