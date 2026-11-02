---
lab:
  title: "Build the MVP"
  module: "Adatum campaign listener"
  description: "Prove a campaign-listener response in 15 minutes, then structure its interpretation."
  duration: "30 minutes"
  level: "200"
  islab: true
  primarytopics: "Foundry, Media & Communications, sales, marketing"
---

# Challenge 1 — Build the MVP

You have one working campaign-listener response in the first 15 minutes, then a structured interpretation.

![Time](https://img.shields.io/badge/time-30%20min-blue)
![Level](https://img.shields.io/badge/level-200-green)

Build running total: 55/150 minutes. Event: 10 kickoff + 150 build + 20 demo = 180 minutes.

## Scenario

Adatum Corporation launches a streaming-media campaign. Marketing owns public engagement
and Product Manager review; Sales owns subscriber recovery through the Conflict Resolution
Specialist. Build one bounded campaign-listener agent that preserves each source post,
grounds a draft in campaign policy and supports an accountable, explicit human handoff.
Industry: Media & Communications. Approved businessUnits: `sales`, `marketing`.
Nino Kapanadze operates Marketing campaigns; Petra Bartosova is the Marketing Product Manager;
Eesha Chatterjee is the Sales Conflict Resolution Specialist receiving subscriber-recovery handoffs.

## What you will learn

Create a bounded prompt agent and retain the raw response and correlation ID.

## High-level lab steps

1. Within the first 15 minutes, create a prompt agent and obtain one response to campaign-01.
2. Bound its job to interpreting a source post and drafting, never granting authority or sending.
3. Extend the response to overall and aspect sentiment, assessment, draft and suggested investigations.
4. Reject nonfinite, out-of-range or non-normalized scores; do not silently repair them into success.
5. Repeat the foundation request and retain both response identifiers without private endpoints.

## Prerequisites

Use [challenge inputs](../../Allfiles/README.md), the [resource links](../../resources.md)
and your isolated, organizer-authorized destination. No new cloud authority is granted by this page.
Have an adapter-capable teammate for the hybrid action increment; no full UI rebuild is required.

## Goal

You have one working campaign-listener response in the first 15 minutes, then a structured interpretation.

## Why this matters

Marketing must not lose public feedback; Sales must receive an accountable subscriber-recovery handoff.
An estimated score or draft never grants a human role or permission to change campaign policy.

## Build on what works

Starting checkpoint: An authenticated model response works in the isolated project.

Smallest useful increment: Create a bounded prompt agent and retain the raw response and correlation ID.

Retained behavior: preserve the prior working prompt, source correlation and identity boundary.
Regression check: repeat at least one earlier success criterion before saving this checkpoint.

## Choose your path

### Foundry portal first

Use the portal agent playground to create/test a prompt agent. Capture a response before tuning.
Use structured output where supported; otherwise validate the returned JSON outside the model.

<details>
<summary>Code-first path with the Foundry SDK</summary>

Use the same prompt-agent API/model contract with the Foundry SDK.
Store a versioned prompt and validate the returned sentiment vectors before downstream use.

</details>

## Done when

- [ ] One native prompt-agent response ID by the halfway checkpoint.
- [ ] Validated source-linked sentiment, draft and assessment; no action executed.
- [ ] The earlier authenticated model request still passes.

## Stuck?

<details>
<summary>Hint 1</summary>

Keep interpretation separate from action authority.

</details>

<details>
<summary>Hint 2</summary>

Retain sourceId and one raw model response before adding schema constraints.

</details>

<details>
<summary>Hint 3</summary>

Validate each vector independently and reject invalid output visibly.

</details>

## Stretch goal

Add one extra synthetic regression without adding another service or expanding business-unit scope.

## Fallback

Keep the first real response and its exact prompt. Defer optional schema polish; preserve the source ID
and a valid draft so Challenge 2 can add policy. Do not replace inference with canned success.

## Summary

Save your prompt, non-secret evidence and the last working checkpoint.
Return to the [challenge index](../../index.md).
