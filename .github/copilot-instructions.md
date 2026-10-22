# ABC Builder - Copilot instructions

## Entry point and workflow

When a technical user asks to **build a hack**, use `az-01-conductor` as the
scenario orchestrator and read
[the canonical workflow](skills/hack-builder-workflow/SKILL.md).

1. Build the Foundry-oriented story and complete technical reference scenario:
   requirements, architecture, diagrams, Bicep, real application, Azure
   deployment, runtime tests and demo guide.
1. Present the working scenario and **wait for explicit user approval** of its
   suitability for the hack. Deployment consent is not scenario approval.
1. Only after recorded approval, a separate `HackCreator Agent` composition
   context derives the minimum participant starter, challenges, learner guide
   and private coach package. Validate locally.
1. Deploy a coach/team event only on a **separate explicit request**.

Each agent executes all of its phase's work directly through skills; no specialist
delegation, agent fanout or nested orchestrator. The scenario process must not
auto-start composition. Never create a package plan before approval.
Existing packages and selected services are not authorization.

## Customization ownership

- Product branding is ABC Builder. Stable agent names, canonical skill folder
  identifiers, executable script names and environment variables remain compatibility APIs.
- `.github/agents/*.agent.md`: exactly two canonical contexts, scenario orchestrator
  (`az-01-conductor`) and hack composition (`HackCreator Agent`). Both have
  `agents: []` and no delegation tools.
- `.github/skills/*/SKILL.md`: canonical reusable skills.
- `.agents/skills/`: manual compatibility launchers and scenario prompts only;
  no duplicate orchestration or implementation rules.
- `.github/instructions/*.instructions.md`: file-scoped standards.
- `AGENTS.md`: repository conventions and validation commands.
- `AGENTSEXPLAINED.md`: inventory, discovery rules and measured execution findings.

Descriptions enable discovery; a file's presence does not prove invocation.
Use dated session evidence to distinguish discoverable from actually used.
Do not assume missing skill files, policy files or npm scripts exist.

## Local portal and noninteractive execution

The lightweight LOCAL web portal collects prompt, validated project slug,
industry, `businessUnits`, services and WAF priorities. Its local authenticated backend launches
real Copilot CLI jobs using the two stable agent names. This is tooling, not an
Azure-hosted learner/progress application or a sandbox.

Interactive VS Code invocation of `az-01-conductor` automatically opens the
local portal using its scoped startup hook and `scripts\start_portal.py`.
The helper starts or reuses a healthy local server; it does not start a scenario.
For hosts without scoped-hook execution, the agent runs the helper once as its
first interactive action. Portal CLI children set `HACKBUILDER_PORTAL_JOB=1`
and must skip startup, avoiding recursive browser launches.

Initial jobs allow local preparation only by instruction: use
`generated-scenarios\{projectSlug}`, prepare the reference and what-if commands,
then stop before Azure operations unless explicitly authorized. Tool execution
requires explicit portal permission. Separate follow-up confirms exact deployment
targets after what-if. Missing consent or decisions in noninteractive mode means
persist **decision required** and stop, not invent approval.

The portal is the normal decision and scenario-progress surface. Workers consume durable intake,
preferences and all resolved answers and report stages through `scripts\portal_workflow.py`.
Honor project writer leases and revision checks; do not edit a portal-owned scenario in parallel.
Confirm architecture design before implementation. For local construction, record provisional
publicly supported region/model choices; defer account, quota and budget checks to authorized
deployment preparation. Status refresh is read-only. Free-text continuation is not cloud consent.

The portal records explicit suitability approval against the reviewed fingerprint,
runs the helper's approval check and only then starts composition as a separate
job. It never auto-approves a scenario or deploys an event.

Industry intake is repository `microsoft_industry_verticals.csv`; Skillable supports
only six industry slugs. Unsupported industries block composition pending an
explicit support-extension or revised/reapproved scenario decision; never silently
map them to another industry.

Apply the workflow's business-unit and reuse catalog contract. Generic is exclusive
of specific units and means a typical industry workflow with no unit targeting.
Carry scope through requirements, personas, application/data and learner/coach content.
Catalog discovery is read-only; workers curate `scenario-manifest.json` through
`python scripts\scenario_catalog.py refresh generated-scenarios\<slug> --metadata <JSON>`.
Inferred metadata stays visibly `needs-review` until curated. Reuse source architecture
as read-only guidance; regenerate business app/data for the target industry and units,
refresh technical evidence, and obtain new design confirmation, validation and approval.
Never inherit source deployment state, secrets, scopes, approvals, packages or runtime success.
Source selection is not consent. Use plain headings/prose/navigation without decorative emoji;
retain functional badges, checkboxes and callouts.

## Technical constraints

- Read `.github/instructions/az-foundry.instructions.md` for current Foundry
  resources, direct child projects, live model/region evidence and acceptance.
- Read `.github/skills/az-consolidated/SKILL.md` for shared defaults, AVM,
  synthetic identity provenance and templates.
- Confirm Azure CLI and azd use the user's selected account, subscription and
  tenant. If a local default-account instruction exists, honor it. If absent,
  ask for target confirmation; never invent a subscription or fail by repeatedly
  reading a nonexistent file.
- Use managed identity, real agent invocation and explicit errors; no mock
  success. A provisioned resource or homepage is not a working scenario.
- Inherit configured model preferences; do not hard-code model names in agents.
- Use GitHub CLI for GitHub operations; publishing is always user-invoked.
