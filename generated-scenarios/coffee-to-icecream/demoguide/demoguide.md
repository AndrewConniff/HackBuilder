# Northwind Traders operations walkthrough

> Updated by az-01-conductor agent | 2026-10-30

## Status and audience

Prepared for store and area operations managers.
The [actual reference application](https://web-ic-gyhmp4vgxvkwy.azurewebsites.net/) is deployed.
Its managed-identity workflows and operator data administration have been exercised through real APIs.
However, the reference is **not ready for suitability approval**: the latest read-latency run failed,
and agent narratives still invent cost-trend commentary despite exact structured financial figures.
The authenticated browser sequence below is a pending walkthrough, not a completed UI acceptance claim.

## Business story and timing

Allow 12 minutes: access boundaries (2), recipe stock and CSV import (3), internal order review (2),
worker coordination and P&L review (3), failure/recovery and limitations (2).
Ten stores form north 001-005 and south 006-010. Store logins each have exactly one store.
The finance handoff is a reviewed managerial report, not a statutory close or journal posting.

## Prerequisites

- The explicitly authorized target is already provisioned and initialized; all three real agents select version 3.
- Retrieve destination-specific logins from restricted `.private/reference-access.json` on the operator host.
  Store accounts are store001 through store010; area accounts are areanorth and areasouth.
  Never copy passwords into public guides, source archives or learner exports.
- Use the actual Azure HTTPS URL linked above, not a source deployment or local development endpoint.
- Real inference, own-user operator CRUD and runtime managed-identity checks passed; retain their evidence.
  Final narrative/performance acceptance and authenticated browser walkthrough remain pending.
- Local UI smoke tests use Development and HTTPS with an existing dev certificate.
  Never disable production TLS/cookies.

## Store-manager flow

1. Sign in as store001. Only 001 is listed. Inspect closing stock, separate spoilage, recipe evidence and P&L.
1. Known synthetic day 001: vanilla closing 11.3 L; net sales USD 598.50; sold COGS USD 99.40;
   spoilage USD 3.00; labor USD 142.00; occupancy USD 45.00; managerial profit USD 309.10.
   These exact deterministic values were observed in the deployed store 001 close evidence.
1. If demonstrating import, inspect the current version and import history first.
   The store 002 packet has already been imported by API acceptance; its exact used bytes must conflict.
   A new, explicitly prepared complete packet replaces the current packet atomically.
   Repeating those same bytes must conflict, not deduct consumption twice.
1. Create a replenishment draft. Review positive shortfalls and confirm the internal order.
   Repeating approval must preserve the same order and timestamp. No supplier transmission occurs.
1. Ask: "Explain ice-cream replenishment, spoilage and sales variance against plan."
   The deployed API produced two store/domain assignments and one synthesis with unique real response IDs.
   Inspect authoritative stock/ledger cards, not only prose: waste is already removed from final stock
   and is expensed separately once. There is no planned profit or historical cost baseline.
   Current unsupported steady-cost commentary is a known failed acceptance case, not an accepted explanation.
1. The generated report is AwaitingReview. Confirm review to persist reviewer/time.
   A changed snapshot or a report older than fifteen minutes requires a new report.

## Area-manager flow

1. Sign in as areanorth. Select 001-005. South stores must never appear.
1. Run the same daily-close question. Actual API proof produced ten assignments and one synthesis,
   not one fixed two-worker panel, for each area.
1. Compare authoritative profit and sales totals with store ledgers; explanations must cite assigned evidence only.
1. Review the report. An individual store manager must not review or read this multi-store report.

## CSV contract

Exact columns:

```csv
StoreId,Date,Kind,Item,Component,Unit,Quantity,UnitCost,Target
```

Each file is one complete store/date packet, not incremental movement.
Use UTF-8, ISO date, invariant decimal, no thousands separators; at most 100 rows and 24,000 characters.
Supported stock base units are `L` and `unit`; money is USD.

- stock: Item is SKU, Component empty, Quantity opening units, UnitCost per base unit, Target desired closing units.
- recipe: Item sold product, Component stock SKU, Quantity per sold product; unused UnitCost/Target zero.
- sale: Item product, unit `unit`, Quantity sold, UnitCost net price, Component empty, Target zero.
- spoilage: Item SKU, base unit, Quantity wasted; Component empty, unused money/Target zero.
- cost: Item `labor`, `occupancy` or `planned-sales`, unit `USD`, Quantity 1, UnitCost amount, other fields empty/zero.

All three cost rows and stock/recipe/sale rows are required.
Negative amounts, unknown recipe components, mixed dates, unknown units, duplicate keys and insufficient stock fail.
Imports need the current snapshot version. No source-specific store assignments or passwords are imported.
Single currency, UTC date and no lot-expiry lifecycle are explicit current limitations.

## Failure and recovery

- Unauthorized store: denial before business reads or inference. Do not repair by granting all stores.
- Stale import/order/report: reload current evidence and generate a new proposal; do not bypass version checks.
- Foundry timeout, missing worker or duplicate receipt: no complete report is stored.
  Inspect correlation/status logs; correct the dependency and rerun within the same authorized scope.
- Missing daily inputs: repair the complete packet, not model-generated substitute numbers.
- Overload/quota: show explicit failure and record rejected requests separately from latency.

Human approval reviews a version-bound managerial artifact; it does not reserve stock or lock every area store.
Snapshots can change after review. Reviewed reports retain their original evidence;
do not present them as live stock.
No autonomous spending, accounting posting, live POS integration or production-scale certification is claimed.

### Observed coordination failure and recovery

The bounded version-3 test temporarily changed the stock-agent name to a nonexistent test name and restarted.
The real close returned 503, trace `0HNPM80BDQCV8:00000004`; close count remained 47.
The test restored the original name in `finally`, restarted and completed a real close; count became 48.
Configuration is restored. Show [retained evidence](../evidence/worker-recovery-acceptance.json)
rather than disrupting the shared live app during a demonstration.
Earlier historical reports remain immutable, including their known misleading version-1 prose.

## Performance and costs

Required targets: ten concurrent managers; read p95 below two seconds and report p95 below sixty.
Latest version-3 observation: 100 reads, zero HTTP failures, p95 3.4644 seconds: **failed**.
Ten real concurrent closes had zero failures and p95 7.4583 seconds; both area closes stayed below sixty.
The earlier passing persistent-connection runs are retained, not substituted for the latest failed run.
Server HTTP logs confirm the latest multi-second read spike; root cause remains unresolved.

Observed official retail-based planning estimate is USD 191-321/month at ten GB logs,
or USD 251-381 at thirty GB, for the architecture's illustrative five-store close volume.
These are not spending caps or measured bills. Token/usage aggregate queries returned no rows;
no actual billed per-close token cost is claimed.
Legacy model deprecation, public TLS/no WAF, the policy-tag exception and preview SDK compatibility remain limitations.

## Screenshot fallback

The integrated browser rendered the actual Azure HTTPS sign-in page with authentication-required state,
disabled business actions and no exposed store data. No browser trust setting changed.
Authenticated desktop/mobile walkthroughs and captures remain pending, not passed.
Use [architecture](../03-architect-diagram.png), [runtime coordination](../04-runtime-diagram.png)
and the retained API receipts as an explicitly labeled fallback; they do not prove authenticated browser behavior.
For interactive UI proof, the operator can sign in as areanorth using the restricted private access file,
without pasting credentials into chat or public documents. The agent can then continue the existing browser page.
Suitability review remains blocked by actual latency/grounding failures regardless of screenshot availability.
