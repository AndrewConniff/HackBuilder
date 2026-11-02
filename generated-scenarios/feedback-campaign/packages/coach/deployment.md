# Destination deployment guide

Local composition grants no rollout authority. A separate event request,
explicit destination choices and scoped permission review precede cloud work.
Neither the reference region nor any shared CLI default is a destination.

## Required destination choices

From this package root, create/select azd environment `feedback-campaign-coach`.
Set resource group `rg-feedback-campaign-coach`. For participant Team 01,
use `01-feedback-campaign-hack` and `rg-01-feedback-campaign-hack` instead.
Each package must retain its own azd directory; never share one.

```powershell
azd env new feedback-campaign-coach
azd env set AZURE_RESOURCE_GROUP rg-feedback-campaign-coach
azd env set AZURE_SUBSCRIPTION_ID "[chosen-destination-subscription]"
azd env set AZURE_TENANT_ID "[chosen-destination-tenant]"
azd env set AZURE_LOCATION "[explicitly-chosen-destination-region]"
```

Select the authorized matching CLI identity separately; scripts fail on mismatch
and never change shared defaults. Resolve placeholders before execution.
Recheck destination availability for gpt-4.1-mini version 2025-04-14,
GlobalStandard capacity 10, Foundry direct projects, Linux B1 .NET 10,
Service Bus Standard, Tables and Monitor. Reference eligibility is not portable.
Run Bicep build/lint and reviewed what-if for these exact targets.

## Scoped deployer and runtime rights

Deployer needs resource-group control-plane deployment rights and role-assignment
authority at only the reviewed resource scopes. Preprovision discovers only the
signed-in installer's object ID; it does not register applications or grant consent.
Bicep grants the installer Table Data Contributor on scenario storage, Azure AI User
on the project, Sender/Receiver on posts and Receiver on replies. These permit
hash installation, agent initialization and stream/DLQ inspection, not directory writes.

App managed identity separately receives Table Data Contributor on scenario storage,
Azure AI User on the project, Receiver on posts and Sender on replies.
No service keys or local app passwords authenticate Azure calls.
Do not grant runtime ARM or Graph permissions to work around a deployment failure.

## Authorized installation sequence

`azd up` is mandatory for later deployment acceptance of each deployable package,
but is not executed in this local composition phase.
Coach hooks: preprovision verifies destination and installer; postprovision
creates/reuses local account hashes; postdeploy installs/reuses the prompt agent,
pins its actual version and inserts initial rule rows only when absent.
Allow scoped RBAC propagation then rerun the same hook on a transient denial.
Never replace a human-promoted rule pointer on rerun.

Publish includes Policy and SeedData through the project content settings.
Initial policy is supplied per invocation; seed posts are explicit operator
input, not automatically transmitted to an external channel.
No reference deployment/runtime receipt ships here.

## Destination acceptance and private delivery

Verify actual model/agent invocation through app MI, source-policy grounding,
positive automatic queue acceptance, both edited human replies, restart persistence,
wrong-role/CSRF/stale/duplicate denials and immutable promotion/rollback.
Inspect actual posts/replies correlation IDs using scoped data roles.
Test failure/retry and DLQ safely in the authorized environment.
Local tests do not prove live provider outage/DLQ behavior.
Deliver participant credentials separately from coach credentials using a private
channel. Keep deployment outputs and access files outside public archives.
Budget, scaling, cleanup and publication need separate event scope decisions.
