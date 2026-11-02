# Private coach deployment guide

This guide is future operator work, not permission to execute it.
Composition performs only local checks; no new coach deployment, event rollout or publication occurred.

## Isolated targets

| Package | azd environment | Resource group |
| --- | --- | --- |
| Coach | `finance-security-hack-coach` | `rg-finance-security-hack-coach` |
| Team 01 | `01-finance-security-hack-hack` | `rg-01-finance-security-hack-hack` |

Event rollout requires an explicit separate request. Then verify current account/tenant/subscription,
exact manifest groups, policies, region/model capacity, costs and private operator connectivity.
Resolve Agent Consumer role, confirm address-space overlap and inspect runtime versus deployment permissions.
Register or identify a single-tenant backend API audience with token version 2; no client secret is needed.
No registration or subscription details are embedded in the package.

## Staged coach procedure

1. Select the coach directory and exact isolated azd environment; populate required nonsecret settings
   from the confirmed target, not another environment. Review `infra/main.parameters.json`.
1. Under preparation permission, use `scripts/Prepare-WhatIf.ps1` with verified exact targets.
   Review actual changes and dated costs, then obtain deployment consent.
1. Provision the foundation with `deployWorkload=false`. The private registry is initially empty;
   no placeholder app is created. An authorized rollout uses `azd up` as the deployment lifecycle,
   with staged parameters and explicit private image/agent installation between the stages.
1. From an authorized private-connected operator host, build/push the real Docker image.
   Set the required nonsecret outputs and run `scripts/Initialize-Reference.ps1` only with explicit
   installation consent and verified subscription, tenant and account arguments.
1. The initializer uploads the FAQ, reads back exact content, and reuses an identical agent version
   or creates a new version. Capture its actual name/version; do not assume a fixed returned version.
1. Review workload what-if again with immutable image and actual agent version, confirm consent covers
   this stage, then deploy `deployWorkload=true` and run the complete runtime acceptance below.

The copied `azure.yaml` deliberately contains no automatic cloud-mutating hooks.
Private image push and guarded initialization are explicit operator steps, not a generic one-shot `azd up` claim.
CLI credentials are installer-only; runtime uses user-assigned managed identity.
Review and remove temporary installer roles after installation.

## Required configuration names

Foundation parameters include environment/location, publisher identity, backend audience and resolved
Agent Consumer role definition. Use the exact parameter names in `infra/main.bicep`.
Installer/runtime require `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `GATEWAY_PRINCIPAL_ID`,
`BACKEND_AUDIENCE`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_AGENT_NAME`, `FOUNDRY_AGENT_VERSION`,
`MODEL_DEPLOYMENT`, `FAQ_BLOB_URL` and `SIGNING_KEY_URL`.
Missing configuration fails explicitly; no local FAQ or model-success fallback is used at runtime.

## Participant rollout

For each manifest team, select its own participant azd environment and exact group.
`azd up` provisions only the isolated group baseline; no app URL or Foundry resource should exist.
Operator assigns scoped team access separately and proves denial of other groups.
No data hook targets nonexistent services: FAQ delivery is local, installation is learner work in C2.

## Runtime acceptance — not executed during authoring

- Real model, named agent version and app chat; actual response identifiers.
- Private FAQ read, twelve source topics, valid citations and hypothetical fee fact.
- Exact-byte receipt verification; tamper and unrelated-identity signing failures.
- Anonymous public edge; public backend/data-plane denial; private DNS from actual runtime path.
- Invalid, expired, wrong-audience, wrong-tenant and unrelated-identity token rejection.
- Trade/account/credential refusal, unsupported question, bounded rate and explicit upstream failure.
- Correlation without routine chat text, retention and privilege review.

Record each new deployment independently. Never relabel historical attestation as these checks.
The six public evaluation prompts and existing deterministic coach tests are reusable acceptance inputs.

## Support, recovery and cleanup

Diagnose exact failure before retrying the same environment; do not switch region/model/targets silently.
If a team fails, stop sequential rollout and obtain the event owner's retry/continue/stop decision.
Keep all new targets planned until real rollout; no copied URLs or deployment state are valid.
Exact-group cleanup needs a separate explicit authorization; no wildcard deletion is supplied.
