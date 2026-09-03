# Skillable package validation checklist

## Structure

- [ ] Public learner and private coach roots are separate.
- [ ] Both roots contain `README.md`, `index.md`, `_config.yml`, `_build.yml`,
      `resources.md`, and `Allfiles/README.md`.
- [ ] Both roots use the same canonical `Instructions/<industry-slug>/` path.
- [ ] Exactly five learner challenge pages use prefixes `01-` through `05-`.
- [ ] The private coach root contains the same five files plus `99-finale.md`.
- [ ] No learner Finale page exists.
- [ ] The scenario root contains exactly one case-sensitive `nextsteps.MD`.

## Frontmatter

- [ ] Every instruction page starts with valid `lab` YAML frontmatter.
- [ ] Every page has a title, module, description, duration, level, and `islab`.
- [ ] Module title and industry are consistent across all challenge pages.
- [ ] Finale sets `audience: coach` and `isfinale: true`.
- [ ] No unresolved template token remains in publishable content.

## Challenge quality

- [ ] The five challenge durations total 150 minutes.
- [ ] Every challenge uses the same scenario.
- [ ] Challenge 0 establishes identity, access, and a model request.
- [ ] Challenge 1 reaches the minimal viable agent.
- [ ] Challenges 2 and 3 add one capability each.
- [ ] Challenge 4 hardens and demonstrates the accumulated solution.
- [ ] Every page identifies its checkpoint, retained behavior, regression test,
      evidence, hints, and fallback.
- [ ] Portal and SDK paths use current, verified product behavior.

## Finale

- [ ] Finale contains one section for every challenge number and exact title.
- [ ] Every challenge section includes all eight required coach-note labels.
- [ ] Finale includes wrap-up, handoff, and cleanup guidance.
- [ ] Finale is excluded from parity comparison only because it is coach-only.
- [ ] Finale is included in private repository and Skillable page validation.

## Supporting artifacts and next steps

- [ ] `nextsteps.MD` contains every required section in template order.
- [ ] Every inventory row has one matching, uniquely numbered `ART-NNN`
      detailed specification.
- [ ] Every entry names exact files, package destinations, challenge use,
      format, schema or structure, size, synthetic content, and Azure target.
- [ ] Every entry defines creation, installation, identity, local validation,
      Azure validation, acceptance, owner, priority, classification, and status.
- [ ] Every `deployment-critical` entry is `packaged` before deployment handoff.
- [ ] Every destination listed for a packaged artifact exists.
- [ ] `release-enrichment` is used only for work that no required challenge or
      deployed acceptance path needs.
- [ ] Learner-safe payloads appear byte for byte in both `Allfiles/` trees.
- [ ] Private or deployable-only artifacts are absent from the public learner
      root.
- [ ] `nextsteps.MD` has no unresolved token, credentials, endpoint values,
      UUID-like identifiers, customer data, personal data, or local paths.

## Safety and publishing

- [ ] Learner pages contain no coach answers or completed implementation.
- [ ] Neither root contains secrets, credentials, tenant details, subscription
      IDs, deployed endpoints, customer data, or local paths.
- [ ] Screenshots are present, current, sanitized, and use meaningful alt text.
- [ ] External links are descriptive and verified.
- [ ] Internal links resolve with exact path capitalization.
- [ ] Learner challenge pages and media are byte-for-byte identical in the coach
      root.
- [ ] Learner and coach `Allfiles/` payloads are byte-for-byte identical.
- [ ] A repository license is copied only when its use is approved.
- [ ] No progress-tracking or challenge-checklist application was introduced.

## Deployment and publication

- [ ] Seed and installation scripts are idempotent and wired to the correct
      `azd` lifecycle hook.
- [ ] Package validation succeeds before Azure preflight.
- [ ] `azd up` is attempted for the coach and every participant manifest entry.
- [ ] Deployment executes every required artifact load or installation step.
- [ ] Azure counts, representative queries, negative cases, and application
      acceptance checks match `nextsteps.MD`.
- [ ] Successful deployment-critical entries are updated to `azure-verified`.
- [ ] Package and deployment evidence is attached to the GitHub pull request.
- [ ] Planned follow-up work was not used to bypass deployment testing.

## Automated check

Run from the repository root:

```powershell
python .github/skills/skillable-lod-authoring/scripts/validate_skillable_package.py `
  generated-scenarios/<project>/packages `
  --industry <industry-slug>
```

A nonzero exit code blocks publishing and package deployment handoff.
