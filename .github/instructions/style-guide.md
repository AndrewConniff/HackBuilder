# Style Guide — UI, Text & Layout for Foundry Hack Challenges

This is the visual and voice contract. Every generated challenge must match it.

---

## 1. Voice & tone

- **Second person, present tense, imperative.** "Deploy the model." Not "The
  participant should deploy the model."
- **Arena energy, not corporate.** Short punchy lines. "You have 35 minutes.
  Ship it." Never cheesy — no forced hype, no exclamation stacking.
- **Sentence case for all headings.** Except the challenge title, which is
  Title Case.
- **Max 2 sentences per paragraph.** If it's longer, it becomes a list.
- **No hedging.** Cut "you may want to", "it might be a good idea to".
- **Reading level:** assume smart, time-pressured, possibly new to Foundry.
  Define a Foundry-specific term the first time it appears, once, in one clause.

---

## 2. Heading hierarchy (fixed)

Skillable pages begin with the `lab` YAML frontmatter from the canonical
challenge or Finale template. The first Markdown heading after frontmatter is
the single H1.

```markdown
# Challenge 02 — Ground Your Agent           <- H1, one per file, number + em dash
## Goal                                     <- H2, fixed section names
### Step 1 — Create the knowledge source      <- H3, numbered steps, em dash
#### (avoid)                                  <- do not go deeper than H3
```

- One H1 per file. Never skip a level.
- Section H2s always appear in the canonical Skillable template order, even if
  short.
- Steps are `### Step N — <verb phrase>`. Always start with a verb.

---

## 3. Clean participant documentation

Use plain-text headings, prose and navigation without decorative emoji.
Keep section names and ordering from the canonical templates. Do not prepend
icons to challenge titles, resource links, status labels or menu items.

Preserve functional time/difficulty badges, Markdown checkboxes and GitHub alert
callouts. They communicate timing, completion or risk rather than decoration.
Use meaningful alt text for instructional images.

---

## 4. The time badge (top of every challenge, verbatim format)

```markdown
> ⏱️ **35 minutes** · Challenge 2 of 5 · Difficulty: ●●○ · Path: Low-code + Code-first
```

- Difficulty uses filled/empty circles only: `●○○` `●●○` `●●●`.
- Always show "N of 5" so teams can pace themselves.

---

## 5. Layout rules

- **Front-load the outcome.** The first 3 lines of a challenge tell the team
  what they will have working at the end. Context comes after.
- **One screen per section.** Nothing between two H2s should exceed ~20 lines.
- **Tables for anything with 2+ parallel attributes** (prereqs, model options,
  tool comparisons). Never a bulleted list of "X — description" pairs.
- **Numbered steps for sequence, bullets for options.** Never mix.
- **Max 6 steps per challenge.** More than 6 means the challenge is too big.
- Horizontal rule `---` between H2 sections on the hack README only; not inside
  a single challenge file.

---

## 6. Callouts (GitHub alert syntax — the only callout style allowed)

```markdown
> [!TIP]
> No data source? Generate a synthetic one with Copilot and upload it to File Search.

> [!IMPORTANT]
> Deploy your model before starting — quota approval can take several minutes.

> [!WARNING]
> Never paste keys into the playground. Use Managed Identity.
```

- Use `TIP` for shortcuts, `IMPORTANT` for blockers, `WARNING` for security only.
- Max 2 callouts per challenge. More and they stop being read.

---

## 7. Dual-path blocks (mandatory in every build challenge)

Always present the portal path first, code second, as collapsed tabs-by-heading:

````markdown
## Choose your path

**Path A — Foundry portal (low-code)**

1. ...

<details>
<summary><b>Path B — Foundry SDK (code-first)</b></summary>

```python
# ≤ 15 lines, no secrets, DefaultAzureCredential only
```

</details>
````

Code-first is always inside `<details>` so the portal path stays the visual
default and the page stays short.

---

## 8. Hints

Hints are always collapsed, always progressive (3 levels, increasingly explicit):

```markdown
## Stuck?

<details><summary>Hint 1 — nudge</summary>Check where the agent's knowledge source is attached.</details>
<details><summary>Hint 2 — narrower</summary>File Search needs the file indexed on the agent, not the thread.</details>
<details>
<summary>Hint 3 — the answer</summary>
In the portal, open Agent → Knowledge → Add → Files, then re-run.
</details>
```

Never reveal an answer outside a `<details>`.

---

## 9. Success criteria style

Checklist, observable, testable in under 60 seconds each:

```markdown
## Done when
- [ ] Your agent returns an answer that cites at least one uploaded document
- [ ] The citation appears in the response, not just in the trace
- [ ] A question outside the knowledge base returns a graceful "I don't know"
```

Never write "the agent works correctly" or "the output is good quality".

---

## 10. Code fence rules

- Always language-tagged with `python`, `bash`, `json`, or `markdown`.
- Placeholders in `UPPER_SNAKE` wrapped in angle brackets: `<YOUR_PROJECT_ENDPOINT>`.
- Never a real endpoint, key, subscription ID, or tenant ID — not even a fake
  realistic-looking one.
- `az` and `pip` commands go in a single fenced block per step, not split.

---

## 11. Links

- Descriptive text, never bare URLs, never "click here".
- Only `learn.microsoft.com`, `ai.azure.com`, `github.com/microsoft|azure-samples`,
  and `aka.ms` links. Anything else needs the user's explicit OK.
- All resource links collect at the bottom under `## Resources`, grouped as
  **Docs**, **Samples**, **Community**. Inline links are allowed only for the
  single primary action of a step.

---

## 12. Length targets

| File | Target |
| --- | --- |
| Hack `README.md` | 150–250 lines |
| Each challenge file | 60–110 lines |
| `resources.md` | under 80 lines |

If a challenge file exceeds 110 lines, move detail into hints or the starter kit.

---

## 13. Never do

- Wall-of-text paragraphs longer than 3 lines
- Nested bullets deeper than 2 levels
- Screenshots referenced but not provided (`![screenshot](TODO.png)`)
- A step that depends on a resource created in an *optional* earlier step
- Marketing copy about Azure — teams are already in the room
- Any mention of judging or prizes inside a challenge file (that lives in README)
