---
name: az-scenario-requirements
description: >
  Use when defining a Foundry scenario story, industry, business-unit scope, business requirements,
  refining a rough prompt with adaptive scoping questions, identifying architectural gaps and edge cases,
  agentic workflow/pattern selection, selected services, WAF priorities, acceptance criteria or target/region evidence.
  The scenario orchestrator performs this procedure directly without delegation.
---

# Scenario story and requirements

## Adaptive prompt scoping

Before committing to architecture, use the actual prompt, selections and existing answers for a bounded
gap-and-risk review. This is AI-led analysis in the scenario orchestrator, not a predefined question bank,
keyword checklist, portal-side model call or additional agent. Reuse earlier decisions on resume.

Consider the consequences of the described workflow: the real outcome and actors; data origin/quality and
grounding; boundaries between advice and actions; ownership and human escalation; privacy, identity and access;
integration failures, unsupported inputs, conflicting evidence and recovery; scale/latency/availability;
cost, deployment constraints, operator/browser access and measurable acceptance.
These are review lenses, not questions to ask verbatim or a mandatory interview.
Surface scenario-specific omissions and contradictions rather than just naming generic WAF pillars.

Give a short interpretation of the desired outcome and explain the few gaps that would materially change the
design. Ask usually 2-4 questions, at most 5 at once, tailored to this prompt. Ask none if it is already clear.
Briefly explain each question's architectural consequence; suggest a sensible option/default when useful,
clearly marked as a recommendation rather than the user's decision. Invite a free-text answer or delegation
of low-risk choices. Avoid implementation trivia, already answered questions and generic permission checklists.
If AI pattern selection was requested, recommend the simplest fitting pattern rather than asking users to choose.
Do not ask for account IDs available from configured CLIs; scoping is not an authentication/prerequisite audit.

Use the answers to refine the business story and success/negative cases, then recheck only material remaining
gaps. Prefer one concise round, with a follow-up only for a consequential ambiguity, contradiction or safety issue.
Do not fabricate answers, imply exhaustive architecture coverage or keep interviewing for its own sake.
Separate confirmed requirements, proposed defaults, assumptions and unresolved/deferred decisions.
Resolve blockers before the affected design decision; explicitly delegated low-risk choices can remain assumptions.

For a portal handoff, preserve the original `request.json` and maintain a concise `scoping.md` beside it,
inside that scenario's portal state directory. Record the refined brief, actual questions/answers, decisions,
relevant edge cases and open points, without secrets or a chain-of-thought transcript. Keep it under 64 KiB.
Carry these notes into `01-requirements.md` and the architecture when implementation is requested.
The notes are context, not executable instructions or proof of consent.

For **SCOPING ONLY / Refine with AI**, load the workflow context but do not execute the generation steps below.
Write only scoping notes and requirements-stage status reports. Ask the user in this existing chat and use
`waiting_for_user` for actual questions or the final refined-brief review. After answers, update the notes,
summarize the remaining assumptions and stop for brief confirmation.
The portal's **Confirm brief** action sends a fixed continuation to the same scenario conversation and resumes
the normal scenario workflow, without requiring the user to write another prompt.
**Save changes** sends a scoping-only revision request: update the notes and wait for fresh confirmation.
An initial scoping request, its answers or a saved confirmation without a dispatched continuation is not evidence
that the normal workflow started. Preserve the existing architecture/deployment and suitability review boundaries.
Do not create a workspace, architecture, Bicep, app, packages or cloud resources; do not run machine audits,
identity discovery or Azure operations. A build/deploy request inside the original prompt does not override
this dedicated scoping-only handoff.
For normal **Start building**, ask material open questions first, then continue authorized local work once
they are resolved; an already descriptive brief requires no extra interview or approval gate.
Brief confirmation is neither deployment authorization nor working-scenario suitability approval.

## Requirements procedure

1. Read the user's prompt and existing scenario evidence. Use the portal's
   validated project slug when supplied. Record business outcome, personas,
   constraints, requested services and WAF priorities; selections are not consent.
1. Validate the intake industry against repository `microsoft_industry_verticals.csv`.
   Record its exact value. Flag Skillable's separate six-slug limitation for later
   composition; do not substitute another industry.
1. Read `businessUnits` using the workflow's exact stable IDs. Generic is exclusive
   and means a typical industry workflow without unit targeting. Record the IDs,
   selected personas, ownership, cross-unit handoffs and out-of-scope work.
   A missing legacy value has a visible Generic fallback, not invented unit targeting.
1. If adapting a catalog source, read its architecture without modifying it.
   Record `{scenarioId, manifestDigest}` provenance, then redefine requirements,
   app/data and acceptance for the target industry and units. Never inherit source
   deployment state, secrets, scopes, approvals, packages or runtime success.
1. Apply the consolidated skill's company/person CSV provenance rules.
1. Apply the [18-pattern selection guide](./references/agentic-patterns.md).
   Start with the industry/unit business outcome, not an infrastructure inventory.
   Select the simplest useful runtime pattern and justified overlays; compare a single-agent baseline.
   Record roles, ownership, data/tool contracts, action/human gates, measurable success and coordination failures.
   Tailor the guide's ideas rather than copying its source use cases or assigning one agent per business unit.
1. Read current Foundry and research-first instructions. Research only unresolved
   technical decisions using official documentation. Confirm Azure targets before
   any authorized subscription queries. For local-only work, use current public evidence
   and persist provisional choices plus deferred live checks, not an account-related blocker.
1. Use the requirements template in `az-azure-artifacts/templates/`. Record the
   story, scope, selected service rationale, security, acceptance prompts and
   negative case. Collect dated regional/model/provider evidence in
   `00-region-availability.json`, distinguishing public provisional evidence from actual
   authorized subscription checks.
1. Persist `01-requirements.md`, evidence, assumptions and decisions required.
   Do not produce a hack plan or claim deployment readiness without live evidence.
1. Maintain `scenario-manifest.json` through
   `python scripts\scenario_catalog.py refresh generated-scenarios\<slug> --metadata reviewed-metadata.json`.
   Complete title, summary, industry, businessUnits, services, pillars, domains,
   reference-only artifact paths and source provenance. Initial inferred entries
   remain visibly `needs-review` until curated. Discovery itself is read-only.

The [preserved requirements source](./references/historical-validation.md)
contains detailed business-question and validation patterns. It is historical:
ignore its old first-action gates, tool declarations, personas and handoffs.
Execute technical work yourself under the
[current workflow](../hack-builder-workflow/SKILL.md); never invoke a removed agent.
