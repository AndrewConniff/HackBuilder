# ABC Builder

Build a working Microsoft Foundry business scenario first. Turn it into a
customer hack only after the technical owner approves it.

New here? Follow the [illustrated how-to guide](ABC-Builder-HOWTO.md) for setup,
browser navigation, VS Code interaction, milestone meanings, approvals and package exports.

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

The [local portal](portal/README.md) collects your brief, opens the real VS Code
agent conversation, displays progress reports and provides file/package browsing.
Use **Refine with AI** on a rough brief for prompt-specific scoping questions before building.
The same scenario agent spots architectural gaps and edge cases, saves a refined brief and waits for confirmation.
**Confirm brief** resumes the normal workflow in that existing conversation without a typed follow-up prompt;
**Save changes** requests a scoping-only revision. Deployment and suitability approvals remain separate.
No fixed questionnaire, extra agent, model credentials or cloud operation is added by refinement.
From the repository root, start or reuse it:

```powershell
.\Start-ABCBuilder.cmd
```

Alternatively, run `python scripts\start_portal.py`.
The launcher opens the local loopback page in your browser.
The active portal does not launch background Copilot CLI jobs or supervise agents;
implementation, tool permissions and decisions remain in VS Code.
See the [how-to guide](ABC-Builder-HOWTO.md) for the complete two-window walkthrough.

The lightweight LOCAL web portal collects a prompt, validated project slug,
industry, `businessUnits`, workflow pattern, requested services and WAF priorities.
It saves a handoff and opens the canonical custom agent through `code chat`.
Project paths are
`generated-scenarios\{projectSlug}`. It is tooling, not an Azure-hosted progress app.

Local preparation can proceed before cloud authorization.
Review the exact deployment scope, authorized what-if results, costs and pending
decisions in the existing VS Code chat. Tool permission and service selections
are not Azure or Entra consent. Matching same-scenario authorization is reused;
missing authority or material new scope requires a focused decision.

The portal never auto-approves scenarios or deploys events.
After you approve the proven scenario's suitability in chat, the agent records
the decision against the reviewed fingerprint. The portal checks current approval
before opening composition as a separate **HackCreator Agent** context.
Scenario work does not auto-start composition; event rollout requires a separate request.

## Sharing this repository

Share source through Git or a source-only archive, not a ZIP of the entire working directory.
The approved visualization portal is the only shipped portal implementation;
the retired CLI runner and dashboard have been removed.

Keep the how-to guide and its screenshots, canonical agents/skills, templates,
identity catalogs, research references and the Scenario Chat bridge.
Local portal state, generated scenario junctions, `.azure`, `.private` credential files,
virtual environments, caches and build/test outputs are ignored and must not be distributed.
Existing local environments and scenario evidence are preserved, not cleaned by deletion.
Never force-add ignored files when preparing a source share.

Each recipient prepares their own tools and Azure identities using the
[manual, online or cached setup routes](ABC-Builder-HOWTO.md#choose-manual-online-or-cached-setup);
no Copilot CLI runner or Python browser installation is needed.
Never include the local `system-tools\cache` or `system-tools\reports` folders in a source share.

## Business scope and reusable scenarios

Choose Generic or one or more specific business units:
Executives, IT, Operations, Communications, Executive assistant, Legal, HR,
Business manager, Finance, Sales and Marketing. Generic is exclusive and means
a typical workflow for the selected industry without targeting a unit.
Selections shape requirements, personas, the business story, application,
synthetic data and, after approval, learner and coach materials.

The portal discovers reusable references from
`generated-scenarios\*\scenario-manifest.json`. Discovery is read-only and inferred
entries remain visibly `needs-review` until a worker curates them.
Workers maintain metadata with
`python scripts\scenario_catalog.py refresh generated-scenarios\<slug> --metadata reviewed-metadata.json`.
See the [schema and stable unit IDs](.github/skills/hack-builder-workflow/SKILL.md).

Selecting a source grants no consent. Adaptations use source architecture as
read-only guidance, regenerate business app/data for the target industry and units,
refresh technical evidence, and require new design confirmation, validation and
suitability approval. Deployment state, secrets, authorization scopes, approvals,
packages and runtime success are never inherited.

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

## Agentic business scenarios

The scenario builder uses the
[18-pattern selection guide](.github/skills/az-scenario-requirements/references/agentic-patterns.md)
as adaptable design guidance.
It starts from the selected industry and business units, compares a single-agent baseline,
and justifies any coordination, human gate or shared-state pattern.
Requirements and architecture record the runtime contract; app/data, tests and demonstration prove it.
Supporting Azure infrastructure is not the business outcome.

After suitability approval, hack composition derives a small progressive agent-building experience
from that working behavior. It does not add unrelated patterns or expose the private completed solution.
Existing scenarios are not rewritten or automatically reapproved, and no new portal selection is required.

## Prerequisites

Choose manual installation from the [complete official download inventory](
ABC-Builder-HOWTO.md#manual-tool-inventory-and-official-downloads), or use the opt-in
[`system-tools` PowerShell setup](system-tools/README.md).
The default downloads all pinned native tools; installation requires `-Install`.
Shared tools are never installed by scenario workers.
The [prerequisite guide](PREREQUISITES.md) also covers authentication and stale-PATH troubleshooting.

From the repository root on Windows:

```powershell
# Check everything required by the portal's System profile; install nothing.
.\system-tools\Install-SystemTools.ps1 -Mode Check

# Preview, then download the complete pinned baseline, including Node.js and GitHub CLI.
.\system-tools\Install-SystemTools.ps1 -WhatIf
.\system-tools\Install-SystemTools.ps1 -AcceptPackageAgreements -Verbose

# One flow: download/reuse every native tool, then install missing tools from those files on Windows x64.
.\system-tools\Install-SystemTools.ps1 -Install -AcceptPackageAgreements -AcceptDockerLicense -Verbose
```

**The offline/native cache is not a fully offline installer for the entire toolchain.**
Native versions, URLs and SHA256 are pinned in [`tool-catalog.json`](system-tools/tool-catalog.json),
including Bicep; WinGet is not needed. Missing Python requirements still need network access.
Vendor dependencies, WSL, extensions and application NuGet packages are not bundled.
This baseline targets Windows x64; ARM64 users should use official native manual installers.
Binaries are downloaded locally on request, ignored by Git and not redistributed with this repository.
Clean machines receive pinned native versions; compatible existing tools are preserved, not forcibly downgraded.
Add `-UseCachedInstallers` with `-Install` to prohibit additional native downloads and require a complete local cache.

Finish work and close the portal before installation. Review vendor terms first.
New Docker installation additionally requires `-AcceptDockerLicense`, working WSL 2.1.5+ and virtualization;
without that separate consent it remains a manual action.
Setup never starts Docker, reboots Windows, signs in or relaunches itself elevated.
Vendor installers can require administrator approval.
Reopen your terminal afterward, complete sign-in and Docker setup, and rerun both System diagnostics.
Timestamped progress and final checks explain what succeeded; local JSON reports are saved under
`system-tools\reports`. Node.js/GitHub CLI are always included; no contributor switch is needed.
Use `-SkipVSCode` only when VS Code is managed separately.

- VS Code and GitHub Copilot custom-agent support, with the `code` launcher
  for portal handoffs; no specialist/subagent fanout is needed.
- Azure CLI, Azure Developer CLI (`azd`) and the Azure CLI Bicep component (`az bicep`).
- .NET 10 SDK for the sample application.
- Python 3.10+ and Graphviz for diagrams; diagram dependencies are listed in
  [`requirements.txt`](requirements.txt).
- For the full shared System profile: Docker's running Linux engine, Functions Core Tools 4+ and k6.
- An Azure subscription with permissions for the required resources and role
  assignments, plus current model quota/capacity in a supported region.

Confirm the intended Azure account, subscription and tenant. No hard-coded
subscription or region is selected. If local account instructions exist, they
are honored; mismatches block deployment. Never paste credentials into chat.

Industry intake comes from [`microsoft_industry_verticals.csv`](microsoft_industry_verticals.csv).
See the current [Skillable authoring industry catalog](
.github/skills/skillable-lod-authoring/references/industry-catalog.md) for supported package industries.
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

- ABC Builder is product branding only: stable agent names, canonical skill
  folder identifiers, executable scripts and environment variables remain compatible.
- [Workflow contract](.github/skills/hack-builder-workflow/SKILL.md)
- [Agent/skill/instruction inventory and October 21 timing findings](AGENTSEXPLAINED.md)
- [Repository conventions and validation commands](AGENTS.md)
- [Canonical agents](.github/agents/)
- [Canonical skills](.github/skills/)

The `.agents/skills` directory contains thin manual launchers and scenario input,
not a second set of agents or independent implementation instructions.
