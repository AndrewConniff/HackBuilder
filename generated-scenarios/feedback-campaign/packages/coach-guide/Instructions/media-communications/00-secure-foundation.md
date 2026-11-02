---
lab:
  title: "Secure Foundation"
  module: "Adatum campaign listener"
  description: "You can make one authenticated model request in your isolated destination without a pasted key."
  duration: "25 minutes"
  level: "200"
  islab: true
  primarytopics: "Foundry, Media & Communications, sales, marketing"
---

# Challenge 0 — Secure Foundation

You can make one authenticated model request in your isolated destination without a pasted key.

![Time](https://img.shields.io/badge/time-25%20min-blue)
![Level](https://img.shields.io/badge/level-200-green)

Build running total: 25/150 minutes. Event: 10 kickoff + 150 build + 20 demo = 180 minutes.

## Scenario

Adatum Corporation launches a streaming-media campaign. Marketing owns public engagement
and Product Manager review; Sales owns subscriber recovery through the Conflict Resolution
Specialist. Build one bounded campaign-listener agent that preserves each source post,
grounds a draft in campaign policy and supports an accountable, explicit human handoff.
Industry: Media & Communications. Approved businessUnits: `sales`, `marketing`.
Nino Kapanadze operates Marketing campaigns; Petra Bartosova is the Marketing Product Manager;
Eesha Chatterjee is the Sales Conflict Resolution Specialist receiving subscriber-recovery handoffs.

## What you will learn

Choose the smallest supported Foundry foundation and prove one real model call.

## High-level lab steps

1. Inspect the starter status and synthetic contacts; agree Marketing-to-Sales ownership.
2. Confirm your organizer-authorized destination group and explicitly chosen region; never reuse another team.
3. Choose a Foundry project/model with current destination eligibility and scoped identity access.
4. Make one authenticated model request and record a non-secret response identifier.
5. Repeat with missing permission and capture a real denial; restore only the intended scoped access.

## Prerequisites

Use [challenge inputs](../../Allfiles/README.md), the [resource links](../../resources.md)
and your isolated, organizer-authorized destination. No new cloud authority is granted by this page.
Have an adapter-capable teammate for the hybrid action increment; no full UI rebuild is required.

## Goal

You can make one authenticated model request in your isolated destination without a pasted key.

## Why this matters

Marketing must not lose public feedback; Sales must receive an accountable subscriber-recovery handoff.
An estimated score or draft never grants a human role or permission to change campaign policy.

## Build on what works

Starting checkpoint: The minimum starter reports not-configured; ten synthetic posts and one policy are available.

Smallest useful increment: Choose the smallest supported Foundry foundation and prove one real model call.

Retained behavior: preserve the prior working prompt, source correlation and identity boundary.
Regression check: repeat at least one earlier success criterion before saving this checkpoint.

## Choose your path

### Foundry portal first

Use the Foundry portal to select your authorized project/model and test a prompt.
Use your signed-in identity and scoped RBAC; an organizer resolves actual quota/access failures.

<details>
<summary>Code-first path with the Foundry SDK</summary>

Use the current Foundry SDK with DefaultAzureCredential for local development.
Use managed identity in an Azure host; retain the actual response ID, not an invented receipt.

</details>

## Done when

- [ ] One real authenticated model response ID with no keys in source.
- [ ] A real permission denial and a working retry after restoring intended access.

## Stuck?

<details>
<summary>Hint 1</summary>

Start with one synthetic sentence, not the whole application.

</details>

<details>
<summary>Hint 2</summary>

Check the selected destination and the caller's project-scoped data role.

</details>

<details>
<summary>Hint 3</summary>

Ask the organizer to inspect the exact access denial; never fall back to a pasted key.

</details>

## Stretch goal

Add one extra synthetic regression without adding another service or expanding business-unit scope.

## Fallback

Keep the status/fixture checks. Ask the organizer to repair scoped access or provide an authorized
isolated foundation. A saved response is diagnostic only; resume real inference before Challenge 1 completes.

## Summary

Save your prompt, non-secret evidence and the last working checkpoint.
Return to the [challenge index](../../index.md).
