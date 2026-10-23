---
name: az-scenario-bicep
description: >
  Use when planning or generating governance-aware AVM-first Bicep, azd wiring,
  identity/RBAC, policy checks or local infrastructure validation for a reference.
  The scenario orchestrator implements directly; deployment is a separate skill.
---

# Reference infrastructure

1. Read requirements, architecture, region evidence, Bicep/Foundry instructions,
   consolidated patterns and the applicable artifact templates.
1. Discover governance only within authorized Azure scope. Verify current AVM
   module metadata, schemas and versions. Never invent policy/capacity evidence.
1. Persist `04-implementation-plan.md`, then implement `infra/` and `azure.yaml`
   with managed identity, least privilege, secure networking and documented
   parameters/outputs. Retain user changes and existing deployed resource names.
1. Wire real project/model/app outputs, runtime fixture installation and hooks.
   Use `az-webapp-development` directly for application integration.
   Follow the workflow's
   [scenario-owned application identity setup](../hack-builder-workflow/SKILL.md#scenario-owned-application-identity-setup).
   Generate idempotent identity setup/verification and azd configuration wiring for required registrations.
   Distinguish directory operations from ARM/Bicep what-if; plan their authorization and real ID capture
   without asking the user to supply IDs for objects that this solution is intended to create.
   Treat solution-created IDs, endpoints and installation receipts as deployment outputs, not user inputs.
   Wire their producer/consumer ordering in the azd lifecycle: authorized identity setup, output capture,
   dependent provisioning/configuration, then real authentication tests. Verify current supported resource
   providers/hooks before choosing the mechanism; ARM Bicep does not automatically manage Graph objects.
   Local-only scaffolding must remain buildable without pre-existing tenant objects.
1. Use `az-azure-diagrams` for architecture and runtime diagrams in this context.
1. Run `az bicep build` and `az bicep lint` for local validation when tooling is
   available. Prepare what-if commands/targets; Azure execution needs its own
   authorization. Record exact results and blockers before proceeding.

The [preserved infrastructure procedure](./references/historical-bicep.md)
retains governance and implementation detail. Historical roles, tool declarations
and handoffs are not active instructions. Perform the full procedure yourself;
use `az-azure-deploy` only within the authorized
[workflow phase](../hack-builder-workflow/SKILL.md), never a deployment agent.
