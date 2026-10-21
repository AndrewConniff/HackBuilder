---
name: azure-foundry-hack-builder
description: >
  Generates Azure AI Foundry hack challenge content from a short prompt or a
   topic/scenario input. Produces a complete Azure AI Foundry agent scenario:
   a fully working coach solution and a 3-hour participant hack broken into
   timed challenges, written in the Agents League house style (badge header,
   time budget, scenario, milestones, success criteria, hints, resources) and
   packaged as GitHub-ready Skillable / Learn On Demand pages.
  Use when the user asks to "build a hack", "create hack challenges",
  "make a Foundry hackathon", "write a challenge for the hack",
  "turn this into a hack", "draft an agent-building lab", or supplies a
  scenario/industry and asks for challenge content. Do NOT use for general
  Azure how-to questions, for non-Foundry hacks, or for judging/scoring
  submissions.
---

# Azure AI Foundry Hack Builder

Turn any input (a scenario, an industry, a customer ask, a product theme) into a
complete set of Azure AI Foundry hack challenges. **Every hack this skill
produces is an Azure AI Foundry agent-building hack that fits in 3 hours.**

When this skill is used by the Azure Demo Builder, the scenario has four
deliverables that share one design:

- A **coach solution** that fully implements the agent in Azure AI Foundry,
   including its Foundry resources and every supporting Azure resource.
- A **participant project** that deploys the same non-Foundry supporting
   resources but intentionally omits every Foundry resource.
- A **hacker file set** that is safe for a public GitHub repository and teaches
   participants to build the omitted Foundry solution.
- A **coach guide** that explains the complete solution and deployment process
   and includes exact copies of the hacker challenges plus a private Finale
   page containing coach notes for every challenge.
- A scenario-level **supporting-artifact plan** named `nextsteps.MD` that
   specifies every synthetic dataset, source document, media file, contract,
   evaluation set, and installation script required by the design.

The two deployable projects must use separate azd environments and separate
resource groups. A participant deployment must never target, reuse, or modify
the coach resource group. The documentation sets are not deployed by `azd`.

## Fixed constraints (never negotiate these)

| Constraint      | Value                                                                       |
| --------------- | --------------------------------------------------------------------------- |
| Platform        | Microsoft Foundry / Azure AI Foundry only (portal + Foundry SDK)            |
| Theme           | Building AI **agents** - not apps, fine-tuning, or data engineering         |
| Total length    | 3 hours (180 min)                                                           |
| Structure       | 10 min kickoff + 150 min build across challenges + 20 min wrap/demo         |
| Challenge count | 4-5 challenges, each 25-40 min                                              |
| Audience        | Mixed skill - every challenge has a low-code and a code-first path          |

## Time budget (default — adjust only if the user overrides)

| Block                           | Minutes | Content                                       |
| ------------------------------- | ------- | --------------------------------------------- |
| Challenge 0 - Secure Foundation | 25      | Project, model, identity, and baseline test   |
| Challenge 1 - Build the MVP     | 35      | First end-to-end agent response               |
| Challenge 2 - Ground It         | 35      | Add one knowledge source and citations        |
| Challenge 3 - Give It Tools     | 35      | Add one authenticated action                  |
| Challenge 4 - Harden & Demo     | 30      | Eval, least privilege, tracing, and demo      |
| Wrap-up                         | 20      | Demos + judging                               |

Rule: the sum of all challenge minutes must equal 150. State the running total
at the top of the generated hack.

## Progressive build contract

Challenges must extend one continuously working solution in dependency order:

1. **Secure foundation:** Deploy only required resources, establish access with
   RBAC and identity, and prove one model request. Never teach pasted keys as a
   temporary shortcut.
2. **Minimal viable agent:** Produce one end-to-end prompt-agent response in the
   first half of Challenge 1. Improve instructions only after that checkpoint.
3. **Grounded increment:** Add one knowledge source and citations while keeping
   the original MVP response path working.
4. **Action increment:** Add one useful tool with agent identity, managed
   identity, `DefaultAzureCredential`, or a managed connection.
5. **Hardening increment:** Add tracing, evaluation, safety tests,
   least-privilege review, and the demo without changing the architecture.

Every challenge states its starting checkpoint, adds one smallest useful
increment, and retests at least one earlier success criterion. Its fallback
preserves the last working checkpoint and supplies only what the next challenge
requires.

## Workflow

1. **Read the input.** Extract: industry/brand, the business problem, the end
   user of the agent, and any named data or systems.
   Before fixing the scenario, apply the
   [CSV-only company identity rules](./az-consolidated/SKILL.md#fictitious-company-identity---csv-only).
   Select the fictitious company only from a valid entry in the repository-root
   `fictitious_company_names.csv`, or verify the identity already recorded in
   the requirements. A prompt brand or example is not an alternative source.
   Record the exact name, domain, derived slug, and catalog provenance in the
   requirements and package contract, then reuse them in all four deliverables.
2. **Fix the scenario.** Write one 2–3 sentence scenario the whole hack hangs
   off. Every challenge must advance that same agent — never switch scenarios
   mid-hack.
3. **Define the solution boundary.** List the fully built coach Foundry
   resources (account, project, model deployment, agent, connections, tools,
   evaluation and identity/RBAC where applicable), the supporting Azure
   resources, and the Foundry resources intentionally omitted from the
   participant package. If a resource is not applicable, state why.
4. **Inventory supporting artifacts.** Create scenario-root `nextsteps.MD`
   from the Skillable template. Name exact files, schemas, synthetic content,
   package paths, Azure targets, creation and installation methods, identity,
   ownership, and acceptance tests. Classify runtime dependencies as
   `deployment-critical`.
5. **Map to the time budget.** Assign the extracted specifics into Challenges
   0–4. If the input has no data source, use the synthetic-data fallback.
6. **Read the Skillable contract** in
   `.github/skills/skillable-lod-authoring/SKILL.md` and select its canonical
   industry slug.
7. **Write each challenge** using
   `.github/skills/skillable-lod-authoring/assets/challenge-page.template.md`
   as the section order and frontmatter contract.
8. **Apply the style rules** in
   `.github/instructions/hack-authoring-instructions.md`.
9. **Emit four file sets** under `packages/`: `coach/`, `participant/`,
   `hack/`, and `coach-guide/`.
10. **Fulfill deployment artifacts.** Create and package every
   deployment-critical entry, wire idempotent load or installation hooks, and
   update its `nextsteps.MD` status to `packaged`.
11. **Create Finale** from the Skillable Finale template. Map every challenge's
   coach notes in the private coach source only.
12. **Self-check** against the checklist below before delivering. Hand both
   deployable projects to the Deploy agent for mandatory `azd up` testing.

## Output file layout

```text
generated-scenarios/<project>/
├─ nextsteps.MD               # Detailed supporting-artifact plan
└─ packages/
   ├─ coach/                     # Complete deployable solution
   ├─ participant/               # Deployable non-Foundry starter
   ├─ hack/                      # Public GitHub-ready participant content
   │  ├─ README.md
   │  ├─ index.md
   │  ├─ _config.yml
   │  ├─ _build.yml
   │  ├─ resources.md
   │  ├─ Allfiles/
   │  └─ Instructions/<industry-slug>/
   │     ├─ 01-secure-foundation.md
   │     ├─ 02-build-the-agent.md
   │     ├─ 03-ground-it.md
   │     ├─ 04-give-it-tools.md
   │     └─ 05-harden-and-demo.md
   └─ coach-guide/               # Private coach documentation
      ├─ README.md
      ├─ index.md
      ├─ _config.yml
      ├─ _build.yml
      ├─ resources.md
      ├─ Allfiles/
      ├─ solution-overview.md
      ├─ deployment-guide.md
      └─ Instructions/<industry-slug>/
         ├─ 01-secure-foundation.md
         ├─ 02-build-the-agent.md
         ├─ 03-ground-it.md
         ├─ 04-give-it-tools.md
         ├─ 05-harden-and-demo.md
         └─ 99-finale.md          # Coach notes for every challenge
```

## Hard rules

- **Never invent** Azure service names, model names, SKUs, quota numbers, or
  doc URLs. Use only models and features confirmed available in Foundry; if
  unsure, write `[verify model availability]` rather than guessing.
- **No credentials, no tenant details, no customer data** in any generated
  content. Prefer Managed Identity / `DefaultAzureCredential` / Key Vault in
  every code sample.
- **Every challenge is independently gradable** — a team that fails Challenge 2
  can still attempt Challenge 3 with a documented fallback.
- **Build an MVP before extensions** — Challenge 1 must produce a useful
   end-to-end response before grounding, tools, evaluation, or polish.
- **Security is progressive, not postponed** — identity, RBAC, and secret safety
   are foundation requirements; Challenge 4 verifies and tightens them.
- **Add one capability at a time** — grounding and tools extend the working MVP
   and each challenge includes a regression check.
- **No challenge exceeds 40 minutes.** If a challenge needs more, split it.
- Code snippets stay under ~15 lines. Longer code belongs in the starter kit,
  not the challenge text.
- The public learner and private coach roots use the same canonical industry
   slug from the Skillable authoring skill.
- Finale is mandatory in the private coach root, prohibited in the public
   learner root, and excluded from challenge hash parity only because it is a
   distinct coach-facing page.
- Keep `nextsteps.MD` at the scenario root with its exact filename. Do not copy
   it into a learner or coach documentation root.
- Every deployment-critical artifact must exist at all listed package paths
   before deployment handoff. Optional release enrichment may remain planned
   only when no challenge or deployed acceptance path depends on it.
- Planned artifact work never replaces coach and participant `azd up`
   deployment and artifact-specific acceptance testing.

## Pre-delivery checklist

- [ ] Challenge minutes sum to 150
- [ ] Scenario is identical across all challenges
- [ ] The coach solution is a complete, runnable Foundry-agent implementation,
   not only a challenge design
- [ ] The participant package retains every required non-Foundry resource and
   omits every Foundry resource, dependency, output, and role assignment
- [ ] Hacker file set contains no coach answers, secrets, environment state,
   tenant details, subscription IDs, deployed endpoints, or local paths
- [ ] Coach guide documents the complete solution and deployment process
- [ ] Coach guide challenge files exactly match the canonical hacker files
- [ ] Both documentation roots contain the required Skillable/Jekyll root files
- [ ] Challenge pages use valid `lab` frontmatter beneath the selected industry
   folder in `Instructions`
- [ ] Private `99-finale.md` maps coach notes to every challenge
- [ ] Public learner content contains no Finale page or coach notes
- [ ] Scenario-root `nextsteps.MD` inventories all supporting artifacts with
   exact files, schemas, fake-data constraints, Azure targets, package paths,
   creation, installation, identity, validation, acceptance, and ownership
- [ ] Every deployment-critical artifact is packaged and wired to an
   idempotent load or installation path
- [ ] Handoff requires `azd up` for the coach and every participant manifest
   entry plus post-deployment artifact validation
- [ ] Challenge 0 states that participants deploy the supporting package to a
   dedicated participant resource group before creating Foundry resources
- [ ] Challenge 0 proves model access with identity and RBAC but no pasted keys
- [ ] Challenge 1 reaches a minimal viable end-to-end response before refinement
- [ ] Challenges 2-4 each preserve and retest an earlier working capability
- [ ] Challenge 4 hardens the accumulated solution instead of redesigning it
- [ ] Coach and participant deployment instructions use distinct azd
   environment names and distinct resource groups
- [ ] Each challenge has: time badge, goal, why-it-matters, steps, success
      criteria, hints (collapsed), stretch goal
- [ ] Both a portal path and an SDK path in every build challenge
- [ ] Success criteria are observable ("the agent cites the PDF"), not vague
      ("the agent works well")
- [ ] No secrets, no fabricated links, no confidential content
- [ ] Emoji, heading levels, and callouts match the style guide

## References

- `.github/instructions/hack-authoring-instructions.md` — authoring style and
   public-content rules
- `.github/skills/skillable-lod-authoring/SKILL.md` — GitHub, industry folder,
   frontmatter, Finale, and validation contract
- `.github/skills/skillable-lod-authoring/assets/challenge-page.template.md` —
   exact challenge page skeleton
- `.github/skills/skillable-lod-authoring/assets/finale-page.template.md` —
   exact private coach Finale skeleton
- `.github/skills/skillable-lod-authoring/assets/nextsteps.template.MD` —
   scenario-level supporting-artifact and delivery plan
- `.github/skills/skillable-lod-authoring/references/scenario-artifact-inventory.md` —
   service-specific artifact detail and deployment rules
