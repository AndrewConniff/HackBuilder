# Adatum brokerage reference — private deployable coach

Sanitized copy of the approved source, infrastructure, fixtures, guarded scripts and deterministic tests.
No deployed state, credentials, workflow evidence or local caches are exported.
See the separately delivered private coach guide for full architecture and staged deployment.

## Isolation

Use azd environment `finance-security-hack-coach`, resource group `rg-finance-security-hack-coach`.
Never target `rg-01-finance-security-hack-hack` or another participant group.
No cloud deployment is authorized by these names or by package validation.

## Local checks

Use .NET 10 to restore/build `src/Brokerage.Web/Brokerage.Web.csproj` and run
`tests/Brokerage.Tests/Brokerage.Tests.csproj`.
Tests use deterministic test-only doubles and synthetic JWT fixtures, not real Azure inference.
Parse and run `scripts/Test-LocalScripts.ps1` to validate consent guards without Azure calls.
Compile and lint `infra/main.bicep` with pinned cached AVM modules.
Build caches and generated ARM belong to private local validation, not an exported archive.

## Deployment prerequisites

Exact targets, model quota, policies, private operator access, image installation, actual agent version,
scoped role definitions and backend audience registration must be verified for a future deployment.
The reference uses staged foundation/private installation/workload deployment, not one-shot provisioning.
No automatic mutation hook is added; preserve the operator script consent guards.

Historical deployment is user-attested only. Resources were deleted in an inaccessible one-off lab.
URL, exact time and granular logs are unavailable; this package has not been newly deployed.
