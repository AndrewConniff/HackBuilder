# Challenge Template — fill, do not restructure

Two skeletons: the hack landing page, then the per-challenge file. Section order
is fixed. Omit nothing; if a section is thin, tighten the wording instead.

---

## A. Hack landing page — `README.md`

```markdown
# 🏟️ <Hack Name>

**Build an Azure AI Foundry agent that <one-line outcome>.**

> ⏱️ **3 hours** · 5 challenges · Microsoft Foundry · All skill levels

## 💡 The scenario

<2–3 sentences. Who the customer is, what hurts today, what the agent must do.
This scenario is identical in every challenge file.>

## ⏱️ Schedule

| Block | Time | What you're doing |
|---|---|---|
| Kickoff | 10 min | Scenario, rules, team setup |
| Challenge 0 — Setup & Deploy | 25 min | Foundry project + model deployment |
| Challenge 1 — Build the Agent | 35 min | Instructions, persona, reasoning |
| Challenge 2 — Ground It | 35 min | Knowledge source + citations |
| Challenge 3 — Give It Tools | 35 min | MCP or OpenAPI action |
| Challenge 4 — Harden & Demo | 30 min | Eval, safety, demo script |
| Wrap-up | 20 min | Demos and judging |
| **Total** | **180 min** | |

## 🎒 Prerequisites

| Requirement | Details | Applies to |
|---|---|---|
| Laptop + internet | Bring your own | Everyone |
| Azure subscription | Model quota available (100k–300k TPM) | Everyone |
| VS Code | Recommended editor | Code-first |
| Python 3.10+ | For the Foundry SDK | Code-first |
| Azure CLI | `az login` for auth | Code-first |

## ⚠️ Security & confidentiality

- No keys, secrets, connection strings, or subscription IDs in any repo or slide
- No customer data or PII — use synthetic data
- Authenticate with Managed Identity or `DefaultAzureCredential`

## 🎯 Challenges

| # | Challenge | Time | You'll finish with |
|---|---|---|---|
| 0 | [Setup & Deploy](challenges/challenge-00-setup.md) | 25 min | A Foundry project + deployed model |
| 1 | [Build the Agent](challenges/challenge-01-build-the-agent.md) | 35 min | An agent that reasons through the task |
| 2 | [Ground It](challenges/challenge-02-ground-it.md) | 35 min | Answers grounded in your data, with citations |
| 3 | [Give It Tools](challenges/challenge-03-give-it-tools.md) | 35 min | An agent that takes a real action |
| 4 | [Harden & Demo](challenges/challenge-04-harden-and-demo.md) | 30 min | Evals, safety, and a 3-minute demo |

## 🏆 Judging

| Criterion | Weight |
|---|---|
| Meets the challenge requirements | 25% |
| Reasoning & multi-step thinking | 25% |
| Creativity & originality | 20% |
| Experience & presentation | 15% |
| Technical implementation | 15% |

## 📚 Resources

See [resources.md](resources.md).
```

---

## B. Per-challenge file — `challenge-NN-<slug>.md`

```markdown
# 🧠 Challenge 02 — Ground Your Agent

> ⏱️ **35 minutes** · Challenge 2 of 5 · Difficulty: ●●○ · Path: Low-code + Code-first

**By the end of this challenge your agent will answer <scenario question> using
your own documents, and show where the answer came from.**

## 🎯 Goal

<One sentence. The observable outcome, not the activity.>

## 💡 Why this matters

<2 sentences max. The real-world reason grounding beats a bigger prompt.>

## 🧭 Choose your path

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

## ✅ Done when

- [ ] <Observable, checkable in under 60 seconds>
- [ ] <Observable>
- [ ] <Observable — include one negative test, e.g. graceful "I don't know">

## 💬 Stuck?

<details><summary>Hint 1 — nudge</summary><...></details>
<details><summary>Hint 2 — narrower</summary><...></details>
<details><summary>Hint 3 — the answer</summary><...></details>

## 🌟 Stretch goal

<One optional add-on for fast teams. Must not be a prerequisite for Challenge 3.>

## 🔁 Fallback

<If this challenge fails, what the team does so Challenge 3 still works.
Every challenge needs this — no team gets stranded.>
```

---

## C. Fill rules

| Placeholder | Source |
|---|---|
| Hack name | From the user's input topic; 2–4 words, arena-flavored |
| Scenario | Derived from the input; never swapped between challenges |
| Industry/brand specifics | From the input only — never invented |
| Data source | From the input; if absent, use the synthetic-data fallback |
| Model names | Only models confirmed available in Foundry; else `[verify model availability]` |
| Links | Only approved domains (see style guide §11) |

## D. Synthetic-data fallback (use when the input names no data source)

> [!TIP]
> No dataset for this scenario? Generate one — a short Word doc or spreadsheet
> of <domain> content via Copilot — and attach it to your agent with File Search.
> Web grounding via a search tool is a valid alternative.
