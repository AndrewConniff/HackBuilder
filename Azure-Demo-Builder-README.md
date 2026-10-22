# Hack Builder

Build a working Microsoft Foundry business scenario first. Turn it into a
customer hack only after the technical owner approves it.

## Start

Open this repository in VS Code with GitHub Copilot and select **az-01-conductor**,
the **scenario orchestrator**. The second and only other agent is
**HackCreator Agent**, the **hack composition agent**. Both work directly through
skills, without specialist subagents or fanout.

Example:

> Build me a hack for a retail business: a Foundry agent that answers product
> questions using approved documents and checks store inventory through a tool.

The optional `/run-conductor` skill launches the same workflow. It is not a
second orchestrator. Reload customizations or start a fresh chat after pulling
workflow changes.

## Local portal

The optional [local portal entry point](portal/README.md) is an alternative to
starting in VS Code. From the repository root, authenticate and start it:

```powershell
copilot login
python scripts\portal_server.py
```

Open the printed private loopback URL and keep its token confidential. Local tool
consent is not an OS sandbox and does not automatically authorize Azure deployment.
The two approval stages remain separate: authorize exact deployment targets after
what-if review, then explicitly approve the working scenario's suitability before
composition. Event rollout requires another separate request.

The lightweight LOCAL web portal collects a prompt, validated project slug,
industry, requested services and WAF priorities. Its local authenticated backend
launches real Copilot CLI jobs with the canonical agent names. Project paths are
`generated-scenarios\{projectSlug}`. It is tooling, not an Azure-hosted progress app.

Initial jobs prepare locally: reference implementation, tests and what-if commands/
target preview, then stop before Azure operations unless explicitly authorized.
Tool execution requires explicit portal permission; this is not a sandbox.
A separate follow-up authorizes exact deployment targets after what-if review.
Selected services, `--allow-all-tools` and `--no-ask-user` are not consent.
Noninteractive jobs stop and return missing user decisions rather than guessing.

The portal never auto-approves scenarios or deploys events. Its approval action
records the explicit response against the reviewed fingerprint, checks approval
and launches composition as a separate job. Scenario jobs do not auto-start it.

## What happens

### A: prove the scenario

The agent produces a concrete story, requirements, architecture/diagrams,
AVM-first Bicep, a real .NET application, synthetic runtime inputs, an Azure
deployment and a demonstration guide. It tests the actual Foundry model,
agent and web chat, grounding/tools where applicable, and an error case.

You receive the live application URL, business-outcome walkthrough, costs,
test evidence and limitations. **The agent stops and asks whether the scenario
is workable and usable as your hack.**

Approve it, request changes, or stop. A request to deploy/fix the application
does not approve the scenario. An existing generated package does not bypass
this review.

### B: derive the hack after approval

After explicit recorded approval, a separate **HackCreator Agent** context creates:

- A sanitized full coach solution.
- A stripped-down minimum starter architecture and deployable learner package.
- Five outcome-led challenges totaling 150 build minutes, within a three-hour
  event including kickoff and wrap-up.
- Public Skillable-ready learner materials and private coach guidance/Finale.
- A supporting-artifact inventory and a planned event deployment manifest.

The minimum starter provides access/isolation and only indispensable fixtures
or prerequisites. Learners decide what components/resources to use and build
the rest. It is not automatically the full non-Foundry reference infrastructure.
Complete architecture and detailed answers remain private.

Local compilation, application tests and package validation finish this phase.
**No coach/team event rollout happens automatically.**

### C: deploy an event when requested

Explicitly request the event rollout and team count (1-20). After what-if and
target confirmation, the agent deploys one coach environment and isolated
numbered participant environments. Every team uses its own resource group and
azd environment. No learner environment reuses the reference/coach group.

Required app URLs depend on the package: a starter without an app needs no URL.
Rollout completion requires real validation of every requested target.
The scenario orchestrator executes deployment skills directly; there is no
deployment specialist agent. Publishing/contribution is also opt-in through a skill.

## Prerequisites

- VS Code and GitHub Copilot custom-agent support, or authenticated Copilot CLI
  for local portal jobs; no specialist/subagent fanout is needed.
- Azure CLI, Azure Developer CLI (`azd`) and Bicep CLI.
- .NET 10 SDK for the sample application.
- Python 3.10+ and Graphviz for diagrams; diagram dependencies are listed in
  [`requirements.txt`](requirements.txt).
- An Azure subscription with permissions for the required resources and role
  assignments, plus current model quota/capacity in a supported region.

Confirm the intended Azure account, subscription and tenant. No hard-coded
subscription or region is selected. If local account instructions exist, they
are honored; mismatches block deployment. Never paste credentials into chat.

Industry intake comes from [`microsoft_industry_verticals.csv`](microsoft_industry_verticals.csv).
Skillable currently supports only `financial-services`, `healthcare`,
`manufacturing`, `retail`, `energy-oil-gas` and `government-public-sector`.
Other industries can inform a reference scenario, but composition blocks until
you explicitly choose to extend authoring support or revise/reapprove the scenario.
The system must not silently map an unsupported industry to another slug.

## Outputs and approval

Run `scripts/New-AzdScenarioWorkspace.ps1` through the conductor to create
physical workspaces in the adjacent `azd-projects` directory with a junction at
`generated-scenarios/<project>`. Existing legacy projects are reused in place.

Phase A creates root `infra/`, `src/`, `azure.yaml`, diagrams,
`06-deployment-summary.md`, `scenario-validation.json`, and `demoguide/`.
The conductor records a review snapshot and, only after your affirmative
response, records approval in `workflow-state.json`.

The workflow helper rejects missing approval and reference changes. Changes to
the story, implementation or evidence require revalidation and renewed review.
The helper is an audit guard, not a substitute for real live tests or user consent.

Phase B adds the package contract, `nextsteps.MD`, and:

```text
packages/
  coach/          Full deployable reference copy
  participant/    Minimum learner starter
  hack/           Public learner repository
  coach-guide/    Private solution and Finale
```

## Repository maintenance

- [Workflow contract](.github/skills/hack-builder-workflow/SKILL.md)
- [Agent/skill/instruction inventory and October 21 timing findings](AGENTSEXPLAINED.md)
- [Repository conventions and validation commands](AGENTS.md)
- [Canonical agents](.github/agents/)
- [Canonical skills](.github/skills/)

The `.agents/skills` directory contains thin manual launchers and scenario input,
not a second set of agents or independent implementation instructions.
