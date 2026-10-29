---
name: az-scenario-architecture
description: >
  Use when designing the reference architecture, Azure SKUs, identity/data paths,
  agentic runtime patterns, WAF trade-offs, cost or service choices for a Foundry business scenario.
  Runs directly in the scenario orchestrator context, without specialist agents.
---

# Reference architecture

1. Read requirements, selected service constraints and current region evidence.
   If target evidence is unavailable, distinguish a provisional local design from
   a validated deployable design; return the exact decision needed.
   Public regional availability is not subscription eligibility. Local-only architecture remains provisional.
   As soon as exact-target read-only preparation is authorized, validate the whole design against that subscription:
   exact service/SKU, required zones/features, model quota, provider restrictions and usable quota headroom.
   Read and produce the subscription matrix in `00-region-availability.json` before calling a region deployable.
   Use the workflow's [subscription regional readiness](../hack-builder-workflow/SKILL.md#subscription-regional-readiness).
1. Trace industry and `businessUnits` into personas, data ownership, app workflows,
   handoffs and acceptance. Generic means an industry workflow without unit targeting.
   For adaptations, source architecture is read-only guidance, not inherited
   deployment state, scopes, approvals or runtime evidence. Confirm the new target design.
1. Use current Microsoft Foundry guidance and AVM metadata. Prefer the simplest
   design meeting business, identity, networking, residency and WAF requirements.
   Explain requested services that are unnecessary or unavailable; do not silently
   substitute them. Distinguish Basic/Standard requirements explicitly.
1. Review the selected [agentic pattern](../az-scenario-requirements/references/agentic-patterns.md)
   against the industry/unit outcome and simpler alternative. Define runtime roles,
   typed handoffs/state, permission boundaries, deterministic policies, human checkpoints,
   termination/budgets and failure recovery. Distinguish native Foundry features from
   app-hosted orchestration invoking Foundry; verify actual SDK/language and low-code support.
   Supporting Azure resources serve this behavior, not an architecture-only demonstration.
1. Document resource/SKU choices, direct child Foundry project, real application
   invocation, data ownership, managed identity/RBAC, operations and cost.
   Apply [sample application accounts and Azure resource access](
   ../hack-builder-workflow/SKILL.md#sample-application-accounts-and-azure-resource-access):
   local app accounts, separate private participant/coach access guides, no consent-dependent Entra login,
   workload managed identities and scoped deploying-admin control/data-plane RBAC for full acceptance.
   Treat [deployment-user full scenario access](
   ../hack-builder-workflow/SKILL.md#deployment-user-full-scenario-access) as a hard design requirement.
   Record the deployment-user access matrix in `02-architecture-assessment.md` for every resource/data component,
   covering resource administration and full data read/write/manage access, not only app-required operations.
   Include IoT device registry/twin operations when applicable, exact scoped roles/grants, identity resolution,
   management-network reachability, grant authority and user-credential acceptance probes.
   Apply the workflow's
   [scenario-owned application identity setup](../hack-builder-workflow/SKILL.md#scenario-owned-application-identity-setup).
   Resolve necessary SPA/API registrations, ownership, scopes/roles, redirects and assignment policy here.
   Dedicated registrations are only for explicitly required non-default integrations, not sample-app login.
   Record directory installation permissions alongside Azure dependencies; do not defer routine identity
   implementation choices into repeated portal business decisions.
   Separate pre-existing integration inputs from deployment-generated outputs such as client IDs and endpoints.
   Plan dependency ordering so creation produces these values automatically; do not make new registrations'
   IDs or administrator receipts prerequisites for completing architecture or independent read-only preparation.
1. For secured workloads, design
   [private-workload management access](../hack-builder-workflow/SKILL.md#private-workload-management-access)
   before implementation. Recommend a concrete operator/automation execution path, not just private endpoints.
   Default to a private management VM with Azure Bastion or approved VPN access unless an existing equivalent
   operator environment is verified. Specify where the operator's browser and CLI run, VM sign-in,
   Azure user sign-in, private DNS/routing, tools and full resource/data administration acceptance.
   A runner or Run Command-only VM does not satisfy human browser/CLI access.
   Compare a supported restricted public-IP exception with a connected runner or private management VM/Bastion;
   preserve private-only requirements. Include bootstrap ordering, DNS, identity, lifecycle and full costs in the
   existing design review. Document how azd publishing, agent initialization and tests actually use that path.
   Apply [authorization continuity and consolidated review](
   ../hack-builder-workflow/SKILL.md#authorization-continuity-and-consolidated-review):
   prepare the preferred access-path repair and cost locally before requesting missing authority.
   Do not ask permission just to design or price it. Mark unauthorized discovery pending rather than querying,
   assuming an existing runner works, or blocking independent local preparation.
   Apply [setup versus hack architecture](
   ../hack-builder-workflow/SKILL.md#setup-architecture-versus-hack-architecture):
   document the complete setup/operator architecture separately from the hack/learner architecture.
   Do not preprovide the full management setup to learners by default or create a hack plan before approval.
   Post-approval composition may turn private access into a bounded challenge without removing coach access.
1. Write `02-architecture-assessment.md` using the artifact template.
   Capture service alternatives, WAF trade-offs and unresolved decisions.
1. Use `az-azure-diagrams` directly for diagrams and persist all decisions.
   This is the complete private reference architecture, not a learner starter.

Read [preserved technical detail](./references/historical-architecture.md)
for assessment patterns. Its old roles, tool declarations and handoffs are
historical only. Execute directly using the
[workflow contract](../hack-builder-workflow/SKILL.md), without delegation.
