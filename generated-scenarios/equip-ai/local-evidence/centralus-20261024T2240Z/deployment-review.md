# equip-ai: Central US read-only deployment preparation review

Updated 2026-10-24 after actual CLI/ARM checks. This is not a deployment or suitability approval request.

## Authority and exact targets

The user explicitly authorized: **"Authorize Central US read-only checks and ARM what-if"**.
The supplied handoff reports this as the actual `ask_user` response; the original approval timestamp
is unavailable. `authorization.json` preserves the response and restrictions without fabricating a portal decision.

| Field | Authorized and observed |
| --- | --- |
| Account | petender@microsoft.com |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76; Enabled |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Region | centralus |
| Resource group / azd environment | rg-equip-ai / equip-ai |
| Current permission | Eligibility reads and ARM what-if only |
| Not permitted | Deployment, Entra writes, quota requests, saved-target or shared-default changes |

CLI account/tenant/subscription matched. `azd auth login --check-status` confirmed the same account.
Explicit `azd env get-values --environment equip-ai --no-prompt` returned the retained Central US environment.
Saved target files were not modified. No `account set`, `az configure`, `azd env set`, provisioning,
Graph operation, resource allocation probe or quota submission was performed.
`rg-equip-ai` does not exist; the subscription-scoped preview models its creation without creating it.

The junction remains `generated-scenarios/equip-ai` to `C:\azd-projects\equip-ai`.
No scenario worker was observed. Unrelated dirty repository changes were preserved.
Historical `.worker` files are read-only evidence; no old worker or orchestration gate was invoked.

## Retained resource and business scope

Adatum Corporation Operations investigates equipment at five Washington sites through one prompt agent.
Typed read tools enforce Tacoma/statewide access outside the model. No equipment control or automatic repair.
The approved local design remains unchanged:

- Foundry AIServices S0 account, direct child project, `gpt-4.1-mini` version `2025-04-14`,
  `GlobalStandard`, deployment `equip-support`, capacity 10.
- IoT Hub B2, one unit, X.509 ingress and managed-identity JSON routing.
- StorageV2 Hot Standard LRS Blob, keyless and anonymous-disabled.
- One Linux B2 App Service worker shared by the public Entra-secured web/API and private cleaner.
- Managed identities, scoped Blob/Foundry RBAC and the custom read/delete-only cleanup role.
- VNet `10.247.0.0/24`, integration `10.247.0.0/26`, endpoints `10.247.0.64/26`,
  three private endpoints and five private DNS zones.
- PerGB2018 Log Analytics, 30-day retention, 1 GB/day quota, Application Insights and sanitized monitoring.
- Separate single-tenant SPA/API PKCE registrations and explicit support/lead assignments.

Foundry public access remains disabled. App-to-Blob uses Private Link.
Storage retains selected-network default-deny with its documented trusted-services IoT exception.
This is not wholly private-only. Two-hour grounding freshness is not platform-wide irreversible erasure.
`GlobalStandard` is not a promise that inference is processed only in Central US.

## Actual readiness results

`command-index.json` indexes 45 recorded commands with exact command lines, working directory,
UTC start/end times, exit codes and raw stdout/stderr. All 45 returned zero; this is not 45 readiness passes.
The Bicep compilation and CLI/azd identity checks are included in that count.
Public retail refresh is separately recorded by its script and response timestamp.

| Dependency | Actual bounded result |
| --- | --- |
| App Service B2 Linux | Region listed; B2 workers 0/10 and aggregate workers 0/10, demand 1 |
| .NET hosting | Linux `DOTNETCORE\|10.0` listed, Active LTS |
| Foundry S0 | Central US subscription SKU returned with no restrictions |
| Model | Exact AIServices model/version/GlobalStandard catalog entry found |
| Model quota | 0 used / 5,000 limit, planned capacity 10 |
| Model capacity | 5,000 available, not reserved |
| Model lifecycle | Legacy; inference deprecation 2027-04-14; no substitution made |
| Agent features | Current new-Agent docs list Central US Responses, Agents, Private VNet and Function |
| Storage | Central US Standard_LRS StorageV2, no SKU restrictions; accounts 0/250, demand 1 |
| IoT Hub | Central US provider location; paid hubs 0/50, demand 1; B2 hub present in actual preview |
| Network | VNets 1/1,000, demand 1; private endpoints 0/65,536, demand 3 |
| Address space | Returned existing VNet uses 10.74.0.0/22; no overlap with 10.247.0.0/24 |
| Private DNS | Global resource; five zones are intended, not five regional services |
| Identity / monitoring | Required resource types list Central US; managed identity, workspace, Insights registered |
| Providers | All ten required providers Registered, including lowercase-returned microsoft.insights |
| ARM permissions | Effective management wildcard returned; not Graph authority or deployment consent |
| Policy | Three inherited assignments and eleven database/SQL Defender definitions read |

No applicable deny was identified in those returned database/SQL policies.
This is not complete Policy certification: what-if did not evaluate every nested resource.
No external/peered network inventory was inferred from the returned subscription VNet list.
IoT's exact Valid SKUs operation requires an existing hub; none exists here.
No nonexistent hub ID was invented and no hub was created for an eligibility probe.
The model catalog and public feature matrix do not prove private agent initialization or runtime tools.
All allocation observations are unreserved and can change.

## ARM what-if: actual success, partial coverage

Executed with the normal provider-validation behavior; no lowered validation level or service substitution:

```powershell
az deployment sub what-if `
  --name equip-ai-readonly-20261024T2240Z `
  --location centralus `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --template-file local-evidence/centralus-20261024T2240Z/independent-preview.json `
  --no-pretty-print --output json
```

The absolute executable/template path and exact execution timestamps are in `independent-whatif.command.json`.
The template was derived from a fresh, successful compile of the current `infra/main.bicep`.
`preview-coverage.json` records the compiled-source SHA-256 and all retained/excluded symbolic resources.

- CLI exit 0; ARM status `Succeeded`.
- Returned changes: **35 Create, 0 Delete, 0 Modify, 0 Unsupported**.
- These counts describe only the evaluated preview, not all eventual infrastructure or directory changes.
- `runtimeConfiguration` is intentionally excluded; historical Entra client IDs are not treated as verified.
- Installer-specific grants use intentionally empty `principalId`, which omits those assignments.
  No fake user, client, service-principal or managed-identity ID was supplied.

ARM returned nine warnings:

- `NestedDeploymentShortCircuited`: telemetry-storage, iot-container-access, foundry-account,
  application-container-access and project-access.
- `NestedDeploymentSkippedFromInternalExpansion`: two DNS deployments, app-web and app-cleaner.

Some skipped nested deployments still yield predicted resource entries.
Their presence among the 35 creates does not prove complete provider/Policy validation.
Storage/Foundry private endpoints, model deployment, identity-dependent assignments, final app settings,
directory installation and private data-plane work therefore remain partly or wholly unevaluated.
The entire-reference what-if remains **not passed**. No destructive change was reported in evaluated coverage.

The dated East US `InternalSubscriptionIsOverQuotaForSku` result remains valid historical evidence.
It is not a Central US quota failure and was not reused as a current denial.

## Refreshed costs and unresolved total

Public retail price inputs were refreshed at the timestamp in `retail-prices.json`.
All historical baseline rates still match fresh public meters; reviewed workload quantities were reused.

| Baseline component | USD/month |
| --- | ---: |
| Linux B2 plan, 730 hours | 25.55 |
| One IoT Hub B2 | 50.00 |
| Three private endpoints | 21.90 |
| Five private DNS zones | 2.50 |
| Fixed baseline subtotal | **99.95** |
| Illustrative usage, including conservatively paid logs | 51.58 |
| Incomplete illustrative baseline | **151.53** |

The baseline assumes 1,000 devices/minute, 10,000 questions/month, 30M input and 5M output tokens,
2,000 GB private-endpoint data, 1 GB stored, 3 GB logs and 1M DNS queries.
Actual tool-loop tokens, retrieval traffic and chat concurrency are not measured.
The first 5 GB monitoring free tier is not assumed available; retained paid-rate logs add USD 8.28.
Before that conservative logging allowance, the same baseline is USD 143.25.
This is an estimate, not a spending cap, quote or consent to charges.

**The complete monthly total is unknown.** Missing costs include the actual management execution host,
compute/disks/connectivity/bootstrap/artifact transport, egress, applicable Entra licensing, taxes and support.
No new VM, Bastion, VPN, peering or firewall exception was selected or priced as though approved.

## Remaining gaps, consolidated

1. **Private execution host and automation:** no authorized connected runner is evidenced.
   This Windows VS Code host is not assumed VNet-connected.
   Publishing to cleaner SCM, fixture ingestion, agent creation and private acceptance must run from the actual host.
   Existing local azd hooks do not move their processes into a VNet.
   Required DNS/TLS/authenticated-service checks and outside-network denial remain planned, not passed.
1. **Complete price/design:** select or discover that host, define identity, artifact transfer, egress,
   lifecycle, shutdown/cleanup and any new SKU/quota needs; update IaC/azd wiring and diagrams together.
   Then consolidate its full cost with the baseline above before any deployment consent.
1. **Directory authority and identity reuse:** saved receipts/IDs are historical, not current ownership evidence.
   Scoped Graph ownership/readback has not been authorized/performed in this continuation.
   Verify owned SPA/API objects before reuse; do not replace them.
   Separately reviewed writes may repair exact HTTPS redirects/scopes/preauthorization/assignment requirements.
   `Equipment.Read`, `Operations.Tacoma` and `Operations.Statewide` remain unchanged.
   Nominate actual support/lead principals for authorized assignments; synthetic personas are not directory users.
   No broad consent, privileged role, default statewide assignment or credentials are authorized.
1. **Preview/governance:** disclose the nine ARM warnings, omitted runtime settings and installer grants.
   Complete dependent installation validation when real outputs exist; never invent IDs to get a green preview.
   Existing nonpassing Checkov assessment (14 appsettings findings) remains disclosed and was not rerun.
1. **Cloud runtime:** IoT X.509-to-Blob routing, identity propagation, private agent invocation, real model
   inference, authenticated app chat, citations/tools, cleanup, negative access cases and chat p95 remain unproved.
   There is no live URL. Local tests are not runtime proof.
1. **Maintainability:** the retained model is Legacy with the date above.
   Do not silently replace it. Retained diagrams have overlapping/historical labels and no execution host.

Local evidence remains the 22:33-22:34 UTC pass: 15 installer contracts, 49 application/browser checks,
clean Bicep build/lint and .NET build/publish. No unnecessary rebuild or machine audit was repeated.

## Next decision, not deployment approval

Preferred next step if an organizational runner exists: authorize **scoped directory ownership/readback and
read-only discovery/verification of an existing authorized VNet-connected runner** for this same scenario.
Do not grant directory writes, connectivity changes or deployment through that choice.
The runner must be able to reach the eventual 10.247.0.0/24 network and private DNS;
do not assume the unrelated existing VNet has suitable routing.

If no reusable runner is available: authorize **local design and costing of a scenario-owned VNet automation host**,
including bootstrap, immutable-artifact transfer, least-privilege identity and azd execution wiring.
That is a material proposed addition, not permission to create it.
Any extra Azure eligibility reads outside the retained service scope must be included explicitly in the next scope.

Alternatively, keep the scenario **local-only** and defer all cloud installation.
No new region/SKU, saved-target reconciliation, quota request, deployment, directory write, suitability approval,
composition or publication occurred. Request a single actual deployment review only after the above scope is complete.

## Evidence navigation

- `authorization.json`: actual reported user response and exact restrictions.
- `command-index.json` and `*.command.json`: exact commands, actual timestamps/exits and raw output filenames.
- `regional-readiness.json`: current complete dependency inventory with bounded pass/unknown results.
- `independent-whatif.json`, `preview-coverage.json`: actual changes, diagnostics and omitted dependencies.
- `cost-estimate.json`, `retail-prices.json`: refreshed public rates, retained quantities and missing total.
- `official-guidance.json`: current new-Agent regional/features support and ARM/IoT API limitations.
- `evidence-verification.json`: derived counts, hashes and assertions; not a deployed acceptance receipt.
