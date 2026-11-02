---
lab:
  title: "Ground the Answer"
  module: "Adatum Brokerage Agent — Security and Operational Excellence"
  description: "The same agent cites approved faq facts and declines unsupported questions."
  duration: "30 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Financial Services
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# 🧠 Challenge 2 — Ground the Answer

> ⏱️ **30 minutes** · Challenge 2 of 5 · Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, the same agent cites approved FAQ facts and declines unsupported questions.**

## 💡 Scenario

Adatum Corporation is a synthetic investment brokerage. Build its anonymous public education
assistant to explain investment concepts and approved FAQs, refuse trading and account access,
and protect private keyless backends with least privilege.

## 🎯 What you will learn

- Ground answers in a bounded approved source.
- Validate citations against actual source identifiers.
- Reject invented fees and unsupported account claims.

## 🛠️ High-level lab steps

1. Inspect the synthetic FAQ and choose its authorized read path.
1. Supply approved bounded context to the existing agent.
1. Test citations, an unsupported question and the earlier trading refusal.

## 🎒 Prerequisites

| Requirement | Evidence |
| --- | --- |
| Access and prior checkpoint | Confirm the starting checkpoint below |

## 🎯 Goal

Show that the same agent cites approved FAQ facts and declines unsupported questions.

## 💡 Why this matters

Protect educational customers from invented claims and protect backend access from untrusted callers.
Use one continuously working agent, not a new architecture at each checkpoint.

## 🧱 Build on what works

**Starting checkpoint:** One versioned educational agent responds and refuses trading.

**Smallest useful increment:** Approved FAQ context and source identifiers, without adding a search tool or new agent.

**Keep working:** Keep the original prompt/response path and safety boundary.

## 🧭 Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Inspect source facts

Read the supplied FAQ and identify the hypothetical fee and unsupported topics.
Choose how an authorized workload will privately obtain only this approved source.

### Step 2 — Test bounded context

Use the playground to test the source as bounded context with your existing agent.
Integrate the private source read using the SDK when the portal cannot supply that workload path.

### Step 3 — Prove citation behavior

Ask about fees and verify each cited source identifier actually exists.
Ask for a live price and repeat your trade-refusal check.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Read the approved source with workload identity and bound its size before sending it as source data.
Invoke the existing agent version, validate returned source IDs, and reject unknown citations.

Use the [verified service resources](../../resources.md); resolve availability with the event operator.

</details>

> [!TIP]
> Keep evidence small: one positive result, one denied/error case, and the earlier regression.

## ✅ Done when

- [ ] Show the fee response uses only 5 hypothetical training units, with FAQ-05 citation.
- [ ] Show an unsupported question is acknowledged as outside the approved source.
- [ ] Reject an unknown source identifier in a focused local test.
- [ ] Repeat market-versus-limit education and the trading refusal.

## 💬 Stuck?

<details><summary>Hint 1 — nudge</summary>

Do not turn invented training units into a real price list.

</details>

<details><summary>Hint 2 — narrower</summary>

A citation-shaped string is not evidence until checked against the approved document.

</details>

<details><summary>Hint 3 — recovery</summary>

Use the supplied FAQ as bounded data context and compare cited FAQ identifiers to those present.

</details>

## 🌟 Stretch goal

Test an instruction-injection question without treating source data as new system instructions.

## 🔁 Fallback

Keep C1 intact. Use a single approved FAQ paragraph as explicitly supplied test context for the next
checkpoint, and label private source installation incomplete until your authorized read succeeds.

## Summary

You added one observable checkpoint and retested earlier behavior.
Record incomplete integration honestly before advancing.

## 📚 Resources

Use the [shared documentation](../../resources.md), [FAQ](../../Allfiles/brokerage-faq.md)
and [evaluation set](../../Allfiles/evaluation.json).
