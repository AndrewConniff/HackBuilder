---
name: az-scenario-demonstration
description: >
  Use when creating a reference scenario demonstration, business walkthrough,
  runbook, audience talking points, screenshots or failure/recovery playbook.
  The scenario orchestrator performs the demonstration procedure directly.
---

# Demonstrate the working reference

1. Read the approved requirements, actual implementation, deployment summary
   and runtime evidence. A local-only design is not a deployed demonstration.
1. Use relevant consolidated demo patterns and artifact templates.
1. Write `demoguide/demoguide.md`: audience, business story, prerequisites,
   exact live app flow, expected grounded/tool behavior, observable negative
   case, timing, cost and limitations. Use real outputs, not fabricated success.
   Demonstrate the requirements' industry and `businessUnits` through the selected
   personas, app/data and cross-unit handoffs. Generic has no unit targeting.
   Follow the selected [agentic pattern](../az-scenario-requirements/references/agentic-patterns.md):
   demonstrate its useful business output, visible coordination/action evidence,
   required human decision and one bounded failure/recovery path. Do not substitute
   a resource inventory or believable text for actual runtime behavior.
1. Exercise the demonstration from the actual identity/network path within
   authorized scope. For private services, document operator entry, where the browser/CLI run and Azure user sign-in;
   demonstrate allowed private administration separately from the expected outside-network denial.
   A Run Command-only automation path is not proof of browser administration.
   Capture screenshots with Playwright when available and
   provide an explicitly labeled screenshot fallback, not fake live acceptance.
1. Persist checks and recovery commands. Present the complete scenario for
   suitability review and stop; do not compose hack challenges.

Use [preserved demonstration detail](./references/historical-demoguide.md)
for runbook patterns. Historical personas, tool declarations and handoffs are
inactive. Follow the [current workflow](../hack-builder-workflow/SKILL.md)
directly in the scenario context without delegation.
