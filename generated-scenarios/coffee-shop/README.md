# Fourth Coffee store readiness and daily close

Deployed reference for Hospitality & Travel, business unit sales, in Sweden Central.
Local login, real managed-identity Foundry calls and the browser walkthrough are verified.
Working-scenario suitability approval is still required; no hack package has been started.

**App:** https://web-fc-keegvmxonq3wc.azurewebsites.net/

> [!WARNING]
> This is a bounded-concurrency demo, not a production capacity claim.
> Ten simultaneous closes produced 2 successful closes and 8 explicit busy responses.
> Ten concurrent HTTPS reads measured p95 2.41 seconds, exceeding the 1-second target.
> Functional acceptance passed; the full performance targets did not.

## Reference navigation

- [Requirements](01-requirements.md)
- [Architecture, security, scaling and cost](02-architecture-assessment.md)
- [Implementation plan](04-implementation-plan.md)
- [Local validation results](05-local-validation.md)
- [Deployment review and requested authorization](06-deployment-review.md)
- [Deployment summary](06-deployment-summary.md)
- [Executed demonstration and recovery](demoguide/demoguide.md)
- [Actual local checks](evidence/local-checks.json)
- [Live evidence status](scenario-validation.json)
- [Actual browser walkthrough](evidence/browser-checks.json)
- [Area-manager screenshot](evidence/browser-area-close.png)
- [Architecture diagram](03-architect-diagram.png)
- [Runtime diagram](04-runtime-diagram.png)

## Sign in

| Account | Role | Stores |
| --- | --- | --- |
| `storeman001` | StoreManager | 001 |
| `storeman002` | StoreManager | 002 |
| `petender` | AreaManager | 001 and 002 |

Store accounts use the password supplied separately by the user, not a password published in this reference.
From the repository root, the original Windows operator can retrieve the separate area-manager password:

```powershell
$login = Import-Clixml -LiteralPath '.abcbuilder-portal\scenarios\coffee-shop\area-login.clixml'
$login.GetNetworkCredential().Password
```

This is an operator-local DPAPI-protected receipt, not a portable/public login document.
No end-user Entra sign-in, directory account creation, registration or consent is used.
Backend managed identity remains for Azure service access.

## Run local verification

From this scenario directory:

```powershell
python scripts\validate_local.py
```

Dependencies: configured .NET 10, Python, Node/npm, PowerShell and Azure CLI Bicep.
The script restores only project-local dependencies and runs no Azure subscription operation.
Diagram generation additionally uses existing Python diagrams and Graphviz.

The real application is under `src/CoffeeShop.Web`; tests under `tests/CoffeeShop.Tests`.
Normal `dotnet run` serves the landing UI but requires initialized Table-backed accounts/data for business access.
There is no production fixture-auth switch or canned Foundry success.
Tests use the actual cookie/password/CSRF path with isolated account/data repositories and agent doubles.

## Authorized deployment and validation

Deployment was explicitly approved on 24 October 2026, with application-local login instead of Entra user sign-in.
This approval does not approve the scenario's hack suitability.
Read-only preparation scripts are `Test-Readiness.ps1` and `Get-ReferenceWhatIf.ps1`.
Their switches are safety guards, not authorization.

After actual review/consent, configure only this azd environment, no shared Azure defaults:
`AZURE_ENV_NAME=coffee-shop-ref`, confirmed subscription/tenant/location/principal,
resolved `FOUNDRY_CONSUMER_ROLE_ID`.
Set `COFFEE_DEPLOY_AUTHORIZED=yes` only under the recorded resource authorization.
Pass installation passwords via process environment only, never azd files or ARM parameters.
`azd up` uses preprovision target assertion, postprovision local-account/fixture/agent initialization,
then service packaging/publishing. Actual IDs/versions/endpoints flow from those operations.
The current operator needs the reviewed Azure resource/data-plane permissions; no directory writes are needed.
Permission denials stop installation; the scripts do not elevate or change policy.

The approved `azd up` completed; the endpoint-route correction was published with `azd deploy --no-prompt`.
See [deployment results](06-deployment-summary.md) for the actual initial failures and in-scope repairs.

With installation passwords supplied only in the current process environment, run:

```powershell
python scripts\validate_live.py --authorized
python scripts\validate_live.py --authorized --concurrent-closes
```

The existing repository virtual environment also runs `scripts\validate_browser.py --authorized`.
Its screenshots contain real deployed UI and response IDs, not test-double output.
The concurrency runner validates safe admission behavior; its passed status does not mean the load target passed.
Inspect `targetPassed` in its evidence. A branch-failure check requires an externally applied real fault;
see the demonstration guide for restoration and recovery.

No hack plans, learner packages, event deployments or publication are included.
