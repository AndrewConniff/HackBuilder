# ABC Builder repository conventions

## Purpose

A technical user asks `az-01-conductor` to build a Foundry-oriented hack.
First prove a complete deployed business scenario. Obtain explicit approval of
its usability, then derive a minimum learner starter and outcome-led challenges.
Event rollout and publication are separate user choices.

Exactly two active agent contexts exist: scenario orchestrator `az-01-conductor`
and hack composition `HackCreator Agent`. Each performs its work directly through
skills with no specialist delegation or agent fanout. The scenario context owns
story, requirements, architecture, Bicep, app, authorized deployment/runtime checks
and demonstration. Composition only distills the approved reference and authors
the starter, challenges, learner and private coach materials.

Read the [workflow contract](.github/skills/hack-builder-workflow/SKILL.md)
and [customization inventory](AGENTSEXPLAINED.md). Do not use historical
generated scenarios as authorization to bypass approval.

## Layout and changes

- ABC Builder is the product name. Preserve `az-01-conductor`, `HackCreator Agent`,
  canonical skill folder identifiers, executable script names and environment
  variables as compatibility APIs; branding does not rename them.
- Canonical agents and skills live under `.github/`.
- Former procedural agent bodies are preserved as historical skill references,
  not discoverable agents or executable handoff rules.
- `.agents/skills/` contains thin manual launchers or scenario inputs only.
- Generated workspaces use `scripts/New-AzdScenarioWorkspace.ps1`; physical
  output lives in the adjacent `azd-projects` folder with a local junction.
  Existing scenario folders are reused, not automatically relocated.
- Preserve user changes, deployed resources, identity/network security, and
  phase-specific completion evidence.
- Use relevant file-scoped instructions, existing artifact templates, current
  official service guidance, AVM-first Bicep, and managed identity.
- Use the repository CSV catalogs for synthetic company and person identities.
- Do not install packages or run nonexistent npm tasks to validate prose.

## Local portal contract

The lightweight LOCAL web portal collects prompt, validated project slug,
industry, `businessUnits`, selected services and WAF priorities. It saves the brief, opens the actual VS Code
custom agent with `code chat --mode`, displays agent-written status and serves files/ZIP exports.
It is visualization/handoff plus explicit read-only System diagnostics: no Copilot CLI workers, stage scheduler,
Azure sign-in manager or approval engine. System checks reuse the existing prerequisite/identity helpers,
never install tools, sign in, retain tokens or change shared defaults.
The normal launcher uses `scripts\portal_visualizer.py`; the old runner is not exposed by the active server.
Brief confirmation and saved changes send fixed, fingerprint-bound continuations through the native editor bridge
to the existing scenario conversation. Confirmation resumes the normal workflow; changes remain scoping-only.
These user actions do not grant Azure/Entra, deployment or suitability authority.
Polling never dispatches work, and missing acknowledgement is not proof of agent execution.

Use the real VS Code agents and skills for all execution. Discuss architecture/deployment approval and
working-scenario suitability approval in that chat, not a second portal decision queue.
Use `generated-scenarios\{projectSlug}` and preserve explicit restrictions and real security/permission gates.
Agents report display-only stage progress with `scripts\portal_status.py`; reporting grants no authority.
The retired CLI runner and its execution gates have been removed. Retain historical records and ensure any old
worker has stopped before editing its scenario. Status refresh never executes work.

After the user's actual suitability approval, record the reviewed fingerprint through `hack_workflow.py`.
The portal checks that approval before opening a separate HackCreator VS Code context, but never records it
or auto-starts composition. Event rollout and publication remain separate requests.

Industry intake uses repository `microsoft_industry_verticals.csv`. Skillable
currently supports eight industry slugs; unsupported industries block composition
pending an explicit support-extension or revised/reapproved scenario decision.
Never silently map unsupported industries.

## Business scope and reuse

Use the [workflow scope and catalog contract](.github/skills/hack-builder-workflow/SKILL.md)
for business-unit IDs, Generic exclusivity, manifest metadata and adaptation rules.
Carry the selected scope through personas, story, application/data, acceptance
tests and post-approval learner/coach materials. Generic means a typical industry
workflow without unit targeting, not a selection of every unit.

Catalog discovery reads `generated-scenarios\*\scenario-manifest.json` only.
Workers maintain curated metadata through `scripts\scenario_catalog.py refresh`
with `--metadata`; inferred manifests remain visibly `needs-review`.
Reuse architecture as read-only guidance, never deployment state, secrets,
scopes, approvals, packages or runtime success. Adaptations require fresh design,
technical evidence, validation and approval. Discovery and source selection grant no consent.

Use crisp, plain-text documentation headings and navigation. No decorative emoji
in prose; preserve functional badges, Markdown checkboxes and alert callouts.

## Validation

For a user-confirmed historical deployment in a deleted, inaccessible one-off environment, follow
the workflow's `attest-history` path. Preserve null unavailable endpoints/test times and empty checks;
keep the user statement distinct from independently observed runtime results. Suitability approval
and the fingerprint guard remain required. Future deployments retain normal evidence/consent gates.

Run from the repository root:

```powershell
python -m unittest discover -s scripts\tests -p "test_*.py"
python .github\skills\skillable-lod-authoring\scripts\validate_skillable_package.py --help
```

Focused customization checks:

```powershell
python -m unittest discover -s scripts\tests -p "test_hack_workflow.py"
python .github\skills\skillable-lod-authoring\scripts\validate_skillable_package.py --check-skill
```

For generated packages, run the Skillable validator with the package path and
canonical industry slug, plus `az bicep build`, `az bicep lint`, `dotnet build`
and focused application tests as appropriate. Run real Azure acceptance only
for the deployment scope authorized by the user.

No package manager manifest or artifact-template lint npm task currently ships
in this repository. Do not claim those commands passed or retry them.
