---
name: az-azure-diagrams
description: >
  Use when generating architecture or runtime diagrams, or an explicitly
  requested standalone Azure diagram. Uses the existing Python diagram library
  and references directly; no diagrammer agent or extra orchestration pass.
---

# Architecture and runtime diagrams

1. Read requirements, architecture and actual IaC. Apply Python and Markdown
   instructions and consolidated diagram patterns.
1. Inspect this skill's existing scripts/references before creating a new source.
1. Generate `03-architect-diagram.png` and `04-runtime-diagram.png` with matching
   Python sources, labeled identity/data paths and resource boundaries.
   Standalone requests may use a user-specified filename and scope.
1. Verify diagram generation, readability and agreement with the implementation.
   Embed images with meaningful alt text; do not claim diagrams prove deployment.

Use [preserved diagram patterns](./references/historical-diagrammer.md)
as technical reference only. Its retired tools, agent roles and handoffs do not
authorize delegation. The scenario orchestrator performs this procedure directly
under the [workflow contract](../hack-builder-workflow/SKILL.md).
