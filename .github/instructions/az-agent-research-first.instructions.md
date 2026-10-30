---
description: "Evidence-first implementation with bounded research and reuse across FBC Builder phases"
applyTo: "**/*.agent.md, **/generated-scenarios/**/*.md, **/.github/skills/**/SKILL.md"
---

# Evidence-first implementation

Before changing artifacts, inspect required inputs, relevant existing patterns,
the applicable output template and technical standards. Query current official
Microsoft documentation for new or changed Azure decisions; verify live
subscription capacity before deployment. Never guess SDKs, models or quotas.

## Reuse and scope

- Read only the skill sections/references needed for the assigned task.
- Reuse dated evidence from the preceding step when its inputs are unchanged.
  Research unresolved questions, not the entire scenario again at each step.
- Record sources, timestamps, decisions and rejected alternatives in their
  owning artifact so subsequent steps can consume them.
- A documentation/customization edit does not require Azure login or a new
  scenario deployment. Local technical scenario generation requires current public service
  evidence; subscription quota/capacity evidence is required before authorized deployment,
  not before provisional local design.
- Both canonical agents perform all work in their own context through skills.
  Do not invoke research or implementation subagents, fan out specialists or
  turn historical skill references into delegation instructions.
- When required context is missing, report the exact gap and obtain the
  necessary decision; do not invent requirements to avoid a checkpoint.

## Workflow and failure boundaries

Read the [workflow contract](../skills/hack-builder-workflow/SKILL.md) for hack
work. Never create challenge plans or packages before explicit scenario approval.
The scenario orchestrator owns implementation and deployment procedures.
The composition agent owns approved-reference authoring only. Neither delegates.

Persist completed work and its validation before returning. Report material
blockers promptly. Deployment is required to prove the reference scenario, but
never bypass authentication, authorization, policy or failed preflight gates.
Record failures honestly, ask for the needed decision, and do not label an
undeployed or failing scenario as complete.
