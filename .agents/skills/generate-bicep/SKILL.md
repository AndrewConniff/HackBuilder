---
name: generate-bicep
description: "Manual launcher for canonical AVM-first reference infrastructure generation."
disable-model-invocation: true
---

# Generate reference Bicep

Load [the Bicep skill](../../../.github/skills/az-scenario-bicep/SKILL.md)
directly in the scenario context with the scenario path and architecture assessment.
Use [the workflow contract](../../../.github/skills/hack-builder-workflow/SKILL.md).
Generate and validate the reference infrastructure and both diagrams.
Do not generate hack packages or start a deployment. Return to the caller.
