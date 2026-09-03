<!-- markdownlint-disable MD033 -->

# Next steps — <SCENARIO_TITLE>

Use this scenario-level file to plan, create, package, upload, and validate every
supporting artifact. Keep it at `generated-scenarios/<PROJECT>/nextsteps.MD`.

## Scenario context

| Property | Value |
| --- | --- |
| Scenario | <SCENARIO_TITLE> |
| Industry | <INDUSTRY_DISPLAY_NAME> |
| Industry slug | `<INDUSTRY_SLUG>` |
| Last updated | <LAST_UPDATED> |
| Inventory owner | <OWNER_OR_ROLE> |
| Package root | `generated-scenarios/<PROJECT>/packages/` |

## Delivery rules

Classify every artifact before work begins:

- `deployment-critical` supports a deployed application path or an acceptance
  test. It must reach `packaged` before deployment handoff.
- `release-enrichment` improves the lab or release but is not required for the
  deployed acceptance path. It may remain `planned` after deployment testing.

Use one of these statuses:

| Status | Meaning |
| --- | --- |
| `planned` | The detailed specification exists, but the file does not. |
| `created` | The file exists in a working location. |
| `validated` | Local schema, safety, and content checks pass. |
| `packaged` | Every listed repository destination exists. |
| `azure-verified` | Azure load or installation and its acceptance check pass. |

> [!IMPORTANT]
> A missing `deployment-critical` artifact blocks package handoff. It does not
> authorize a dry run or omission of deployment testing.

## Artifact inventory

| ID | Proposed file or file set | Challenge use | Azure target | Classification | Status |
| --- | --- | --- | --- | --- | --- |
| ART-001 | `<FILE_NAME>` | <CHALLENGE_OR_SETUP_USE> | <AZURE_TARGET> | `deployment-critical` | `planned` |

Add one row and one detailed specification for every dataset, document, media
file, API contract, message sample, evaluation set, or installation script.

## Detailed artifact specifications

### ART-001 — <ARTIFACT_NAME>

- **Purpose and challenge use:** <BUSINESS_PURPOSE_AND_EXACT_CHALLENGE_USE>
- **Deployment classification:** `deployment-critical`
- **Status:** `planned`
- **Proposed filename:** `<FILE_NAME>`
- **Repository destinations:** `packages/coach/data/<FILE_NAME>` and
  `packages/participant/data/<FILE_NAME>`
- **Package visibility:** <PUBLIC_LEARNER_SAFE_OR_PRIVATE_OR_DEPLOYABLE_ONLY>
- **Artifact type and format:** <JSON_JSONL_CSV_PDF_MARKDOWN_YAML_OR_OTHER>
- **Target Azure service and destination:** <SERVICE_AND_LOGICAL_DESTINATION>
- **Schema or document structure:** <TOP_LEVEL_SHAPE_SECTIONS_OR_PAGE_OUTLINE>
- **Required fields or sections:** <FIELD_NAMES_TYPES_REQUIRED_RULES_OR_HEADINGS>
- **Expected quantity or size:** <RECORD_FILE_PAGE_AND_APPROXIMATE_SIZE_COUNTS>
- **Synthetic content requirements:** <CATEGORIES_RANGES_EDGE_CASES_AND_FAKE_DATA_RULES>
- **Generation method and dependencies:** <HOW_TO_CREATE_AND_REQUIRED_INPUTS>
- **Upload or installation method:** <SCRIPT_HOOK_SDK_OR_PORTAL_METHOD>
- **Identity and access:** <MANAGED_IDENTITY_RBAC_OR_DEFAULT_AZURE_CREDENTIAL>
- **Local validation:** <SCHEMA_COUNT_CHECKSUM_RENDERING_OR_SAFETY_CHECK>
- **Azure validation:** <QUERY_COUNT_SEARCH_RESULT_EVENT_OR_APPLICATION_CHECK>
- **Acceptance criteria:** <OBSERVABLE_PASS_CONDITIONS>
- **Owner and creation priority:** <OWNER_ROLE_AND_PRIORITY>

Repeat the `ART-NNN` block for every inventory row. Enumerate every proposed
filename when one artifact represents a document collection.

## Creation and review sequence

1. Create every `deployment-critical` artifact from its detailed specification.
1. Validate schemas, required fields, record counts, file readability, and
   deterministic identifiers locally.
1. Review synthetic content for realism without customer data, personal data,
   secrets, real endpoints, tenant IDs, or subscription IDs.
1. Place each file at every listed repository destination.
1. Copy learner-safe `Allfiles/` payloads to the private coach documentation
   root byte for byte.
1. Update each artifact status to `packaged` only after every destination exists.
1. Create and review `release-enrichment` artifacts before the public release
   when their challenge pages reference them.

## Package and GitHub publication

- [ ] Create a branch for the scenario package work.
- [ ] Add all created assets only at their listed repository destinations.
- [ ] Keep private coach material out of `packages/hack/` and public repositories.
- [ ] Confirm learner-safe assets match under `packages/hack/Allfiles/` and
      `packages/coach-guide/Allfiles/`.
- [ ] Run the Skillable package validator and sensitive-data checks.
- [ ] Complete coach and participant deployment testing before publication.
- [ ] Commit the scenario, package assets, and this updated inventory together.
- [ ] Push the branch to GitHub and open a pull request with validation and
      deployment evidence.
- [ ] Merge or publish only after required reviews and checks pass.

Record the intended repositories and visibility before pushing:

| Content | GitHub destination | Visibility | Publication state |
| --- | --- | --- | --- |
| Scenario and deployable packages | <SCENARIO_REPOSITORY> | <VISIBILITY> | <STATE> |
| Learner instructions | <LEARNER_REPOSITORY> | Public | <STATE> |
| Coach guide | <COACH_REPOSITORY> | Private | <STATE> |

## Azure load and installation plan

For every artifact, document these implementation decisions in its detailed
specification:

- The Azure resource created by infrastructure as code and the logical target,
  such as a Cosmos DB container, Storage table, Blob container, or search index.
- The idempotent load or installation script and its package-relative path.
- The `azd` lifecycle hook that runs the script. Use `postprovision`,
  `postdeploy`, or `postup` according to resource and application dependencies.
- The managed identity or `DefaultAzureCredential` flow and minimum RBAC role.
- The local preflight, expected loaded count, representative query, negative
  test, and rerun behavior.
- The cleanup or reset behavior needed to repeat a workshop deployment.

Do not store credentials or resolved endpoint values in this file or the data
payloads.

## Deployment and test gate

`azd up` is mandatory for `packages/coach/` and for every manifest entry that
uses `packages/participant/`. Planned follow-up work never replaces deployment.

Before deployment handoff:

- [ ] Every `deployment-critical` artifact has status `packaged`.
- [ ] Every listed destination for a packaged artifact exists.
- [ ] Load scripts are idempotent and fail on schema or count mismatches.
- [ ] Coach and participant Bicep build and lint checks pass.
- [ ] Application and focused integration tests pass locally.

During and after deployment:

- [ ] Run the configured data load and installation hooks as part of `azd up`.
- [ ] Verify the coach application uses the real supporting artifacts.
- [ ] Verify each participant environment receives its required synthetic data.
- [ ] Run every artifact's Azure validation and application acceptance check.
- [ ] Update successful artifact statuses to `azure-verified`.
- [ ] Record failures and remediation without marking deployment as skipped.

If a critical artifact or deployment fails, fix and retry or ask the user for a
decision. Do not silently remove the artifact, bypass the test, or claim success.

## Completion tracking

| Workstream | Owner | Due or milestone | Evidence | Status |
| --- | --- | --- | --- | --- |
| Artifact creation | <OWNER> | <MILESTONE> | <PATH_OR_REVIEW> | <STATE> |
| Safety and schema review | <OWNER> | <MILESTONE> | <VALIDATION_OUTPUT> | <STATE> |
| Package placement | <OWNER> | <MILESTONE> | <PACKAGE_PATHS> | <STATE> |
| Azure load verification | <OWNER> | <MILESTONE> | <DEPLOYMENT_EVIDENCE> | <STATE> |
| GitHub publication | <OWNER> | <MILESTONE> | <PULL_REQUEST_OR_RELEASE> | <STATE> |

- [ ] No unresolved template token remains.
- [ ] Every artifact has one inventory row and one detailed specification.
- [ ] All deployment-critical artifacts are `azure-verified` after testing.
- [ ] Deferred release-enrichment work has an owner and milestone.
- [ ] GitHub publication includes package and deployment validation evidence.
