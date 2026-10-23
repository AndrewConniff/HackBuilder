---
name: az-scenario-requirements
description: >
  Use when defining a Foundry scenario story, industry, business-unit scope, business requirements,
  agentic workflow/pattern selection, selected services, WAF priorities, acceptance criteria or target/region evidence.
  The scenario orchestrator performs this procedure directly without delegation.
---

# Scenario story and requirements

1. Read the user's prompt and existing scenario evidence. Use the portal's
   validated project slug when supplied. Record business outcome, personas,
   constraints, requested services and WAF priorities; selections are not consent.
1. Validate the intake industry against repository `microsoft_industry_verticals.csv`.
   Record its exact value. Flag Skillable's separate six-slug limitation for later
   composition; do not substitute another industry.
1. Read `businessUnits` using the workflow's exact stable IDs. Generic is exclusive
   and means a typical industry workflow without unit targeting. Record the IDs,
   selected personas, ownership, cross-unit handoffs and out-of-scope work.
   A missing legacy value has a visible Generic fallback, not invented unit targeting.
1. If adapting a catalog source, read its architecture without modifying it.
   Record `{scenarioId, manifestDigest}` provenance, then redefine requirements,
   app/data and acceptance for the target industry and units. Never inherit source
   deployment state, secrets, scopes, approvals, packages or runtime success.
1. Apply the consolidated skill's company/person CSV provenance rules.
1. Apply the [18-pattern selection guide](./references/agentic-patterns.md).
   Start with the industry/unit business outcome, not an infrastructure inventory.
   Select the simplest useful runtime pattern and justified overlays; compare a single-agent baseline.
   Record roles, ownership, data/tool contracts, action/human gates, measurable success and coordination failures.
   Tailor the guide's ideas rather than copying its source use cases or assigning one agent per business unit.
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
1. Maintain `scenario-manifest.json` through
   `python scripts\scenario_catalog.py refresh generated-scenarios\<slug> --metadata reviewed-metadata.json`.
   Complete title, summary, industry, businessUnits, services, pillars, domains,
   reference-only artifact paths and source provenance. Initial inferred entries
   remain visibly `needs-review` until curated. Discovery itself is read-only.

The [preserved requirements source](./references/historical-validation.md)
contains detailed business-question and validation patterns. It is historical:
ignore its old first-action gates, tool declarations, personas and handoffs.
Execute technical work yourself under the
[current workflow](../hack-builder-workflow/SKILL.md); never invoke a removed agent.
