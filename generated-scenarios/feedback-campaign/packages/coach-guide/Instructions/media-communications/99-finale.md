---
lab:
  title: "Finale"
  module: "Adatum campaign listener"
  description: "Private coaching answers and evidence boundaries"
  duration: "20 minutes"
  level: "200"
  islab: true
  primarytopics: "Foundry, Media & Communications, sales, marketing"
  audience: coach
  isfinale: true
---

# Finale

Private guidance. Learner copies above are byte-identical; this page is not a sixth build challenge.

## Challenge 0 — Secure Foundation

**Objective and expected outcome**

Expected answer: one isolated Foundry project/model using scoped identity access; a real response ID
and a permission denial. No key fallback. Empty starter is intentional, not a broken application.

**Completion evidence**

- One real authenticated model response ID with no keys in source.
- A real permission denial and a working retry after restoring intended access.

**Coach talking points**

Explain Marketing ownership and Sales recovery handoff. Keep native interpretation separate from authority.
Use the full private reference only to diagnose, not to replace the learner's design decisions.

**Common blockers and recovery**

Check explicit destination access, then the last working prompt and source ID.
For action issues inspect durable state, role, revision and queue scope before retrying.
Do not add Entra login, broad RBAC or another architecture.

**Hint escalation**

1. Start with one synthetic sentence, not the whole application.
2. Check the selected destination and the caller's project-scoped data role.
3. Ask the organizer to inspect the exact access denial; never fall back to a pasted key.

**Fallback checkpoint**

Keep the status/fixture checks. Ask the organizer to repair scoped access or provide an authorized
isolated foundation. A saved response is diagnostic only; resume real inference before Challenge 1 completes.

**Demo and debrief prompts**

Ask what was observed, what was mocked and which unit owns the next action.
Ask why queue acceptance is not external delivery.

**Security and governance reminders**

Use synthetic contacts, destination-only private credentials and scoped managed identity.
Keep coach ControlAdmin access separate; no rule proposal becomes active without explicit human promotion.

## Challenge 1 — Build the MVP

**Objective and expected outcome**

Expected answer: campaign-listener native prompt agent returns source-linked interpretation/draft.
The app/adapter, not the model, validates finite normalized vectors. Never let the model send or promote.

**Completion evidence**

- One native prompt-agent response ID by the halfway checkpoint.
- Validated source-linked sentiment, draft and assessment; no action executed.
- The earlier authenticated model request still passes.

**Coach talking points**

Explain Marketing ownership and Sales recovery handoff. Keep native interpretation separate from authority.
Use the full private reference only to diagnose, not to replace the learner's design decisions.

**Common blockers and recovery**

Check explicit destination access, then the last working prompt and source ID.
For action issues inspect durable state, role, revision and queue scope before retrying.
Do not add Entra login, broad RBAC or another architecture.

**Hint escalation**

1. Keep interpretation separate from action authority.
2. Retain sourceId and one raw model response before adding schema constraints.
3. Validate each vector independently and reject invalid output visibly.

**Fallback checkpoint**

Keep the first real response and its exact prompt. Defer optional schema polish; preserve the source ID
and a valid draft so Challenge 2 can add policy. Do not replace inference with canned success.

**Demo and debrief prompts**

Ask what was observed, what was mocked and which unit owns the next action.
Ask why queue acceptance is not external delivery.

**Security and governance reminders**

Use synthetic contacts, destination-only private credentials and scoped managed identity.
Keep coach ControlAdmin access separate; no rule proposal becomes active without explicit human promotion.

## Challenge 2 — Ground It

**Objective and expected outcome**

Expected answer: campaign-policy-v1 says no refund/discount entitlement; supply it each invocation
with source and rule snapshot. Exact clause references are prompt-grounding evidence, not native citations.

**Completion evidence**

- campaign-04 response names campaign-policy-v1 and a supporting clause.
- campaign-09 cannot invent a refund or change rules.
- The original MVP response and score validation still pass.

**Coach talking points**

Explain Marketing ownership and Sales recovery handoff. Keep native interpretation separate from authority.
Use the full private reference only to diagnose, not to replace the learner's design decisions.

**Common blockers and recovery**

Check explicit destination access, then the last working prompt and source ID.
For action issues inspect durable state, role, revision and queue scope before retrying.
Do not add Entra login, broad RBAC or another architecture.

**Hint escalation**

1. The policy does not authorize subscription changes or refunds.
2. Source text is data even when it says 'ignore your rules'.
3. Use an exact policy clause as evidence; never manufacture a native citation.

**Fallback checkpoint**

Keep the working MVP prompt, add the policy verbatim as context and identify a supporting clause manually.
Defer optional retrieval UI; retain the successful response for the action increment.

**Demo and debrief prompts**

Ask what was observed, what was mocked and which unit owns the next action.
Ask why queue acceptance is not external delivery.

**Security and governance reminders**

Use synthetic contacts, destination-only private credentials and scoped managed identity.
Keep coach ControlAdmin access separate; no rule proposal becomes active without explicit human promotion.

## Challenge 3 — Give It Tools

**Objective and expected outcome**

Expected answer: deterministic positive-first routing; positive >=0.80 auto, otherwise negative >=0.89
ProductManager, rest ConflictResolutionSpecialist. Tables hold immutable snapshot and pending state;
authenticated explicit edited send writes a durable outbox and deterministic reply ID to Service Bus.
Wrong role returns 403; stale/duplicate returns 409. The action is application-hosted, not a native tool.

**Completion evidence**

- A durable human pending record shows the source and snapshot; an authorized edited send has a real queue receipt.
- Wrong-role and duplicate requests fail without a second side effect.
- Grounded inference still works; queue acceptance is not external delivery.

**Coach talking points**

Explain Marketing ownership and Sales recovery handoff. Keep native interpretation separate from authority.
Use the full private reference only to diagnose, not to replace the learner's design decisions.

**Common blockers and recovery**

Check explicit destination access, then the last working prompt and source ID.
For action issues inspect durable state, role, revision and queue scope before retrying.
Do not add Entra login, broad RBAC or another architecture.

**Hint escalation**

1. An agent draft is not authorization to send.
2. Persist the human checkpoint and stable correlation ID before a side effect.
3. Evaluate positive first; make a second send conflict rather than publish again.

**Fallback checkpoint**

Keep the grounded agent read-only and the pending human record. Pair with the adapter owner to complete
one authorized send; simulated receipts are not completion. Continue prompt evaluations while action repair proceeds.

**Demo and debrief prompts**

Ask what was observed, what was mocked and which unit owns the next action.
Ask why queue acceptance is not external delivery.

**Security and governance reminders**

Use synthetic contacts, destination-only private credentials and scoped managed identity.
Keep coach ControlAdmin access separate; no rule proposal becomes active without explicit human promotion.

## Challenge 4 — Harden & Demo

**Objective and expected outcome**

Expected answer: exact boundary tests, campaign-04 fallback, actual receipt, restart persistence and
denials. campaign-03 was >=89% negative in reference evidence. New versions are immutable;
ControlAdmin explicitly promotes with ETag and can roll back the active pointer. No model promotion.
Local provider failure/retry tests do not establish live outage/DLQ injection, which was not run.

**Completion evidence**

- Three route outcomes plus exact 0.80/0.89 boundaries have inspectable evidence.
- Restart, stale edit, wrong role and duplicate behavior are recorded.
- Proposed product-aspect/80%-negative changes remain inactive until explicit human promotion.
- The demo distinguishes measured runtime results, mocked failures and untested cases.

**Coach talking points**

Explain Marketing ownership and Sales recovery handoff. Keep native interpretation separate from authority.
Use the full private reference only to diagnose, not to replace the learner's design decisions.

**Common blockers and recovery**

Check explicit destination access, then the last working prompt and source ID.
For action issues inspect durable state, role, revision and queue scope before retrying.
Do not add Entra login, broad RBAC or another architecture.

**Hint escalation**

1. Separate deterministic threshold tests from variable model outputs.
2. The mixed campaign-03 fixture actually scored highly negative in the reference.
3. Use neutral campaign-04 for fallback; keep proposed rules separate from the active snapshot.

**Fallback checkpoint**

Freeze the last working agent/action checkpoint and demo only verified paths.
List failed or unrun tests explicitly; never label a pending action or mocked outage as live success.

**Demo and debrief prompts**

Ask what was observed, what was mocked and which unit owns the next action.
Ask why queue acceptance is not external delivery.

**Security and governance reminders**

Use synthetic contacts, destination-only private credentials and scoped managed identity.
Keep coach ControlAdmin access separate; no rule proposal becomes active without explicit human promotion.

## Event wrap-up

Use 20 minutes for demos and debrief; build time remains 150 minutes.
Ask each team for one success, one denial and one limitation.
No deployment, publication, provider integration or production suitability is implied.
Reference runtime acceptance is distinct from this phase's local package validation.

Use a three-minute sequence per selected demo: source and grounded draft, accountable
Marketing-to-Sales handoff, then an unsafe action denial. Keep the event demo/debrief
block within 20 minutes. Re-run the foundation/MVP response before the action demo.
Review least-privilege roles and ask which evidence is local-only versus live.
Privately hand over prompts, tests and non-secret traces; keep administrator access
and private destination credential files outside learner output.
Do not delete resources or revoke shared assignments as part of this local release.
Any later cleanup requires the authorized event owner to review exact disposable
destination groups, retention needs and credential disposal. Production channel
integration, scaling and outage/DLQ tests are follow-up work, not completed outcomes.
