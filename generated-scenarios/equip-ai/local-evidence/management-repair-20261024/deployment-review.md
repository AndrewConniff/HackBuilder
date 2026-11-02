# equip-ai: consolidated private-management addition review

Continuation note, 2026-10-24: the proposal below is retained as originally reviewed.
The user subsequently approved it conditionally; see `user-approval.json`.
NAT prices now match the proposed rates, but actual Central US Standard_B2s subscription eligibility failed.
See `execution-result.md` and `management-readiness.json`; no provisioning was attempted.

Prepared 2026-10-24. Local implementation and public prices only; the new management scope is not authorized.
This review supersedes derived authorization summaries, not actual user responses or retained evidence.

## Existing authority retained

The actual 00:05:54 UTC response was **Authorize reviewed ordered ARM and dedicated directory installation**.
Decision `157b9eb7c2f14f9e957e45e26826e35d` covers ordered ARM installation in Central US and only the
dedicated equip-ai SPA/API objects, scopes/roles, assignment-required service principals and generated redirect.
It explicitly excludes a new runner and user assignments. Existing object ownership must be verified before reuse.

The 19:48 answer confirmed the retained design for local validation; it did not say to revoke that deployment grant.
The 20:31 East US read-only answer and subsequent **Authorize Central US read-only checks and ARM what-if**
response likewise contain no explicit withdrawal. The `prohibited` list in the later derived authorization JSON
is agent-authored, not quoted user revocation. Do not expand that read grant or erase the original write grant.
The installer receipt's one-hour worker timer was not user-imposed and no longer rejects continuing consent.
Tests still reject real, explicitly expiring grants.

No new cloud queries, provisioning, Entra operations, identity sign-in or shared-default changes occurred
while preparing this repair. The actual brief remains `.abcbuilder-portal/projects/equip-ai.json`;
the missing scenario request file was not recreated or repeatedly probed.

## Exact targets

| Field | Retained value |
| --- | --- |
| Account | petender@microsoft.com |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76 |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Region / group / azd environment | centralus / rg-equip-ai / equip-ai |
| VNet | vnet-equip-equip-ai; 10.247.0.0/24 |
| New management subnet | management; 10.247.0.128/27 |
| New VM / NIC | vm-equip-management-equip-ai / nic-equip-management-equip-ai |
| New outbound resources | nat-equip-management-equip-ai / pip-equip-management-equip-ai |
| New NSG | nsg-equip-management-equip-ai |

No East US deployment, alternate region, quota request, resource-provider registration, shared default,
tenant policy change, VPN/peering, broad Graph consent, credentials or public ingress exception is proposed.

## Preferred concrete repair

One Ubuntu 24.04 Gen2 `Standard_B2s` VM, 2 vCPUs/4 GiB, 32 GiB E4 Standard SSD LRS OS disk,
Trusted Launch, secure boot/vTPM, system-assigned identity and platform patching. No public NIC address.
NSG denies all inbound, including SSH from the VNet. A generated local SSH key satisfies the Linux VM
creation contract; its private half stays local and is not used for publishing.
Standard NAT and one Standard static IPv4 address supply explicit outbound connectivity.
The NAT public address cannot initiate inbound connections to the VM.

The VM uses the existing Azure-provided DNS and five linked private DNS zones, including private cleaner SCM
and Foundry. Existing app integration, Blob private access, Foundry public-access-disabled settings,
keyless Storage and trusted-IoT exception stay unchanged. No additional private endpoint or DNS zone is needed.
The runner's outbound Internet access remains allowed through NAT for VM-agent responses, OS patches,
Entra and Azure management; this is not a deny-all-egress design or an egress-FQDN firewall.

The VM identity receives only a custom read/publish action role on the two scenario sites and the existing
installer role (`Foundry User`, ID verified before deployment) on the single equipment-operations project.
It receives no Entra permission, subscription contributor, RBAC management, Blob write/delete or device key.
The operator invokes Run Command through existing Azure control-plane access.
Run Command executes as root: treat its control-plane permission as privileged VM administration.

### Real execution wiring

1. The guarded azd preprovision hook creates a local SSH public key and scenario-only management parameters.
   It calls the existing authorized, ownership-checking directory installer, reusing the retained IDs.
1. AVM NAT/IP/NSG resources precede VNet subnet creation; the AVM VM and project/site grants follow.
   The full VNet declaration retains the management subnet on subsequent deployments, avoiding child-subnet loss.
1. The existing redirect installer consumes the actual generated ARM hostname.
1. The postprovision hook publishes the existing .NET app locally as self-contained Linux x64.
   No remote SDK, Azure CLI, package installation, third-party artifact host or repository copy is needed.
1. `private_runner.py` sends only publish outputs in serial 512 KiB base64 chunks through authenticated ARM
   Run Command; parts are private root files and a complete SHA-256 is verified before extraction/execution.
   Hidden files, symlinks and credential-like extensions fail packaging.
1. Final repository-Python measurement of the retained artifact is 53,624,006 compressed bytes:
   103 commands, at least 2,060 seconds (34.3 minutes) for transfer alone.
   The earlier system-Python compression produced 55,370,632 bytes/106 commands;
   compression-library differences change size/hash, so each actual run computes and verifies its own digest.
   This is deliberately simple, not a production artifact-distribution service.
   The 4 KiB Run Command output limit carries only summaries/agent-version receipts, never the artifact.
1. Guest code requires private DNS resolution, then initializes the actual Foundry agent using managed identity.
   It deploys the identical ZIP to each site's SCM using a short-lived IMDS ARM bearer token.
   Basic publishing credentials stay disabled. Guest success markers are required; ARM success alone is insufficient.
1. The local hook captures the generated agent version, sets the web app's `AgentVersion` through ARM,
   and saves the installation receipt. `services: {}` prevents azd from repeating workstation SCM publication.
   Use `azd provision` (or infrastructure-only `azd up`) to run these hooks; `azd deploy` alone is not this path.
1. Runtime acceptance then uses actual signed-in browser tokens, IoT certificates and Foundry calls.
   Installation success is never relabeled as inference/chat acceptance.

Use `EQUIP_PRIVATE_RUNNER_APPROVED=true` only after this addition is approved in chat.
The flag is an accidental-execution guard, not a grant. No approval has been recorded for this addition.

## Incremental and total illustrative cost

730 hours/month; USD retail PAYG, Linux, no reservations or credits.
VM, disk and IPv4 rates were retrieved from the public Retail Prices API in this evidence directory.
The NAT query returned no matching rows; **$0.045/hour and $0.045/GB are planning assumptions**, not a
successful Central US retail API observation. The public pricing page confirms separate hour/data/egress billing
but returned dynamic dollar placeholders. Verify that meter before allocation; material increase returns for review.

| Addition | Assumption | Monthly USD |
| --- | --- | ---: |
| B2s VM | $0.0499/hour x 730 | 36.43 |
| E4 LRS OS disk | 32 GiB | 2.40 |
| Standard NAT | assumed $0.045/hour x 730 | 32.85 |
| Standard static IPv4 | $0.005/hour x 730 | 3.65 |
| NAT processing | assumed 5 GB x $0.045 | 0.23 |
| Disk transactions allowance | E4 $0.002/10,000 operations | 0.01 |
| **Incremental management estimate** | continuously provisioned | **75.56** |
| Retained scenario usage estimate | prior $99.95 fixed plus $51.58 usage | 151.53 |
| **Combined estimate** | same retained workload plus this management path | **227.09** |

VM deallocation alone saves compute, not the $2.40 disk, $32.85 NAT or $3.65 public IP charges.
With only 20 VM hours but NAT/IP retained all month, the incremental estimate is about $40.13/month.
NAT has no stop mode. Delete NAT/IP and the installation VM/disk after acceptance if repeatability is not needed.
Deletion must detach NAT from the management subnet first and remove the runner identity's grants.
Do not switch `enableManagement` off and assume incremental ARM deletes these resources.
Clean the guest artifact directory using `private_runner.py clean` before deallocation.
Removal is scenario-only; never run a subscription/shared-network cleanup.

The combined number includes management compute/disk/NAT/IP and the retained scenario usage assumptions.
Internet egress, additional diagnostics ingestion, private-endpoint traffic above baseline, disk transaction
variation, extra Entra licensing if applicable, taxes and support remain variable/excluded.
No Bastion, VPN gateway or remote build service is included or required.
This is an estimate, not a quote or a user-approved spend ceiling.

## Actual evidence and pending checks

Local compile/lint pass for the integrated AVM IaC. All **24 Python tests pass**: 15 retained installer contracts
and 9 new runner/consent contracts. Existing 49 app/browser checks and Linux publish are reused unchanged.
The two updated diagram sources render using the already installed Graphviz path, without a shared PATH change.
An initial render failed because this shell lacked that path; the corrected per-process invocation succeeded.
Diagrams show proposed resources, not deployed resources; some crossing labels remain a readability limitation.

The last **actual** independent ARM what-if returned 35 creates, no delete/modify, nine nested warnings.
It predates this repair and is not a preview of the new VM/NAT resources or a full-reference pass.
Central US saved B2/model eligibility has headroom; East US B2 quota failed and is not silently substituted.
Historical policy scanning remains nonpassing and is not relabeled by compilation success.

After new-scope authority, use shared `azure_context.py` identity helpers and azd auth status without signing in
or changing defaults. Check Central US B2s SKU restrictions, regional plus B-series 2-vCPU and VM-count headroom,
Trusted Launch/image support, network quotas/policy, NAT SKU and actual prices. No capacity is reserved.
Refresh exact full-reference what-if with real verified identity outputs and this addition before provisioning.
Stop on actual denial, destructive change or material scope/cost increase; repair in-scope code errors directly.
The new management eligibility checks and exact what-if have not been executed.

From the actual VM, prove private DNS, TLS, authenticated SCM publishing and agent initialization; prove
outside-network/unauthorized denial without opening endpoints. Then capture real model inference,
agent invocation, authenticated chat, cited tool grounding, device-to-Blob routing/freshness, cleanup and 401/403.
The existing runtime JSON remains blocked with null URL/time and no passing runtime checks.
Snapshot/suitability approval waits for those results; no hack composition has started.

## Only missing authority requested

1. Authorize Central US readiness reads, exact ARM what-if and conditional provisioning/operation of the
   listed management VM, disk/NIC, subnet, NAT/IP/NSG and project/site-scoped identity grants, including
   Run Command artifact transfer/installation, cleanup and deallocation, at the above incremental/total estimate.
   The original reviewed ARM/dedicated-directory scope is reused, not submitted for routine approval again.
1. For real interactive acceptance, nominate **petender@microsoft.com only** for assignment to the dedicated
   SPA and API. Verify its actual principal ID from the configured account, then grant the SPA default role
   and API `Operations.Tacoma` for cross-site-denial testing; replace that API assignment with
   `Operations.Statewide` for the statewide walkthrough. Final access is statewide; remove temporary Tacoma access.
   This adds only scoped application role assignments, not directory privileges or broad admin consent.
   Existing installer code refuses assignments until this nomination is actually approved/materialized.

No other users/groups, directory objects, tenant permissions, event deployment, publication or suitability
approval is requested. Actual tenant refusal still requires the appropriately authorized administrator;
chat approval does not elevate the current account.

## References

- [Action Run Command restrictions and permissions][run-command]
- [Private endpoint DNS][dns]
- [AVM VM schema][vm]
- [NAT billing and lifecycle][nat]
- [Retail prices API][prices]

[run-command]: https://learn.microsoft.com/azure/virtual-machines/linux/run-command
[dns]: https://learn.microsoft.com/azure/private-link/private-endpoint-dns
[vm]: https://github.com/Azure/bicep-registry-modules/tree/main/avm/res/compute/virtual-machine
[nat]: https://azure.microsoft.com/pricing/details/azure-nat-gateway/
[prices]: https://prices.azure.com/api/retail/prices
