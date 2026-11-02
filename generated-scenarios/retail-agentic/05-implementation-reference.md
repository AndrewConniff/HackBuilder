# Step 5: Implementation Reference - retail-agentic

> Local implementation evidence | 2026-10-28 | Not deployed

## IaC Templates Location

Use [the subscription entry point](./infra/main.bicep),
[resource composition](./infra/resources.bicep) and [separate scoped roles](./infra/roles.bicep).
[The implementation plan](./04-implementation-plan.md) records the verified AVM versions.
[azd configuration](./azure.yaml) wires Linux App Service and the Windows postprovision hook.

## File Structure

```text
retail-agentic\
  infra\                         AVM-first resources and separate human/workload grants
  src\Woodgrove.Web\              .NET 10 Razor Pages and real Foundry SDK integration
    Models\Commerce.cs            Deterministic commitment, expiry and synthetic-payment policy
    Services\                     Native Azure Table persistence, accounts, agents and durable worker
    SeedData\products.json        Twelve synthetic grocery fixtures; installation only
    wwwroot\icons\                Official Microsoft Fluent System Icons and MIT license
  scripts\                       Guarded deployment and private-host installation
  tests\Woodgrove.Tests\          Local policy, transaction and authenticated HTTP tests
  tests\Test-LocalPreparation.ps1 Syntax and no-CLI provisional-evidence guard
  Woodgrove.sln                   Application/test solution
```

`.private`, `.azure`, binaries and compiled ARM output are gitignored.
No actual reference passwords, endpoints or deployment outputs have been generated.

## Validation Status

| Check | Result | Scope |
| --- | --- | --- |
| .NET tests | Passed: 28, zero skipped | Policy, atomicity, replay, budgets, local auth and HTTP boundaries |
| Solution build | Passed: zero warnings/errors | SDK and Razor compatibility; warnings treated as errors |
| Locked restore | Passed | Pinned runtime dependency graph |
| Portable publish | Passed | Actual DLL, twelve seed products and web assets included |
| Bicep build/lint | Passed | Local compilation and lint only |
| PowerShell | Passed | Four installers parsed; provisional evidence stops before all CLI calls |
| azd YAML | Passed | Syntax and App Service wiring, not a cloud deployment |
| UI fixtures | Passed | Static rendered customer/login pages; responsive, keyboard and contrast checks |
| Repository workflow tests | Passed: 48 | Existing workflow/customization guard coverage |
| Authoring skill validation | Passed | Existing skill resources only; no hack content created |
| Azure readiness | Authorized, incomplete | Original VM SKU restricted; dated target and quota evidence recorded |
| ARM what-if | Incomplete, not a passed gate | 25 evaluated creates; five dependent modules short-circuited |
| Private initialization | Not executed | SSH, signed bootstrap, private DNS/TLS and MI still need real acceptance |
| Foundry/app runtime | Not executed | Model/agent responses, full journeys and exported logs remain unproven |

Commands below run from the scenario root; all listed local commands passed on 2026-10-28.

```powershell
dotnet test tests\Woodgrove.Tests\Woodgrove.Tests.csproj --nologo -v quiet
dotnet build Woodgrove.sln --no-incremental --nologo -v quiet -warnaserror
dotnet restore src\Woodgrove.Web\Woodgrove.Web.csproj --locked-mode --nologo -v quiet
dotnet publish src\Woodgrove.Web\Woodgrove.Web.csproj -c Release --no-restore --no-self-contained
az bicep build --file infra\main.bicep
az bicep lint --file infra\main.bicep
pwsh -NoProfile -File tests\Test-LocalPreparation.ps1
```

Tests also ran with a 30-second test-session timeout.
The publish validation used a gitignored `bin\PublishCheck` output directory.
The UI check rendered actual Razor pages against isolated test services and served those static files on loopback.
The temporary server was stopped; no runtime mock was registered in production.
Cleanup commands failed without a diagnostic.
Static previews remain in session files and publish checks in ignored `bin`.
Exclude these retained validation outputs from any release or export.
An initial test-only key-ring warm-up tried an unreachable managed-identity endpoint; the test was stopped.
Test key storage and telemetry transport are now isolated. That failure is not Azure runtime evidence.

On 2026-10-28, read-only readiness and official Bastion extension installation were explicitly authorized.
The extension is installed at 1.4.3. No provisioning, role grants, Entra changes or spending were authorized.
See [the exact target, SKU, quota, policy and what-if observations](./00-region-availability.json).

The read-only proposal used subscription `efd64343-6ef4-4926-951f-d3229f38bd76`,
Sweden Central, environment `retail-agentic`, group `rg-retail-agentic` and Standard_D2s_v5.
No azd environment or resource group was created. Original Standard_B2ms defaults remain unchanged.
VM size and verified inherited human role reuse are now explicit Bicep parameters.
Build/lint and compiled ARM parameter/condition assertions passed after this change.
Storage and workload data grants remain separate; no grant was executed.

The actual what-if command used an owner-only ephemeral secure-parameter file:

```powershell
az deployment sub what-if --subscription efd64343-6ef4-4926-951f-d3229f38bd76 `
  --name retail-agentic-readiness --location swedencentral --template-file infra\main.bicep `
  --parameters '@.private\readiness\what-if.parameters.json' --no-pretty-print --output json
```

Default validation was Provider. ARM returned Succeeded with 25 evaluated creates and no modifications/deletes.
Five modules were short-circuited: network, business-state, foundry-private-access,
grocery-console and explicit-data-and-operator-access. Seven further internal expansion warnings were returned.
The observed count is not a complete resource inventory or a passed readiness gate.
Generated identities and private runtime checks remain installation-dependent, not invented what-if inputs.
The ephemeral parameter file was removed successfully; raw results remain private and gitignored.
Earlier retained local validation outputs described above are a separate cleanup issue.

## Resources Created

**None.** These are local definitions, not an inventory of provisioned resources.

| Definition | Intended resource | Implementation |
| --- | --- | --- |
| Resource group | `rg-{environment}` with mandatory tags | Subscription entry point |
| Foundry | AIServices S0, direct child project and configurable model | AVM plus documented project exception |
| Business state | Private LRS Storage, Table/Blob endpoints | Native Table transactions and Blob session keys |
| App | Linux B1 App Service, public HTTPS and outbound VNet integration | azd service `web` |
| Private access | Four subnets, five DNS zones, three private endpoints | AVM network composition |
| Human/automation host | Private Windows Server 2022 Standard_B2ms and Bastion Standard | No VM public IP |
| Management egress | Standard NAT plus its separate Standard public IP | Default outbound access disabled |
| Telemetry | Log Analytics and Application Insights | Web SDK instrumentation; live export pending |
| Roles | Distinct human, web MI and VM MI grants | Foundry User/Owner and Storage data roles |

The app is public and authenticated; Foundry/Storage ingress is private.
NAT is outbound connectivity, not destination filtering. Basic agent egress/state remains platform-managed.
See [the architecture and current cost envelope](./02-architecture-assessment.md).

## Deployment Instructions

Do not provision from this local-validation result.

1. Reuse the recorded read-only authority and observed matching target; do not change shared defaults.
1. Review the unapproved Sweden Central/D2s_v5 revision and its approximately USD 73/month compute increment.
1. Complete remaining SKU/feature checks and dependent what-if expansion; keep the region unselected meanwhile.
1. Wire approved VM/reuse values through azd and preserve separate Storage/workload data grants.
1. Review exact what-if, scoped role changes, private execution, current pricing and total spending together.
1. Only after actual deployment consent, run the prepared installer in the reviewed azd environment.

The eventual command is [the guarded wrapper](./scripts/Install-Reference.ps1), not permission by itself.
It requires non-provisional evidence and matching CLI/azd target settings.
The postprovision hook builds locally and pins the ARM-returned SSH host key.
It verifies SHA256 and transfers the runtime archive through Bastion.
Initialization runs on the VM using its managed identity; local azd publishes through public authenticated SCM.
Endpoint/model values are encoded as JSON data, not interpolated as executable PowerShell.
Successful initialization revokes its exact SSH key.
Failed initialization explicitly retains restricted retry material.

Generated customer and operator credentials return as three separate owner-only files:

```text
.private\{environment}\customer-001-access.json
.private\{environment}\customer-002-access.json
.private\{environment}\operator-001-access.json
```

These are not Entra or Azure credentials. Do not copy the operator file to a customer.
Human administration still requires Bastion RDP, a VM browser and the deploying user's own Azure sign-in.
VM managed-identity initialization does not satisfy that acceptance.

## Key Implementation Notes

- Three real, separately version-pinned Foundry agents use typed client-executed tools.
  Definition digests make installation repeatable; no mock completion or JSON runtime fallback exists.
- `Product.Id` is an integer; order IDs are stable 24-character hashes for customer-bound create deduplication.
  This intentionally differs from a generic integer-ID CRUD sample.
- The same warehouse partition contains order, stock, daily counter and action receipts.
  Exact ETags and atomic batches prevent duplicate reservations or synthetic captures.
- Stage zero authorizes the accepted synthetic amount; fulfillment reserves and captures atomically.
  Customer-approved replacements update authorization. Dispatch does not reprice reserved goods.
  Undispatched cancellation atomically returns stock and records the synthetic refund.
- Customer approval binds owner, full cart, total, slot, version and ten-minute expiry.
  Expired proposals become holds; cancellation is the explicit recovery path.
- Operator delay and adapter-failure controls never approve changes or manufacture an inference result.
- Durable request/tool/token counters survive retry. Active time is conservatively reserved in separate rows.
  A process crash can exhaust the remaining stage budget rather than silently granting a new 60 seconds.
- Before-call input accounting uses serialized UTF-8 bytes plus a 4,000-token overhead allowance.
  Actual returned usage is checked and persisted. This allowance is not a measured strict provider guarantee;
  validate it with real traces before accepting the provisional token NFR.
- Session keys use private Blob access and Storage encryption at rest, without a separate Key Vault envelope layer.
  Installer logs remain console output; web instrumentation exports through the configured Insights connection.
- Real network denials, MI calls, restart recovery, load, telemetry redaction and human administration remain pending.
  Never create a passed runtime receipt, suitability approval or hack package from these local checks.
