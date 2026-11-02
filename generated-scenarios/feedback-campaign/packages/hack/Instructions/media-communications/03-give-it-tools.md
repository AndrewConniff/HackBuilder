---
lab:
  title: "Give It Tools"
  module: "Adatum campaign listener"
  description: "Add a separate authenticated action that enforces human authority over a proposed reply."
  duration: "35 minutes"
  level: "200"
  islab: true
  primarytopics: "Foundry, Media & Communications, sales, marketing"
---

# Challenge 3 — Give It Tools

Your working agent proposes a useful reply while a separate authenticated action enforces human authority.

![Time](https://img.shields.io/badge/time-35%20min-blue)
![Level](https://img.shields.io/badge/level-200-green)

Build running total: 120/150 minutes. Event: 10 kickoff + 150 build + 20 demo = 180 minutes.

## Scenario

Adatum Corporation launches a streaming-media campaign. Marketing owns public engagement
and Product Manager review; Sales owns subscriber recovery through the Conflict Resolution
Specialist. Build one bounded campaign-listener agent that preserves each source post,
grounds a draft in campaign policy and supports an accountable, explicit human handoff.
Industry: Media & Communications. Approved businessUnits: `sales`, `marketing`.
Nino Kapanadze operates Marketing campaigns; Petra Bartosova is the Marketing Product Manager;
Eesha Chatterjee is the Sales Conflict Resolution Specialist receiving subscriber-recovery handoffs.

## What you will learn

Add one explicit human send with durable state, role enforcement and a queue receipt.

## High-level lab steps

1. Identify the smallest reply action and its input contract; keep recommendations advisory.
2. Use deterministic overall scores: positive >=80% auto; otherwise negative >=89% ProductManager;
3. send the remaining cases to ConflictResolutionSpecialist with source, assessment and investigation context.
4. Require explicit human intent and role, persist the pending case and rule snapshot, then accept one edited reply.
5. Record real queue acceptance and prove a wrong role or duplicate cannot produce a second reply.
6. Re-run the grounded agent; distinguish native prompt execution from your application-hosted action.

## Prerequisites

Use [challenge inputs](../../Allfiles/README.md), the [resource links](../../resources.md)
and your isolated, organizer-authorized destination. No new cloud authority is granted by this page.
Have an adapter-capable teammate for the hybrid action increment; no full UI rebuild is required.

## Goal

Your working agent proposes a useful reply while a separate authenticated action enforces human authority.

## Why this matters

Marketing must not lose public feedback; Sales must receive an accountable subscriber-recovery handoff.
An estimated score or draft never grants a human role or permission to change campaign policy.

## Build on what works

Starting checkpoint: A policy-grounded draft works and the original source ID is preserved.

Smallest useful increment: Add one explicit human send with durable state, role enforcement and a queue receipt.

Retained behavior: preserve the prior working prompt, source correlation and identity boundary.
Regression check: repeat at least one earlier success criterion before saving this checkpoint.

## Choose your path

### Foundry portal first

Use the playground to inspect the draft and proposed action payload before sending anything.
The approved reference has no native portal tool or durable low-code workflow to clone.
For durable role-gated action and real queue evidence, use a small code adapter with your team;
a portal-only trace does not meet this checkpoint. Do not build a replacement web UI.

<details>
<summary>Code-first path with the Foundry SDK</summary>

Implement one bounded adapter using the action contract, durable checkpoint and scoped workload identity.
Use authenticated server-side roles and idempotent message IDs; never trust a caller-selected role.
Foundry SDK prompt execution does not make this adapter a native agent tool.

</details>

## Done when

- [ ] A durable human pending record shows the source and snapshot; an authorized edited send has a real queue receipt.
- [ ] Wrong-role and duplicate requests fail without a second side effect.
- [ ] Grounded inference still works; queue acceptance is not external delivery.

## Stuck?

<details>
<summary>Hint 1</summary>

An agent draft is not authorization to send.

</details>

<details>
<summary>Hint 2</summary>

Persist the human checkpoint and stable correlation ID before a side effect.

</details>

<details>
<summary>Hint 3</summary>

Evaluate positive first; make a second send conflict rather than publish again.

</details>

## Stretch goal

Add one extra synthetic regression without adding another service or expanding business-unit scope.

## Fallback

Keep the grounded agent read-only and the pending human record. Pair with the adapter owner to complete
one authorized send; simulated receipts are not completion. Continue prompt evaluations while action repair proceeds.

## Summary

Save your prompt, non-secret evidence and the last working checkpoint.
Return to the [challenge index](../../index.md).
