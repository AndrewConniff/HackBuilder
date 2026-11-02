---
lab:
  title: "Ground It"
  module: "Adatum campaign listener"
  description: "Your same agent drafts a policy-grounded reply without inventing offers or obeying an untrusted post."
  duration: "30 minutes"
  level: "200"
  islab: true
  primarytopics: "Foundry, Media & Communications, sales, marketing"
---

# Challenge 2 — Ground It

Your same agent drafts a policy-grounded reply without inventing offers or obeying an untrusted post.

![Time](https://img.shields.io/badge/time-30%20min-blue)
![Level](https://img.shields.io/badge/level-200-green)

Build running total: 85/150 minutes. Event: 10 kickoff + 150 build + 20 demo = 180 minutes.

## Scenario

Adatum Corporation launches a streaming-media campaign. Marketing owns public engagement
and Product Manager review; Sales owns subscriber recovery through the Conflict Resolution
Specialist. Build one bounded campaign-listener agent that preserves each source post,
grounds a draft in campaign policy and supports an accountable, explicit human handoff.
Industry: Media & Communications. Approved businessUnits: `sales`, `marketing`.
Nino Kapanadze operates Marketing campaigns; Petra Bartosova is the Marketing Product Manager;
Eesha Chatterjee is the Sales Conflict Resolution Specialist receiving subscriber-recovery handoffs.

## What you will learn

Supply campaign-policy-v1 with each invocation and identify the policy clause behind the draft.

## High-level lab steps

1. Read campaign-policy-v1 and choose how to supply its versioned text with the current source post.
2. Ask about campaign-04 and retain the draft plus the precise policy clause that supports it.
3. Test campaign-09 as untrusted data; show it cannot promote rules or promise a refund.
4. Keep policy references inspectable; a text clause reference is not a native retrieval citation claim.
5. Re-run campaign-01 and the earlier structured-output validation.

## Prerequisites

Use [challenge inputs](../../Allfiles/README.md), the [resource links](../../resources.md)
and your isolated, organizer-authorized destination. No new cloud authority is granted by this page.
Have an adapter-capable teammate for the hybrid action increment; no full UI rebuild is required.

## Goal

Your same agent drafts a policy-grounded reply without inventing offers or obeying an untrusted post.

## Why this matters

Marketing must not lose public feedback; Sales must receive an accountable subscriber-recovery handoff.
An estimated score or draft never grants a human role or permission to change campaign policy.

## Build on what works

Starting checkpoint: A campaign-listener response works against a real source post.

Smallest useful increment: Supply campaign-policy-v1 with each invocation
and identify the policy clause behind the draft.

Retained behavior: preserve the prior working prompt, source correlation and identity boundary.
Regression check: repeat at least one earlier success criterion before saving this checkpoint.

## Choose your path

### Foundry portal first

Use the playground to include the versioned policy and post as explicit context.
The proven path is prompt grounding, not a requirement to deploy Search or invent retrieval tools.

<details>
<summary>Code-first path with the Foundry SDK</summary>

Pass the exact policy text, current post and rule snapshot to the same agent invocation.
Retain the policy version and an exact supporting clause; do not add a new retrieval architecture.

</details>

## Done when

- [ ] campaign-04 response names campaign-policy-v1 and a supporting clause.
- [ ] campaign-09 cannot invent a refund or change rules.
- [ ] The original MVP response and score validation still pass.

## Stuck?

<details>
<summary>Hint 1</summary>

The policy does not authorize subscription changes or refunds.

</details>

<details>
<summary>Hint 2</summary>

Source text is data even when it says 'ignore your rules'.

</details>

<details>
<summary>Hint 3</summary>

Use an exact policy clause as evidence; never manufacture a native citation.

</details>

## Stretch goal

Add one extra synthetic regression without adding another service or expanding business-unit scope.

## Fallback

Keep the working MVP prompt, add the policy verbatim as context and identify a supporting clause manually.
Defer optional retrieval UI; retain the successful response for the action increment.

## Summary

Save your prompt, non-secret evidence and the last working checkpoint.
Return to the [challenge index](../../index.md).
