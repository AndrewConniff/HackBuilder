---
lab:
  title: "Give It Tools"
  module: "Fourth Coffee sales readiness and daily close"
  description: "Build the next safe sales-readiness checkpoint for Fourth Coffee."
  duration: "35 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Hospitality & Travel
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# Challenge 3 — Give It Tools

> ⏱️ **35 minutes** · Challenge 3 of 5 ·
> Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, a scoped internal proposal can be reviewed and human-approved without duplicate
action.**

## Scenario

Fourth Coffee sales managers need stores ready to sell tomorrow and a defensible daily margin review.
Help store managers inspect only their own store and the north-area manager compare 001/002, never 003.
Prepare an internal replenishment proposal for human approval and a reviewed managerial close for finance;
do not transmit supplier orders, spend money or post a ledger.

Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.

## What you will learn

- Add one authenticated internal draft/review/approval boundary; keep writes outside agent authority.
- Keep authorized citations and cross-store denial before any read.
- Collect observable evidence without secrets.

## High-level lab steps

1. Define the internal action.
1. Review before approval.
1. Prove repeat safety.

## Prerequisites

| Requirement | Evidence |
| --- | --- |
| Prior checkpoint | Grounded 001 evidence is cited and unauthorized store requests are denied. |
| Files | Download the local Allfiles payloads and read workflow-contract.md. |

## Goal

A scoped internal proposal can be reviewed and human-approved without duplicate action.

## Why this matters

Sales managers need a defensible readiness decision, not an unreviewed model action.
Preserve the reviewed finance handoff without adding a selected business unit.

## Build on what works

**Starting checkpoint:** Grounded 001 evidence is cited and unauthorized store requests are denied.

**Smallest useful increment:** Add one authenticated internal draft/review/approval boundary; keep writes outside
agent authority.

**Keep working:** Keep authorized citations and cross-store denial before any read.

## Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Define the internal action

Use workflow-contract.md to choose an authenticated application/SDK boundary.
The portal remains a prompt-test surface, not a transactional authorization or order-write engine.

### Step 2 — Review before approval

Implement or demonstrate a scoped deterministic draft, explicit human review and durable confirmation.
Keep the model advisory; it must not call a write action or decide a user's store entitlement.

### Step 3 — Prove repeat safety

Repeat the same approval, then change the source version and try a stale draft.
Retest the grounded response and cross-store denial; never transmit to a supplier.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Implement the contract in your authenticated application; use MI or DefaultAzureCredential for backend services.
Persist the approval atomically with an idempotency key and optimistic concurrency.

Use the current verified SDK references in [resources](../../resources.md).

</details>

> [!IMPORTANT]
> Portal prompt tests do not implement durable actions, server authorization or application orchestration.
> Use your chosen application/SDK boundary for these requirements; do not replace them with model instructions.

## Done when

- [ ] A human-reviewed internal draft carries explicit quantities, units and authoritative totals.
- [ ] Repeating the same confirmation returns the same durable receipt.
- [ ] A stale version or unauthorized store approval is rejected with no side effect.
- [ ] The earlier grounded reply and denied-store regression still pass.

## Stuck?

<details>
<summary>Hint 1 — nudge</summary>

A proposal is not an approval.

</details>

<details>
<summary>Hint 2 — narrower</summary>

Bind the draft to its source version and the authenticated reviewer.

</details>

<details>
<summary>Hint 3 — recovery</summary>

Repeat the same confirmation key; return the original durable receipt rather than writing twice.

</details>

## Stretch goal

Compare a second permitted store without broadening identity grants or making this a prerequisite.

## Fallback

Keep grounding and a reviewable draft, but disable approval until durability/replay tests pass.
Continue evaluation with draft-only evidence and disclose the uncompleted action.

## Summary

Add one authenticated internal draft/review/approval boundary; keep writes outside agent authority.
Retest the earlier checkpoint and save evidence of any remaining gap.
