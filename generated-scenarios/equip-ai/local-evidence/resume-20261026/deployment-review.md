# equip-ai: current-state and rebuild review

Prepared 2026-10-26 UTC after the user requested resumption of incomplete validation.
This is not deployment success, historical success attestation or suitability approval.

## Observed state

The authenticated Azure CLI and azd identities match the retained target.
The exact subscription-scoped `az group exists` check returned `false` for `rg-equip-ai`.
The recorded application hostname no longer resolves. No resources were deleted by this resumption.
No alternate subscription, region or replacement group was selected or queried.

The source, private installation state, diagrams and historical approvals remain local.
All 29 Python installer tests passed in this resumption. The previously recorded 49 application/browser
checks are dated local evidence, not newly executed live acceptance.
See [the current receipt](current-state.json).

## Retained authority and changed scope

The October 24 exact-target deployment and D2als_v7 management approvals remain recorded.
They are not revoked by an initial intake flag, later read-only answer or portal migration.
However, there is no existing Azure reference to finish testing in place.
This review asks whether to restore it now, including the newer local-account requirement,
rather than silently allocating the full paid environment.

Retain the account, tenant and subscription in the current receipt, Central US,
`rg-equip-ai` and azd environment `equip-ai`. Reuse the existing reference code and architecture;
do not restart the business design, compose a hack or deploy teams.

## Proposed continuation

1. Replace the old sample-app Entra login with unique local participant/coach accounts,
   following the user's newer repository-wide requirement.
   Preserve server-enforced Tacoma-only versus statewide access, evidence/tool authorization,
   secure sessions, CSRF protection, login throttling/lockout and durable salted password hashes.
   Deliver actual passwords only through separate private, gitignored access files.
1. Keep telemetry read-only for the web identity. Account persistence must not grant
   that identity write/delete access to telemetry.
1. Preserve private Foundry/Blob endpoints, the private cleaner, VNet integration and the
   approved managed-identity management/publishing path. No anonymous bypass or public-IP exception.
1. Include the existing local IoT Hub Registry Contributor correction for the deploying
   user at this hub only. Verify its deployment and propagation before registering test devices.
   Preserve X.509 device authentication, disabled shared keys/SAS, and managed-identity routing.
1. Recheck current subscription eligibility, exact SKU/model capacity, affected role scopes,
   cost and complete what-if before allocation. Present any material difference before proceeding.
   Reuse saved identities only where still needed and verified; no new Entra sign-in registration,
   administrator consent, directory elevation or deletion of existing registrations is proposed.
1. Restore and publish the reference, then prove actual model/agent inference, authenticated app chat,
   site-isolated tools and evidence, certificate ingress through IoT Hub into Blob, exact values/citations,
   freshness/expiry, denial and observable dependency failure behavior.
1. Persist actual results, update the demo and request separate suitability approval only after passing.

## Cost and boundaries

The last approved complete illustration was **USD 249.36/month** for continuously allocated resources,
including **USD 97.83/month** for management. It is historical pricing, not a refreshed quote or spending cap.
The full environment would begin incurring charges again when restored.
No additional paid service is proposed merely for sample-account authentication.
Refresh prices and allocation eligibility before provisioning; return for a material cost/security/scope change.

This continuation does not authorize a different subscription/region, broad tenant roles,
weakening private access, resource/directory deletion, hack authoring, event rollout or publication.
The unavailable, incompletely validated reference cannot be converted into a successful historical attestation.
