# Deployment summary

## Deployment Details

Deployment status: **Central US reference deployed; local-account and real application acceptance passed**.
Application: <https://fc-web-kvjmo565tswuy.azurewebsites.net>
Login: <https://fc-web-kvjmo565tswuy.azurewebsites.net/Login>
Latest retained application acceptance: **2026-10-25 18:32:45 UTC**.

Actual user response: "attempt deployment o centralus".
Account `petender@microsoft.com`, subscription `efd64343-6ef4-4926-951f-d3229f38bd76`
and tenant `16b3c013-d300-468d-ac64-7eda0820b6d3` match the reviewed scope.
Exact Central US model quota/capacity and B1 worker quota checks passed before deployment;
see [regional evidence](00-region-availability.json). No region fallback or shared-default changes occurred.
These retained observations are not fresh capacity reservations.

The user subsequently replaced consent-dependent Entra app login with local accounts.
No tenant consent, tenant-policy weakening or directory elevation was performed.
Managed identities still authenticate Azure workload operations. Suitability approval
is a separate pending user decision; no hack packages or team environments have been created.

## Deployed Resources

All Azure resources are in `rg-feedback-campaign`, centralus:

- Foundry `fc-ai-kvjmo565tswuy`, direct child project `campaign`, deployment `campaign-model`:
  `gpt-4.1-mini`, version `2025-04-14`, GlobalStandard capacity 10.
- Native prompt agent `campaign-listener:1`, with its version pinned in application settings.
- B1 plan `fc-plan-kvjmo565tswuy`, web app `fc-web-kvjmo565tswuy`.
- Standard Service Bus `fc-bus-kvjmo565tswuy`, queues `posts` and `replies`.
- Storage `stfckvjmo565tswuy`, durable `campaignstate` table.
- Log Analytics `fc-log-kvjmo565tswuy` and Insights `fc-insights-kvjmo565tswuy`.

The initially authorized dedicated Entra registration/service principal
`feedback-campaign-reference` remains unused by sample sign-in. It was not deleted.
No new registration is needed when deploying the current local-account design.

## Outputs (Expected)

Actual application/service outputs are retained in the scenario's local azd environment
and non-secret installation receipts. Passwords, cookies and tokens are not runtime evidence.

- [Participant access guide](docs/participant-access.md): three restricted local accounts.
- [Coach access guide](docs/coach-access.md): separate ControlAdmin reference account.
- Actual generated credentials: private, gitignored `.private/participant-access.json`
  and `.private/coach-access.json`, with restrictive local access. Never publish these files.
- [Architecture](03-architect-diagram.png) and [runtime flow](04-runtime-diagram.png).
- [Demonstration walkthrough](demoguide/demoguide.md).
- [Acceptance index](scenario-validation.json) and [live receipt](evidence/local-app-runtime.json).

## Actual Commands and Results

Commands were run from the reference workspace unless indicated otherwise.
Historical evidence is retained rather than rewritten as if the final design existed initially.

### Initial installation

- `python scripts\identity_setup.py prepare`: initial registration creation succeeded,
  then a redundant automatic-owner link returned HTTP 400. Checking existing ownership
  repaired the root cause; verified-object retry succeeded. This hook is now inactive.
- `az deployment sub what-if --location centralus --name feedback-campaign-review`
  with `infra\review.bicep`, the exact subscription and real identity parameters:
  **passed**, 23 creates, no resource deletes. See `evidence/centralus-whatif.json`.
- `azd up --no-prompt`: **passed**, 10m11s, including 2m23s provisioning and 7m47s deployment.
  Deployment `feedback-campaign-1792950654`; log `evidence/centralus-azd-up.log`.
- Postdeploy initialized the real agent and durable initial rules without overwriting active versions.
- `python scripts\probe_runtime.py`: **passed** direct model inference, versioned agent
  invocation and anonymous HTTP 401. These direct probes use the installer, not runtime MI.

### Local-account migration and validation

- `python scripts\setup_lab_accounts.py prepare` and `install`: **passed**; resolved the
  existing deployer, generated separate participant/coach private files and stored only salted hashes.
  Active azd hooks no longer create registrations or request consent.
- `dotnet test tests\FeedbackCampaign.Tests.csproj -c Release --nologo`
  with TRX output under `evidence\tests`: **passed**, 32 application tests,
  including local login/logout, lockout, role enforcement, CSRF and session validation.
- `python -m unittest discover -s tests -p "test_*.py"`: **passed**, eight installation tests.
- From the repository root,
  `python -m unittest discover -s scripts\tests -p "test_hack_workflow.py"`:
  **passed**, 43 workflow/customization tests including the canonical auth/RBAC policy.
- Main and review Bicep builds/lints: **passed**. Main build/lint was rerun
  after adding the deployer's queue-scoped data roles and passed.
- `azd deploy web --no-prompt`: **passed**, 2m54s. New local-auth code was published
  while platform authentication still protected the old path. Only after the new
  application was verified was this app's platform Entra authentication disabled.
  App-owned authentication remains mandatory for protected APIs.
- A targeted `authsettingsV2` update disabled only this app's platform login.
  Config propagation initially retained HTTP 401 on `/Login`; an authorized app restart
  and bounded wait resolved it. Anonymous APIs still return HTTP 401.
- The scoped deployer-role what-if: **passed**, exactly three new queue assignments,
  no resource deletions or new services. Only these assignments were applied;
  generated assignment names were aligned to deterministic IaC names.
  See `evidence/deployer-rbac-whatif.json` and `evidence/deployer-rbac.json`.
- `python scripts\probe_local_app.py`: **passed** against the actual HTTPS deployment,
  reading credentials privately in memory. Latest receipt: `evidence/local-app-runtime.json`.

### Observed application behavior

- All four local accounts sign in with server-assigned roles; invalid login and
  anonymous access fail. Wrong reviewer, missing CSRF, duplicate approval and
  stale real ETag are rejected. Logout ends the session.
- Actual app-managed-identity chat invoked Foundry and refused to promise an unsupported
  refund, faithfully applying `campaign-policy-v1` and retaining a real response ID.
- Actual positive feedback scored 1.0 positive and reached automatic reply-stream acceptance.
  Negative feedback scored 1.0 negative and reached Product Manager human review.
  Neutral feedback scored 1.0 neutral and reached Conflict Resolution Specialist.
  The mixed fixture scored 0.9 negative and also reached Product Manager; scores were not forced.
- Both assigned humans edited and approved real replies, with `AcceptedByReplyStream` receipts.
- A real App Service restart preserved the pending human case, snapshot, ETag and protected session.
- A coach saved/promoted an immutable rule version, verified an existing case kept its
  original snapshot, and explicitly rolled the pointer back.

### Identity and authorization boundaries

App runtime MI has Table Data Contributor, project Azure AI User, `posts` Receiver
and `replies` Sender on the reviewed scenario scopes.
The deploying user has separate Table/project data roles, `posts` Sender/Receiver
and `replies` Receiver for initialization, inference, stream and DLQ inspection.
No tenant-wide directory roles, service keys or shared service-principal secrets were added.

## Limitations and Review Boundary

- Live provider-outage injection and poison-ingress/DLQ exercises were **not performed**.
  Provider failure/retry is covered locally; recovery instructions are not live success receipts.
- Replies terminate in the Service Bus stream; acceptance is not external email/social delivery.
- Scores are estimates, not calibrated probabilities. The fixed routing boundaries are
  >=80% positive, otherwise >=89% negative, otherwise Conflict Resolution Specialist.
  Proposed product-aspect/80%-negative rules are inactive unless explicitly promoted.
- Public authenticated synthetic reference, single B1 worker/LRS, no private endpoints,
  production SLA, enterprise SSO/MFA or external CRM integration.
- Session keys persist outside the published app under `HOME/data/feedback-campaign-keys`,
  relying on platform disk/access protection. This is not a production key-management claim.
- GlobalStandard processing is not guaranteed region-local.
- Planning cost: USD 40-95/month, reviewed estimate ceiling USD 100/month, **not a spending cap**.
  Retained B1 rate USD 0.018/hour (13.14/730 hours), Standard Service Bus base USD 10/month;
  metered usage, tax and egress vary. Deployed resources now incur charges.
- Cleanup requires separate resource/directory deletion authorization. Existing resources
  and the unused Entra registration were not deleted.

Present this working reference for explicit suitability approval. Deployment authorization,
authentication repair and successful tests are not approval to compose or deploy a hack.
Media & Communications is not currently supported by the Skillable authoring catalog;
future composition requires an explicit support-extension or revised/reapproved-scenario decision.
