# Adatum brokerage agent — minimum starter

You receive no application, model deployment or agent.
The starter contains an empty resource-group template, local status check and approved synthetic FAQ.

## Isolation and access

The default team environment is `01-finance-security-hack-hack`.
Its resource group is `rg-01-finance-security-hack-hack`.
The event operator supplies scoped team access; no subscription-wide grants are included.
Use only your assigned group. Never reuse another environment or its resources.

Validate your effective access to your team group and lack of access to other teams before building.
Ask the event operator for scoped access if denied; do not broaden your own roles.
Deployment-time role-assignment permissions must be separate from runtime identity permissions.

## Local check

Run `python scripts/starter_status.py`.
It reports `not-configured`, no application URL and required learner work; this is expected.
The template compiles without building services, RBAC, endpoints, agents or an application.

## Future authorized preparation

Event rollout is a separate decision. The operator must confirm target, location, costs,
quotas, service policies and private-connected operator access before provisioning.
The team needs service deployment and scoped role-management support within its isolated boundary.
Entra registration privileges, if needed, are separately governed; never create a client secret.

After authorization, select the exact assigned azd environment and target before provisioning.
`infra/main.parameters.json` contains azd expressions, not concrete Azure CLI inputs.
There are no ingestion hooks: install your chosen knowledge path as part of Challenge 2.
The FAQ is the only indispensable business fixture; no people or customer records exist.

## Build contract

Keep the public chat anonymous and educational. Private backend hops require workload identity.
Produce a real agent response before extensions. Never fabricate success during missing configuration.
Use the paired Skillable instructions supplied for the event; no full solution is supplied here.
