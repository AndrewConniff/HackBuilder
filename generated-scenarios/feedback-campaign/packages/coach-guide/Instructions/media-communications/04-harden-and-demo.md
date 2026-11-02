---
lab:
  title: "Harden & Demo"
  module: "Adatum campaign listener"
  description: "Collect regression, denial and recovery evidence for the unchanged agent/action checkpoint."
  duration: "30 minutes"
  level: "200"
  islab: true
  primarytopics: "Foundry, Media & Communications, sales, marketing"
---

# Challenge 4 — Harden & Demo

Your unchanged agent/action checkpoint has observable regression, denial and recovery evidence for a demo.

![Time](https://img.shields.io/badge/time-30%20min-blue)
![Level](https://img.shields.io/badge/level-200-green)

Build running total: 150/150 minutes. Event: 10 kickoff + 150 build + 20 demo = 180 minutes.

## Scenario

Adatum Corporation launches a streaming-media campaign. Marketing owns public engagement
and Product Manager review; Sales owns subscriber recovery through the Conflict Resolution
Specialist. Build one bounded campaign-listener agent that preserves each source post,
grounds a draft in campaign policy and supports an accountable, explicit human handoff.
Industry: Media & Communications. Approved businessUnits: `sales`, `marketing`.
Nino Kapanadze operates Marketing campaigns; Petra Bartosova is the Marketing Product Manager;
Eesha Chatterjee is the Sales Conflict Resolution Specialist receiving subscriber-recovery handoffs.

## What you will learn

Evaluate thresholds, authority, duplicates and recovery without adding another architecture.

## High-level lab steps

1. Run labeled examples and deterministic boundary cases; report model scores as estimates, not calibration.
2. Show a positive auto reply, ProductManager review and campaign-04 fallback with correlation receipts.
3. Deny wrong role, stale edit, duplicate send and unsafe input; retain the working success path.
4. Prove pending work survives restart and propose a rule version without letting the model promote it.
5. Record live versus local-only failure tests honestly, then rehearse a two-minute demo.

## Prerequisites

Use [challenge inputs](../../Allfiles/README.md), the [resource links](../../resources.md)
and your isolated, organizer-authorized destination. No new cloud authority is granted by this page.
Have an adapter-capable teammate for the hybrid action increment; no full UI rebuild is required.

## Goal

Your unchanged agent/action checkpoint has observable regression, denial and recovery evidence for a demo.

## Why this matters

Marketing must not lose public feedback; Sales must receive an accountable subscriber-recovery handoff.
An estimated score or draft never grants a human role or permission to change campaign policy.

## Build on what works

Starting checkpoint: A grounded draft plus one authenticated durable reply action works.

Smallest useful increment: Evaluate thresholds, authority, duplicates and recovery without adding another architecture.

Retained behavior: preserve the prior working prompt, source correlation and identity boundary.
Regression check: repeat at least one earlier success criterion before saving this checkpoint.

## Choose your path

### Foundry portal first

Use the playground for prompt regressions and compare saved examples.
The adapter owner runs durability and denial tests. Portal inspection alone cannot prove those gates.

<details>
<summary>Code-first path with the Foundry SDK</summary>

Use parameterized local tests for thresholds and mocks for provider failure, plus real destination receipts
only when authorized. Test optimistic concurrency and immutable rule promotion/rollback separately.

</details>

## Done when

- [ ] Three route outcomes plus exact 0.80/0.89 boundaries have inspectable evidence.
- [ ] Restart, stale edit, wrong role and duplicate behavior are recorded.
- [ ] Proposed product-aspect/80%-negative changes remain inactive until explicit human promotion.
- [ ] The demo distinguishes measured runtime results, mocked failures and untested cases.

## Stuck?

<details>
<summary>Hint 1</summary>

Separate deterministic threshold tests from variable model outputs.

</details>

<details>
<summary>Hint 2</summary>

The mixed campaign-03 fixture actually scored highly negative in the reference.

</details>

<details>
<summary>Hint 3</summary>

Use neutral campaign-04 for fallback; keep proposed rules separate from the active snapshot.

</details>

## Stretch goal

Add one extra synthetic regression without adding another service or expanding business-unit scope.

## Fallback

Freeze the last working agent/action checkpoint and demo only verified paths.
List failed or unrun tests explicitly; never label a pending action or mocked outage as live success.

## Summary

Save your prompt, non-secret evidence and the last working checkpoint.
Return to the [challenge index](../../index.md).
