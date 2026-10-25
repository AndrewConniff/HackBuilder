---
name: skillable-lod-authoring
description: >
  Creates GitHub-ready Learn On Demand and Skillable instruction repositories
  with industry challenge pages, Jekyll metadata, release packaging, and a
  private Finale page containing coach notes for every challenge. It also
  creates a detailed nextsteps.MD inventory for synthetic data, supporting
  documents, package placement, GitHub publication, and Azure installation.
  Use for Skillable labs, Learn On Demand content, industry challenge pages,
  GitHub lab repositories, Finale coach notes, supporting artifact plans, or
  HackCreator participant materials.
---

# Skillable Learn On Demand authoring

Create a public learner repository and a private coach repository from one
scenario. Each challenge is a separate Markdown page beneath the selected
industry folder in `Instructions`.

For ABC Builder scenarios, first enforce
[the workflow contract](../hack-builder-workflow/SKILL.md) and current recorded
approval. This skill never bypasses scenario review. Package validation is a
local authoring milestone; event rollout is separately requested.

## Required research

Before generating content:

1. Read `.github/skills/az-consolidated/SKILL.md`.
1. Read `.github/instructions/az-agent-research-first.instructions.md`.
1. Read `.github/instructions/az-markdown.instructions.md`.
1. Read `.github/instructions/hack-authoring.instructions.md`.
1. Read `.github/instructions/style-guide.md`.
1. Read `.github/skills/azure-foundry-hack-builder/SKILL.md` for Foundry hacks.
1. Read all files in this skill's `references/` directory.
1. Inspect the scenario requirements and package contract.
1. Confirm the industry is in `assets/industry-catalog.json`.

Do not generate Azure-specific steps until current service behavior, model
availability, and documentation are verified by the scenario orchestrator.

The repository `microsoft_industry_verticals.csv` is the broader intake catalog,
not a replacement for this skill's explicitly supported industry slugs. Before authoring,
verify the exact selected slug against `assets/industry-catalog.json`. Unsupported
industries block composition pending an explicit decision to extend authoring
support or revise/reapprove the scenario; never silently map to a supported slug.
In noninteractive jobs, report the required decision and stop.

## Required inputs

| Input | Rule |
| --- | --- |
| Scenario | One unchanged business scenario across all pages |
| Industry | One supported display name and canonical slug |
| Business units | Approved `businessUnits` IDs and personas; Generic means no unit targeting |
| Module title | One title shared by all page frontmatter |
| Challenge plan | Five progressive challenges totaling 150 build minutes |
| Coach context | Expected evidence, recovery paths, and debrief guidance |
| Supporting artifact plan | Exact files, schemas, Azure targets, creation work, and tests |
| Verified links | Current public documentation links only |

Derive missing values from the requirements and package contract. Use visible
placeholders only when evidence is unavailable; never invent values.

Company identity is not a placeholder or free-form input. Apply the
[CSV-only company identity rules](../az-consolidated/SKILL.md#fictitious-company-identity---csv-only)
and verify the requirements' exact company name against the repository-root
`fictitious_company_names.csv`. If no identity is recorded, select and record
a valid catalog entry before authoring. Keep that identity consistent across
all five challenges, synthetic business documents, `nextsteps.MD`, public
materials, and private coach notes. Any secondary fictitious company must
also come from a valid catalog entry; never invent customer or supplier brands.
Do not copy internal source paths into public learner materials.

Apply the
[CSV-only people identity rules](../az-consolidated/SKILL.md#fictitious-people-identity---csv-only)
to all sample-data person references in challenges, supporting documents,
payloads, and coach notes. Source names only from valid records in the
repository-root `fictitious_people_names.csv`; reuse the dataset's deterministic
entity-to-record mapping rather than inventing new people while authoring.
Record provenance in the internal supporting-artifact plan, not absolute
workstation paths in public learner pages. Keep names identical in matching
learner and coach content.

## Publishing boundaries

Create two GitHub-ready documentation roots under `packages/`:

- `hack/` is the public learner source.
- `coach-guide/` is the private coach source used for coach-facing Skillable
  instructions.

The coach source contains byte-for-byte copies of all learner challenge pages
and media. It adds one required `99-finale.md` page. The Finale is the canonical
location for coach notes for every challenge and must never be copied into the
public learner source.

Both roots include `README.md`, `index.md`, `_config.yml`, `_build.yml`,
`resources.md`, and learner-safe payloads under `Allfiles/`. The private coach
root also retains `solution-overview.md` and `deployment-guide.md` from the
package contract.

Create one scenario-level `nextsteps.MD` beside the workflow artifacts. It is
an internal, GitHub-safe creation and delivery plan, not a Skillable instruction
page. Do not copy it into either documentation root.

## Required layout

Use the selected slug in both roots and keep `nextsteps.MD` at the scenario
root:

```text
generated-scenarios/<project>/
├── nextsteps.MD
└── packages/
    ├── hack/
    │   ├── README.md
    │   ├── index.md
    │   ├── _config.yml
    │   ├── _build.yml
    │   ├── resources.md
    │   ├── Allfiles/
    │   └── Instructions/<industry-slug>/
    │       ├── 00-secure-foundation.md
    │       ├── 01-build-the-agent.md
    │       ├── 02-ground-it.md
    │       ├── 03-give-it-tools.md
    │       ├── 04-harden-and-demo.md
    │       └── media/
    └── coach-guide/
        ├── README.md
        ├── index.md
        ├── _config.yml
        ├── _build.yml
        ├── resources.md
        ├── Allfiles/
        ├── solution-overview.md
        ├── deployment-guide.md
        └── Instructions/<industry-slug>/
            ├── 00-secure-foundation.md
            ├── 01-build-the-agent.md
            ├── 02-ground-it.md
            ├── 03-give-it-tools.md
            ├── 04-harden-and-demo.md
            ├── 99-finale.md
            └── media/
```

Omit `media/` only when no page uses local media. Never add an empty directory
or a broken image reference.

## Industry contract

Use exactly one of these stable slugs per scenario:

| Industry | Folder slug |
| --- | --- |
| Financial Services | `financial-services` |
| Healthcare | `healthcare` |
| Manufacturing | `manufacturing` |
| Retail | `retail` |
| Energy / Oil & Gas | `energy-oil-gas` |
| Government / Public Sector | `government-public-sector` |
| Hospitality & Travel | `hospitality-travel` |
| Media & Communications | `media-communications` |

The catalog in `assets/industry-catalog.json` is the machine-readable source of
truth. Do not create synonyms or alternate folder spellings.

## Challenge page contract

Start from `assets/challenge-page.template.md`. Every learner page must:

- Begin with valid `lab` YAML frontmatter.
- Use one H1 and the required H2 sections in template order.
- Preserve the scenario and module title across all five pages.
- Preserve the approved business-unit scope, personas, handoffs and dataset meaning.
- Use plain headings, prose and navigation without decorative emoji; retain
  functional badges, checkboxes and alert callouts.
- State the starting checkpoint, smallest useful increment, retained behavior,
  and regression check.
- Offer the Foundry portal path first and a collapsed SDK path second.
- Include observable completion evidence, three progressive hints, and a
  fallback that preserves the last working checkpoint.
- Use relative links for local content and verified public links for external
  content.
- Contain no coach answer key, completed implementation, environment state,
  credentials, tenant details, subscription IDs, or deployed endpoints.
- Let learners select/build components from outcomes and constraints. Keep the
  complete solution architecture and prescriptive answer steps in private Finale.

Copy the completed learner pages to the coach source without editing them.

## Finale coach-notes contract

Start from `assets/finale-page.template.md`. The private
`Instructions/<industry-slug>/99-finale.md` page is mandatory and must:

- Set `lab.audience` to `coach` and `lab.isfinale` to `true`.
- Map all five challenges by number and exact title.
- Give the objective, expected outcome, completion evidence, talking points,
  common blockers, recovery guidance, hint escalation, fallback checkpoint,
  demo prompts, and security reminders for each challenge.
- Include the event wrap-up and handoff guidance.
- Avoid credentials, deployed endpoint values, customer data, and tenant or
  subscription identifiers.

Finale is a distinct coach page. Exclude it from learner/coach challenge hash
comparison, but require it in private-package validation.

## Supporting artifact and next-steps contract

Start from `assets/nextsteps.template.MD` and follow
`references/scenario-artifact-inventory.md`. Create the output with the exact
case-sensitive name `generated-scenarios/<project>/nextsteps.MD`.

The file must inventory every synthetic dataset, source document, media file,
API contract, message sample, evaluation set, seed script, and installation
script required by the scenario. Each `ART-NNN` entry must define:

- The exact proposed filename and every package-relative destination.
- Its business purpose and setup or challenge dependency.
- Format, schema or document structure, required fields or sections, and size.
- Synthetic categories, ranges, edge cases, deterministic identifiers, and
  privacy constraints.
- Target Azure service and logical destination.
- Reproducible generation, idempotent upload or installation, identity, and
  dependency requirements.
- Local checks, Azure checks, observable acceptance criteria, ownership, and
  priority.
- A `deployment-critical` or `release-enrichment` classification and current
  lifecycle status.

Create `nextsteps.MD` during package planning with entries at `planned`. During
package generation, create every deployment-critical artifact, place it at all
listed destinations, and update it to `packaged`. Release-enrichment artifacts
may remain planned only when no required challenge or deployed acceptance path
depends on them.

Missing deployment-critical artifacts block handoff to deployment. Package
authoring itself stops at local validation. After a separate explicit event
request, Deploy runs `azd up` for coach and each participant manifest entry,
executes the applicable load hooks, runs artifact-specific Azure checks, and
updates successful entries to `azure-verified`.

Keep `nextsteps.MD` safe for GitHub. It must contain no customer or personal
data, coach answer key, credentials, resolved endpoints, tenant IDs,
subscription IDs, deployment state, or local absolute paths.

## Repository files

Copy and fill the assets as follows:

| Asset | Destination in each documentation root |
| --- | --- |
| `assets/readme.template.md` | `README.md` |
| `assets/index.template.md` | `index.md` |
| `assets/config.template.yml` | `_config.yml` |
| `assets/build.template.yml` | `_build.yml` |
| `assets/resources.template.md` | `resources.md` |
| `assets/allfiles-readme.template.md` | `Allfiles/README.md` |
| `assets/challenge-page.template.md` | Five numbered challenge pages |
| `assets/finale-page.template.md` | Private coach `99-finale.md` only |
| `assets/nextsteps.template.MD` | Scenario-root `nextsteps.MD` only |

Remove every template token before publication. Preserve an organization-approved
`LICENSE` when packaging an existing repository; do not invent licensing terms.

## Generation workflow

1. Select one canonical industry slug.
1. Create or update scenario-root `nextsteps.MD` with a detailed specification
  for every supporting artifact.
1. Create every deployment-critical artifact and put it at every listed
  package destination before deployment handoff.
1. Create both documentation roots and common repository files.
1. Generate five learner challenge pages in dependency order.
1. Add media only when the file exists and meaningful alt text is available.
1. Copy learner pages, media, resources, and `Allfiles/` byte for byte to the
  coach root.
1. Generate the private Finale with coach notes for all five challenges.
1. Run the validation script.
1. Stop on missing pages, unpackaged deployment-critical artifacts, stale
  tokens, unsafe content, parity failures, or incomplete Finale mappings.
1. Finish with **packages validated; event not deployed**. Only a separate explicit
  event request authorizes the scenario orchestrator to execute deployment skills
  and run real coach/team acceptance; no agent handoff or rollout is automatic.

## Validation

From the repository root, run:

```powershell
python .github/skills/skillable-lod-authoring/scripts/validate_skillable_package.py `
  generated-scenarios/<project>/packages `
  --industry <industry-slug>
```

Validate the bundled authoring resources with:

```powershell
python .github/skills/skillable-lod-authoring/scripts/validate_skillable_package.py `
  --check-skill
```

See `references/validation-checklist.md` for manual release checks.

## Non-negotiable rules

- Do not publish Finale or any coach notes in `packages/hack/`.
- Do not weaken byte-for-byte parity for the five challenge pages.
- Do not place multiple industries in one scenario package.
- Do not rename `Instructions`, change its capitalization, or add `Labs` between
  `Instructions` and the industry folder.
- Do not reduce the existing five-challenge progression to three.
- Do not create an Azure-hosted progress-tracking or challenge-checklist app.
  The repository's local authenticated CLI-launching workflow portal is tooling,
  not a learner app, and cannot auto-approve scenarios or deploy events.
- Preserve the real coach solution application and applications participants
  build or complete during the challenges.
- Do not omit `nextsteps.MD`, rename it, or copy it into a documentation root.
- Do not leave a deployment-critical artifact at `planned`, `created`, or
  `validated` when declaring packages locally validated.
- Do not use planned artifact creation as a reason to skip coach or participant
  acceptance after an explicitly requested event rollout.
