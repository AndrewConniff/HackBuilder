---
lab:
  title: "Finale — Coach notes"
  module: "Adatum Brokerage Agent — Security and Operational Excellence"
  description: "Private recovery, answer mapping and debrief for all five challenges."
  duration: "20 minutes"
  level: 200
  islab: true
  audience: coach
  isfinale: true
  primarytopics:
    - Coaching
    - Microsoft Foundry
    - Financial Services
---

<!-- markdownlint-disable MD025 MD036 -->

# Finale — Coach notes

Private only. The reference deployment is historically user-attested, not independently verified.
The one-off lab was deleted; former URL, exact time and logs are unavailable.
No new coach environment has been deployed, and no current runtime checks or capacity are inferred.
Use local package tests as deterministic evidence only; future cloud acceptance requires separate authorization.


## Challenge 0 — Secure Foundation

**Objective and expected outcome**

Your team proves an identity-backed model request inside its isolated boundary.

**Completion evidence**

- Show a real model response in under a minute.
- Explain the team boundary and the identity that made the request.
- Demonstrate a denied unauthorized path, not just a role screenshot.
- Recheck no write access to another team group and no stored shared keys.

**Coach talking points**

Use Standard private Foundry, BYO Storage/Cosmos/Search, delegated agent subnet and private endpoints.
The approved foundation is in coach/infra/main.bicep and modules/project.bicep; Basic is not equivalent.

**Common blockers and recovery**

Missing quota, provider policy, delegated subnet or private operator DNS blocks real inference.
Escalate to the event owner; do not widen access or move targets silently.

**Hint escalation**

Start with Hint 1 after the team states the failing observation; use Hint 2 to narrow scope.
Use Hint 3 only for the smallest recovery step; keep architecture answers on this private page.

**Fallback checkpoint**

Keep the empty team group and scoped access. Pair with a team member who has a working private
operator path to continue model and agent construction; record your missing foundation as unresolved.

**Demo and debrief prompts**

Ask: What evidence proves this increment, which earlier behavior still works, and what remains untested?
Use the matching supplied evaluation prompt, not a real customer request.

**Security and governance reminders**

Do not share tokens or resolved environment details; do not broaden runtime identities to unblock deployment.
No trading, customer-account integration or agent tool belongs in this reference.


## Challenge 1 — Build the Agent

**Objective and expected outcome**

One versioned foundry agent gives a real educational answer and refuses trading.

**Completion evidence**

- Show an answer with a real agent response identifier.
- Show the selected agent version, not only a model deployment name.
- Show refusal to buy shares or guarantee a return, with no trading call.
- Repeat the C0 request and demonstrate the original identity still works.

**Coach talking points**

Use the approved DeclarativeAgentDefinition and AgentReference(name, version) path in
coach/src/Brokerage.Web/AzureBrokerage.cs. Runtime consumes the agent; installer alone creates versions.

**Common blockers and recovery**

Confusing model output with agent output or leaving an unpinned mutable agent loses the checkpoint.
Inspect response metadata and use the installed version printed by the guarded initializer.

**Hint escalation**

Start with Hint 1 after the team states the failing observation; use Hint 2 to narrow scope.
Use Hint 3 only for the smallest recovery step; keep architecture answers on this private page.

**Fallback checkpoint**

Keep C0 working. Test your drafted education-only instructions in the working team's agent path,
then use the FAQ locally for C2 design; mark your own agent integration as pending.

**Demo and debrief prompts**

Ask: What evidence proves this increment, which earlier behavior still works, and what remains untested?
Use the matching supplied evaluation prompt, not a real customer request.

**Security and governance reminders**

Do not share tokens or resolved environment details; do not broaden runtime identities to unblock deployment.
No trading, customer-account integration or agent tool belongs in this reference.


## Challenge 2 — Ground the Answer

**Objective and expected outcome**

The same agent cites approved faq facts and declines unsupported questions.

**Completion evidence**

- Show the fee response uses only 5 hypothetical training units, with FAQ-05 citation.
- Show an unsupported question is acknowledged as outside the approved source.
- Reject an unknown source identifier in a focused local test.
- Repeat market-versus-limit education and the trading refusal.

**Coach talking points**

The app privately reads knowledge/brokerage-faq.md, validates its size and passes a developer data
message to the same pinned agent. ChatService rejects unknown FAQ IDs; no indexer or file-search tool.

**Common blockers and recovery**

A valid citation does not guarantee a grounded answer; review the exact hypothetical fact too.
Missing source must fail rather than fall back to a local runtime fixture.

**Hint escalation**

Start with Hint 1 after the team states the failing observation; use Hint 2 to narrow scope.
Use Hint 3 only for the smallest recovery step; keep architecture answers on this private page.

**Fallback checkpoint**

Keep C1 intact. Use a single approved FAQ paragraph as explicitly supplied test context for the next
checkpoint, and label private source installation incomplete until your authorized read succeeds.

**Demo and debrief prompts**

Ask: What evidence proves this increment, which earlier behavior still works, and what remains untested?
Use the matching supplied evaluation prompt, not a real customer request.

**Security and governance reminders**

Do not share tokens or resolved environment details; do not broaden runtime identities to unblock deployment.
No trading, customer-account integration or agent tool belongs in this reference.


## Challenge 3 — Sign the Receipt

**Objective and expected outcome**

A workload-authenticated receipt protects answer integrity while private backend access stays denied.

**Completion evidence**

- Show a signature verifies for the exact original answer and fails after tampering.
- Show unrelated-identity signing fails and private key material never leaves the key service.
- Show anonymous customer entry succeeds but direct untrusted backend access fails.
- Repeat the FAQ citation and education-only regression through the integrated path.

**Coach talking points**

APIM is the anonymous public edge with outbound VNet integration and its own MI. Internal ACA validates
JWT signature/lifetime/issuer/audience/tenant/gateway oid. App MI reads FAQ, consumes agent and signs
SHA-256 answer digest with Key Vault RS256; key-scoped Crypto User, no backend shared keys.

**Common blockers and recovery**

Private image push, DNS, audience registration and APIM provisioning can exceed the challenge budget.
Use the isolated signing checkpoint for partial progress; do not claim a public/private integration pass.

**Hint escalation**

Start with Hint 1 after the team states the failing observation; use Hint 2 to narrow scope.
Use Hint 3 only for the smallest recovery step; keep architecture answers on this private page.

**Fallback checkpoint**

Preserve C2. Sign a clearly labeled local synthetic answer to test integrity independently,
then integrate when the private route is ready; report missing live integration instead of passing it.

**Demo and debrief prompts**

Ask: What evidence proves this increment, which earlier behavior still works, and what remains untested?
Use the matching supplied evaluation prompt, not a real customer request.

**Security and governance reminders**

Do not share tokens or resolved environment details; do not broaden runtime identities to unblock deployment.
No trading, customer-account integration or agent tool belongs in this reference.


## Challenge 4 — Harden and Demo

**Objective and expected outcome**

Your accumulated agent passes a small regression set with sanitized failure evidence.

**Completion evidence**

- Show recorded outcomes for every supplied prompt.
- Show a sanitized explicit upstream error with a correlation identifier, not fabricated chat.
- Show a controlled rejection and explain remaining privilege or exposure limits.
- Repeat the agent, citation and tamper-receipt regressions without changing the architecture.

**Coach talking points**

Reuse coach/tests/Brokerage.Tests and guarded script tests as deterministic baselines.
Runtime acceptance must additionally verify real model/agent/grounding, private paths, signing and
observable negative cases. APIM limits are approximate; no WAF or production scale guarantee exists.

**Common blockers and recovery**

Tests with local doubles do not verify cloud capacity, network isolation or model behavior.
Keep those results separate, and retain explicit unresolved runtime items for future authorized checks.

**Hint escalation**

Start with Hint 1 after the team states the failing observation; use Hint 2 to narrow scope.
Use Hint 3 only for the smallest recovery step; keep architecture answers on this private page.

**Fallback checkpoint**

Demo the last working checkpoint and run all remaining cases as explicit failures or not evaluated.
Carry the unresolved items into a follow-up list; do not replace them with a simulated pass.

**Demo and debrief prompts**

Ask: What evidence proves this increment, which earlier behavior still works, and what remains untested?
Use the matching supplied evaluation prompt, not a real customer request.

**Security and governance reminders**

Do not share tokens or resolved environment details; do not broaden runtime identities to unblock deployment.
No trading, customer-account integration or agent tool belongs in this reference.


## Event wrap-up

### Three-minute demonstration sequence

1. Ask market versus limit orders, show the real agent response and a valid FAQ citation.
1. Show the exact-byte receipt verifies, then mutate an answer byte and show failure.
1. Request a trade and show refusal; show a denied backend caller or sanitized upstream error.

### Cross-challenge regression checks

- [ ] Identity-backed model request and isolated team access.
- [ ] Version-pinned real agent invocation; educational response and trading refusal.
- [ ] Approved hypothetical fee with FAQ-05; unsupported live-price question.
- [ ] Valid answer-digest receipt, tamper rejection and private backend denial.
- [ ] Sanitized correlation, bounded overload and explicit upstream failure.

### Debrief prompts

- Which identity has only the permissions needed for its operation?
- Why does receipt integrity not imply grounding or factual correctness?
- Which production risks remain: anonymous abuse, approximate throttles, quota, capacity, egress and costs?

### Handoff and cleanup

Retain redacted evaluation outcomes and explicit unresolved work, not tokens or chat transcripts.
Do not publish private solution or Finale files; release only reviewed public roots.
Exact-target cleanup or rollout requires separate authorization through the scenario owner.
