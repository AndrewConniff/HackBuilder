# Manufacturing Sales-to-Marketing reference: deployment preparation

## Deployment Details

Read-only preparation observed on 2026-10-24; **blocked, not deployed or deployment-ready**.
Canonical design confirmation and same-workspace local evidence were reused without regeneration.
Only exact-target preparation decision `c5b9b6e615064c5085134c1a62948c7f` authorized these cloud reads.

| Property | Authorized value |
| --- | --- |
| Account | `petender@microsoft.com` |
| Subscription | `efd64343-6ef4-4926-951f-d3229f38bd76` |
| Tenant | `16b3c013-d300-468d-ac64-7eda0820b6d3` |
| Resource group | `rg-manu-multi-agent` |
| Environment | `manu-multi-agent` |
| Region | `eastus2` |
| Evidence | `.resume-evidence/f24af8561b624fa292a41c561c8fb38e/` |

### Actual checks and limitations

CLI subscription/account/tenant matched; azd reported the same account. Subscription state is Enabled.
The target resource group does not exist; local azd environment listing returned an empty array.
No shared CLI default was changed and no environment was created.

All 13 queried providers are registered. Model metadata lists AIServices S0,
`gpt-4.1-mini` version `2025-04-14`, Responses/agentsV2 and GlobalStandard.
Model lifecycle is Legacy with inference deprecation dated 2027-04-14.
Quota is 0 used of 5000 units against the template's 30-unit demand; this is not allocation capacity.

Cosmos East US 2 is Online and regular subscription access is true.
Zonal access is false despite availability-zone support. The existing nonzonal design is unchanged.
APIM StandardV2 is listed in eastus2 with no returned restrictions, minimum one and maximum ten units.
ACA managed-environment count is 0 of 50; this alone does not validate Consumption core capacity.
Other service regional metadata and foundation what-if do not prove exact SKU allocation.
Private DNS is global, not an eastus2 regional service.

Effective subscription ARM actions include an unrestricted wildcard entry.
Three subscription policy assignments were returned; complete policy effects remain unproven.
Foundry Agent Consumer resolves to built-in `eed3b665-ab3a-47b6-8f48-c9382fb1dad6`.
No broader runtime role was substituted.

Graph identified target-tenant principal `214d672b-df87-4f3b-94fd-7863032546c1` as Member,
with default `allowedToCreateApps: true`. This does not create objects or grant directory-write consent.
Initial principal CLI syntax and authorization-policy selection errors were corrected and retained in evidence.

### What-if

The actual group-existence check returned false.
A subscription-scoped wrapper therefore includes the intended group and unchanged compiled foundation,
with the real target-tenant installer principal and `deploymentPhase=foundation`.
This is an independent preview, not a separate foundation deployment-approval stage.

| Result | Count |
| --- | --- |
| Create | 72 |
| Modify | 0 |
| Delete | 0 |
| Unsupported | 13 |

ARM returned `status: Succeeded`, null error and null diagnostics.
The 13 unsupported changes depend on future managed-identity principal IDs and ACA default-domain outputs:
role assignments and internal DNS cannot be completely evaluated before installation.
Full workload what-if additionally requires generated backend identity, image, agent, fixture and key outputs.
None was invented. No complete-reference what-if pass is claimed.

The formatted wrapper exceeded ARM's 4 MB request limit.
Equivalent compact JSON, 2,171,625 bytes, succeeded; both attempt logs are retained.
Use the retained compact wrapper only for authorized read-only preparation, never as a substitute installation.
The existing azd lifecycle remains the single intended installation entry point after all gates pass.

### Execution blocker

The first capacity GET lost query parameters because Windows interpreted URL ampersands.
The corrected command was denied by the execution host before an execution result was available.
The tool reported unavailable interactive approval without identifying the missing permission.
This is a **workflow-error**, not failed Azure sign-in, insufficient quota, or user setup evidence.
No retry through another route was attempted.
See `execution-denial.json` in the evidence directory and the canonical portal blocker.

The backend must first identify the missing CLI permission from structured execution diagnostics.
Canonical blocker `57f2f100051d467fab4a9526cb433495` exposes no user setup or approval action until diagnosis.
After that repair, verify the same read-only capacity GET under unchanged host restrictions.
A fresh worker must use the blocker verification protocol; another affirmative answer is not verification.

The successful independent what-if command, with `$evidence` set to the retained evidence directory, was:

```powershell
az deployment sub what-if `
  --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --location eastus2 --name manu-multi-agent-readonly-preflight `
  --template-file "$evidence\subscription-whatif-template.compact.json" `
  --result-format FullResourcePayloads --no-pretty-print --output json
```

Actual exit code: 0; ARM status and limitations are recorded above.

### Single installation, directory changes and private access

Preserve the existing guarded `azd provision --environment manu-multi-agent --no-prompt` lifecycle.
After separately recorded exact-target deployment consent, it creates/verifies one owned secretless
single-tenant API application/service principal, provisions foundation, installs private image/fixtures/agents/key,
then wires the workload with real outputs. No client secrets, Graph permission grants,
tenant-wide admin consent or elevation are planned.
Generated client/object IDs are outputs, not user decision inputs.

No directory mutation is authorized or performed now.
Default application-creation policy is evidence, not proof that every installation operation will succeed.
The lifecycle's existing principal lookup also passes unsupported `--subscription` to
`az ad signed-in-user show`; the observed CLI error must be repaired and locally tested before installation.
Preparation used the successful subscription-scoped Graph `/me` GET instead; no installer was executed.

Host `LAPTOP-JS6TIS5L` shows an IPv4 default route through Wi-Fi via `10.0.0.1`,
and no specific `10.84` route in the narrow observation.
This does not establish either private reachability or its absence.
No target endpoints exist to probe. A verified connected execution host and approved artifact/result channel
remain unresolved. Existing private-only data planes cannot be relaxed to bypass this dependency.
If no authorized connected host exists, one consolidated priced management-path design repair is required
before deployment review; no VM, VPN, Bastion, peering, runner or firewall change is currently authorized.

### Dated cost inventory

Official USD consumption meters were retrieved from the [Azure Retail Prices API][retail] on 2026-10-24.
These are retail estimates, not agreement-specific quotes or permission to spend.
Use 730 hours per month; recurring units continue billing independently of demo activity.

| Component | Observed rate and planning calculation |
| --- | --- |
| APIM Standard v2 | $0.9589/hour; one unit approximately $700.00/month, plus applicable calls |
| Search Standard S1 | $0.336/hour; one replica/partition $245.28/month |
| ACR Premium | $1.6666/day; 730-hour equivalent approximately $50.69, plus extra storage |
| Cosmos provisioned RU/s | $0.008 per 100 RU/s-hour; 5000 RU/s planning ceiling would cost $292/month |
| ACA active replica | 0.5 vCPU and 1 GiB approximately $39.42/month before grants and requests |
| ACA idle replica | Same sizing approximately $11.83/month before grants; active periods cost more |
| Key Vault | Standard operations $0.03/10,000; automated rotation $1/rotation |
| Log Analytics | Paid ingestion tier $2.76/GB; 30-day retention and actual volume govern charges |
| Private endpoints | Seven endpoints plus data processing; correct Private Link meter unresolved |
| DNS | Eight service zones plus internal ACA zone and queries; rates unresolved |
| Blob storage | Two LRS accounts, versions, retention, capacity and transactions; exact rates pending |
| Model | Actual input/output tokens priced separately; exact model rates not yet retrieved |
| Management path | Verified existing-host allocation or fully priced new path remains unresolved |
| Other | Network egress, build/image transfer, requests, taxes and agreement differences |

APIM, Search and ACR alone total approximately **$995.97/month**.
This excludes Cosmos, ACA, networking, logs, data, model and management access; it is not an all-in estimate.
The 5000 RU/s account ceiling is not evidence of actual installed/billed Cosmos throughput.
For 100 handoffs, retain the application's maximum 700 Responses requests and 3,000,000 combined tokens;
that combined ceiling is not a fabricated input/output split.

The first broad variable-rate response was paginated and is not a complete price inventory.
Narrower complete responses resolved the Search S1 and ACA/Key Vault/log meters.
No ACA Environment Private Endpoint charge was substituted for the seven service Private Link endpoints.
The final global/private-network/model rate request was in the denied batch and has no observed result.
Complete these rates and private execution costs before requesting one end-to-end deployment authorization.

## Deployed Resources

**None created or changed by this attempt.** The target resource group was observed absent.
What-if changes are proposals, not provisioning results. No homepage, model inference,
agent invocation, grounding, signing or live negative-case result is claimed.

## Outputs (Expected)

There are no newly generated deployment outputs or live application URL.
Future authorized installation must capture backend identity, real endpoints, image digest,
three actual agent versions, fixture digest and immutable signing-key version automatically.
Actual model/agent/application/grounding/tools/coordination/negative acceptance must then pass
before a fingerprinted suitability review.

No suitability approval, hack composition, team deployment, publication or cleanup was authorized.
The next step is execution-blocker verification, not another sign-in or deployment-ID questionnaire.

[retail]: https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices
