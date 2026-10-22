---
name: generate-webapp
description: "Manual launcher for the .NET Foundry reference application skill."
disable-model-invocation: true
---

# Generate the reference application

Load [the application skill](../../../.github/skills/az-webapp-development/SKILL.md)
directly in the scenario context with the scenario path and industry.
Use [the workflow contract](../../../.github/skills/hack-builder-workflow/SKILL.md).
Build the real Foundry application and focused tests. Do not require a package
contract or derive learner code before approval. Return to the caller.
