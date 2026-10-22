# Hack composition procedure

Migrated from the composition agent body on 2026-10-22. Execute in the
`HackCreator Agent` context, using skills directly; do not invoke other agents.

You author a hack from an approved reference. You do not invent a second
solution, deploy resources, or invoke other agents.

## Approval prerequisite

Before writing anything, read the
[workflow contract](../../hack-builder-workflow/SKILL.md) and run:

```powershell
python scripts\hack_workflow.py check-approval generated-scenarios\{project}
```

A nonzero result blocks **both modes**, including direct/manual invocation.
Return the failure and request scenario review; never approve on
the user's behalf or treat legacy packages as approval.

## Required context

Read requirements, architecture, root IaC/application, region evidence,
`scenario-validation.json`, deployment summary and demo guide. Load:

- `.github/skills/azure-foundry-hack-builder/SKILL.md`
- `.github/skills/skillable-lod-authoring/SKILL.md` and the applicable templates/references
- `.github/instructions/hack-authoring.instructions.md`
- `.github/instructions/style-guide.md`
- `.github/skills/az-multi-team-deployment/SKILL.md` for manifest shape only

Reuse reference synthetic fixtures, catalog provenance, APIs and passing tests.
Refresh evidence only when inputs or current service behavior require it.

Before either mode, compare the recorded industry from repository
`microsoft_industry_verticals.csv` with Skillable's six supported slugs. Do not
silently map an unsupported industry. Return **decision required** and stop for
an explicit support-extension or scenario-revision decision. Reapproval is
required if the scenario changes. Do not guess in a noninteractive job.

## Plan mode

Create `08-hack-package-contract.md` and scenario-root `nextsteps.MD`, using the
Skillable inventory template. These are **post-approval** artifacts.

The contract records:

- The approved reference fingerprint, unchanged story and supported industry slug.
- Full coach solution and a **scenario-specific minimum** participant starter.
- A private resource matrix: reference resource, preprovided/learner-built/
  coach-only disposition, rationale, challenge dependency and acceptance check.
- A stripped-down starter architecture showing only preprovided resources.
- Learner design decisions, observable challenge checkpoints and fallback paths.
- Integration placeholders and the starter's explicit not-configured behavior.
- Distinct coach and participant azd environments/resource groups.
- Five progressive challenges totaling 150 minutes, plus kickoff and wrap-up.
- Package validation and separately requested event rollout acceptance.

Do not automatically preserve all supporting resources. Provide only isolation,
access and indispensable fixtures/prerequisites. Learners determine which
components/resources to build. Explain each exception to the minimal boundary.
No Foundry accounts, projects, models, agents or completed agent logic in starter
IaC/code. No completed solution architecture or answer key in public materials.

Inventory exact supporting-artifact filenames, schemas, synthetic rules,
destinations, Azure targets, load hooks, tests and owners in `nextsteps.MD`.
Reuse already-implemented runtime files. Mark genuinely required artifacts
`deployment-critical`; optional additions are `release-enrichment`.

## Package mode

Recheck approval, then read the package contract and inventory.
Create all four self-contained roots:

| Root | Contents |
| --- | --- |
| `packages/coach/` | Sanitized deployable copy of the approved reference, full app and IaC |
| `packages/participant/` | Minimum starter IaC, safe fixtures, optional incomplete app |
| `packages/hack/` | Public Skillable learner repository and outcome-led challenges |
| `packages/coach-guide/` | Private solution overview, deployment guide, challenge copies and Finale |

Exclude credentials, environment/deployment state, private operational evidence,
local paths and concrete deployed endpoints from exported packages. Preserve the
approved source untouched. Do not copy `.azure/`, build caches, `.env` files,
`workflow-state.json` or `scenario-validation.json`.

Remove omitted resources' modules, dependencies, role assignments, outputs,
configuration, load hooks and completed implementation together. The starter
must compile and intentionally report missing learner configuration rather than
fabricate successful chat. No app or application URL is required when no starter
app is included. An empty resource-group starter is valid.

Create public and private Skillable roots with `README.md`, `index.md`,
`_config.yml`, `_build.yml`, `resources.md`, `Allfiles/`, and five challenge pages
under `Instructions/<industry-slug>/`. Use the same scenario throughout.

Challenges state outcomes, constraints, required evidence, starting checkpoint,
smallest useful increment, retained behavior and regression test. Learners
choose and implement components. Provide portal-first and collapsed SDK options,
three escalating collapsed hints and a fallback preserving prior progress.
Do not turn the primary task into a prescribed reference-solution walkthrough.

Challenge 0 establishes access, safe identity and required foundation.
Challenge 1 proves an MVP agent; 2 adds grounding; 3 adds an authenticated action;
4 hardens/evaluates the working solution without redesign. Match these
capabilities to the approved scenario rather than inventing unrelated work.

The private coach guide has `solution-overview.md`, `deployment-guide.md`,
byte-identical learner challenge/media/payload copies and
`Instructions/<industry-slug>/99-finale.md`. Keep the full architecture, detailed
solution steps, resource decisions and coach notes only in private material.
Finale maps every challenge and never appears in the public source.

Create `09-hack-event-manifest.json` with the requested team count (default one,
range 1-20). All new deployments remain `planned`. A manifest does not authorize
rollout. No deployment state or URLs may be copied from another environment.

## Validation and return

Run from the package directory, adapting app paths only when an app exists:

```powershell
az bicep build --file coach\infra\main.bicep
az bicep lint --file coach\infra\main.bicep
az bicep build --file participant\infra\main.bicep
az bicep lint --file participant\infra\main.bicep
```

Build/test the copied coach app and any starter app. Test the intended incomplete
starter state, omitted resource denylist in source and compiled ARM, placeholder
configuration, and absence of completed agent code. Verify both packages'
environment names and resource groups are distinct.

Every deployment-critical supporting file must exist at each listed destination,
pass local validation, and reach `packaged`. Wire idempotent ingestion hooks only
for resources each package actually provides; learner installation belongs in
the corresponding challenge rather than an invalid starter hook.

Run from the repository root:

```powershell
python .github\skills\skillable-lod-authoring\scripts\validate_skillable_package.py `
  generated-scenarios\{project}\packages --industry <industry-slug>
python scripts\hack_workflow.py check-approval generated-scenarios\{project}
```

Return artifact paths, exact local validation results, omission matrix, known
limitations and **packages validated; event not deployed**. Do not deploy resources.
An event rollout later requires coach and all requested team acceptance checks.
