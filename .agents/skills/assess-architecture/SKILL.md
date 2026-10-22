---
name: assess-architecture
description: "Manual launcher for the reference architecture skill in the scenario context."
disable-model-invocation: true
---

# Assess the reference architecture

Load [the architecture skill](../../../.github/skills/az-scenario-architecture/SKILL.md)
directly in the scenario context with the scenario path and requirements.
Use [the workflow contract](../../../.github/skills/hack-builder-workflow/SKILL.md).
Do not require a hack package contract in Phase A. Return to the caller after
persisting the assessment and checks; do not start the next stage.
