---
lab:
  title: "Sign the Receipt"
  module: "Adatum Brokerage Agent — Security and Operational Excellence"
  description: "A workload-authenticated receipt protects answer integrity while private backend access stays denied."
  duration: "40 minutes"
  level: 200
  islab: true
  primarytopics:
    - Microsoft Foundry
    - AI agents
    - Financial Services
---

<!-- markdownlint-disable MD025 MD033 MD036 -->

# 🧠 Challenge 3 — Sign the Receipt

> ⏱️ **40 minutes** · Challenge 3 of 5 · Difficulty: ●●● · Path: Low-code + Code-first

**By the end of this challenge, a workload-authenticated receipt protects answer integrity while private backend
access stays denied.**

## 💡 Scenario

Adatum Corporation is a synthetic investment brokerage. Build its anonymous public education
assistant to explain investment concepts and approved FAQs, refuse trading and account access,
and protect private keyless backends with least privilege.

## 🎯 What you will learn

- Add an authenticated workload action without an agent tool.
- Verify an answer digest with a nonexportable signing key.
- Keep anonymous customer access separate from authenticated backend hops.

## 🛠️ High-level lab steps

1. Choose an identity-authorized signing path for the existing answer.
1. Generate and verify an answer-digest receipt, including a tamper test.
1. Prove anonymous customer entry and denial of untrusted backend access.

## 🎒 Prerequisites

| Requirement | Evidence |
| --- | --- |
| Access and prior checkpoint | Confirm the starting checkpoint below |

## 🎯 Goal

Show that a workload-authenticated receipt protects answer integrity while private backend access stays denied.

## 💡 Why this matters

Protect educational customers from invented claims and protect backend access from untrusted callers.
Use one continuously working agent, not a new architecture at each checkpoint.

## 🧱 Build on what works

**Starting checkpoint:** Your agent answers with approved citations; earlier education and refusals still pass.

**Smallest useful increment:** One backend signing action over the exact answer bytes, not a trading or agent tool.

**Keep working:** Keep citations and the pinned agent path; never add customer login as a core prerequisite.

## 🧭 Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — Choose the protected action

Inspect managed-identity permissions for a nonexportable signing key.
Choose the narrow signing scope and verify an unrelated identity has no permission.

### Step 2 — Verify integrity

Use the portal to inspect key metadata and role scope, then pair with the SDK path
to sign and verify exact answer bytes; the portal alone cannot implement the workload.

### Step 3 — Prove the boundary

Expose only anonymous educational entry while authenticating private backend hops.
Show wrong-identity and wrong-audience denials without sharing actual token or endpoint values.

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

Hash the exact UTF-8 answer with SHA-256, sign the digest through Key Vault using workload identity,
and verify with the public key. Mutate one answer byte and show verification fails.
Connect the existing agent path to your anonymous edge; reject untrusted backend tokens.

Use the [verified service resources](../../resources.md); resolve availability with the event operator.

</details>

> [!TIP]
> Keep evidence small: one positive result, one denied/error case, and the earlier regression.

## ✅ Done when

- [ ] Show a signature verifies for the exact original answer and fails after tampering.
- [ ] Show unrelated-identity signing fails and private key material never leaves the key service.
- [ ] Show anonymous customer entry succeeds but direct untrusted backend access fails.
- [ ] Repeat the FAQ citation and education-only regression through the integrated path.

## 💬 Stuck?

<details><summary>Hint 1 — nudge</summary>

Signing is an application action after inference, not a new agent capability.

</details>

<details><summary>Hint 2 — narrower</summary>

A digest without authenticated signing cannot identify the signer.

</details>

<details><summary>Hint 3 — recovery</summary>

Separate customer access from workload tokens; verify audience and allowed caller identity at the backend.

</details>

## 🌟 Stretch goal

Design optional authenticated public chat after the core timer; retain all private/keyless controls.

## 🔁 Fallback

Preserve C2. Sign a clearly labeled local synthetic answer to test integrity independently,
then integrate when the private route is ready; report missing live integration instead of passing it.

## Summary

You added one observable checkpoint and retested earlier behavior.
Record incomplete integration honestly before advancing.

## 📚 Resources

Use the [shared documentation](../../resources.md), [FAQ](../../Allfiles/brokerage-faq.md)
and [evaluation set](../../Allfiles/evaluation.json).
