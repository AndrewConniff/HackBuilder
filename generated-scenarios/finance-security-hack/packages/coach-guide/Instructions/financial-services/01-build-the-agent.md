---
lab:
  title: "Build the Agent"
  module: "Adatum Brokerage Agent — Security and Operational Excellence"
  description: "One versioned foundry agent gives a real educational answer and refuses trading."
  duration: "30 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Financial Services
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# 🧠 Challenge 1 — Build the Agent

> ⏱️ **30 minutes** · Challenge 1 of 5 · Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge, one versioned Foundry agent gives a real educational answer and refuses trading.**

## 💡 Scenario

Adatum Corporation is a synthetic investment brokerage. Build its anonymous public education
assistant to explain investment concepts and approved FAQs, refuse trading and account access,
and protect private keyless backends with least privilege.

## 🎯 What you will learn

- Create one agent before adding integrations.
- Distinguish model inference from agent invocation.
- Use instructions to enforce an education-only boundary.

## 🛠️ High-level lab steps

1. Reuse the working identity and model.
1. Get a prompt-agent response within the first 15 minutes.
1. Add education-only instructions and retest the original prompt plus a trading refusal.

## 🎒 Prerequisites

| Requirement | Evidence |
| --- | --- |
| Access and prior checkpoint | Confirm the starting checkpoint below |

## 🎯 Goal

Show that one versioned Foundry agent gives a real educational answer and refuses trading.

## 💡 Why this matters

Protect educational customers from invented claims and protect backend access from untrusted callers.
Use one continuously working agent, not a new architecture at each checkpoint.

## 🧱 Build on what works

**Starting checkpoint:** An identity-backed model request succeeds from a private-capable operator path.

**Smallest useful increment:** One versioned prompt agent, without tools, returning a real response identifier.

**Keep working:** Keep model access and least-privilege separation; do not build a UI before this checkpoint.

## 🧭 Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Create the smallest agent

Create one prompt agent using the working model in Foundry.
An agent is a versioned instruction-and-model configuration, not a collection of trading tools.

### Step 2 — Get the first answer

Ask about market versus limit orders in the playground within 15 minutes.
Record the agent version and real response metadata before refining wording.

### Step 3 — Set the boundary

Refuse trading, portfolio access and personalized advice.
Repeat the first question and the request to buy shares with a guaranteed return.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Use the current Foundry project client to create a versioned declarative agent.
Invoke that named version with the project Responses client; keep creation credentials out of runtime.

Use the [verified service resources](../../resources.md); resolve availability with the event operator.

</details>

> [!TIP]
> Keep evidence small: one positive result, one denied/error case, and the earlier regression.

## ✅ Done when

- [ ] Show an answer with a real agent response identifier.
- [ ] Show the selected agent version, not only a model deployment name.
- [ ] Show refusal to buy shares or guarantee a return, with no trading call.
- [ ] Repeat the C0 request and demonstrate the original identity still works.

## 💬 Stuck?

<details><summary>Hint 1 — nudge</summary>

Prove a single prompt/response before styling anything.

</details>

<details><summary>Hint 2 — narrower</summary>

An inference response from a model alone does not prove an agent was invoked.

</details>

<details><summary>Hint 3 — recovery</summary>

Pin the agent version and record its response identifier; remove unnecessary tools rather than add them.

</details>

## 🌟 Stretch goal

Compare two instruction versions using the same harmless question.

## 🔁 Fallback

Keep C0 working. Test your drafted education-only instructions in the working team's agent path,
then use the FAQ locally for C2 design; mark your own agent integration as pending.

## Summary

You added one observable checkpoint and retested earlier behavior.
Record incomplete integration honestly before advancing.

## 📚 Resources

Use the [shared documentation](../../resources.md), [FAQ](../../Allfiles/brokerage-faq.md)
and [evaluation set](../../Allfiles/evaluation.json).
