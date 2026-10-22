---
name: az-scenario-requirements
description: >
  Use when defining a Foundry scenario story, industry, business requirements,
  selected services, WAF priorities, acceptance criteria or target/region evidence.
  The scenario orchestrator performs this procedure directly without delegation.
---

# Scenario story and requirements

1. Read the user's prompt and existing scenario evidence. Use the portal's
   validated project slug when supplied. Record business outcome, personas,
   constraints, requested services and WAF priorities; selections are not consent.
1. Validate the intake industry against repository `microsoft_industry_verticals.csv`.
   Record its exact value. Flag Skillable's separate six-slug limitation for later
   composition; do not substitute another industry.
1. Apply the consolidated skill's company/person CSV provenance rules.
1. Read current Foundry and research-first instructions. Research only unresolved
   technical decisions using official documentation. Confirm Azure targets before
   any authorized subscription queries. For local-only work, use current public evidence
   and persist provisional choices plus deferred live checks, not an account-related blocker.
1. Use the requirements template in `az-azure-artifacts/templates/`. Record the
   story, scope, selected service rationale, security, acceptance prompts and
   negative case. Collect dated regional/model/provider evidence in
   `00-region-availability.json`, distinguishing public provisional evidence from actual
   authorized subscription checks.
1. Persist `01-requirements.md`, evidence, assumptions and decisions required.
   Do not produce a hack plan or claim deployment readiness without live evidence.

The [preserved requirements source](./references/historical-validation.md)
contains detailed business-question and validation patterns. It is historical:
ignore its old first-action gates, tool declarations, personas and handoffs.
Execute technical work yourself under the
[current workflow](../hack-builder-workflow/SKILL.md); never invoke a removed agent.
