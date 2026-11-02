---
lab:
  title: "Harden & Demo"
  module: "Fourth Coffee sales readiness and daily close"
  description: "Build the next safe sales-readiness checkpoint for Fourth Coffee."
  duration: "25 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Hospitality & Travel
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# Challenge 4 — Harden & Demo

> ⏱️ **25 minutes** · Challenge 4 of 5 ·
> Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, you can demonstrate bounded independent evidence work, safe failure and retained
earlier behavior.**

## Scenario

Fourth Coffee sales managers need stores ready to sell tomorrow and a defensible daily margin review.
Help store managers inspect only their own store and the north-area manager compare 001/002, never 003.
Prepare an internal replenishment proposal for human approval and a reviewed managerial close for finance;
do not transmit supplier orders, spend money or post a ledger.

Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.

## What you will learn

- Extend independent evidence handling with bounded combination and test a failed dependency.
- Keep the model, MVP, citations, authorization and replay-safe human action working.
- Collect observable evidence without secrets.

## High-level lab steps

1. Bound independent evidence work.
1. Fail safely and recover.
1. Demonstrate the business outcome.

## Prerequisites

| Requirement | Evidence |
| --- | --- |
| Prior checkpoint | Grounding and a human-reviewed internal action work together without autonomous spending. |
| Files | Download the local Allfiles payloads and read workflow-contract.md. |

## Goal

You can demonstrate bounded independent evidence work, safe failure and retained earlier behavior.

## Why this matters

Sales managers need a defensible readiness decision, not an unreviewed model action.
Preserve the reviewed finance handoff without adding a selected business unit.

## Build on what works

**Starting checkpoint:** Grounding and a human-reviewed internal action work together without autonomous spending.

**Smallest useful increment:** Extend independent evidence handling with bounded combination and test a failed
dependency.

**Keep working:** Keep the model, MVP, citations, authorization and replay-safe human action working.

## Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Bound independent evidence work

Keep the agent working while comparing independent readiness and margin evidence.
Choose an application/SDK coordination boundary with a deadline, bounded concurrency and observable receipts.

### Step 2 — Fail safely and recover

Use evaluation-cases.json and an isolated dependency fault; a failed branch must block a completed close.
Restore the dependency and retest earlier checkpoints; do not alter store grants or ledger completeness.

### Step 3 — Demonstrate the business outcome

Show authorized evidence, one real completed agent response and a human-reviewed internal receipt.
Use the portal for agent inspection; show coordination/action traces from your chosen application boundary.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Coordinate independent evidence calls in your application using a shared deadline and cancellation.
Record branch/completion events, inject one isolated failure and verify no success is synthesized.

Use the current verified SDK references in [resources](../../resources.md).

</details>

> [!IMPORTANT]
> Portal prompt tests do not implement durable actions, server authorization or application orchestration.
> Use your chosen application/SDK boundary for these requirements; do not replace them with model instructions.

## Done when

- [ ] A real success has correlation/response receipts and source IDs, not just plausible prose.
- [ ] Independent work is bounded; an injected dependency failure prevents a completed close.
- [ ] Recovery reruns the prior grounded response and replay-safe action without privilege expansion.
- [ ] Your demo separates admitted success, rejection, failed work and unmeasured scaling.

## Stuck?

<details>
<summary>Hint 1 — nudge</summary>

A completed narrative cannot hide a failed branch.

</details>

<details>
<summary>Hint 2 — narrower</summary>

A bounded deadline must cover all independent calls and combination work.

</details>

<details>
<summary>Hint 3 — recovery</summary>

Fail one dependency in an isolated test; assert no completed close, restore it, then rerun the previous test.

</details>

## Stretch goal

Compare a second permitted store without broadening identity grants or making this a prerequisite.

## Fallback

Demonstrate the last passing checkpoint and failed-test evidence honestly.
Do not label unproved coordination, safe approval or scale targets as complete.

## Summary

Extend independent evidence handling with bounded combination and test a failed dependency.
Retest the earlier checkpoint and save evidence of any remaining gap.
