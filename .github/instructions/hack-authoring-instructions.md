# Hack Authoring — Personal Instructions

Add this to your personal instructions file (`copilot-instructions.md`). These are
always-on defaults; the detailed layout rules live in the
`azure-foundry-hack-builder` skill.

---

## Hack authoring defaults

When I ask for a hack, hackathon, challenge, lab, or workshop, assume:

- **Platform is always Microsoft Foundry / Azure AI Foundry.** Never propose
  another platform unless I explicitly name one.
- **The subject is always building AI agents** — instructions, grounding,
  tools/MCP, evaluation, multi-agent. Not model training, not data pipelines,
  not generic app dev.
- **Total length is always 3 hours**, structured as 10 min kickoff + 150 min of
  challenges + 20 min wrap-up and demos.
- **4–5 challenges**, each 25–40 minutes, and the challenge minutes must sum to
  150. Show the running total.
- **Every build challenge offers two paths**: a Foundry portal (low-code) path
  first, and a Foundry SDK (code-first) path collapsed underneath.
- Invoke the `azure-foundry-hack-builder` skill for the actual writing — it
  carries the layout, style, and template.
- Apply `.github/skills/skillable-lod-authoring/SKILL.md` for the GitHub-ready
  repository shape, `lab` frontmatter, industry path, and private Finale.
- Create scenario-root `nextsteps.MD` from the Skillable template. Give every
  supporting artifact an exact filename, detailed schema or structure,
  synthetic-data rules, package destinations, Azure target, creation and
  installation work, tests, owner, classification, and status.

## Non-negotiables in anything hack-related

- Never invent Azure service names, model names, quota figures, or doc URLs.
  Write `[verify]` instead of guessing.
- Never include keys, connection strings, subscription IDs, tenant IDs, endpoints,
  or customer/PII data — in prose, code, or screenshots. Auth examples use
  Managed Identity or `DefaultAzureCredential`.
- Assume the output may land in a public repo. General-level content only.
- Every challenge needs a fallback so a team that fails it can still start the
  next one.
- Every runtime artifact must be `packaged` before deployment. Optional
  follow-up artifacts may remain planned only when no required challenge or
  acceptance path depends on them.
- Planned follow-up work never replaces coach or participant `azd up`
  deployment and testing.

## Default output shape

Deliver the learner and coach content as separate GitHub-ready roots, never as
one long chat response:

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
    │   └── Instructions/<industry-slug>/01-..05-*.md
    └── coach-guide/
        ├── README.md
        ├── index.md
        ├── _config.yml
        ├── _build.yml
        ├── resources.md
        ├── Allfiles/
        └── Instructions/<industry-slug>/
            ├── 01-..05-*.md
            └── 99-finale.md
```

The five numbered coach challenge files are exact copies of the learner pages.
`99-finale.md` is private, contains the coach notes for every challenge, and
must not appear in `packages/hack/`.

## Default writing style

- Second person, imperative, present tense. Sentence case headings.
- Front-load the outcome: the first three lines say what will be working at the end.
- Tables for parallel attributes, numbered steps for sequence, bullets for options.
- Max 6 steps per challenge; max 3 lines per paragraph.
- Success criteria are observable and checkable in under a minute — never
  "works correctly" or "good quality".
- Hints are always collapsed in `<details>`, in three escalating levels.

## Ask me only when

- The input names no industry, scenario, or end user, **and** none can be found
  in my email, Teams, or files.
- I ask for something outside Foundry agents — confirm before switching platform.

Otherwise draft it and mark gaps with visible `[placeholders]`.
