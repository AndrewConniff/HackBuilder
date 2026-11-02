# Conditional installation result, 2026-10-24

## Actual authorization

The user handoff quotes the parent ask_user response verbatim:
**Approve the listed additions, subject to passing readiness, pricing and what-if checks**.
See `user-approval.json` for provenance and exact scope. This is deployment-scope approval,
not suitability approval. The retained same-scenario ARM and dedicated directory grant remains valid.

## Commands and observed results

- Shared `scripts/azure_context.py` `identity`/`discover` helpers: Azure CLI usable token metadata
  and `azd auth login --check-status --no-prompt` verified petender@microsoft.com, subscription
  efd64343-6ef4-4926-951f-d3229f38bd76, tenant 16b3c013-d300-468d-ac64-7eda0820b6d3.
  The legacy project contains East US; the actual current approval and existing scenario azd
  environment select Central US. An explicit discovery override reconciles this without changing defaults.
- `az vm list-skus --location centralus --size Standard_B2s --all --subscription ... --output json`:
  exit 0, actual `NotAvailableForSubscription` restrictions for Central US location and zones 1/2/3.
  The location-wide restriction affects the proposed nonzonal VM too.
- `az vm list-usage --location centralus --subscription ... --output json`: exit 0.
  B-series quota 0/100, regional cores 0/100 and VM count 0/25000; demand 2 cores/one VM fits.
  **Quota headroom does not override SKU eligibility.**
- `az vm image show --location centralus --urn Canonical:ubuntu-24_04-lts:server:latest ...`:
  exit 0; actual image 24.04.202610210, x64/V2, Active, TrustedLaunchSupported.
- `az provider show --namespace Microsoft.Compute ...`: exit 0, Registered.
- `az network list-usages --location centralus ...`: exit 0, observed NAT/IP/NSG/NIC/VNet
  quota headroom. This is not deployment or runtime proof.
- Official NAT pricing page raw HTML embeds `data-amount` regional `us-central` prices:
  **USD 0.045/hour and USD 0.045/GB**, matching the disclosed assumptions.
  `verified-nat-page-prices.json` preserves extraction, source and HTML SHA-256.
  Public Retail Prices API filters still returned zero NAT rows; those are not presented as verified meters.
  Existing VM/disk/IP public pricing evidence is reused.
- New collection script had two local bugs (junction-derived repository path and string quota arithmetic).
  Both were repaired directly. Same-session expensive SKU enumeration was reused; no eligibility retry,
  allocation probe, alternative region, default change, login or tool installation occurred.

## Concrete blocker and skipped dependent operations

**Management readiness failed. No provisioning was attempted in this continuation.**

The complete exact ARM what-if was not executed after the eligibility failure. Neither the earlier partial
preview nor compilation is relabeled as a full what-if pass. No directory reads/writes or assignments,
VM Run Command, artifact transfer, publication, inference, agent invocation, application chat, tool grounding,
IoT acceptance, cleanup or deallocation occurred. There is no new deployment URL or runtime success evidence.
No new management resources were created by this continuation; this statement does not inventory historical resources.

## Exact next action

Restore Central US `Standard_B2s` subscription SKU eligibility through the subscription owner/Azure support,
then rerun the approved readiness collector without `--reuse-skus`, review the full exact ARM what-if and
continue via guarded azd hooks only if all conditions pass.
An alternate SKU or region requires a separately reviewed scope/cost change; none was selected or queried.
No quota/support request was submitted automatically. No repeated approval of the unchanged scope is required.

Incremental estimate remains USD75.56/month, combined USD227.09/month under the retained assumptions.
Prices are estimates, not quotes; egress, diagnostics, taxes and other disclosed variable costs remain excluded.
The management estimate has not been incurred by this continuation.

Suitability remains unapproved. No hack content, packages, event rollout or publication was started.
