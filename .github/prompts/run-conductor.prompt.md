---
description: "Run the full Azure infrastructure workflow end-to-end"
agent: "az-01-conductor"
model: "Claude Opus 4.6"
tools:
  - agent
  - edit/createFile
  - edit/editFiles
  - read/readFile
  - search/listDirectory
  - execute/runInTerminal
argument-hint: Describe the Azure infrastructure project you want to build
---

# Run Conductor — End-to-End Workflow

Orchestrate the complete Azure infrastructure development workflow
for a new project, delegating to specialized agents with automatic handoffs
between each step.

## Mission

Guide a project from business description through a fully working coach Foundry
solution and a participant hack package using the full agent pipeline:
Requirements → Hack plan → Architect → Design → Bicep → Development
(conditional) → Hack packages → Deploy both packages → Demo Guide.
All steps are required to have a successful project and do the handover to the user. After the final handoff, prompt the user to confirm the project run is complete.

## Scope & Preconditions

- User describes their project in business terms or technical terms
- All artifacts are saved to `generated-scenarios/${input:projectName}/`
- Bicep templates are saved to `generated-scenarios/${input:projectName}/infra/` and should support `azd provision`
- Each step produces artifacts that feed the next step
- The workflow always produces two packages in `generated-scenarios/${input:projectName}/packages/`:
  - `coach/` contains the full Azure demo, including Azure AI Foundry resources, and is deployable for technology review before the hack
  - `participant/` retains the supporting Azure resources but excludes Azure AI Foundry resources; it contains the five challenge files that guide teams to build those resources themselves
- The packages use separate azd environments and separate resource groups. The
  coach resource group contains the complete Foundry solution; the participant
  resource group contains supporting Azure resources only.
- Proceed through workflow steps automatically unless the user explicitly pauses

## Inputs

| Variable                      | Description                                       | Default  |
| ----------------------------- | ------------------------------------------------- | -------- |
| `${input:projectName}`        | Project name (kebab-case)                         | Required |
| `${input:projectDescription}` | Business or technical description of the workload | Required |

## Workflow

### Step 1: Requirements

Delegate to **Requirements** agent with the project description.
Wait for `01-requirements.md` to be generated.

Automatically continue to Step 2 after requirements generation.

### Step 1b: Hack package plan

Delegate to **HackCreator Agent** in `plan` mode. It turns the scenario into a
two-package contract before architecture and Bicep work begin. The contract
ensures the coach package includes all required Foundry and supporting resources,
while the participant package can safely omit Foundry and teach its construction
through challenges.

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
create `coach/` and `participant/`, assign distinct azd environment and
resource-group names, and verify that participant IaC omits every Foundry
resource, output, dependency, and Foundry-specific role assignment.

### Step 6: Deploy both packages

Delegate to **Deploy** agent. Run a what-if analysis for each package, prompt
the user for Azure credentials and one confirmation, then deploy coach and
participant packages with `azd up` to their dedicated resource groups. Validate
the coach agent and Foundry resources, and validate that no Foundry resource is
present in the participant group. Generate package deployment summaries.

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
├── /demoguide/demoguide.md
├── /demoguide/images/*.png
├── /packages/coach/               # Complete, deployable coach technology review package
├── /packages/participant/         # Supporting resources + Foundry challenge materials
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
- [ ] Coach and participant packages exist with the documented Foundry boundary
- [ ] Coach and participant deployments use distinct resource groups
- [ ] Coach Foundry resources are running and participant deployment has no Foundry resource
- [ ] Prompted the user to confirm the project run is complete at the end
