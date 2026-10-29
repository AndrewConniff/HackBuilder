---
name: az-multi-team-deployment
description: >
  Defines manifest-driven deployment of one coach package and 1-20 isolated
  participant hack environments with zero-padded team IDs, distinct Azure
  resource groups, azd environments, validation, failure handling, and reports.
---

# Multi-Team Hack Deployment

Use this skill to plan manifests after scenario approval, or to execute a
**separate explicit event-deployment request**. Team count alone is not rollout
consent. The scenario orchestrator remains the only owner of actual Azure deployment,
executing deployment skills directly in its own context.

Reference deployment never uses this manifest. Package authoring may finish
with all targets `planned`; only requested event rollout requires live success.
An application URL is required only when the minimum starter includes an app.

## Team Rules

- Resolve destination subscription, tenant and region independently for coach and each participant target.
  Never inherit reference-validation targets, `.azure` settings or eligibility evidence.
  Packages take region from explicit destination environment parameters, not a hardcoded validation default.
  Run subscription-specific regional/SKU/model/quota checks for each distinct destination scope before what-if.

- Accept an integer team count from 1 through 20.
- Default to one team when no count is supplied.
- Format team IDs as `01`, `02`, through `20`.
- Use azd environment `{teamId}-{project}-hack`.
- Use resource group `rg-{teamId}-{project}-hack`.
- Deploy the coach package exactly once to its package-defined environment and
  resource group.
- Deploy the same participant package once for each team.
- Never deploy participant resources into the coach resource group.

The `rg-` prefix preserves repository naming policy while the zero-padded team
identifier remains the first variable segment of every participant group.

## Deployment Manifest

The HackCreator Agent creates
`generated-scenarios/{project}/09-hack-event-manifest.json`. Use this shape:

```json
{
  "schemaVersion": 1,
  "project": "contoso-agent-hack",
  "teamCount": 2,
  "coach": {
    "azdEnvironment": "contoso-agent-coach",
    "resourceGroup": "rg-contoso-agent-coach",
    "applicationUrl": null,
    "deploymentStatus": "planned"
  },
  "teams": [
    {
      "id": "01",
      "displayName": "Team 01",
      "azdEnvironment": "01-contoso-agent-hack",
      "resourceGroup": "rg-01-contoso-agent-hack",
      "applicationUrl": null,
      "deploymentStatus": "planned"
    }
  ]
}
```

Validate before deployment:

- `teamCount` equals the number of team entries.
- IDs are unique, contiguous, zero-padded, and in range.
- azd environments and resource groups are unique.
- No participant resource group equals the coach resource group.
- No application URL, identifier, or status from a previous deployment is
  retained.

The scenario orchestrator and hack composition agent must use this manifest as
the single source of truth for deployment state. Do not pass team count only
in prose, and do not use this manifest to track challenge completion.

## Deployment Sequence

1. Verify current scenario approval and the explicit event-deployment request.
   Confirm Azure CLI, azd and available extension contexts match the user-selected
   subscription/tenant and any local default-account instruction. Stop on mismatch.
2. Read and validate the deployment manifest.
3. Build, lint, and run what-if for the coach package.
4. Build and lint the participant package once, then run what-if for every
   distinct participant resource group.
5. Present one confirmation containing the coach group and all numbered team
   groups.
6. Deploy and validate the coach package once.
7. Deploy participant environments sequentially in team ID order.
8. After each deployment, capture non-secret application outputs and update
   that team's manifest URLs and status.
9. Generate a deployment matrix in the deployment summary.

Use one azd environment per team. Set `AZURE_RESOURCE_GROUP` to the exact
manifest value before `azd up --no-prompt`. Never reuse the currently selected
environment implicitly.

## Idempotency

- Select or create the named azd environment before setting values.
- Reuse the same environment and resource group on retries.
- Confirm the active environment and target group before every `azd up`.
- Do not generate new suffixes or alternate names after a partial failure.
- Mark manifest status as `planned`, `deploying`, `succeeded`, or `failed` and
  include a non-secret failure summary.

## Failure Handling

Deploy sequentially to reduce quota contention and make failures attributable.
When one team fails:

1. Stop before deploying the next team.
2. Preserve successful team environments and deployment state.
3. Record the failed team ID, phase, and remediation in the manifest.
4. Present the error and ask the user whether to retry, continue with later
   teams, or stop. Never choose automatically.
5. Never redirect a later team to the failed team's resource group.

Do not delete or recreate resource groups without explicit user approval.

## Post-Deployment Validation

For the coach group, validate the complete solution resources and invoke the
deployed application when the package includes one.

For every participant group, validate:

- The resource group exists and matches the manifest.
- Only the minimum starter resources listed in the package contract are present
  and healthy; do not require the full reference supporting infrastructure.
- No forbidden coach-only or prebuilt Foundry resources exist when the package
  contract requires learners to create them.
- The participant application URL is reachable when an app is included.

The final report includes one row per team with environment, resource group,
deployment status, application URL when applicable, and validation result.

Completion requires exactly one successful coach deployment and one successful
participant deployment per manifest team. No team may remain `planned` or
`deploying`, and no required application URL may be null.

## Teardown

Generate explicit coach and per-team teardown commands, but do not execute them
without user confirmation. Enumerate target environments and resource groups
before any destructive action. Never use a wildcard or subscription-wide
deletion operation.

## References

- [Azure Developer CLI environments](https://learn.microsoft.com/azure/developer/azure-developer-cli/manage-environment-variables)
- [Azure Developer CLI deployment](https://learn.microsoft.com/azure/developer/azure-developer-cli/deploy-provision-resource)