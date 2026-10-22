---
name: az-scenario-architecture
description: >
  Use when designing the reference architecture, Azure SKUs, identity/data paths,
  WAF trade-offs, cost or service choices for a Foundry business scenario.
  Runs directly in the scenario orchestrator context, without specialist agents.
---

# Reference architecture

1. Read requirements, selected service constraints and current region evidence.
   If target evidence is unavailable, distinguish a provisional local design from
   a validated deployable design; return the exact decision needed.
1. Use current Microsoft Foundry guidance and AVM metadata. Prefer the simplest
   design meeting business, identity, networking, residency and WAF requirements.
   Explain requested services that are unnecessary or unavailable; do not silently
   substitute them. Distinguish Basic/Standard requirements explicitly.
1. Document resource/SKU choices, direct child Foundry project, real application
   invocation, data ownership, managed identity/RBAC, operations and cost.
1. Write `02-architecture-assessment.md` using the artifact template.
   Capture service alternatives, WAF trade-offs and unresolved decisions.
1. Use `az-azure-diagrams` directly for diagrams and persist all decisions.
   This is the complete private reference architecture, not a learner starter.

Read [preserved technical detail](./references/historical-architecture.md)
for assessment patterns. Its old roles, tool declarations and handoffs are
historical only. Execute directly using the
[workflow contract](../hack-builder-workflow/SKILL.md), without delegation.
