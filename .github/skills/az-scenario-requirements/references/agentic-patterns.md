# Agentic business scenario patterns

Use this guide during requirements and architecture selection, then carry the chosen behavior into
implementation, runtime evidence and post-approval hack composition. It is guidance, not a prescribed architecture.
Azure resources support the business workflow; provisioning resources alone is not the scenario's outcome.

These are **Foundry solution runtime** patterns, not permission to add Copilot agents, delegate implementation,
or bypass design confirmation, deployment consent or suitability approval. FBC Builder still has two agent contexts.

## Source and technical status

This original selection guide draws on the user-supplied
[Enterprise Agentic System Patterns 2026](../../../../Enterprise_Agentic_System_Patterns_2026.pdf),
dated 22 October 2026: selection/taxonomy on PDF pages 2-4, chapters on pages 5-58, controls on pages 59-60.
Page references below use the PDF page number. The PDF is background reading, not a runtime or learner dependency.
Do not reproduce its chapters, illustrations or full use-case specifications in generated packages.

The 18 labels describe different dimensions: control flow, triggering, shared state and human governance.
They are not 18 native Foundry features, nor do all require multiple agents.
Do not import another vendor's runtime merely because the report mentions it.

Official guidance checked on 2026-10-22:

- [Azure agent design patterns][architecture] recommends the lowest adequate complexity, often one agent with tools.
- [Agent Framework orchestrations][orchestrations] documents sequential, concurrent, handoff, group chat and Magentic.
- [Workflow human interaction][human] describes request/response mechanisms; production durability and authorization
  still require an explicitly designed and tested implementation.

At scenario creation, verify the current Foundry APIs, SDK/language, hosting, persistence, feature status,
region and tool support. Distinguish Foundry Agent Service capabilities from application-hosted orchestration
that invokes Foundry agents. Record dated official evidence in the normal requirements/architecture artifacts.
A conceptual pattern is not evidence that its SDK, low-code route or hosted implementation is supported.

## Select from the business problem

1. Read the prompt, exact industry, selected `businessUnits`, personas and requested outcome.
   Identify the trigger, business artifact or action, owner and measurable improvement over the current process.
1. Tailor authoritative documents, entity relationships, terminology, access boundaries and exceptional cases
   to that industry and those units. Generic means an industry workflow without department targeting.
1. Compare a single-agent tool loop with plausible alternatives. Default to one primary pattern;
   add supporting patterns only for an identified dependency, quality, ownership or risk requirement.
   Do not attempt to demonstrate all 18 or create one agent per selected unit.
1. Explain why the chosen pattern beats the simpler alternative for this scope.
   Prefer bounded, observable behavior that can later be learned within a three-hour hack.
   A multi-agent choice needs real role separation, independent evidence, ownership transfer or another concrete gain.
1. Record the selection and runtime contract in the existing templates before design confirmation.
   For reuse, reevaluate the source pattern for the new business scope rather than inheriting its suitability.
1. Implement and test that contract. Keep deterministic calculations, identity checks, entitlements and action limits
   in code/policy, not in a model's judgment. Never represent a static canned response as an agent execution.

## Industry and business-unit prompts

These are starting questions, not mappings from a unit to a mandatory pattern.
Combine multiple selected units into one process with explicit ownership and data handoffs.
Keep the industry's constraints: an energy work order, retail return and public-sector request are not interchangeable.

| Selected unit | Business question to tailor | Candidate starting point |
| --- | --- | --- |
| `executives` | Which evidence changes an industry-specific investment decision? | Concurrent review; synthesis |
| `it` | How should an incident be classified and transferred to its accountable responder? | Routing; handoff |
| `operations` | How does an exception become a reviewed corrective-work draft? | Sequential; approval |
| `communications` | Is an incident notice substantiated and cleared for release? | Evaluator-optimizer; approval |
| `executive-assistant` | Which dependencies constrain an industry meeting or visit plan? | Planner-executor |
| `legal` | Which obligations or clause deviations need an authorized reviewer? | Sequential; evaluator |
| `hr` | Which policy evidence supports an onboarding request without exposing employee data? | Single-agent tools |
| `business-manager` | Who owns the next step in a branch/site exception review? | Supervisor; handoff |
| `finance` | Which invoice/cost discrepancies need investigation before an adjustment? | Sequential; approval |
| `sales` | Which eligibility and pricing constraints shape a proposal? | Routing; planner-executor |
| `marketing` | Which campaign claims are supported by approved industry evidence? | Evaluator-optimizer |
| `generic` | Which typical industry workflow has a useful result and exception? | Simplest adequate pattern |

For example, energy plus `finance` and `operations` might investigate maintenance-cost variance:
validate a work-order packet, gather cost and asset-history evidence, draft a proposed correction, then request review.
Use sequential stages as the baseline; add concurrency only if the evidence gathering is genuinely independent.
Amounts come from deterministic calculations. Human authorization protects any committed adjustment.
Synthetic fixtures include a normal packet, missing evidence, an access-denied record and a repeated action request.
For retail, rebuild the entities and policies around its business process rather than renaming the energy dataset.

## Pattern catalog

### 01. Single-Agent Tool Loop

PDF pp. 5-7. One bounded agent chooses among permitted retrieval/action tools.
Use when a coherent domain can meet the outcome without coordination overhead.
Limit calls and elapsed time; distinguish draft/read operations from approved writes; surface tool failure explicitly.

### 02. Sequential / Pipeline

PDF pp. 8-10. Ordered stages consume validated outputs from preceding stages.
Use for intake, evidence checking and a resulting business draft with real dependencies.
Define stage schemas, durable checkpoints where needed, and the retry/compensation boundary.

### 03. Concurrent / Fan-Out-Fan-In

PDF pp. 11-13. Independent branches examine different evidence before a reducer combines findings.
Use when parallel work improves a measured latency or evidence-coverage target.
Cap concurrency and branch budgets; specify disagreement, timeout and incomplete-result behavior.

### 04. Routing / Triage

PDF pp. 14-16. A classifier or policy chooses an appropriate destination.
Use for distinct intents, sensitivity tiers or service responsibilities, not merely extra agent names.
Test route accuracy, uncertainty and a safe fallback; enforce entitlement before destination access.

### 05. Handoff / Transfer of Control

PDF pp. 17-19. Active ownership moves to another authorized runtime agent or human.
Use when responsibility changes during a case or conversation; a route chosen at intake alone is not a handoff.
Transfer a minimal typed summary, preserve case identity, and stop cycles or unauthorized transfers.

### 06. Moderated Group Chat

PDF pp. 20-22. A moderator coordinates participants reviewing a common case.
Use when contrasting views and unresolved objections must be visible in the outcome.
Constrain shared data, speaker turns and completion; record dissent instead of manufacturing consensus.

### 07. Magentic Dynamic Collaboration

PDF pp. 23-25. A manager adapts specialist participation and revises a progress ledger for open-ended work.
Use only when a fixed sequence or inspectable planner-executor is insufficient.
Bound replans, stalls and spending; require plan review where appropriate and retain evidence behind conclusions.

### 08. Supervisor / Hierarchical Delegation

PDF pp. 26-28. A single runtime entry point requests scoped results from known specialists.
Use when several bounded business domains need one accountable response.
Keep policy at the supervisor, minimize specialist context, and test tool/data permissions for every role.

### 09. Orchestrator-Workers

PDF pp. 29-31. Runtime decomposition creates assignments based on the input's size or structure.
Use for variable-sized evidence packets rather than a fixed panel of specialists.
Bound assignments, queues and total cost; reconcile duplicate, failed and missing partitions.

### 10. Planner-Executor

PDF pp. 32-34. An explicit plan separates proposed steps from execution.
Use when business users must inspect dependencies or approve consequential actions.
Validate plan structure and decision rights; checkpoint execution and reapprove materially changed plans.

### 11. Deterministic Loop

PDF pp. 35-37. A programmatic condition controls repeat-until processing.
Use when completeness or correctness can be machine-checked, not judged by conversational agreement.
Enforce an iteration/time cap, idempotency and a failure outcome when the condition remains unmet.

### 12. Evaluator-Optimizer / Reflection

PDF pp. 38-40. A producer revises output in response to an explicit evaluation rubric.
Use for evidence-backed narrative quality where deterministic validation is insufficient.
Separate generation from evaluation, cap revisions, and test a held-out case;
self-approval is not independent assurance.

### 13. Mixture of Agents

PDF pp. 41-43. Diverse candidate outputs feed one or more synthesis layers.
Use only if diversity improves a measured high-value outcome enough to justify extra calls.
Bound layers/candidates, preserve provenance and disagreements, and do not mistake majority agreement for truth.

### 14. Event-Driven / Reactive Agents

PDF pp. 44-46. An authorized event or stream record triggers a bounded agent workflow.
Choose discrete-event versus stream infrastructure from delivery/order requirements, not from the pattern name.
Test deduplication, idempotent actions, late/replayed events, retry limits and a dead-letter/recovery path.

### 15. Blackboard / Shared Workspace

PDF pp. 47-49. Contributors coordinate through a shared evidence/task artifact rather than one conversation.
Use when the case evolves over time and persisted findings must remain inspectable.
Specify typed/versioned writes, provenance, access isolation and conflict resolution;
shared storage alone is insufficient.

### 16. Swarm / Peer-to-Peer

PDF pp. 50-52. Authorized peers coordinate without one fixed central decision-maker.
Use cautiously when decentralized availability or ownership is a real requirement.
Allowlist identities/capabilities, limit transfers and global work, and provide termination and a human recovery owner.

### 17. Human-in-the-Loop (HITL)

PDF pp. 53-55. An attributable human decision gates a risky or ambiguous business action.
This is an overlay on another pattern, not a requirement to add another model agent.
Persist the exact proposal/version and authorized decision;
support rejection, edit, cancellation, expiry and safe resume.
Do not reuse a decision for a changed proposal. Business approval never grants FBC Builder deployment consent.

### 18. Adaptive Hybrid / Composite Orchestration

PDF pp. 56-58. An explicit policy composes a small set of patterns for different work or risk classes.
Use only when one primary pattern plus a simple overlay cannot satisfy the confirmed scope.
Keep common state/identity contracts and one trace; test transitions and fallback without silently changing controls.

## Required scenario record and acceptance

Use `01-requirements.md` and `02-architecture-assessment.md`, not a separate package plan before approval.
Record:

- Selected pattern IDs/names, optional overlays, business justification and rejected simpler alternative.
- Exact industry, `businessUnits`, personas, trigger, expected business output and excluded actions.
- Runtime roles and ownership; entry point; typed input/output, handoff and state contracts;
  context deliberately withheld.
- Authoritative grounding/tool sources, synthetic fixture schemas and company/person CSV provenance.
- Read/draft/commit permissions, managed identities, deterministic policies and human decision rights.
- Persistence/recovery strategy and concrete limits for time, calls/tokens, retries, rounds, concurrency and cost.
- Positive, ambiguous and failing cases with numerical targets or explicit pass/fail conditions.
- Current official implementation evidence, feature limitations and any still-required user decision.

The app/demo must expose the useful business result and an inspectable execution summary, not hidden chain-of-thought.
Trace correlation, agent/tool identities, stage/handoff decisions, evidence references and action receipts;
redact sensitive payloads. Verify at least one coordination-specific failure as well as the ordinary success path.
Examples include a rejected route, missing branch, revision cap, stale approval, conflicting write or duplicate event.
Do not claim coordination worked solely because the final answer sounds plausible.

For a new pattern-scoped reference, index the actual runtime checks as `checks.agenticWorkflow`
in `scenario-validation.json`, with detailed commands/results in the deployment summary.
Local tests or a design diagram do not satisfy deployed-runtime acceptance.
Existing scenarios are not automatically rewritten, reapproved or certified by adding this guide.

## Post-approval hack use

After the normal approval check, derive one progressive agent-building experience from the approved runtime behavior.
Teach the smallest useful coordination increment, retain the last working checkpoint and make success observable.
Do not add unrelated patterns to fill challenges or swap the approved architecture to match this catalog.
Learners receive business outcomes, constraints, fixtures and progressive hints, not a completed specialist roster,
solution graph or coach implementation. Private notes explain pattern trade-offs, expected traces and recovery.
Stay within the existing time budget and low-code/code-first contract; verify actual route support.
If the approved behavior cannot fit those constraints,
request a scope/reapproval decision rather than inventing a route.

[architecture]: https://learn.microsoft.com/azure/architecture/ai-ml/guide/ai-agent-design-patterns
[orchestrations]: https://learn.microsoft.com/agent-framework/workflows/orchestrations/
[human]: https://learn.microsoft.com/agent-framework/workflows/human-in-the-loop
