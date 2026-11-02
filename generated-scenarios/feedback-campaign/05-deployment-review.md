# Consolidated architecture and deployment review

Status: **Central US deployed; local sample accounts replaced the original Entra sign-in**.
This is not working-scenario suitability approval.

## Active sample authentication revision

The user reported no tenant consent-administrator rights and explicitly requested:
"in an earlier scenario, we used a local user and password option, which feels good enough for these sample apps.
store the credentials in the scenario participant and coach file".

The app now uses local, server-role-scoped accounts with salted framework password
hashes in the existing Tables. Separate private participant and coach access files
contain deployment-specific generated passwords; public-safe guides contain
retrieval instructions only. No new Azure service or cost was added.
Backend Azure managed identity and scoped RBAC remain unchanged.
The original dedicated Entra registration is unused and retained, not deleted.

The local-auth what-if succeeded with no resource deletions. Provider-generated
property/default differences were reviewed; only the existing site's authentication
configuration was applied, avoiding unrelated provider-normalized changes.
New app code was deployed first; its local login link was verified before
disabling this site's EasyAuth enforcement. Configuration propagation required
an App Service restart. No directory policy or consent was changed.

Actual acceptance passed local login/logout, invalid-password/anonymous/CSRF/
wrong-role denial, app managed-identity grounded chat, real positive and both
human routing, edited replies, stale/duplicate decision rejection, durable
case/session restart and explicit rule promotion/rollback.
See `evidence/local-app-runtime.json` and the deployment summary.
The following original scope sections preserve earlier decisions/history;
their Entra sign-in requirements are superseded by this revision.

## Central US user follow-up

Actual user response on 2026-10-25: "attempt deployment o centralus".
This replaces the provisional eastus2 target with centralus; the subscription,
tenant, resource group and proposed resource/security scope remain unchanged.
Do not switch to another region without a decision. The previous readiness form
explicitly excluded Entra writes, so directory installation authority requires
focused clarification before those operations. The user then explicitly selected:
"Authorize the listed scenario-only Entra installation and acceptance operations".
The dedicated registration, service principal and four installer role assignments
were installed within that authority; see `evidence/identity-installation.json`.
An initial redundant owner assignment returned 400 because creation already
assigned ownership. Verified owned-object retry succeeded; the installer now
checks automatic ownership before adding an owner.

Observed Central US checks:

- Exact gpt-4.1-mini 2025-04-14 GlobalStandard model is listed.
- Model quota is 40 used of 5,000; requested allocation is 10.
- Documented model-capacity API reports 4,960 available; allocation is not reserved.
- Microsoft.Web B1 quota is 1 used of 11; one worker is required.
- B1 Linux locations include Central US; .NET 10 Linux runtime is active.
- Required providers are registered, including the lowercase `microsoft.insights` entry.
- Supporting resource provider location metadata includes Central US.
- Current Learn Agent Service matrix lists Central US Responses API and Agents support.
- The target resource group does not exist. No resources have been created.

Raw observations are retained under `evidence/centralus-*.json`,
`evidence/b1-linux-locations.json` and `evidence/linux-runtimes.json`.
An initial incorrect capacity URL returned 404; the documented subscription-level
modelCapacities endpoint succeeded. A Windows CLI URL-quoting failure was corrected.
Neither failure was interpreted as an actual model-capacity denial.
Policy assignments were retrieved. Parameter-complete subscription what-if
succeeded with 23 Create operations and no deletes or diagnostics. The Linux B1
retail rate is USD 0.018/hour, USD 13.14 for 730 hours; Service Bus Standard base
meter is USD 10/month. No material scope/cost change was identified before azd up.
Model capacity was checked, not reserved. Earlier eastus2 references describe
the original proposal, not the active deployment target.

## Existing authority and evidence

Actual intake authorizes local scenario preparation only. No same-scenario
historical user response authorizing Azure reads, installation or deployment was
found in current/legacy portal records searched for `feedback-campaign`. There
was no scenario folder in generated-scenarios or adjacent azd-projects. The
repository helper created the new adjacent workspace and junction. No remaining
matching scenario worker was observed; unrelated repository changes were preserved.
Selections of services, CLI tool permission, and current identity confer no cloud
resource authority. No old portal execution gate or lease was used.

Existing CLI/azd metadata was refreshed with the shared `azure_context.identity`
and `discover` helpers, not interactive login or a full audit. Both identify
`petender@microsoft.com`; no mismatch or default change was observed.
See `evidence/identity-observation.json` for the actual timestamp and checks.

## Exact proposed targets

| Target | Value |
| --- | --- |
| Account | petender@microsoft.com |
| Tenant | 16b3c013-d300-468d-ac64-7eda0820b6d3 |
| Subscription | efd64343-6ef4-4926-951f-d3229f38bd76 |
| Environment / resource group | feedback-campaign / rg-feedback-campaign |
| Region | centralus, explicitly requested by user; no fallback authorized |
| Directory objects | One dedicated `feedback-campaign-reference` application + service principal; marker/owner checks before reuse |
| Foundry | `fc-ai-<suffix>`, direct child `campaign`, deployment `campaign-model` |
| Hosting | `fc-plan-<suffix>` B1 Linux, `fc-web-<suffix>` .NET 10 |
| Data | `stfc<suffix>` StorageV2 Standard_LRS / `campaignstate` Table |
| Messaging | `fc-bus-<suffix>` Standard / `posts`, `replies`, DLQs |
| Monitoring | `fc-log-<suffix>` workspace, `fc-insights-<suffix>` App Insights |

`<suffix>` is exactly `uniqueString(resourceGroup().id)` in Bicep; no live
resource names or endpoints are claimed before deployment. The app URL is a
deployment output, currently unavailable. No existing deployment is adopted.

## Missing operations, separated by authority

1. **Exact-target Azure read-only preparation:** provider registration *state*,
   scoped policy/RBAC, service locations, Microsoft.Web B1 worker quota/.NET 10
   support, Foundry prompt-agent/Responses availability, exact model
   gpt-4.1-mini 2025-04-14 GlobalStandard capacity 10 and quota headroom,
   supporting SKUs, resource-name collision discovery, pricing and ARM what-if.
   No provider registration, support/quota requests, probe allocation or shared
   subscription/default change is implied by these reads.
2. **Scenario-owned Entra reads/writes:** inspect exact application-name matches
   and ownership; create the dedicated single-tenant application, assign installer
   ownership, create its service principal, require app-role assignment, define four
   application roles, assign the signed-in installer those four roles for demo
   acceptance, and set only the generated app's HTTPS callback. Include temporary
   removal/restoration of only that installer's own four scenario-app assignments
   for real wrong-role acceptance (no new users or unrelated assignments). No secrets,
   delegated API permissions, admin consent, broad directory roles or unrelated
   objects. Tenant denial stops installation; administrator capability is unknown.
3. **Azure reference installation:** create/tag the named group and resources;
   scoped RBAC assignments for app MI (Table Contributor, project Azure AI User,
   posts Receiver, replies Sender) and installer (Table Contributor and project
   Azure AI User for initialization); publish .NET using azd App Service hosting;
   configure EasyAuth/settings; create/reuse real versioned Foundry agent, initialize
   v1 rules without overwriting active promotions, pin agent version and restart
   app configuration as required. This includes ordinary in-scope repairs only.
4. **Real acceptance:** direct project model inference and agent invocation,
   signed-in app chat and policy-grounded assessment, human edit/send, wrong-role
   and anonymous denials, stable reply correlation/deduplication, retained state on
   restart and poison/error/recovery. Manual signed-in browser steps are required;
   no automated sign-in, permission escalation or fictional response is acceptable.
   Any additional queue-producer/consumer operator RBAC needed for direct stream
   tests must be reviewed rather than assigned ad hoc; UI-to-worker reply stream
   receipts can be verified with the already scoped storage initialization access.

## What-if and readiness

**Not run**: no resource reads, what-if, provisioning, Graph queries/writes or model
inference have been authorized. Local Bicep compilation is not ARM what-if.
Expected intended scope is additive to this new group, but existing resources,
policy and name collisions are unverified. A destructive or materially different
what-if, unavailable model/region, required new consent, or cost above ceiling
must return for review, not be silently accepted.

`infra/review.bicep` previews the whole group+reference from subscription scope.
Its identity-dependent parameters must use actual setup-generated IDs.
Independent readiness reads happen first; directory setup happens only if its
specific authority is granted. A final parameter-complete what-if follows setup
and precedes provisioning. ARM what-if does **not** preview Graph changes or
agent/model data-plane behavior. No invented IDs or passing checks are supplied.

## Security and management impact

This is a **public, authenticated synthetic reference**, not private-only or
production ready: TLS public PaaS endpoints, no shared service keys, managed
identity data access, EasyAuth tenant/audience validation and application roles,
same-origin writes, version/ETag controls and no source body/contact telemetry.
The landing page/static CSS/JS and configuration-only health endpoint are public;
case/rule/chat APIs require sign-in and business roles.

Secretless EasyAuth uses ID-token implicit sign-in with ID-token issuance enabled;
there is no downstream delegated-token use or token store. Modern production
authorization-code/PKCE or confidential-client/federated authentication should be
reviewed before expansion. This trade-off is disclosed, not falsely called PKCE.
Installer has all four business roles for demo only; production requires separation.
GlobalStandard model processing is not guaranteed region-local residency.

Provisioning, publishing, initialization and tests run on the actual current
workstation over public TLS with existing user credentials; runtime uses only MI.
No VNet, private endpoint, VM, Bastion, VPN or private runner is needed or included.
No public-IP discovery or network-security relaxation is performed.

## Incremental and total cost

No approved existing baseline: entire estimate is incremental.
Planning estimate **USD $40–95/month**, ceiling for review **$100/month**:
B1 $13–20; Service Bus Standard $10–15; LRS Tables $1–5; Monitor $0–15;
model $16–40. Assumptions: 730 hosting hours, 10,000 posts/month,
2,000 input + 500 output tokens/post, 5 GB logs. No model capacity reservation.
This is an allowance, not a retrieved retail quote; authorized preparation must
refresh regional rates and actual usage. No additional channel license, mail/Teams
connector or external reply adapter is included. Alerts are not spending caps.

## Evidence, limitations and the single remaining review

Local results: `evidence/local-validation.json`, TRX, installation contract tests,
rendered PNGs and local-only unauthenticated UI preview. Cloud/runtime checks are
explicitly pending in `scenario-validation.json`; a suitability snapshot is not
valid until they pass.

Parent may collect one focused scope response using this complete review: whether
to authorize the exact-target preparation and complete reference installation
(including the explicitly listed directory operations and $100/month ceiling),
conditional on matching non-destructive what-if/readiness; or grant preparation
only, retaining the write boundary. No additional question about generated IDs,
installer choice or runner discovery is necessary. This document itself records
**no approval**. Material differences return for review.

External sending is currently the real Service Bus reply stream, not an email or
social-platform delivery claim. Suitability approval cannot establish production
delivery integration. Media & Communications is not a supported current Skillable
industry slug; only after scenario suitability, composition would need an explicit
support-extension/reapproval decision. No hack plans or packages were created.
