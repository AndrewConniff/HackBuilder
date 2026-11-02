# Authorized reference deployment runbook

Central US installation is authorized and in progress; see `06-deployment-summary.md`
for actual outcomes. All cloud commands require the scope in `05-deployment-review.md`.
Run from `C:\HackBuilder\generated-scenarios\feedback-campaign`.
Do not run login, switch shared defaults, register providers, allocate quota probes
or install tools as an automatic workaround.

## Readiness, before installation

1. Refresh `scripts/azure_context.py` identity/discover from the repository helper;
   compare to the review. Reuse `evidence/identity-observation.json` while unchanged.
2. Under exact-target read-only authorization, capture provider registration
   state for Microsoft.CognitiveServices, Microsoft.Web, Microsoft.Storage,
   Microsoft.ServiceBus, Microsoft.OperationalInsights, Microsoft.Insights.
   Inspect inherited policy and required scoped RBAC without changing them.
3. Check `az cognitiveservices model list --location centralus --subscription
   efd64343-6ef4-4926-951f-d3229f38bd76` and `az cognitiveservices usage list
   --location centralus --subscription ...` for exact gpt-4.1-mini/2025-04-14,
   GlobalStandard 10 headroom. Public model lists are not a capacity reservation.
4. Check Microsoft.Web B1 Linux regional worker eligibility/quota, not Compute
   VM family quota. Inspect the regional Microsoft.Web `/locations/centralus/usages`
   ARM endpoint and current `az appservice list-locations --sku B1
   --linux-workers-enabled --subscription ...`; verify .NET 10 Linux runtime.
5. Confirm Standard Service Bus supports selected queue settings, LRS Storage,
   workspace and App Insights availability and policy. Reject unsupported features
   rather than disabling security or switching region automatically.
6. Persist actual command/output evidence and resource/SKU/model matrix into
   `00-region-availability.json`. `selectedRegion` stays null until all pass.

## Scenario-local environment and installation

After explicit reviewed reference installation authority:

```powershell
azd env new feedback-campaign --subscription efd64343-6ef4-4926-951f-d3229f38bd76 --location centralus
azd env set AZURE_RESOURCE_GROUP rg-feedback-campaign
azd env set AZURE_TENANT_ID 16b3c013-d300-468d-ac64-7eda0820b6d3
```

These are scenario-local azd values, not shared `az account set`.
Do not execute provisioning until the model/region/policy evidence passes.
Use the existing azd lifecycle. Installer identity discovery sets only the
existing signed-in user's object ID; no app registration or consent is needed:

```powershell
python scripts/setup_lab_accounts.py prepare
$scope = azd env get-values --output json | ConvertFrom-Json
az deployment sub what-if --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --location centralus --template-file infra/review.bicep `
  --parameters environmentName=feedback-campaign location=centralus `
  installerObjectId=$scope.INSTALLER_OBJECT_ID
```

Review actual what-if for existing-resource changes/deletion. The initial
`setup_lab_accounts.py prepare` is read-only installer discovery, not approval.
No generated client ID or directory mutation is required for this sample login.

With matching non-destructive reviewed scope and actual installation consent:

```powershell
azd up
```

Preprovision verifies the installer; postprovision creates/reuses local accounts
and private access files, uploading only password hashes. Postdeploy creates/reuses the actual Foundry
agent version and initial Table rules, then pins the real agent version in site
settings. Runtime waits/errors until dependencies exist; there is no canned
success. RBAC propagation may require a bounded retry of the same hook, not
broader role assignment. Tenant/host denial or material change returns for review.

For an existing Entra-authenticated deployment, first install local account hashes
and deploy the new authentication code with `azd deploy web --no-prompt`. Only
after verifying the new UI, disable EasyAuth on this one site, matching the
updated `infra/main.bicep`, then wait for configuration propagation/restart.
Never disable the platform boundary while old code still trusts platform headers.
The original registration is unused; do not delete it without deletion authority.

See `participant-access.md` and `coach-access.md` for private credential delivery.
Public guide templates never contain live passwords.

## Real acceptance and evidence

```powershell
python scripts\probe_runtime.py
python scripts\probe_local_app.py
```

The first probe records direct installer model/agent and anonymous-denial receipts;
it cannot prove the app managed identity. The second reads private credentials in
memory and exercises actual local login, app managed-identity chat, both reviewer
roles, reply-stream acceptance, restart persistence, rule promotion/rollback and
negative authorization/concurrency checks. It restarts only the reviewed reference
app and creates synthetic cases, so run only within that deployment authority.
Retain actual IDs/timestamps/queue receipts. Inspect policy grounding semantically;
a citation string alone is not proof of faithful policy use.

The 2026-10-25 live run passed; see `evidence/local-app-runtime.json`.
Live provider-outage injection and poison-ingress/DLQ exercises were not run.
Their recovery procedures below are instructions, not successful test receipts.
Local application tests cover the provider failure/retry behavior.

Only after every required check passes, update `scenario-validation.json` with
actual HTTPS app URL, UTC test time and true evidence-backed checks. Then:

```powershell
python C:/HackBuilder/scripts/hack_workflow.py snapshot .
```

Present that working reference and stop for suitability approval. Do not call
`approve`, compose materials, publish or roll out teams on the user's behalf.

## Recovery and teardown boundaries

- Foundry HTTP/schema/time-budget error: case becomes Failed; no reply. Inspect
  sanitized error category, repair configuration/provider access, explicitly Retry.
- Reviewer conflict: refresh ETag and content; never overwrite stale human work.
- Crash during send: same PendingSend row and `reply-<caseID>` republished; queue
  deduplication is seven days, not unlimited external exactly-once delivery.
- Poison ingress: inspect `posts/$DeadLetterQueue` under separately scoped
  operator receiver authority; never log contact or body or silently purge DLQ.
- Rule regression: explicitly promote an older saved version with reason; existing
  cases retain their snapshots. This is not an automatic retroactive reroute.
- Teardown only with deletion authority for `rg-feedback-campaign` and the specific
  scenario-owned Entra app/SP, after retaining non-secret evidence; app registrations
  are not automatically removed by deleting the resource group.
