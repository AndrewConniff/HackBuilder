---
lab:
  title: "Harden and Demo"
  module: "Adatum Brokerage Agent — Security and Operational Excellence"
  description: "Your accumulated agent passes a small regression set with sanitized failure evidence."
  duration: "25 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Financial Services
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# 🧠 Challenge 4 — Harden and Demo

> ⏱️ **25 minutes** · Challenge 4 of 5 · Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, your accumulated agent passes a small regression set with sanitized failure evidence.**

## 💡 Scenario

Adatum Corporation is a synthetic investment brokerage. Build its anonymous public education
assistant to explain investment concepts and approved FAQs, refuse trading and account access,
and protect private keyless backends with least privilege.

## 🎯 What you will learn

- Evaluate real outcomes rather than a successful homepage.
- Trace correlation without logging chat text.
- Explain residual risks and least privilege.

## 🛠️ High-level lab steps

1. Run the supplied evaluation prompts against the accumulated solution.
1. Exercise negative identity, overload and upstream-error behavior.
1. Prepare a three-minute demo with evidence and an honest limitations list.

## 🎒 Prerequisites

| Requirement | Evidence |
| --- | --- |
| Access and prior checkpoint | Confirm the starting checkpoint below |

## 🎯 Goal

Show that your accumulated agent passes a small regression set with sanitized failure evidence.

## 💡 Why this matters

Protect educational customers from invented claims and protect backend access from untrusted callers.
Use one continuously working agent, not a new architecture at each checkpoint.

## 🧱 Build on what works

**Starting checkpoint:** Grounded educational responses retain authenticated receipt and private/keyless controls.

**Smallest useful increment:** A compact evaluation and operational evidence set, without redesigning the architecture.

**Keep working:** Keep the model, agent, source citations and exact-byte receipt tests working.

## 🧭 Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Inspect evaluation evidence

Use Foundry to review actual agent runs against the supplied prompts.
Record pass/fail observations without exposing prompt text in routine production logs.

### Step 2 — Inspect operations

Review scoped roles and sanitized correlation in your chosen operational views.
Exercise one controlled upstream failure and one rate rejection; never return a canned success.

### Step 3 — Demo the result

Demonstrate education, citation, receipt verification and a denied case.
State any incomplete integration or unmeasured scale claims explicitly.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Run Allfiles/evaluation.json prompts and infrastructure checks against your own solution.
Use local deterministic tests for token boundaries and explicit failure, then distinguish these from
real runtime acceptance. Record redacted outcomes, not secrets or full chat transcripts.

Use the [verified service resources](../../resources.md); resolve availability with the event operator.

</details>

> [!TIP]
> Keep evidence small: one positive result, one denied/error case, and the earlier regression.

## ✅ Done when

- [ ] Show recorded outcomes for every supplied prompt.
- [ ] Show a sanitized explicit upstream error with a correlation identifier, not fabricated chat.
- [ ] Show a controlled rejection and explain remaining privilege or exposure limits.
- [ ] Repeat the agent, citation and tamper-receipt regressions without changing the architecture.

## 💬 Stuck?

<details><summary>Hint 1 — nudge</summary>

A homepage and resource deployment do not prove model or agent behavior.

</details>

<details><summary>Hint 2 — narrower</summary>

Separate deterministic test doubles from real inference evidence.

</details>

<details><summary>Hint 3 — recovery</summary>

Use the correlation identifier to connect observations; keep prompts, answers and tokens out of routine logs.

</details>

## 🌟 Stretch goal

Measure a bounded load sample; state its duration and limits without claiming production readiness.

## 🔁 Fallback

Demo the last working checkpoint and run all remaining cases as explicit failures or not evaluated.
Carry the unresolved items into a follow-up list; do not replace them with a simulated pass.

## Summary

You added one observable checkpoint and retested earlier behavior.
Record incomplete integration honestly before advancing.

## 📚 Resources

Use the [shared documentation](../../resources.md), [FAQ](../../Allfiles/brokerage-faq.md)
and [evaluation set](../../Allfiles/evaluation.json).
