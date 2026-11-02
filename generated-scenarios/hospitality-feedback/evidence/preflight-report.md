## Preflight Outcome

**Continuation supersedes the consent blocker, 2026-10-22 18:36 UTC:** conditional reference deployment
authorization is now explicit. Read-only Entra discovery could not establish an intended compatible registration.
CLI and azd identity match the verified deployer; RG remains absent. No cloud writes or further preview occurred.
See [the authentication gate report](auth-blocker-2026-10-22.md) for commands, findings and exact next action.
The original preview report below is preserved as historical evidence.

**Decision required — preview completed, not deployed.** Date: 2026-10-22 UTC.

The scenario remains the locally tested hospitality reference. No application or fixture regeneration was needed.
Read-only Azure queries, local azd configuration, local compilation and two subscription what-if operations ran.
No provider registration, Entra application creation, RBAC write or resource deployment ran.

### Exact Target

- Account: `petender@microsoft.com`.
- Subscription: `MCAPS-Hybrid-REQ-152516-2026-petender`, `efd64343-6ef4-4926-951f-d3229f38bd76`.
- Tenant: `16b3c013-d300-468d-ac64-7eda0820b6d3`.
- New RG: `rg-hospitality-feedback`; azd environment: `hospitality-feedback`.
- Recommendation: **West US 3**, after East US 2 failed B1 quota.
- Foundry Basic **S0**, project `hotel-feedback`, model deployment `hotel-analysis`.
- `gpt-4.1-mini` / `2025-04-14` / **Standard** / capacity **10**.
- Linux App Service **B1 × 1**, `DOTNETCORE|10.0`.
- StorageV2 **Standard_LRS**, Hot, four private containers, ingestion and poison queues.

The current model is catalogued Legacy, with inference deprecation `2027-04-14`.
Use is recommended only for the short reference; future longer-term use requires model lifecycle review.
Standard is regional rather than GlobalStandard; no global model processing was silently selected.

### Checks and Actual Results

- Azure CLI subscription Enabled; exact tenant and account verified.
- azd token identity has the same tenant and object ID as the deployer. Only non-secret claims were retained.
- All six required provider namespaces are Registered; no registration was attempted.
- Foundry account/project provider locations, model catalog, quota and capacity cover all three candidates.
- West US 3 model quota limit **5000**, usage **0**, live available capacity **5000**; requested **10** units.
- Linux B1 region listing and live `.NET 10` regional runtime catalog verified.
- Standard_LRS StorageV2 SKU has no returned location restriction for West US 3.
- Three inherited/subscription policy assignments and eleven rule definitions inspected.
  Returned initiatives concern Defender for relational/SQL resources; no applicable deny found.
- Deployer ARM effective permissions include `*`; permissions are not consent to execute writes.
- Bicep build/lint passed; previous application tests remain 30 passed, not rerun during this preflight.
- RG absence verified again after previews.

East US 2 provider validation failed with `InternalSubscriptionIsOverQuotaForSku`, B1 limit **0**, usage **0**,
required **1**. Read-only West US 3 usage reported total regional VM limit **10**, usage **0**.
West US 3 provider what-if then **Succeeded**.

### Expected Changes

Actual final what-if: **24 Create, 0 Modify, 0 Delete, 2 Unsupported**.
No unrelated subscription/resource-group changes were identified.

Creates include the RG, managed identity, Foundry account/model/project, Foundry grants, Storage services/containers/
queues and deployer grants, Linux plan/site, authentication-safe publication policies and app/log settings.
Two additional intended runtime Blob/Queue contributor grants cannot be fully analyzed because the role-assignment
resource IDs depend on the managed identity's future principal ID. Their expression scopes are the intended Storage.
What-if does not prove runtime RBAC propagation, capacity reservation, model inference or application authentication.

### Preview-Only Parameters and Required Decision

`infra/preview.parameters.json` uses `urn:hospitality-feedback:preview-only-unresolved-audience`.
This is deliberately not a usable Entra API audience and must never be deployed.
The local azd environment leaves `API_AUDIENCE` unset, preventing normal unresolved-parameter provisioning.
The operator allowlist provisionally uses deployer object ID `214d672b-df87-4f3b-94fd-7863032546c1`.

Next provide the existing API registration's exact audience, scope/role and consent readiness, and confirm the operator.
Resolve final parameters, rerun what-if, and review the new result before explicitly authorizing deployment.
No Entra registration discovery was expanded beyond the signed-in user; no directory object was invented.

After that review, the confirmation must name the account, subscription ID, tenant ID, RG, azd environment,
West US 3, model/version/Standard capacity 10, S0, B1 × 1 and Standard_LRS.
It must explicitly authorize reference provisioning, web deployment, synthetic fixture ingestion and live
model/agent/application/negative-case acceptance, and acknowledge any remaining unsupported grants.
It does not authorize participants, packages or publication.

### Planning Cost

Official retail Linux B1 price: **USD 0.017/hour**, **USD 12.41 at 730 hours**.
Allow **USD 1–10/month** for low-volume Storage/related usage, plus metered model tokens and possible egress.
Plan roughly **USD 15–30/month before model usage**; model rates were not verified and are not invented.
For 48 hours, hosting alone is **USD 0.816**. Taxes, agreement discounts and wider subscription charges are excluded.
No budget or billable resource was created.

### Evidence Index and Recovery

- Exact authorization: `preflight-consent.json`.
- Live query commands, dates, exits and results: `preflight/*.json`.
- Safe azd identity claims: `azd-auth-alignment.json`.
- Failed initial region: `what-if-eastus2-blocked.json`.
- Successful final provider preview: `what-if.json`.
- Input hashes and machine-readable review: `what-if-review.json`.
- Shared recommendation: `../00-region-availability.json`.

Initial capacity queries lost ampersand query parameters through Windows `az.cmd` quoting.
The actual `ParameterIsMissing` errors are preserved as `capacity-*.initial-error.json`;
corrected quoted API calls succeeded. A guessed Storage CLI subcommand was unavailable; documented REST succeeded.
An intermediate region-stack API path included subscription scope incorrectly; the official provider path succeeded.
A local validation tool invocation returned `Access is denied (os error 5)`; the narrower build/lint retry passed.
None of these course corrections changed cloud state or disabled security.

Do not resume with `azd up`. Resolve authentication configuration, repeat preview, obtain exact consent, then proceed.
