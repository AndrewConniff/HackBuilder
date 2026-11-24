# Skillable deployment package

## Final deliverable

After the learner, coach, starter and solution packages pass their local checks,
create this additional private delivery folder for every newly composed hack:

```text
packages/
  Skillable Deployment Package/
    skillable-deployment.zip
    content/
      README.md
      azuredeploy.json
      azuredeploy.parameters.learner.json
      azuredeploy.parameters.reference.json
      deployment-manifest.json
      scripts/
        Deploy.ps1
      payload/
        learner/
        reference/
```

Omit empty payload directories. ZIP entries start directly with `README.md`,
`azuredeploy.json` and the other content files, not an extra parent directory.
The ZIP is the operator handoff. Keep the unpacked content for review and reproducible rebuilding.
Never put this combined solution-bearing ZIP or its content in learner downloads,
`packages/hack`, `packages/participant` or either documentation root's `Allfiles`.
The portal's existing learner and coach exports remain unchanged; open the package folder for this ZIP.

## Single ARM template and two modes

`azuredeploy.json` is the only ARM template anywhere in the delivery content.
It contains every resource, dependency, role assignment, identity, network setting,
model deployment and supported initialization resource needed for either mode.
Derive it from the approved sanitized coach and participant IaC, not from a live export.
Preserve the approved reference; do not redesign it or copy operational state.

Use the resource-group deployment schema:
`https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#`.
Expose `deploymentMode` as a string with `allowedValues: ["learner", "reference"]`
and `defaultValue: "learner"`. Both parameter examples target the same template;
each sets its matching mode and contains only portable, non-secret inputs.

- `learner` provisions exactly the minimum participant starter from the omission matrix.
  No completed agent, Foundry account/project/model, reference-only services or coach credentials.
  An empty starting resource set is valid.
- `reference` provisions the complete sanitized approved solution with its real application,
  data, identity/RBAC and required initialization. This mode is for instructors/operators.
- Mode conditions must gate resources, child resources, assignments, deployment scripts,
  configuration, outputs and artifact installation together. ARM conditions do not cascade
  automatically to child resources. Do not evaluate references to absent resources.
- Inline nested deployments are allowed inside this same JSON file. Embed every module's
  template in `properties.template`; no `templateLink`, `parametersLink`, template spec,
  Bicep registry dependency or second ARM file at deployment time.
- Keep all deployments inside the Skillable-provided resource group. Do not create resource
  groups, subscriptions or cross-group deployments. Generate unique names from that group.
  Use the destination resource-group location or explicit portable service-location parameters,
  preserving verified model availability and colocation constraints without a reference-region default.
- Do not embed fixed subscription/tenant IDs, deployed endpoints, credentials or private keys.
  Supply secure parameters at launch through approved Skillable mechanisms; never ship their values.
  Preserve managed identity, least privilege and private-network controls.

Compile the scenario-specific unified Bicep locally if used for authoring, then include only its
compiled ARM JSON in this delivery. Do not concatenate JSON or copy resource arrays without
reconciling parameters, variables, outputs, scope and dependency expressions.
The JSON must fit ARM's 4 MiB template limit; do not split it or switch to external links to evade the contract.
If the approved architecture cannot fit one resource-group deployment, stop with the exact compatibility
blocker. Do not claim a complete Skillable package or silently omit infrastructure.
Directory operations and subscription-level grants are not ordinary resource-group ARM resources:
document their required host permissions and block unsupported requirements rather than inventing ARM equivalents.

## Everything required in the ZIP

Include published app bundles or container build contexts, dependency manifests,
synthetic fixtures, grounding documents, schemas, evaluation inputs, load/seed scripts,
initialization tools, smoke tests and cleanup guidance used by either mode.
Use portable relative paths. Reuse sanitized artifacts already produced by composition.
Do not include local environments, certificates, caches, downloaded toolchains, secrets,
deployment receipts or unrelated scenario evidence.

ARM cannot automatically consume an adjacent local ZIP or perform every service data-plane operation.
Embed supported resource configuration and deployment-script content in the single ARM file.
For unavoidable app publishing, image building or data-plane initialization, include the actual
payload and idempotent scripts in the ZIP and list their order explicitly per mode.
These scripts must not provision hidden infrastructure or fetch another template.
They must fail visibly on errors and on schema/count/acceptance mismatches.
Never run reference-only initialization for learner mode.

`scripts/Deploy.ps1` must accept an explicit destination resource group and mode
(default learner), use `$PSScriptRoot`-relative paths, and invoke this one template with the
matching parameter file. It must not depend on the authoring checkout, Bicep, azd or a second template.
Use already-authenticated Azure CLI, propagate native failures, require real deployment consent,
then run only the selected mode's post-deployment scripts.
Document a validate/what-if path that does not publish apps, load data or provision resources.
For Skillable lifecycle actions, allow initialization after Studio has deployed the template,
without provisioning the infrastructure a second time.
Do not sign in, change subscription defaults or weaken security automatically.

`README.md` must document:

- Private operator-only distribution, both modes, their resource matrix and expected starting states.
- Required tools, resource-group permissions, model/quota/region prerequisites and unresolved blockers.
- Importing this ARM JSON into a Studio Cloud Resource Template, binding parameters, and selecting a mode.
- Where to place ZIP assets in the lab VM and which lifecycle actions publish/load them, in order.
- Exact local validation, what-if, deployment, mode-specific initialization and smoke-test commands.
- Runtime secure-parameter injection without committing values, and isolated cleanup for the lab group.
- Which checks ran locally and which destination/Studio checks remain pending.
  Local authoring is not proof of a deployed Skillable lab.

Declare all supporting file dependencies in `deployment-manifest.json`:

```json
{
  "schemaVersion": 1,
  "modes": {
    "learner": {
      "requiredFiles": [],
      "postDeployScripts": []
    },
    "reference": {
      "requiredFiles": ["payload/reference/app.zip", "payload/reference/seed.json"],
      "postDeployScripts": ["scripts/Initialize-Reference.ps1"]
    }
  }
}
```

Use this shape, replacing example paths with actual files. Paths are ZIP-root-relative with `/` separators.
Every supporting file must belong to at least one mode; common files may belong to both.
An empty list is valid only when that mode genuinely needs no supporting payload or post-deployment work.
Include these artifacts and their mode dependencies as deployment-critical entries in `nextsteps.MD`.
The manifest and ZIP checks prove declared-file completeness, not that an author listed every runtime dependency.

## Build, validate and finish

From the repository root, after current reference approval and content authoring:

```powershell
python scripts\skillable_delivery.py build generated-scenarios\{project}
python scripts\skillable_delivery.py validate generated-scenarios\{project}
```

The helper rejects missing dependencies, extra/external templates, non-resource-group scope,
unsafe paths, insecure parameter values, absent modes and stale or incomplete archives.
It does not generate a generic solution, evaluate ARM expressions or deploy Azure resources.
Scenario-specific tests must verify both modes against the approved resource matrix,
including child-resource conditions, absent-resource outputs, starter omissions,
reference completeness, artifact selection and failure behavior of deployment scripts.
Record actual successful commands as `skillable-arm-learner`, `skillable-arm-reference`
and `skillable-delivery` in `packages/validation/local-checks.json`.
Run the normal Skillable validator and archive checks afterward, then record the package receipt.
Changed content requires rebuilding the ZIP, rerunning checks and recording a fresh receipt.

Finish by linking the exact `Skillable Deployment Package/skillable-deployment.zip` path,
identifying both modes, reporting local results and pending destination tests, and stating
**packages validated; event not deployed**. Adding this workflow does not repackage existing scenarios.
After a separate authorized rollout, test both fresh modes in isolated destination groups,
their acceptance checks, repeated initialization and two concurrent lab launches for naming isolation.

## Sources

- [Skillable Azure resource template best practices](
  https://docs.skillable.com/docs/azure-resource-templates-best-practices)
- [Skillable Studio resource template configuration](
  https://docs.skillable.com/docs/configure-a-resource-template-to-a-resource-group)
- [ARM inline nested templates](https://learn.microsoft.com/azure/azure-resource-manager/templates/linked-templates)
