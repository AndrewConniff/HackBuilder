---
description: "Mandatory current Microsoft Foundry architecture, research, region, project, model, agent, and validation rules"
applyTo: "**/*.agent.md, **/.github/skills/**/SKILL.md, **/generated-scenarios/**/*.bicep, **/generated-scenarios/**/*.md"
---

# Microsoft Foundry Instructions

Use these rules whenever a scenario includes Microsoft Foundry, Foundry Models,
Foundry Agent Service, Azure OpenAI, agents, model deployments, or an AI chatbot.

## Research Current Technology First

Foundry changes quickly. Do not rely on remembered product names, resource
models, SDK versions, API versions, model versions, regions, or quotas.

Before requirements are finalized or architecture is selected:

1. Search current Microsoft Learn documentation for the requested Foundry
   capabilities, project model, SDK, agents API, model, and deployment type.
2. Fetch and read the high-value Learn pages found by the search.
3. Query current AVM metadata and Azure resource schemas before generating
   Bicep.
4. Query the selected Azure subscription for model quota and capacity by
   candidate region. Documentation availability alone is insufficient.
5. Record the evidence date, URLs, subscription name and ID, requested
   regions, candidate regions, and selected region in
   `00-region-availability.json`.

If current official documentation conflicts with repository guidance, current
Microsoft documentation controls. Update the affected repository guidance in
the same change.

## Use Foundry Resources and Projects

For greenfield solutions, use the current Microsoft Foundry resource model:

- One `Microsoft.CognitiveServices/accounts` Foundry resource.
- One direct child Foundry project under that resource.
- Model deployments, Agent Service configuration, connections, identity,
  RBAC, and application settings associated with that resource and project.
- The current Foundry project endpoint consumed by the application.

Do not create an Azure AI Hub or hub-based project for a new scenario. In
particular, greenfield output must not contain:

- `Microsoft.MachineLearningServices/workspaces` with hub or project kinds.
- `aiHub`, `hubName`, `hubResourceId`, or equivalent hub modules and outputs.
- Azure Machine Learning hub SDK or CLI workflows.
- Classic Foundry project endpoints or SDKs when a current replacement exists.

Hub-based projects are a legacy migration concern. Generate or preserve one
only when the user explicitly requests maintenance or migration of an existing
hub-based solution. Document the exception and the migration path to a current
Foundry project.

## Validate One Deployable Region

Treat a requested region as a preference until Azure proves it is deployable.
Build the candidate set from every region requested by the user plus current
supported alternatives. For each candidate, validate all of the following in
the target subscription and tenant:

- Foundry resource and project availability.
- Foundry Agent Service and every required tool or feature.
- Exact model name, version, deployment type, SKU, quota, and live capacity.
- Every supporting Azure resource and selected SKU.
- Azure Policy and provider registration constraints.

Select a single region where the complete resource set can deploy whenever
the requirements allow colocation. If no common region exists, produce an
explicit multi-region design with data residency, latency, networking, and
failure implications. Never silently substitute a region or model.

The machine-readable evidence file must contain:

- `subscriptionName`, `subscriptionId`, `tenantId`, and `checkedAtUtc`.
- `requestedRegions`, `candidateRegions`, and `selectedRegion`.
- One result per resource, feature, model, version, deployment type, and SKU.
- Quota and capacity evidence for the selected model.
- Rejection reasons for every unsuccessful candidate.
- The final recommendation and any assumptions that still need confirmation.

Requirements, architecture, Bicep, package, and deployment agents must read
the same evidence file. They must not replace its selected region from memory
or from a static default.

## Required End-to-End Output

A complete coach solution includes all of these outcomes:

- Foundry resource and direct child project.
- A deployable, usable model deployment.
- Orchestrator and specialist agents or idempotent creation automation.
- A coach solution web application with a real chat endpoint that invokes the
  orchestrator through managed identity.
- One isolated participant deployment per manifest team.

Do not create a separate web application solely to track hack progress. This
does not remove a solution application that participants build or complete as
part of the challenges.

Do not accept a placeholder-only coach chatbot. Missing project endpoint,
model deployment, agent ID, or agent automation is a failed completion gate.
The participant starter may intentionally omit Foundry resources only when the
hack contract requires learners to create them.

## Completion Evidence

Before claiming success, verify and record:

1. The deployed resource is a Foundry resource and has a direct child project.
2. No hub resource exists unless an explicit legacy exception was approved.
3. The selected model deployment accepts a test inference.
4. The orchestrator and required specialist agents exist and can be invoked.
5. The coach chatbot returns a grounded response through its deployed URL.
6. Every manifest team resource group exists, is isolated, and has a reachable
   application URL when the package includes an application.
7. The deployment manifest contains no `planned` or `deploying` status and no
   null application URL required by the package contract.

Use Playwright for web acceptance checks and Azure queries for resource,
project, model, agent, quota, capacity, and deployment evidence.

## Current Official References

- [What is Microsoft Foundry?](https://learn.microsoft.com/azure/foundry/what-is-foundry)
- [Create a Foundry project](https://learn.microsoft.com/azure/foundry/how-to/create-projects)
- [Deploy a Foundry resource with Bicep](https://learn.microsoft.com/azure/foundry/how-to/create-resource-template)
- [Foundry regional availability](https://learn.microsoft.com/azure/foundry/reference/region-support)
- [Azure OpenAI quota and capacity](https://learn.microsoft.com/azure/foundry/openai/quotas-limits)

These links are starting points, not cached truth. Search and fetch them again
at generation time and follow newer official guidance when available.
