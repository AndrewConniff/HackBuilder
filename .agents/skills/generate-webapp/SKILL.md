---
name: generate-webapp
description: Scaffold a .NET 10 C# sample web application with industry-specific data for the demo workload scenario.
disable-model-invocation: true
argument-hint: Provide the project name and business industry for the sample webapp
---
# Generate Sample Web Application

Scaffold a .NET 10 C# Razor Pages web application with industry-specific
seed data, wire it into the azd framework, and validate the build.

## Mission

Generate a complete, buildable sample web application that demonstrates
the Azure demo workload with realistic local data. The application must
integrate with the existing infrastructure via the `azure.yaml` service
configuration. Its visual theme must come from the original scenario prompt
and use Fluent design and icons for navigation and common actions.

## Scope & Preconditions

- `generated-scenarios/${input:projectName}/02-architecture-assessment.md` must exist
- `generated-scenarios/${input:projectName}/infra/` must contain validated Bicep templates
- Read `.github/skills/az-consolidated/SKILL.md` for naming conventions and defaults
- Read `.github/skills/az-webapp-development/SKILL.md` for .NET 10 patterns
- For Foundry applications, read
  `.github/skills/az-webapp-development/app-creation-SKILL.md`
- Read `.github/instructions/az-dotnet-webapp.instructions.md` for coding standards
- Output saved to `generated-scenarios/${input:projectName}/src/{ProjectName}.Web/`

## Inputs

| Variable               | Description                                  | Default  |
| ---------------------- | -------------------------------------------- | -------- |
| `${input:projectName}` | Project name matching the `generated-scenarios/` folder | Required |
| `${input:industry}`    | Business industry for seed data              | Required |
| `${input:visualTheme}` | Optional visual cues; otherwise derive them from the original prompt | Derived |

## Workflow

### Step 1: Context Extraction

1. Read `02-architecture-assessment.md` to identify compute targets
2. Read the original scenario prompt when available and `01-requirements.md`
  to derive the audience, tone, industry, brand cues, and visual theme
   Company identity must follow the
   [CSV-only company rules](../../../.github/skills/az-consolidated/SKILL.md#fictitious-company-identity---csv-only).
   Verify the recorded company against the repository-root
   `fictitious_company_names.csv`; select and record a valid entry if absent.
   Use the exact company name for branding and its derived slug for
   company-bearing technical names. Theme cues never override this identity.
3. Determine if webapp is eligible (App Service, Container Apps, ACI, AKS)
4. If compute is VM-only, skip webapp generation entirely

### Step 2: Scaffold .NET 10 Project

1. Run `dotnet new webapp --framework net10.0 --name {ProjectName}.Web`
2. Set up project structure per skill patterns

### Step 3: Generate Models and Seed Data

1. Create entity models based on industry selection
2. Generate 10-20 realistic seed records per entity as JSON
   All person names must follow the
   [CSV-only people rules](../../../.github/skills/az-consolidated/SKILL.md#fictitious-people-identity---csv-only).
   Read `fictitious_people_names.csv` from the repository root and select
   complete valid records. Use exact full names and matching same-record
   components, preserving Unicode and native name order. Record deterministic
   entity-to-source mappings and reuse them in related records and package copies.
   Never invent people, recombine names, or copy unverified example names.
3. Create `SampleDataService` for in-memory data loading

### Step 4: Build Razor Pages

1. Build a professional Fluent 2 application shell themed from the original prompt
2. Use official Microsoft Fluent System Icons in responsive, accessible navigation
3. Add a home dashboard with entity counts and clear routes to primary workflows
4. Add List and Detail pages per entity type
5. Implement loading, empty, error, current-page, focus, and mobile navigation states

### Step 5: Container Support (if needed)

1. Generate multi-stage Dockerfile for container targets
2. Create `.dockerignore`

### Step 6: Wire azure.yaml

1. Add `services:` block to existing `azure.yaml`
2. Set `host:` based on compute target

### Step 7: Validate Build

1. Run `dotnet build` — must succeed
2. Verify seed data files are included in output
3. Verify Fluent icons, keyboard navigation, responsive layout, and WCAG 2.2 AA contrast
4. Generate `07-webapp-summary.md` with the selected prompt-derived theme documented
5. Verify every person-name field and embedded person reference against its
   selected catalog record, including imported data and displayed UI values

## Output Expectations

```text
generated-scenarios/{projectName}/
├── 07-webapp-summary.md
├── src/{ProjectName}.Web/
│   ├── {ProjectName}.Web.csproj
│   ├── Program.cs
│   ├── Dockerfile           (container targets)
│   ├── Models/
│   ├── Services/
│   ├── SeedData/
│   ├── Pages/
│   └── wwwroot/
└── azure.yaml               (updated with services block)
```
