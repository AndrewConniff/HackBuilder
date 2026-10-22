---
name: oilgas-field-ops-agent
description: "Manual oil-and-gas scenario input for the canonical Hack Builder workflow; this is a skill, not an agent."
disable-model-invocation: true
---

# Oil and gas scenario launcher

Extract the business scenario and requirements from
[the preserved input](../../../.github/skills/hack-builder-workflow/references/oilgas-legacy-input.md).
Ignore the archived orchestration/deployment directives.
Pass the scenario and current user overrides to `az-01-conductor`.
Follow [the workflow contract](../../../.github/skills/hack-builder-workflow/SKILL.md):
prepare locally, deploy only when authorized, prove the reference and stop for
explicit suitability approval. Composition is a separate user-driven context.
Team deployment is a separate explicit request.
