---
name: azure-foundry-hack-builder
description: >
  Generates Azure AI Foundry hack challenge content from a short prompt or a
   topic/scenario input. Produces a complete Azure AI Foundry agent scenario:
   a fully working coach solution and a 3-hour participant hack broken into
   timed challenges, written in the Agents League house style (badge header,
   time budget, scenario, milestones, success criteria, hints, resources).
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

When this skill is used by the Azure Demo Builder, the scenario has two
deliverables that share one design:

- A **coach solution** that fully implements the agent in Azure AI Foundry,
   including its Foundry resources and every supporting Azure resource.
- A **participant hack package** that deploys the same non-Foundry supporting
   resources but intentionally omits every Foundry resource. Its challenges
   teach participants to build that remaining Foundry solution themselves.

The two packages must use separate azd environments and separate resource
groups. A participant deployment must never target, reuse, or modify the
coach resource group.

## Fixed constraints (never negotiate these)

| Constraint | Value |
|---|---|
| Platform | Microsoft Foundry / Azure AI Foundry only (portal + Foundry SDK) |
| Theme | Building AI **agents** — not apps, not fine-tuning, not data engineering |
| Total length | 3 hours (180 min) |
| Structure | 10 min kickoff + 150 min build across challenges + 20 min wrap/demo |
| Challenge count | 4–5 challenges, each 25–40 min |
| Audience | Mixed skill — every challenge has a low-code path and a code-first path |

## Time budget (default — adjust only if the user overrides)

| Block | Minutes | Content |
|---|---|---|
| Challenge 0 – Setup & Deploy | 25 | Foundry project, model deployment, playground |
| Challenge 1 – Build the Agent | 35 | Instructions, persona, reasoning pattern |
| Challenge 2 – Ground It | 35 | File Search / Bing / knowledge source |
| Challenge 3 – Give It Tools | 35 | MCP server or OpenAPI action |
| Challenge 4 – Harden & Demo | 30 | Eval, safety, tracing, demo script |
| Wrap-up | 20 | Demos + judging |

Rule: the sum of all challenge minutes must equal 150. State the running total
at the top of the generated hack.

## Workflow

1. **Read the input.** Extract: industry/brand, the business problem, the end
   user of the agent, and any named data or systems.
2. **Fix the scenario.** Write one 2–3 sentence scenario the whole hack hangs
   off. Every challenge must advance that same agent — never switch scenarios
   mid-hack.
3. **Define the solution boundary.** List the fully built coach Foundry
   resources (account, project, model deployment, agent, connections, tools,
   evaluation and identity/RBAC where applicable), the supporting Azure
   resources, and the Foundry resources intentionally omitted from the
   participant package. If a resource is not applicable, state why.
4. **Map to the time budget.** Assign the extracted specifics into Challenges
   0–4. If the input has no data source, use the synthetic-data fallback.
5. **Write each challenge** using `reference/challenge-template.md` verbatim as
   the section order.
6. **Apply the style rules** in `reference/style-guide.md` — headings, emoji
   set, tables, callouts, code fences, link style.
7. **Emit files** — one `README.md` for the hack, one `challenge-NN-<slug>.md`
   per challenge, plus `resources.md`.
8. **Self-check** against the checklist below before delivering.

## Output file layout

```
<hack-name>/
├─ README.md                  # Arena page: scenario, schedule, prereqs, judging
├─ challenges/
│  ├─ challenge-00-setup.md
│  ├─ challenge-01-build-the-agent.md
│  ├─ challenge-02-ground-it.md
│  ├─ challenge-03-give-it-tools.md
│  └─ challenge-04-harden-and-demo.md
└─ resources.md               # Links, FAQ, help
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
- **No challenge exceeds 40 minutes.** If a challenge needs more, split it.
- Code snippets stay under ~15 lines. Longer code belongs in the starter kit,
  not the challenge text.

## Pre-delivery checklist

- [ ] Challenge minutes sum to 150
- [ ] Scenario is identical across all challenges
- [ ] The coach solution is a complete, runnable Foundry-agent implementation,
   not only a challenge design
- [ ] The participant package retains every required non-Foundry resource and
   omits every Foundry resource, dependency, output, and role assignment
- [ ] Challenge 0 states that participants deploy the supporting package to a
   dedicated participant resource group before creating Foundry resources
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

- `reference/style-guide.md` — UI, text style, layout, tone
- `reference/challenge-template.md` — the exact markdown skeleton to fill
