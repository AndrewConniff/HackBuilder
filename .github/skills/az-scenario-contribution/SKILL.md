---
name: az-scenario-contribution
description: >
  Use only when the user explicitly requests GitHub publication or contribution
  of a completed scenario. Creates a standalone repository and registry PR
  directly through gh CLI; never invokes a contribution agent.
---

# Optional scenario publication

1. Confirm an explicit publication request, intended account, repository name,
   visibility and exact sanitized publication scope. This is separate from
   scenario approval, package authoring and event deployment.
1. Verify the active `gh` account. Inspect existing repository state and preserve
   user changes. Never publish credentials, private coach answers into public
   learner content, deployment state or internal operational evidence.
1. Follow the technical repository/registry steps in the
   [preserved contribution source](./references/historical-contribution.md).
   Old agent roles, tool declarations and handoffs are historical only; execute
   commands yourself. Stop on a missing account or publication decision.
1. Before drafting a PR, inspect the target repository's PR templates and
   preserve their headings/checklists. Run relevant documented validation and
   report exact commands/results or explicitly state what was not run.
1. Return repository/PR URLs and publication limitations. Never make publication
   an automatic continuation of the [hack workflow](../hack-builder-workflow/SKILL.md).
