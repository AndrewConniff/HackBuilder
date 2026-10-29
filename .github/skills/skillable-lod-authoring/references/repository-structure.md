# Skillable repository structure

## Purpose

This contract adapts the Microsoft Learn-style repository pattern for
industry-specific Skillable challenge pages while preserving separate learner
and coach publishing boundaries.

## Reference pattern

The researched repository uses these conventions:

- Published instruction content lives beneath a capitalized `Instructions`
  directory.
- Each lab is a separate, numbered Markdown file.
- Every lab begins with nested `lab` YAML frontmatter.
- A root `index.md` discovers instruction pages with Jekyll Liquid.
- `_config.yml` configures the Microsoft Learning Jekyll theme.
- `_build.yml` packages Markdown and supporting files for release.
- `Allfiles/` holds learner-safe files consumed by the labs.
- Media uses relative paths and meaningful alt text.

The reference does not define a Finale page. This repository adds Finale as a
mandatory private coach page because the coached hack workflow requires notes
for every challenge.

## Scenario package roots

A generated scenario has two documentation roots:

| Root | Visibility | Skillable audience |
| --- | --- | --- |
| `packages/hack/` | Public | Participants |
| `packages/coach-guide/` | Private | Coaches |

Each root is independently GitHub-ready. A publisher may place them in separate
repositories or apply repository-level access controls, but must not merge the
private coach files into the public learner root.

The scenario root also contains `nextsteps.MD`. This file is the detailed
supporting-artifact inventory and delivery plan. It is not copied into either
documentation root, but it identifies every file that must be added to the
deployable packages or learner-safe `Allfiles/` trees.

## Canonical instruction paths

Use `Instructions/<industry-slug>/` directly. Do not add a generic `Labs`
folder because the industry folder is the requested grouping layer.

Learner pages use stable sequence numbers:

| Page | Filename prefix | Purpose |
| --- | --- | --- |
| Challenge 0 | `00-` | Secure foundation |
| Challenge 1 | `01-` | Minimal viable agent |
| Challenge 2 | `02-` | Grounding and citations |
| Challenge 3 | `03-` | Authenticated tool or action |
| Challenge 4 | `04-` | Evaluation, security, and demo |
| Finale | `99-` | Private coach notes and wrap-up |

The two-digit filename prefix matches the visible challenge number, from
`00-` for Challenge 0 through `04-` for Challenge 4. Finale retains `99-`
because it is a separate private coach page, not a learner challenge.

## Root files

| File | Purpose |
| --- | --- |
| `README.md` | Human entry point and challenge map |
| `index.md` | Jekyll page listing |
| `_config.yml` | Jekyll theme and plugin settings |
| `_build.yml` | Release archive definition |
| `resources.md` | Verified common links and optional assets |
| `Allfiles/` | Learner-safe downloads, starter files, and synthetic data |

The private coach root additionally retains its solution overview and deployment
guide. It uses the same challenge pages and common media so every participant
instruction renders identically for a coach.

Copy the complete `Allfiles/` tree to the coach root byte for byte. Do not put
coach answers, solution code, credentials, or environment files in `Allfiles/`.

## Scenario-level next steps

Create `generated-scenarios/<project>/nextsteps.MD` from the bundled template.
Use the exact filename capitalization so Windows and Linux validation agree.

The file contains:

- A summary inventory and a detailed `ART-NNN` specification for every
  supporting artifact.
- Creation, schema, synthetic-data, package placement, and review requirements.
- Azure target, idempotent load or installation, identity, and validation
  requirements.
- GitHub destination, visibility, branch, review, and publication work.
- A deployment gate that requires packaged runtime artifacts and preserves
  coach and participant `azd up` testing for separately requested event rollout.

Keep planned release enrichment separate from deployment-critical work. A
runtime artifact cannot remain deferred when packages are handed to deployment.

## Media rules

Place industry-specific media at
`Instructions/<industry-slug>/media/<descriptive-name>.<extension>`.

- Use relative links such as `media/agent-trace.png` from a challenge page.
- Copy media to the coach root without modification.
- Do not reference a screenshot until the file exists.
- Do not include screenshots with tenant names, subscription IDs, deployed
  endpoints, customer data, credentials, or unrelated browser chrome.
- Prefer text when a screenshot will become stale quickly.

## Jekyll behavior

The bundled `index.template.md` lists pages whose path contains
`Instructions/` and whose `lab.islab` value is true. The public root naturally
contains only learner pages. The private root also lists Finale because Finale
is a coach-facing Skillable instruction page.

Keep page order deterministic through two-digit filename prefixes. Do not rely
on title sorting.
