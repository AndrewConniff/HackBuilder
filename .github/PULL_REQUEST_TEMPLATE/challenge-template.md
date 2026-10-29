# Challenge Template — fill, do not restructure

Two skeletons: the hack landing page, then the per-challenge file. Section order
is fixed. Omit nothing; if a section is thin, tighten the wording instead.

> [!IMPORTANT]
> Apply the frontmatter and complete page contract from
> `.github/skills/skillable-lod-authoring/assets/challenge-page.template.md`.
> This file preserves the Foundry challenge content pattern only.
> Use plain headings, prose and navigation; preserve functional badges,
> checkboxes and alert callouts. Keep the approved industry/business-unit scope.

---

## A. Hack landing page — `README.md`

```markdown
# <Hack Name>

**Build an Azure AI Foundry agent that <one-line outcome>.**

> ⏱️ **3 hours** · 5 challenges · Microsoft Foundry · All skill levels

## The scenario

<2–3 sentences. Who the customer is, what hurts today, what the agent must do.
This scenario is identical in every challenge file.>

## Schedule

| Block | Time | What you're doing |
|---|---|---|
| Kickoff | 10 min | Scenario, rules, team setup |
| Challenge 0 — Secure Foundation | 25 min | Project, model, access, and baseline test |
| Challenge 1 — Build the MVP | 35 min | First end-to-end agent response |
| Challenge 2 — Ground It | 35 min | Add one knowledge source + citations |
| Challenge 3 — Give It Tools | 35 min | Add one authenticated action |
| Challenge 4 — Harden & Demo | 30 min | Eval, least privilege, tracing, and demo |
| Wrap-up | 20 min | Demos and judging |
| **Total** | **180 min** | |

## Prerequisites

| Requirement | Details | Applies to |
|---|---|---|
| Laptop + internet | Bring your own | Everyone |
| Azure subscription | Model quota available (100k–300k TPM) | Everyone |
| VS Code | Recommended editor | Code-first |
| Python 3.10+ | For the Foundry SDK | Code-first |
| Azure CLI | `az login` for auth | Code-first |

## Security & confidentiality

- No keys, secrets, connection strings, or subscription IDs in any repo or slide
- No customer data or PII — use synthetic data
- Authenticate with Managed Identity or `DefaultAzureCredential`

## Challenges

| # | Challenge | Time | You'll finish with |
|---|---|---|---|
| 0 | [Secure Foundation](Instructions/<industry-slug>/00-secure-foundation.md) | 25 min | Access and baseline |
| 1 | [Build the MVP](Instructions/<industry-slug>/01-build-the-agent.md) | 35 min | End-to-end response |
| 2 | [Ground It](Instructions/<industry-slug>/02-ground-it.md) | 35 min | Grounded citations |
| 3 | [Give It Tools](Instructions/<industry-slug>/03-give-it-tools.md) | 35 min | Authenticated action |
| 4 | [Harden & Demo](Instructions/<industry-slug>/04-harden-and-demo.md) | 30 min | Evaluation and demo |

## Build progression

| Stage | Add only | Preserve from earlier stages |
|---|---|---|
| Foundation | Required resources, access, and one model test | A repeatable starting checkpoint |
| MVP | Minimal instructions and one end-to-end response | Foundation access and model test |
| Grounded | One knowledge source with citations | The ungrounded MVP still responds |
| Action-enabled | One tool using identity or a managed connection | MVP and grounding behavior |
| Hardened | Evals, tracing, least privilege, and negative tests | Every earlier success check |

## Judging

| Criterion | Weight |
|---|---|
| Meets the challenge requirements | 25% |
| Reasoning & multi-step thinking | 25% |
| Creativity & originality | 20% |
| Experience & presentation | 15% |
| Technical implementation | 15% |

## Resources

See [resources.md](resources.md).
```

---

## B. Per-challenge file — `Instructions/<industry-slug>/NN-<slug>.md`

````markdown
# Challenge 02 — Ground Your Agent

> ⏱️ **35 minutes** · Challenge 2 of 5 · Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge your agent will answer <scenario question> using
your own documents, and show where the answer came from.**

## Goal

<One sentence. The observable outcome, not the activity.>

## Why this matters

<2 sentences max. The real-world reason grounding beats a bigger prompt.>

## Build on what works

**Starting checkpoint:** <The observable result learners already have.>

**Smallest useful increment:** <The one new capability added in this challenge.>

**Keep working:** <The earlier success check that must still pass.>

## Choose your path

**Path A — Foundry portal (low-code)**

### Step 1 — <verb phrase>
<1–3 lines. One primary inline link max.>

### Step 2 — <verb phrase>
<...>

### Step 3 — <verb phrase>
<...>

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

```python
# ≤ 15 lines. DefaultAzureCredential only. <YOUR_PROJECT_ENDPOINT> placeholders.
```
</details>

> [!TIP]
> <One shortcut that saves 5+ minutes. Max 2 callouts per file.>

## Done when

- [ ] <Observable, checkable in under 60 seconds>
- [ ] <Observable>
- [ ] <Observable — include one negative test, e.g. graceful "I don't know">
- [ ] <Regression check proving the previous challenge still works>

## Stuck?

<details><summary>Hint 1 — nudge</summary><...></details>
<details><summary>Hint 2 — narrower</summary><...></details>
<details><summary>Hint 3 — the answer</summary><...></details>

## Stretch goal

<One optional add-on for fast teams. Must not be a prerequisite for Challenge 3.>

## Fallback

<If this challenge fails, what the team does so Challenge 3 still works.
Every challenge needs this — no team gets stranded.>
````

---

## C. Fill rules

| Placeholder | Source |
| --- | --- |
| Hack name | From the user's input topic; 2–4 words, arena-flavored |
| Scenario | Derived from the input; never swapped between challenges |
| Industry/brand specifics | From the input only — never invented |
| Business units and personas | Approved scope; Generic is an industry workflow without unit targeting |
| Data source | From the input; if absent, use the synthetic-data fallback |
| Model names | Only models confirmed available in Foundry; else `[verify model availability]` |
| Links | Only approved domains (see style guide §11) |
| Progression | One working increment per challenge; never rebuild from scratch |

## D. Synthetic-data fallback (use when the input names no data source)

> [!TIP]
> No dataset for this scenario? Generate one — a short Word doc or spreadsheet
> of {domain} content via Copilot — and attach it to your agent with File Search.
> Web grounding via a search tool is a valid alternative.

## E. Required build order

1. Challenge 0 creates only the required foundation and proves model access.
   It establishes RBAC, identity, and secret-safety prerequisites; these are
   never postponed to the final challenge.
2. Challenge 1 produces a minimal viable agent in the first half of the timebox.
   Learners improve instructions only after one end-to-end response succeeds.
3. Challenge 2 adds one grounding source to the working MVP and verifies a
   citation without breaking the original response path.
4. Challenge 3 adds one useful action. Authentication uses agent identity,
   managed identity, `DefaultAzureCredential`, or a managed connection, never
   a pasted key.
5. Challenge 4 adds tracing, repeatable evaluation, safety tests, least-privilege
   review, and the demo. It hardens the accumulated solution rather than
   introducing a new architecture.

Every fallback must preserve the previous checkpoint and provide the minimum
artifact needed to continue. Every challenge must include a regression check
for at least one earlier capability.

## F. Finale

Create the coach-only `Instructions/<industry-slug>/99-finale.md` from the
Skillable Finale template. It contains coach notes for Challenges 0 through 4
and must not appear in the public learner package.
