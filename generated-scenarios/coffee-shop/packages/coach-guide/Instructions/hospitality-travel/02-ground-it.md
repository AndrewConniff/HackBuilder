---
lab:
  title: "Ground It"
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

# Challenge 2 — Ground It

> ⏱️ **35 minutes** · Challenge 2 of 5 ·
> Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, the working agent explains authorized stock and margin evidence with source IDs.**

## Scenario

Fourth Coffee sales managers need stores ready to sell tomorrow and a defensible daily margin review.
Help store managers inspect only their own store and the north-area manager compare 001/002, never 003.
Prepare an internal replenishment proposal for human approval and a reviewed managerial close for finance;
do not transmit supplier orders, spend money or post a ledger.

Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.

## What you will learn

- Add scoped structured grounding without replacing the working MVP path.
- Keep the original MVP reply working when optional context is absent.
- Collect observable evidence without secrets.

## High-level lab steps

1. Select scoped evidence.
1. Explain with citations.
1. Probe the boundary.

## Prerequisites

| Requirement | Evidence |
| --- | --- |
| Prior checkpoint | The MVP replies through a real agent and denies unsupported factual certainty. |
| Files | Download the local Allfiles payloads and read workflow-contract.md. |

## Goal

The working agent explains authorized stock and margin evidence with source ids.

## Why this matters

Sales managers need a defensible readiness decision, not an unreviewed model action.
Preserve the reviewed finance handoff without adding a selected business unit.

## Build on what works

**Starting checkpoint:** The MVP replies through a real agent and denies unsupported factual certainty.

**Smallest useful increment:** Add scoped structured grounding without replacing the working MVP path.

**Keep working:** Keep the original MVP reply working when optional context is absent.

## Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Select scoped evidence

Read stores.json and choose a structured grounding path that filters scope before inference.
Start with 001 only; do not upload all stores into a common agent context.

### Step 2 — Explain with citations

Use the portal playground to test an agent with an authorized evidence slice and source row IDs.
Compute authoritative shortages and money outside the model; ask it only for advisory explanation.

### Step 3 — Probe the boundary

Test a crafted request for 002 from a 001 session and preserve the denied evidence.
Retest the MVP and a missing-ledger case; never invent a completed close from incomplete evidence.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Filter evidence using authenticated grants before building model input; include snapshot and source IDs.
Keep exact arithmetic and authorization in your application, not agent instructions.

Use the current verified SDK references in [resources](../../resources.md).

</details>

> [!IMPORTANT]
> Portal prompt tests do not implement durable actions, server authorization or application orchestration.
> Use your chosen application/SDK boundary for these requirements; do not replace them with model instructions.

## Done when

- [ ] An authorized stock/margin explanation carries source IDs from the correct snapshot.
- [ ] A crafted cross-store request is denied before business data reads or inference.
- [ ] An incomplete ledger does not produce a completed close.
- [ ] The original MVP still replies, and unsupported facts remain visibly uncertain.

## Stuck?

<details>
<summary>Hint 1 — nudge</summary>

Check what evidence reaches the model, not only what the model says.

</details>

<details>
<summary>Hint 2 — narrower</summary>

Use server grants before selecting a snapshot; preserve source IDs in the prompt.

</details>

<details>
<summary>Hint 3 — recovery</summary>

Reduce to authorized 001 evidence and prove a denied 002 request before adding more context.

</details>

## Stretch goal

Compare a second permitted store without broadening identity grants or making this a prerequisite.

## Fallback

Keep the MVP and supply a manually reviewed 001-only evidence slice with source IDs.
Mark automated retrieval incomplete; use that safe slice to define the internal action.

## Summary

Add scoped structured grounding without replacing the working MVP path.
Retest the earlier checkpoint and save evidence of any remaining gap.
