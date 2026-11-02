---
lab:
  title: "Secure Foundation"
  module: "Adatum Brokerage Agent — Security and Operational Excellence"
  description: "Your team proves an identity-backed model request inside its isolated boundary."
  duration: "25 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Financial Services
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# 🧠 Challenge 0 — Secure Foundation

> ⏱️ **25 minutes** · Challenge 0 of 5 · Difficulty: ●○○ · Path: Low-code + Code-first

**By the end of this challenge, your team proves an identity-backed model request inside its isolated boundary.**

## 💡 Scenario

Adatum Corporation is a synthetic investment brokerage. Build its anonymous public education
assistant to explain investment concepts and approved FAQs, refuse trading and account access,
and protect private keyless backends with least privilege.

## 🎯 What you will learn

- Choose a private-capable agent foundation from constraints.
- Separate deployment access from runtime access.
- Prove identity without shared keys.

## 🛠️ High-level lab steps

1. Confirm team isolation and effective permissions.
1. Choose a private-capable foundation and establish identity-backed model access.
1. Capture one real model response and one denied access result.

## 🎒 Prerequisites

| Requirement | Evidence |
| --- | --- |
| Access and prior checkpoint | Confirm the starting checkpoint below |

## 🎯 Goal

Show that your team proves an identity-backed model request inside its isolated boundary.

## 💡 Why this matters

Protect educational customers from invented claims and protect backend access from untrusted callers.
Use one continuously working agent, not a new architecture at each checkpoint.

## 🧱 Build on what works

**Starting checkpoint:** Your assigned group exists, contains no application, and is isolated from other teams.

**Smallest useful increment:** One real model request with scoped identity access.

**Keep working:** Keep isolation intact and store no credentials in files.

## 🧭 Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Inspect your boundary

Inspect your assigned group and effective roles in the Azure portal.

### Step 2 — Choose your foundation

Use Foundry to inspect private-capable project and model choices.
Have the operator verify quota and private reachability; never switch to public access to save time.

### Step 3 — Prove model access

Send a harmless educational question with identity authentication.
Record response metadata and a denied unauthorized path; omit resolved identifiers from shared evidence.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Use your selected Foundry SDK's model inference sample with DefaultAzureCredential from the operator host.
Run the same educational question and record real response metadata; do not substitute a mock response.

Use the [verified service resources](../../resources.md); resolve availability with the event operator.

</details>

> [!TIP]
> Keep evidence small: one positive result, one denied/error case, and the earlier regression.

## ✅ Done when

- [ ] Show a real model response in under a minute.
- [ ] Explain the team boundary and the identity that made the request.
- [ ] Demonstrate a denied unauthorized path, not just a role screenshot.
- [ ] Recheck no write access to another team group and no stored shared keys.

## 💬 Stuck?

<details><summary>Hint 1 — nudge</summary>

Start with effective access and network reachability, not the chatbot UI.

</details>

<details><summary>Hint 2 — narrower</summary>

A project region alone does not prove model quota or private agent support.

</details>

<details><summary>Hint 3 — recovery</summary>

Have the operator repair only the missing scoped permission or private DNS route, then repeat inference.

</details>

## 🌟 Stretch goal

Measure a second request's latency without claiming production throughput.

## 🔁 Fallback

Keep the empty team group and scoped access. Pair with a team member who has a working private
operator path to continue model and agent construction; record your missing foundation as unresolved.

## Summary

You added one observable checkpoint and retested earlier behavior.
Record incomplete integration honestly before advancing.

## 📚 Resources

Use the [shared documentation](../../resources.md), [FAQ](../../Allfiles/brokerage-faq.md)
and [evaluation set](../../Allfiles/evaluation.json).
