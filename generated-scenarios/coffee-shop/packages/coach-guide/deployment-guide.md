# Private deployment guide

## Status and destination isolation

Composition is local only; no coach or team environment is deployed.
A separate explicit event request must go to the scenario orchestrator before cloud operations.
Use the deployable coach archive for full code and participant archive for the empty starter.
Use coffee-shop-coach / rg-coffee-shop-coach; default team 01-coffee-shop-hack / rg-01-coffee-shop-hack.
Never reuse the reference or deploy participants into the coach group.

## Prepare a separately reviewed destination

1. Reuse current CLI/azd identity; verify matching account and tenant without changing shared defaults.
1. Validate exact destination subscription eligibility: Foundry APIs/model/version/capacity, P0v3 and Table storage.
1. Resolve Foundry Agent Consumer by exact built-in name; do not substitute a guessed ID or broader User.
1. Review public TLS, MI/RBAC, local-cookie authentication, costs and real ARM what-if for every target.
1. Set explicit region and identifiers from that review. Do not inherit reference location, IDs or quota evidence.
1. Obtain separate event deployment approval; an existing manifest or package receipt is not consent.

## Coach configuration and installation

From coach root, select a new coffee-shop-coach azd environment only after the separate request.
Set AZURE_RESOURCE_GROUP to rg-coffee-shop-coach and AZURE_LOCATION to the reviewed destination region.
Supply AZURE_SUBSCRIPTION_ID, AZURE_PRINCIPAL_ID and FOUNDRY_CONSUMER_ROLE_ID through destination azd configuration.
The guard also requires process COFFEE_EXPECTED_SUBSCRIPTION_ID and COFFEE_EXPECTED_TENANT_ID from the review.
COFFEE_DEPLOY_AUTHORIZED=yes is an execution guard, never standalone proof of actual user consent.
Supply COFFEE_STORE_PASSWORD and COFFEE_AREA_PASSWORD only in process memory through an approved secret input path.
Never put passwords in azd environment files, command logs, ARM parameters, repositories or the event manifest.

After authorized what-if/consent, azd up runs:

1. Prepackage Build-Assets.ps1: pinned npm ci/assets and locked .NET restore.
1. Preprovision Assert-DeploymentScope.ps1: consent marker, exact coach env/group and reviewed target/tenant.
1. ARM resources/RBAC with explicit location and managed identities.
1. Postprovision Initialize-Scenario.ps1: reassert target; bootstrap Table accounts/fixtures and agents.
1. Bootstrap reuses owner/digest-matching agent versions and configures 100% endpoint version selection.
1. Install fresh agent settings into the destination web app, then publish .NET application.

Generated agent-installation.json contains new deployment state and must remain unexported.
Bootstrap adds absent snapshots and preserves existing stock; existing accounts must match grants/passwords.
No directory registration, Graph write or end-user Entra consent is part of this approved design.
Use storeman001 for 001, storeman002 for 002 and petender for north 001/002, with separately supplied passwords.
These are technical local usernames, not catalog people or operator identity requirements.

## Team installation

Select the exact numbered environment from the manifest; set its matching group and explicit region/subscription.
Only after separate approval set COFFEE_TEAM_DEPLOY_AUTHORIZED=yes and run azd up from participant root.
No data ingestion hook or app exists; local fixture files remain local until learners install their chosen components.
No participant app URL is expected. Check only the isolated empty group and starter not-configured status.

## Authorized runtime acceptance and recovery

Require real model inference, three agent response/version receipts, grounded close and negative cases.
Verify secure cookie login, CSRF, 001-to-002 denial, north-to-003 denial, missing ledger and branch failure.
Draft/approve 001, replay and stale-version tests must show durable human ownership without supplier effects.
Use isolated fault testing and restore the dependency before rerunning the complete close.
MI 403: inspect exact role, propagation and agent endpoint selector; never broaden role or paste a key.
Report failed latency/concurrency goals unchanged; do not treat HTTP 409 rejection as successful close latency.
Only successful real rollout changes planned manifest entries or inventory items to azure-verified.

## Cleanup and publication

Neither is authorized by composition. Enumerate exact environments/groups and ask before destructive teardown.
Stopping the web app does not stop App Service plan charges.
No resource deletion, publication, repository push or event deployment is performed here.
