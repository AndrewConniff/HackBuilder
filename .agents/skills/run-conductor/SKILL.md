---
name: run-conductor
description: Run the full Azure infrastructure workflow end-to-end
disable-model-invocation: true
argument-hint: Describe the Azure infrastructure project you want to build
---
# Run Conductor — End-to-End Workflow

Orchestrate the complete Azure infrastructure development workflow
for a new project, delegating to specialized agents with automatic handoffs
between each step.

## Mission

Guide a project from business description through two deployable Azure projects,
a public hacker file set, and a private coach guide using the full agent pipeline:
Requirements → Hack plan → Architect → Design → Bicep → Development
(conditional) → Hack packages → Deploy coach and team packages
→ Demo Guide.
All steps are required to have a successful project and do the handover to the user. After the final handoff, prompt the user to confirm the project run is complete.

## Scope & Preconditions

- User describes their project in business terms or technical terms
- All artifacts are saved to `generated-scenarios/${input:projectName}/`
- Bicep templates are saved to `generated-scenarios/${input:projectName}/infra/` and should support `azd provision`
- Each step produces artifacts that feed the next step
- The workflow always produces four file sets under
  `generated-scenarios/${input:projectName}/packages/`:
  - `coach/` is the full deployable solution, including Azure AI Foundry resources
  - `participant/` is the deployable starter with supporting resources and no Foundry resources
  - `hack/` is public GitHub-ready Skillable content with five industry challenge pages
  - `coach-guide/` contains exact challenge copies and a private Finale with coach notes
- The packages use separate azd environments and separate resource groups. The
  coach resource group contains the complete Foundry solution; the participant
  resource group contains supporting Azure resources only.
- Proceed through workflow steps automatically unless the user explicitly pauses

## Company identity prerequisite

Before Requirements generates business content, apply the
[CSV-only company identity rules](../../../.github/skills/az-consolidated/SKILL.md#fictitious-company-identity---csv-only).
Read `fictitious_company_names.csv` from the repository root, select a valid
company entry, and record its exact name, domain, derived slug, and catalog
provenance in the requirements. Pass that identity to every delegated step;
do not let agents invent a replacement brand for apps, packages, or resources.
Stop and ask the user if no eligible valid catalog entry can be read.

For sample datasets, also apply the
[CSV-only people identity rules](../../../.github/skills/az-consolidated/SKILL.md#fictitious-people-identity---csv-only).
Read the repository-root `fictitious_people_names.csv` before assigning people.
Pass the deterministic entity-to-catalog-record mapping to Development,
HackCreator, and DemoGuide so names stay unchanged across datasets and packages.
Do not allow invented names in seed data or supporting scenario references.

## Inputs

| Variable                      | Description                                       | Default  |
| ----------------------------- | ------------------------------------------------- | -------- |
| `${input:projectName}`        | Project name (kebab-case)                         | Required |
| `${input:projectDescription}` | Business or technical description of the workload | Required |
| `${input:teamCount}`          | Hacker teams from 1 through 20                    | `1`      |

## Workflow

### Step 1: Requirements

Delegate to **Requirements** agent with the project description.
Wait for `01-requirements.md` to be generated.

Automatically continue to Step 2 after requirements generation.

### Step 1b: Hack package plan

Delegate to **HackCreator Agent** in `plan` mode. It turns the scenario into a
four-output contract before architecture and Bicep work begin. The contract
defines two deployable projects, public hacker content, and private coach
guidance before implementation starts.

Automatically continue to Step 2 after `08-hack-package-contract.md` is generated.

### Step 2: Architecture Assessment

Delegate to **Architect** agent to review requirements and produce
WAF assessment with cost estimates.

Automatically continue to the next step after architecture generation.

### Step 3: Design Artifacts

Delegate to **Design** agent to generate architecture diagrams.
Automatically continue to Step 4 after design generation.

### Step 4: Bicep Templates

Delegate to **Bicep** agent for governance discovery, implementation
planning, template generation, and validation.

After templates are generated, verify `bicep build` and `bicep lint` pass.

Automatically continue to Step 4b (Development) if user requested a sample webapp, otherwise skip to Step 5 (Deploy).

### Step 4b: Development (Conditional)

If the user requested a sample web application during Step 1:

1. Delegate to **Development** agent with the project name and chosen industry
2. The agent scaffolds a .NET 10 C# Razor Pages webapp with local seed data
3. Wires the app into `azure.yaml` as a service
4. Generates `07-webapp-summary.md`

Skip this step if:

- The user declined a sample webapp
- The architecture is VM-only (no App Service, Container Apps, ACI, or AKS)

Automatically continue to Step 5 (Deploy).

### Step 5: Build hack packages

Delegate to **HackCreator Agent** in `package` mode before deployment. It must
create `coach/`, `participant/`, `hack/`, and `coach-guide/`. It assigns distinct
azd environment and resource-group names to the two projects, verifies the
participant Foundry exclusion, scans hacker files for public-repository safety,
confirms the coach challenge copies match the hacker files exactly, validates
the private Finale notes for every challenge, and creates the team deployment
manifest. Default to one team when the count is omitted.

### Step 6: Deploy both packages

Delegate to **Deploy** agent. Run a what-if analysis for each package, prompt
the user for Azure credentials and one confirmation, then deploy coach once and
the participant package once per manifest team. Validate the coach application,
agent, and Foundry resources. Validate every team group and confirm that no
prebuilt Foundry resource is present when the challenge contract omits it.

Automatically continue to Step 7 (Demo Guide).

### Step 7: Demo Guide

Generate **demo step-by-step instructions guide**.

With this final step completed successfully, **after** running the validation, **prompt** the user in chat to **confirm** the project run is complete.

After this step, hand the two deployed package paths and their distinct resource
groups to the user, then prompt for project-run confirmation.

## Output Expectations

```text
generated-scenarios/{projectName}/
├── 01-requirements.md
├── 02-architecture-assessment.md
├── 03-architect-diagram.py
├── 04-implementation-plan.md
├── 04-dependency-diagram.py
├── 04-dependency-diagram.png
├── 04-runtime-diagram.py
├── 04-runtime-diagram.png
├── 04-preflight-check.md
├── 05-implementation-reference.md
├── 06-deployment-summary.md
├── 07-webapp-summary.md          (conditional — if sample webapp requested)
├── 09-hack-event-manifest.json
├── /demoguide/demoguide.md
├── /demoguide/images/*.png
├── /packages/coach/               # Complete, deployable coach technology review package
├── /packages/participant/         # Deployable supporting resources without Foundry
├── /packages/hack/                # Public GitHub-ready challenge materials
├── /packages/coach-guide/         # Private coach solution, deployment, and challenge copy
└── README.md

generated-scenarios/{projectName}/infra/
├── main.bicep
├── main.bicepparam
└── modules/

generated-scenarios/{projectName}/src/         (conditional — if sample webapp requested)
└── {ProjectName}.Web/
```

## Quality Assurance

Before completing each step, verify:

- [ ] Artifact file exists and follows the H2 template from azure-artifacts skill
- [ ] No stale references to previous steps
- [ ] Workflow progressed through automatic handoffs
- [ ] All validation commands pass before proceeding
- [ ] Coach and participant projects exist with the documented Foundry boundary
- [ ] Hacker file set is public-repository safe and contains five challenges
- [ ] Challenges are Skillable pages under one canonical industry folder in `Instructions`
- [ ] Coach guide has matching challenge copies and a private Finale covering every challenge
- [ ] Coach and participant deployments use distinct resource groups
- [ ] Team count defaults to one and never exceeds 20
- [ ] Every team has a unique azd environment and numbered resource group
- [ ] Deployment manifest statuses and required application URLs are complete
- [ ] Coach Foundry resources are running and participant deployment has no Foundry resource
- [ ] Prompted the user to confirm the project run is complete at the end
