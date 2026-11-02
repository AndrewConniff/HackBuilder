---
lab:
  title: "Secure Foundation"
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

# Challenge 0 — Secure Foundation

> ⏱️ **25 minutes** · Challenge 0 of 5 ·
> Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, you can prove isolated, identity-based model access without exposing a key.**

## Scenario

Fourth Coffee sales managers need stores ready to sell tomorrow and a defensible daily margin review.
Help store managers inspect only their own store and the north-area manager compare 001/002, never 003.
Prepare an internal replenishment proposal for human approval and a reviewed managerial close for finance;
do not transmit supplier orders, spend money or post a ledger.

Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.

## What you will learn

- Choose the minimum foundation and prove one real model response.
- Keep synthetic files local and team isolation intact.
- Collect observable evidence without secrets.

## High-level lab steps

1. Inspect the minimum starter.
1. Prove safe access.
1. Capture the baseline.

## Prerequisites

| Requirement | Evidence |
| --- | --- |
| Prior checkpoint | Local fixture files and an isolated team target are available; nothing is configured. |
| Files | Download the local Allfiles payloads and read workflow-contract.md. |

## Goal

You can prove isolated, identity-based model access without exposing a key.

## Why this matters

Sales managers need a defensible readiness decision, not an unreviewed model action.
Preserve the reviewed finance handoff without adding a selected business unit.

## Build on what works

**Starting checkpoint:** Local fixture files and an isolated team target are available; nothing is configured.

**Smallest useful increment:** Choose the minimum foundation and prove one real model response.

**Keep working:** Keep synthetic files local and team isolation intact.

## Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Inspect the minimum starter

Run the local status command and inspect the fixture scope; expect not-configured.
Choose foundation resources inside your isolated target; the starter contains no app or Foundry resources.

### Step 2 — Prove safe access

Use the Foundry portal to verify project access and select an eligible deployed model.
Prove one identity-authenticated model request; ask the facilitator about unavailable quota, not for keys.

### Step 3 — Capture the baseline

Record a real response receipt and the target isolation evidence without identifiers or secrets.
Verify no business data is publicly exposed and no finance or operations unit is added.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Use the approved destination identity with DefaultAzureCredential in a local SDK client.
Make one model request with your selected configuration; keep endpoints in runtime configuration, not lab files.

Use the current verified SDK references in [resources](../../resources.md).

</details>

> [!IMPORTANT]
> Portal prompt tests do not implement durable actions, server authorization or application orchestration.
> Use your chosen application/SDK boundary for these requirements; do not replace them with model instructions.

## Done when

- [ ] A real identity-authenticated model request has a receipt.
- [ ] The target is isolated from other teams and no credentials appear in saved evidence.
- [ ] Local starter status remains explicitly not-configured until you supply your own integration.
- [ ] The fixture files remain readable and no business data is exposed anonymously.

## Stuck?

<details>
<summary>Hint 1 — nudge</summary>

Separate your operator access from the future application identity.

</details>

<details>
<summary>Hint 2 — narrower</summary>

An empty resource group is intentional; inspect available model/project access.

</details>

<details>
<summary>Hint 3 — recovery</summary>

Use a facilitator-approved, isolated project if quota blocks you; keep the same files and never paste a key.

</details>

## Stretch goal

Compare a second permitted store without broadening identity grants or making this a prerequisite.

## Fallback

Keep your isolated files and pair on facilitator-approved access to an eligible project.
Do not mark model access complete until a real request passes; use that request to start the MVP.

## Summary

Choose the minimum foundation and prove one real model response.
Retest the earlier checkpoint and save evidence of any remaining gap.
