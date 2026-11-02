## Dedicated identity installation and authorization review

Latest continuation, 2026-10-24: Central US readiness reads and ARM what-if only were authorized and executed.
No Graph call or directory write was performed. Existing installation receipts/IDs remain historical;
current ownership/readback and actual support/lead assignments are unverified.
Any historical permission/installation statement below is not a current grant.
The consolidated remaining identity, management-path, cost and preview review is
`local-evidence/centralus-20261024T2240Z/deployment-review.md`.

> [!IMPORTANT]
> Current resume, 2026-10-24: recovered portal state grants no directory operations.
> Installation and permission statements below are historical evidence, not current authorization or readback.
> Preserve the existing identity receipt. After exact-target permission, verify ownership before reuse;
> do not recreate registrations, infer assignments or request generated IDs as user inputs.

Updated 2026-10-24 UTC for the retained Central US reference.
The dedicated registration installation completed under the portal's recorded exact-target authorization.
The confirmed design and new dedicated registration choice are retained.
The canonical correction supersedes the historical administrator/manual-receipt questionnaire.
Client IDs, object IDs, definition IDs, endpoints and receipts are tooling outputs, never user-supplied values.

### Exact target and current boundary

| Item | Retained target |
| --- | --- |
| Account | petender@microsoft.com |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76 |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Group / environment / reference region | rg-equip-ai / equip-ai / centralus |
| Current permission | Reviewed ordered ARM and dedicated directory installation; local scenario work |
| Directory installation | Registrations/service principals installed and verified; redirects await ARM output |
| ARM deployment | Authorized but not executed; private runner setup is required |

The prepared installer is `scripts\install_identity.py`.
It runs only with a separate, unexpired, provenance-bearing directory authorization for the identical scope.
Local execution consent, ARM ownership, an azd hook and a what-if result grant no directory permission.
Do not create an authorization receipt merely to make its guard pass.
The worker materialized only the accepted registration/redirect operations from canonical decision
`157b9eb7c2f14f9e957e45e26826e35d`, retaining its exact scope, provenance and a one-hour local expiry.
No assignment operation was included.

### Observed installation and remaining prerequisites

Run evidence: `.worker\7e73b648de00400c98f4ad9ef15eb880`.
Actual non-secret IDs, ownership markers and installer identity are retained in
`.installation\equip-ai\identity.json` and exported to the scenario-only `equip-ai` azd environment.
Graph readback confirmed the API/SPA contract and both assignment-required service principals.
The current identity has no returned active directory-role memberships, while tenant policy permits app creation.
Actual successful operations, not that policy or role list alone, prove this installation's permissions.
No privilege elevation, Graph consent or tenant policy change occurred.

The first attempt created both applications, then Graph rejected simultaneous scope/preauthorization creation
with `InvalidValue`: the delegated permission ID was not found.
The installer now persists and verifies the API scope before its separate preauthorization update.
The retry reused the captured applications and definition IDs, then installed both service principals.
Fifteen local installer tests passed, including dependency ordering, failed readback and duplicate prevention.

The complete-template what-if consumes actual client and installer IDs, but still reports skipped nested checks.
It is not a full-reference validation pass or runtime proof.
This Windows host's selected route to `10.247.0.65` is the Wi-Fi Internet default route via `10.0.0.1`.
No private publishing/agent runner is evidenced. No packet probe was sent to an unallocated private address.
Arrange an authorized VNet-connected execution path with private DNS before provisioning a paid reference
that this host cannot publish to or validate. This approval does not create a runner or authorize connectivity changes.
Redirects remain pending the actual ARM hostname. Real support-user nominations remain separately unauthorized.

### Proposed directory changes

Create only `equip-ai-api` and `equip-ai-spa`, both `AzureADMyOrg`, and their service principals.
Use a stable marker derived from this scenario's complete target plus verified installer ownership.
The installer refuses unrelated/ambiguous names, changed recorded identities and unexpected credentials.
Checkpoint definition IDs before creation and actual application/client/principal IDs after successful responses.
Retries reuse marked, owned objects; no automatic replacement, deletion or adoption of foreign objects.

| Object | Exact intended settings |
| --- | --- |
| API | `api://<actual-client-id>`, access-token version 2; no requested Graph/application permissions |
| API scope | Enabled `Equipment.Read`, Admin consent type; scoped read evidence only |
| API roles | Enabled User roles `Operations.Tacoma` and `Operations.Statewide` |
| SPA | Dedicated API's delegated read scope only; no credentials, implicit flow or public-client fallback |
| API preauthorization | Only this dedicated SPA for the exact read-scope definition ID |
| Both service principals | Assignment required; no blanket user, group or Statewide access |
| SPA redirect | Exact actual ARM web hostname with HTTPS and trailing `/`; no guessed or wildcard URL |

Creation/configuration, preauthorization, assignment-policy updates, redirect updates and approved principal
assignments must be covered explicitly in the directory authorization. No tenant-wide consent is requested.
Preauthorization of this SPA is a directory change; ARM what-if does not model it.
Real support/lead principal nominations remain an access-policy input for eventual live acceptance.
No nominations are currently saved. The installer grants nobody access by default and reports assignments pending.
Synthetic fixture personas are not directory accounts. Leave an unassigned negative-test account unassigned.

### Permissions and installer capabilities

These are requirements of the installation identity, **not permissions requested by the scenario SPA/API**.
Current delegated Graph documentation lists `Application.ReadWrite.All` for application updates and
service-principal creation/update. Application creation alone lists `AppRegistration.Create`.
Owned single-tenant service-principal creation/update requires an applicable directory role;
the documented non-admin owned-app route includes Application Developer.
Ordinary app-registration permission alone does not prove those later operations are permitted.
An appropriately scoped custom role or supported application-management administrator may satisfy the contract.
No administrator role, member registration setting or usable Graph grant has been observed in this preparation.
Do not elevate the current account, modify tenant policy or grant Graph consent automatically.

Explicit user/group app-role assignments use the resource principal's `appRoleAssignedTo` relationship.
The documented API requires `AppRoleAssignment.ReadWrite.All` plus `Application.Read.All`
and an applicable supported directory role, such as Cloud Application Administrator for these non-Graph roles.
Group assignment can require applicable Entra licensing. No broad Graph application role is being assigned.
The installer resolves `/me` with the existing authorized delegated identity and records its actual object ID.
It checks Graph token tenant metadata without retaining tokens. No app-only installation path is assumed.
If those calls are denied in a later authorized installation, retain the exact error; do not retry via another host.

### Producer/consumer order and automatic capture

1. Present one exact-target installation/deployment review containing these directory changes,
   ARM what-if coverage, post-installation dependencies, cost and private runner requirements.
   Obtain actual separate directory/ARM authorization; nothing in this document grants it.
1. The controller supplies saved account/tenant/subscription/group/environment/region to the owned azd environment.
   It writes the approved `directory-authorization.json` under `.installation\equip-ai`,
   retaining scope, approval reference, approver, expiry, `directoryOperations` and any nominated assignments.
   The generated installer object ID need not be transcribed; tooling resolves and records it.
1. The azd `preprovision` hook runs `python scripts\install_identity.py registrations`.
   It installs and reads back the API/SPA contract and assignment-required policy.
   Real outputs populate `EQUIP_API_CLIENT_ID`, `EQUIP_SPA_CLIENT_ID` and `AZURE_PRINCIPAL_ID`
   through explicit `azd env set --environment equip-ai`, never shared defaults.
   Exact built-in Foundry role definitions are read and their IDs captured the same way.
1. Dependent Bicep consumes these actual outputs. Site creation, system identities, private endpoints and RBAC
   do not require Entra client IDs; `runtimeConfiguration` alone consumes them.
   Its complete appsettings preserve keyless backend endpoints, WorkerRole and sanitized monitoring.
   The cleaner receives no browser identity settings. Missing web auth config fails closed, not anonymously.
1. The azd `postprovision` hook reads the actual web resource and `APPLICATION_URL`, verifies target ownership
   and sets/readbacks only that actual SPA redirect. Both resource ID and URL are ARM outputs.
   Nominated assignments are installed with the separately authorized `assignments` operation,
   using the same non-secret receipt; no generated-value portal questionnaire.
1. A VNet-connected authorized deployment runner uses Entra ARM publishing, not basic SCM credentials.
   Read actual cleaner/private endpoint outputs and private DNS; both app and SCM records are generated by
   the private DNS zone group. Verify connectivity before ZIP deployment and private Foundry agent installation.
   No runner is provisioned or connectivity proved by this preparation.
1. Recheck exact identity-dependent appsettings/assignments/Policy and real principal propagation.
   Install the agent, capture its real version into app configuration, then prove login, scoped answers,
   missing-role/scope/site denials, private/keyless backend access and expiry behavior.
   Provisioning or installer readback alone does not pass runtime acceptance.

Private installation state and authorization stay outside catalog metadata and future learner/event packages.
No hack/event region parameter inherits this reference's Central US target.

### Consolidated review limitation

Independent previews run now without fake application IDs.
The reviewed infrastructure creates the cleaner endpoint from the actual site resource ID, not a guessed hostname.
Live RBAC evidence proves Agent Consumer only allows endpoint interaction, not the Responses calls this app uses.
The reference now also grants the narrow project-scoped Foundry Project Runtime User role (`responses/*`).
The web identity remains Blob Reader; only the cleaner has custom read/delete; IoT retains container Contributor.

Unknown generated-principal propagation, directory permissions and live sign-in remain pending installation.
The strict regional provisioning validator rejects unknown checks, as it should.
The resumed worker inspected the current agent-owned portal reporting path rather than assuming the older
signature-only verification proves a consent-review failure. Current reporting permits a separate
exact-target deployment decision with truthful partial-preview and directory-installation limitations.
That decision does not mark full preparation passed or bypass later dependent checks.
No generated-value questionnaire, broad tenant privilege request or new workflow blocker is required.

### Official evidence

Fetched 2026-10-23; documentation is not proof of this tenant's permissions.

- [Application creation][create], [application updates][update] and [API application schema][api].
- [Service-principal creation][sp-create] and [service-principal updates][sp-update].
- [App-role assignments][assign], [azd hooks][hooks] and [private App Service DNS/SCM][private].

[create]: https://learn.microsoft.com/en-us/graph/api/application-post-applications
[update]: https://learn.microsoft.com/en-us/graph/api/application-update
[api]: https://learn.microsoft.com/en-us/graph/api/resources/apiapplication
[sp-create]: https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-serviceprincipals
[sp-update]: https://learn.microsoft.com/en-us/graph/api/serviceprincipal-update
[assign]: https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignedto
[hooks]: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility
[private]: https://learn.microsoft.com/en-us/azure/app-service/overview-private-endpoint
