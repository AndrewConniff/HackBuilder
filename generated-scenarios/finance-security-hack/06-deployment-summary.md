# Finance security reference: local validation and deployment checkpoint

> Updated 2026-10-22 | Existing scenario resumed; no new workspace created

> [!IMPORTANT]
> Historical update, 2026-10-22: the user reports successful deployment and complete expected scenario
> behavior, then deletion to save costs. The one-off hosted lab subscription is no longer accessible.
> The former URL, deployment time, targets and granular test logs are unavailable. This is a user
> attestation, not an independently verified runtime test by this assistant. Earlier sections below
> retain the local implementation checkpoint and commands actually run by this assistant.
> The user explicitly approved the reference for local hack composition and authorized the distinct
> historical-attestation workflow path. No Azure operations or redeployment are authorized.
> Future deployments will use a permanent subscription with retained target/runtime evidence.

## 📋 Deployment Details

| Property | Value |
| --- | --- |
| Status | Local implementation complete; reference undeployed |
| Deployment name / duration | None / not applicable |
| Azure operations | None executed in this continuation |
| Subscription / tenant / account / cloud | Deferred to separately authorized deployment preflight |
| Resource group / azd environment | Unconfirmed; required naming relationship is `rg-{environment}` |
| Region | Provisional `eastus2`; not verified against subscription features or capacity |
| Model | Provisional `gpt-4.1-mini`, `2025-04-14`, GlobalStandard |
| Deployment authorization | Not granted |
| Cost | No Azure changes by this job; target-specific service estimate pending |
| Method | Local CLI checks only; future deployment is staged, not a one-shot `azd up` |

D1-D6 are resolved for local construction, as recorded in `01-requirements.md`.
Budget, target reconciliation and measurable production sizing are not local blockers.
Anonymous customer entry is selected; optional future authentication authoring is intent only.
No new public-document research was needed for this continuation.
Persisted official evidence is reused without reclassifying it as live subscription evidence.

### What-If Summary

**Not executed.** Create/modify/delete/no-change counts are unknown, not zero.
`scripts/Prepare-WhatIf.ps1` exists and was tested with a synthetic local fixture.
It requires actual boolean target/evidence confirmations, account and target fields, valid GUIDs and matching RG/env.
It writes foundation parameters and prints a safely quoted command; it never invokes Azure.
Its synthetic test output was deleted and must never be used as a real target confirmation.
Workload-stage previews must additionally include the installed agent version and immutable private image.
The helper currently prepares foundation parameters only.

### Verified local commands and results

Commands ran from `C:\HackBuilder\generated-scenarios\finance-security-hack` on 2026-10-22 UTC.
`$dotnet` below is the session SDK, not the older SDK on the system PATH:

```text
C:\Users\petender\.copilot\session-state\c325fe77-0030-44d6-8b42-65777dcb3064\files\tools\dotnet\dotnet.exe
```

| Command / check | Observed result |
| --- | --- |
| `& $dotnet --version` | 10.0.402 |
| `& $dotnet build src/Brokerage.Web/Brokerage.Web.csproj -c Release --no-restore` | Pass; 0 warnings/errors |
| `& $dotnet test tests/Brokerage.Tests/Brokerage.Tests.csproj -c Release --no-restore` | Pass; 18/18 |
| Local publish command below | Pass; both installation fixtures included |
| Standalone Bicep `--version` | 0.48.1 |
| Bicep build/lint on root and all three local modules, `--no-restore` | Pass; no diagnostics |
| `.\scripts\Test-LocalScripts.ps1` | Pass; 17/17 parser and safety checks; no real Azure/installer invocation |
| Source ownership check | No matching external writer process; source stable across repeated hashes |
| Catalog recheck | Adatum Corporation/adatum.com record 1; Financial Services/Capital Markets valid |
| Docker client | 29.8.2, desktop-linux context |
| Docker engine | Unavailable: `dockerDesktopLinuxEngine` named pipe not found |
| Final artifact checks, 19:12 UTC | Pass; JSON/status, headings, local links, Markdown line limits and PNG CRCs |

```powershell
& $dotnet publish src/Brokerage.Web/Brokerage.Web.csproj -c Release --no-restore `
    -o artifacts/publish /p:UseAppHost=false
```

Build/lint used the existing standalone executable at `$env:USERPROFILE\.azure\bin\bicep.exe`.
No `az bicep` wrapper, automatic tool installation or registry restore was needed.
Root and module build commands followed this pattern:

```powershell
& $bicep build infra/main.bicep --no-restore --outfile infra/main.local-validation.json
& $bicep lint infra/main.bicep --no-restore
```

The same checks passed for `project.bicep`, `post-host.bicep` and `workload.bicep` under `infra/modules`.
Generated ARM JSON is local compiler output, not an executed plan.
It is stored under `artifacts/bicep/` after validation to avoid confusion with deployment inputs.

The 18 app tests cover answer digest/source checks, unknown citations, no success fallback, fixture inclusion,
gateway-authorized HTTP flow, anonymous rejection, tenant/object-ID/audience/issuer/lifetime boundaries,
blank/oversized messages and sanitized upstream HTTP 502.
The logged failure for the injected upstream-error test is expected; the test passed.
The source, inference and signing operations are test doubles only in the test project.
Neither an actual Key Vault signature nor real model behavior was proved by these tests.
The demo guide's focused commands were also exercised: authorized flow 1/1, token boundaries 5/5,
and sanitized upstream failure 1/1 passed.

Script tests exercise PowerShell parsing, denied consent, missing output, insecure URL, command-only WhatIf,
wrong account, malformed/unconfirmed targets and local parameter/command generation.
The Azure CLI is replaced by a lexical process-local double; the real CLI and installer never run.
Two initial test-harness failures (counter scope and expected parameter count) were corrected before the final run.
They were local test defects, not Azure attempts.

`Initialize-Reference.ps1` now checks exact account name, enabled subscription and tenant after consent/ShouldProcess.
`-WhatIf` performs no Azure reads. The installer accepts `-DotnetPath` and restores the prior tenant environment.
It still requires separate installation consent and private connected operator access.
It uploads/read-verifies the FAQ and creates/reuses a real immutable agent version only when explicitly run later.
It is not a transactional installer: if a later step fails, uploaded fixture changes can remain.

Docker build/run was not attempted after the engine readiness failure.
Static Dockerfile/azd inspection confirms root build context, .NET 10 multi-stage build, fixture inclusion,
port 8080 and non-root runtime user. Container image execution remains unverified.

## 🏗️ Deployed Resources

**None deployed by this job.** No resource provisioning state or health evidence exists for this reference.
No Azure account lookup, provider registration, quota query, role change, image push, fixture upload,
agent creation, ARM validation, what-if or deployment executed.
Local Bicep success proves syntax/module type checks, not Azure policy, permissions or runtime behavior.
The documented capability-host schema suppression and live Consumer role resolution remain deployment-time risks.

### Remaining deployment and runtime gates

1. Obtain a separate request authorizing exact-target Azure evidence checks.
   Reconcile existing CLI/azd account, subscription, tenant, cloud, RG and environment without assuming defaults.
1. Verify all feature/SKU intersections, exact model/version/type/quota/capacity, provider/policy constraints,
   Consumer role GUID, single-tenant backend audience, private DNS/operator connectivity and address overlap.
1. Prepare/review authorized what-if and dated itemized service/token costs.
   Obtain explicit deployment consent for the exact targets and staged change set after that review.
1. Provision the foundation; privately build/push the real image and install source/agent;
   preview and authorize the workload stage as described in `04-implementation-plan.md`.
1. Prove deployment, direct model inference, agent invocation, browser chat, grounding and negative cases
   from the deployed identity/network path; document actual outputs and screenshots.
1. Only after all live checks pass, create the required runtime evidence index and review snapshot,
   present suitability for review and stop. Do not self-approve or compose.

## 📤 Outputs (Expected)

| Output | Current value |
| --- | --- |
| Application URL | None deployed; expected public APIM URL is an IaC output, not a working endpoint |
| Foundry project endpoint | None deployed |
| Installed agent version / response IDs | None from Azure |
| Runtime FAQ / signing receipt | Local fixtures and contract tests only; no live read/signing evidence |
| Architecture / runtime diagrams | Present; provisional design images, not live screenshots |
| Demo guide | `demoguide/demoguide.md`; local rehearsal plus gated future live steps |
| Local evidence | `local-validation.json`; not `scenario-validation.json` |
| Operational checkpoint | `phase-a-status.json`; no shared portal status edited |
| Runtime acceptance / review snapshot | Not created; live acceptance pending |

### Cleanup and stopping boundary

No cloud cleanup command is appropriate because this job created no Azure resources.
Local publish/compile/test outputs stay under the scenario; temporary script-test target fixtures are removed.
No portal, shared scripts, instructions, agents or skills were modified.
No approval helper, hack package, composition, publication or event rollout was invoked.
**Stop at local completion. Deployment is not authorized; live acceptance remains pending.**
