---
name: design-diagram
description: "Manual standalone diagram request; not an extra FBC Builder pipeline stage."
disable-model-invocation: true
---

# Design an ad-hoc diagram

Load [the diagram skill](../../../.github/skills/az-azure-diagrams/SKILL.md)
directly for this explicitly requested task. The scenario orchestrator also uses
this skill for the normal workflow's two diagrams; do not launch another agent.
Use [the workflow contract](../../../.github/skills/hack-builder-workflow/SKILL.md)
for phase boundaries. Return the requested diagrams without continuing a pipeline.
