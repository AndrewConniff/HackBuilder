---
lab:
  title: "Build the MVP"
  module: "Fourth Coffee sales readiness and daily close"
  description: "Build the next safe sales-readiness checkpoint for Fourth Coffee."
  duration: "30 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Hospitality & Travel
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# Challenge 1 — Build the MVP

> ⏱️ **30 minutes** · Challenge 1 of 5 ·
> Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, a real Foundry agent answers a store manager's sales-readiness question.**

## Scenario

Fourth Coffee sales managers need stores ready to sell tomorrow and a defensible daily margin review.
Help store managers inspect only their own store and the north-area manager compare 001/002, never 003.
Prepare an internal replenishment proposal for human approval and a reviewed managerial close for finance;
do not transmit supplier orders, spend money or post a ledger.

Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.

## What you will learn

- Reach a useful prompt-agent reply within the first 15 minutes, then refine its instructions.
- Keep identity-based model access and the no-key boundary.
- Collect observable evidence without secrets.

## High-level lab steps

1. Ship one useful reply.
1. Constrain the role.
1. Retest the baseline.

## Prerequisites

| Requirement | Evidence |
| --- | --- |
| Prior checkpoint | A real identity-authenticated model request succeeds. |
| Files | Download the local Allfiles payloads and read workflow-contract.md. |

## Goal

A real foundry agent answers a store manager's sales-readiness question.

## Why this matters

Sales managers need a defensible readiness decision, not an unreviewed model action.
Preserve the reviewed finance handoff without adding a selected business unit.

## Build on what works

**Starting checkpoint:** A real identity-authenticated model request succeeds.

**Smallest useful increment:** Reach a useful prompt-agent reply within the first 15 minutes, then refine its
instructions.

**Keep working:** Keep identity-based model access and the no-key boundary.

## Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Ship one useful reply

In the Foundry portal, create or select your own prompt agent and test a sales-readiness question.
By minute 15, show one real agent response; do not delay it for tools, grounding or UI polish.

### Step 2 — Constrain the role

Make uncertainty visible: no invented stock, no authoritative money calculation and no order execution.
Use synthetic store/area personas from the files, not directory membership inferred from names.

### Step 3 — Retest the baseline

Repeat your original model request and agent prompt, then ask for an unsupported ledger posting.
Capture the refusal or safe deferral and real invocation evidence.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Create and invoke your own prompt agent with the verified Foundry SDK guidance in resources.md.
Keep the call small, capture its real response ID and preserve the foundation test.

Use the current verified SDK references in [resources](../../resources.md).

</details>

> [!IMPORTANT]
> Portal prompt tests do not implement durable actions, server authorization or application orchestration.
> Use your chosen application/SDK boundary for these requirements; do not replace them with model instructions.

## Done when

- [ ] A useful real agent response exists by minute 15 of this challenge.
- [ ] A request to post a ledger or spend money is declined or deferred to human review.
- [ ] The response makes missing evidence explicit instead of inventing stock or money.
- [ ] The original model-access check still passes without keys.

## Stuck?

<details>
<summary>Hint 1 — nudge</summary>

Prefer the shortest useful agent reply before improving instructions.

</details>

<details>
<summary>Hint 2 — narrower</summary>

Missing business evidence should produce uncertainty, not a fabricated number.

</details>

<details>
<summary>Hint 3 — recovery</summary>

Test one store-readiness question with no action attached, then save its real receipt.

</details>

## Stretch goal

Compare a second permitted store without broadening identity grants or making this a prerequisite.

## Fallback

Keep the smallest real prompt-agent response and defer instruction polish.
Use this checkpoint for grounding; do not substitute a canned answer for invocation.

## Summary

Reach a useful prompt-agent reply within the first 15 minutes, then refine its instructions.
Retest the earlier checkpoint and save evidence of any remaining gap.
