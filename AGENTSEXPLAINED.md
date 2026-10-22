# ABC Builder customization and execution map

## One workflow, three phases

Select **az-01-conductor** and ask "build me a hack for ...".
The [workflow contract](.github/skills/hack-builder-workflow/SKILL.md) is the
single authority for ordering, review, approval, resumption and completion.

| Phase | User receives | Exit condition |
| --- | --- | --- |
| A: reference | Story, architecture, IaC, app, deployment, tests, demo guide | Explicit suitability approval |
| B: hack authoring | Minimum starter, challenges, learner/coach guides | Local package validation |
| C: optional rollout | Isolated coach and numbered team environments | Separate request and live acceptance |

Deployment confirmation is not scenario approval. Package creation is not event
deployment consent. Missing state on an existing scenario means unreviewed,
not implicitly approved. The helper in
[`scripts/hack_workflow.py`](scripts/hack_workflow.py) fingerprints the reference
and rejects missing or stale approval before authoring.

## Exactly two canonical agents

All active definitions live in [`.github/agents/`](.github/agents/). Both are
user-invocable, have `agents: []`, expose no delegation tool, and inherit the
host's configured model preferences without pins.

| Stable agent name | Visible role and responsibility | Phase |
| --- | --- | --- |
| `az-01-conductor` | Scenario orchestrator: story through live demonstration | A; explicitly requested C |
| `HackCreator Agent` | Hack composition: approved reference to starter and materials | B only |

The scenario orchestrator owns requirements, architecture, AVM-first Bicep, both
diagrams, application development, authorized deployment, runtime acceptance and
demonstration. The composition agent distills the minimum starter and authors
challenges, learner content and private coach materials only after approval.
Each performs every procedure directly in its own context through skills.
There is no specialist fanout, deployment agent, nested conductor or automatic
cross-agent handoff. Scenario jobs stop at review; they never auto-start composition.

On **2026-10-22**, the former requirements, architecture, diagram, Bicep,
development, deployment, demonstration and contribution agent bodies were moved
into their owning skills' `references/historical-*.md`. These preserve technical
detail and original historical text; their old frontmatter/tool lists/roles/
first-action gates/handoffs are not active instructions. The old conductor body
is historical workflow evidence, not a runnable pipeline. Composition procedure
content lives in the authoring skill's `references/composition-procedure.md`.

## Skills: canonical procedures and resources

ABC Builder is the product name. `az-01-conductor`, `HackCreator Agent`,
canonical skill folder IDs, executable script names and environment variables
remain stable compatibility APIs; branding does not rename them.
See the [ABC Builder overview](ABC-Builder-README.md).

Canonical reusable knowledge lives under [`.github/skills/`](.github/skills/).
Discoverable skills use `<name>/SKILL.md`, with matching folder and skill names.
Discovery does not prove invocation: the host may load a skill on demand, or an
agent can explicitly read it. Reload customizations/start a new chat after changes.

| Skill | Role |
| --- | --- |
| `hack-builder-workflow` | Phase boundaries and approval; invoked for "build a hack" |
| `azure-foundry-hack-builder` | Post-approval challenge/content rules |
| `skillable-lod-authoring` | Page templates, industry catalog, private Finale, validator |
| `az-consolidated` | Technical defaults, AVM, synthetic identity catalogs, diagram patterns |
| `az-scenario-requirements` | Story, industry, services/WAF intake and requirements evidence |
| `az-scenario-architecture` | Reference design, identity/data flows, SKUs, cost and WAF trade-offs |
| `az-scenario-bicep` | Governance, AVM-first IaC, azd wiring and local validation |
| `az-azure-diagrams` | Architecture/runtime and standalone diagrams |
| `az-webapp-development` | .NET scaffolding and azd application wiring |
| `az-azure-deploy` | Deployment mechanics and recovery |
| `az-azure-validate` | Pre/post-deployment checks |
| `az-scenario-demonstration` | Business walkthrough, evidence and recovery runbook |
| `az-scenario-contribution` | Explicitly requested publication and registry PR via gh CLI |
| `az-multi-team-deployment` | Post-approval manifest planning and explicitly requested event rollout |

Former public skill names `azd-demo-builder`, `webapp-development`,
`azure-deploy` and `azure-validate` now match their existing canonical directory
names above. Explicit file references stay valid; use the new names for skill
invocation. The formerly loose `azure-foundry-hack-builder-SKILL.md` is now a
proper skill folder. Its former location was not a standard discoverable skill,
although HackCreator explicitly read it.

The `az-azure-artifacts` directory is a template library, **not** a discoverable
skill: it has no `SKILL.md`. `az-azure-diagrams` now has a concise discovery entry
that reuses the existing scripts/references. The application companion
`az-webapp-development/app-creation-SKILL.md` is explicitly read by the scenario
orchestrator, not a separately discoverable `app-creation` skill.

## The colleague's `.agents/skills` directory

These files are **skills, not agents**. Both `.github/skills` and `.agents/skills`
are supported skill locations, and workspace settings now explicitly list both.
Previously the settings listed only `.github/skills`, but the test session
explicitly read `.agents/skills/run-conductor/SKILL.md` eight times. Both sources
therefore affected the run; presence/settings alone cannot establish precedence.

All seven alternate skills are manual-only (`disable-model-invocation: true`):

| Launcher | Canonical target |
| --- | --- |
| `run-conductor` | `az-01-conductor` and the workflow contract |
| `assess-architecture` | Load `az-scenario-architecture` directly |
| `generate-bicep` | Load `az-scenario-bicep` directly |
| `generate-webapp` | Load `az-webapp-development` directly |
| `generate-demoguide` | Load `az-scenario-demonstration` directly |
| `design-diagram` | Load `az-azure-diagrams` directly |
| `oilgas-field-ops-agent` | Oil/gas business input to `az-01-conductor` |

They now contain only routing and boundary reminders, not duplicate pipelines.
The original oil/gas scenario is preserved as a clearly marked
[historical input reference](.github/skills/hack-builder-workflow/references/oilgas-legacy-input.md),
not an active workflow.

## Local portal and industry boundary

Industry and `businessUnits` are independent intake dimensions. Use the exact
[workflow unit IDs and Generic exclusivity](.github/skills/hack-builder-workflow/SKILL.md):
Generic means an industry workflow without unit targeting. Scope flows into
requirements, personas, business story, app/data, tests and learner/coach content.

The portal's read-only catalog discovers
`generated-scenarios\*\scenario-manifest.json`, schema version 1. Workers curate
title, summary, industry, businessUnits, services, pillars, domains, reference-only
artifact paths and nullable `{scenarioId, manifestDigest}` source provenance via
`scripts\scenario_catalog.py refresh --metadata`. Inferred entries stay visibly
`needs-review` until curated. Discovery and source selection grant no consent.
Adaptations use source architecture as read-only guidance and regenerate target
business app/data, refresh technical evidence and require new design, validation
and approval. Never inherit source deployment state, secrets, scopes, approvals,
packages or runtime success.

The optional [local portal entry point](portal/README.md) launches the same two
agent contexts. From the repository root:

```powershell
copilot login
python scripts\portal_server.py
```

Open the printed private loopback URL; keep its token confidential. Local tool
consent is not an OS sandbox or automatic Azure deployment authorization.
Separate gates apply: local design confirmation, authorized exact-target cloud preparation,
deployment consent after actual what-if/cost review, then explicit suitability approval of
the working scenario before composition. Event rollout still requires a separate request.

Interactive scenario-agent sessions now start or reuse the local portal through
an agent-scoped `sessionStart` hook. The idempotent helper is
`python scripts\start_portal.py`; it opens the authenticated entry point without
printing the private token. Hosts must trust the workspace and permit scoped
hooks. The agent instructions provide a once-per-task fallback when hooks do not
execute. Portal-launched CLI jobs set `HACKBUILDER_PORTAL_JOB=1` and skip startup.
The detached process is local tooling, not a system service or hosted web app.
See the [portal lifecycle and stopping instructions](portal/README.md).

Startup verification on **2026-10-22** confirmed authenticated health, reuse of
the same live PID, and actual scenario-agent execution of the fallback helper
with only the shell tool available. The installed CLI deferred `sessionStart`
hooks at its workspace-trust gate, including the one-session trust smoke test.
That test does not prove scoped-hook execution; the fallback was exercised
successfully instead. No Azure operations or scenario jobs ran in these tests.

The lightweight LOCAL web portal collects prompt, validated project slug,
industry, selected services and WAF priorities. Its local authenticated backend
launches actual Copilot CLI jobs using the two stable agent names:
`--agent az-01-conductor --prompt <text>` or `--agent "HackCreator Agent"`.
The CLI supports `--output-format text/json`, `--allow-all-tools` and
`--no-ask-user`; none of these flags grants scenario approval or deployment consent.

Initial jobs allow local preparation only by instruction, not a sandbox.
Tool execution requires explicit portal permission. Prepare reference artifacts
and what-if commands/targets; stop before Azure operations unless explicitly
authorized. A separate follow-up confirms exact deployment targets after what-if.
In noninteractive jobs, return **decision required** and stop for missing user
decisions; an unavailable question tool is never permission to guess.

The portal is the normal decision surface and scenario-level progress dashboard.
Workers report structured stages and decisions with `scripts\portal_workflow.py`.
Versioned intake/history and scoped authorizations persist separately from run logs and
suitability evidence. A writer lease and revision checks coordinate cooperating portal/VS Code
work; arbitrary filesystem editors are not sandboxed. Refresh is read-only and CLI exit zero
does not prove stage success. Local design uses public provisional region/model evidence;
account/quota/budget checks are deferred until authorized cloud preparation.

The backend approval action records the explicit suitability response against the
reviewed fingerprint, checks approval and then starts a separate composition job.
The portal never auto-approves scenarios or deploys events.
Use `generated-scenarios\{projectSlug}` without silently deriving a new slug.

The intake catalog is repository `microsoft_industry_verticals.csv`. Skillable
currently supports six slugs: `financial-services`, `healthcare`, `manufacturing`,
`retail`, `energy-oil-gas` and `government-public-sector`. Unsupported selections
block composition pending an explicit support-extension or revised/reapproved
scenario decision. Never silently map another industry.

## Instructions: discovery versus explicit reading

| Surface | Activation and ownership |
| --- | --- |
| `AGENTS.md` | Repository-wide conventions in hosts that support it |
| `.github/copilot-instructions.md` | Copilot repository defaults and entry-point routing |
| `az-agent-research-first.instructions.md` | Matching agent/skill/scenario Markdown; bounded evidence reuse |
| `az-foundry.instructions.md` | Matching Azure/agent artifacts; current resource model and phase-specific acceptance |
| `hack-authoring.instructions.md` | Package/contract/inventory content; also explicitly read by authoring |
| `az-markdown.instructions.md` | Markdown style and template requirements |
| Bicep, .NET, PowerShell, Python instructions | Their matching file types |
| `az-code-commenting.instructions.md` | Cross-cutting comment guidance |
| `az-azure-artifacts.instructions.md` | Generated artifact template headings |
| `style-guide.md` | Explicit authoring reference, not an automatically applied instruction file |

The former `hack-authoring-instructions.md` was a personal-instruction note
without discovery metadata. It now has scoped frontmatter and the conventional
`.instructions.md` suffix. It no longer directs agents to search personal mail
or Teams for missing scenario context.

Earlier guidance referenced nonexistent `AGENTS.md`, default-account/policy
instruction files, Microsoft-docs/code-reference skills and npm lint commands.
The repository guide now exists. Active workflow agents use available official
documentation/metadata tools and confirmed Azure targets instead of retrying
missing resources. A locally supplied default-account rule is still honored;
its absence requires explicit target confirmation, not an invented account.

## Evidence from the October 21 test

Source: the local retail test session starting **2026-10-21 15:44:29 UTC**,
with activity through **2026-10-22 04:39:44 UTC**. Debug-export logs were not
present in the checked VS Code log directories; the findings below use the
session's persisted event history. This is one test, not a performance benchmark.
No private prompts, resource identifiers, deployed URLs or credentials are
copied here.

Observed invocations included the conductor, Validations, HackCreator plan,
Architect and several general-purpose implementation/deployment/repair agents.
The log explicitly recorded loading the old-name skills `azure-deploy` (9),
`az-multi-team-deployment` (6), `azd-demo-builder` (4), `azure-validate` (4),
`skillable-lod-authoring` (2) and `webapp-development` (1).
Those counts do not include every explicit file read. The event history does
not independently prove every scoped instruction was injected.

Explicit read attempts also show the effective cross-cutting context:
consolidated skill (26), Markdown instructions (23), Foundry instructions (18),
research instructions (13), artifact instructions (13), and Bicep instructions
(12). The missing default-account instruction was requested six times.
These are attempted file reads, not counts of successful instruction injection.

| Observation | Measured evidence | Change |
| --- | --- | --- |
| Broad run | About 12h55 elapsed, including pauses/resumes | Separate phase time from waits |
| User-response waits | 8 forms; 175.5 min total; longest 137.9 min | Keep gates; exclude waits from compute |
| Early hack planning | About 14m22 across two plan workers before architecture | No pre-approval HackCreator |
| Requirements repeats | About 29m35 across validation and replacement writer | One owner, persisted evidence |
| Unavailable model pins | Four failures named an unavailable pinned model | Inherit host model preferences |
| Tool-call failure | One task lacked a required name | Remove implementation subagent delegation |
| Heavy re-reading | 595 view calls, 28 failed; 66 searches | Reuse valid evidence; fix stale mandatory paths |
| Nested execution | 20 task calls; summed spans about 244 min | Two direct skill-driven contexts; no fanout |
| Deployment/bootstrap effort | Bootstrap span about 32m52 | Preflight tools, identity and deployment wiring once |
| Azure capacity | Search S1 failed in-region, then again on retry | Recheck constrained supporting services |
| App not proven | Repairs needed after infrastructure deployment | Test model, agent, chat and error path |
| Private ingestion | Upload failed with data-plane authorization/network evidence | Test actual principal/path first |
| Recovery spans | Chat about 48m19; ingestion about 14m40 | Repair components, not whole environments |

Tool durations overlap parent/child work and may include waiting. They must not
be added together or represented as pure model time. The Architect's recorded
span lasted several hours across interrupted work; it does not establish hours
of active architecture computation. Some "successful" shell tool calls contained
failing deployment commands, so tool success was not treated as Azure success.

The refactored contract prohibits pre-approval packaging and automatic team fan-out. It
does not promise a fixed build duration or eliminate Azure capacity/network
delays. The same Standard/private-network requirements still need real proof.
Current [Foundry setup guidance][foundry-setup] confirms that Standard requires
customer-owned Storage, Search and Cosmos; a smaller design must not silently
discard required security or data-ownership constraints.

## Verification

The **2026-10-22** two-agent refactor is configuration and local regression work.
The October 21 invocation counts above describe the old flow only. No new actual
agent invocation, Azure deployment, performance gain or portal acceptance is
claimed from those historical logs.

Run the focused repository tests:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py"
python .github\skills\skillable-lod-authoring\scripts\validate_skillable_package.py --check-skill
```

These verify local workflow guards and customization contracts, not real cloud
deployment or deterministic LLM compliance. Test the new end-to-end agent flow
in a fresh chat against an explicitly authorized Azure target.

[foundry-setup]: https://learn.microsoft.com/azure/foundry/agents/environment-setup
