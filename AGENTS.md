# Hack Builder repository conventions

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
industry, selected services and Well-Architected Framework priorities. Its local
authenticated backend launches actual Copilot CLI jobs, not simulated results.
It uses stable agent names `az-01-conductor` and `HackCreator Agent`.

Initial jobs permit local preparation only by instruction, not a sandbox.
The portal is the normal decision and progress surface. Workers read persisted intake/history and
report stage transitions through `scripts\portal_workflow.py`; never infer stage success from CLI exit.
Confirm design before local implementation. Defer account/quota/budget checks until separately
authorized deployment preparation; current public evidence supports provisional local choices.
Honor project writer leases and revision checks, including work initiated outside the portal.
Status refresh is read-only. Free-text continuation does not grant cloud authorization.
Use `generated-scenarios\{projectSlug}`, prepare reference code and what-if commands/
targets, and stop before Azure operations unless explicitly authorized. Tool
execution requires explicit portal permission. A separate user follow-up confirms
exact Azure targets after what-if; selected services and permissive CLI flags are
not deployment consent. Noninteractive jobs return **decision required** and stop
on missing authorization rather than guessing because ask-user is unavailable.

The scenario process never auto-starts composition. The portal approval action
records the actual suitability decision against the reviewed fingerprint and
checks approval before launching the separate composition job. It never
auto-approves scenarios or deploys events. Event rollout remains a separate request.

Industry intake uses repository `microsoft_industry_verticals.csv`. Skillable
currently supports six industry slugs; unsupported industries block composition
pending an explicit support-extension or revised/reapproved scenario decision.
Never silently map unsupported industries.

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
