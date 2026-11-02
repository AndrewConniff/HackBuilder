# Fourth Coffee private solution overview

## Approved scope and reference behavior

Hospitality & Travel; businessUnits `["sales"]`. Sales owns store readiness, stock drafts and managerial close.
Store managers see one assigned store; north-area manager sees 001/002, never 003.
Finance receives a reviewed report only. No supplier transmission, spending or ledger posting exists.
Fourth Coffee is the exact catalog identity; the four synthetic people retain their deterministic mapping.

## Complete reference graph

Browser local credentials -> secure cookie/CSRF -> .NET 10 Razor Pages/API.
Server-owned role/store claims -> Table CoffeeBackOffice -> authorized snapshot.
Deterministic stock/margin calculations -> two concurrent stock and margin Foundry agents -> close coordinator.
App-hosted orchestration, not a Foundry-hosted native workflow. No agent receives an order-write tool.
Human approval -> ETag-protected durable internal order; replay returns the original approval receipt.
Changing stock invalidates stale unapproved drafts. Shared dummy credentials are demo-only, not production auth.

AIServices S0/direct child backoffice project/model deployment support three persisted prompt agents.
App Service Linux P0v3 baseline 1, elastic cap 3; StorageV2 Standard_LRS with shared keys/public blobs disabled.
Backend system MI uses Table Data Contributor and project-scoped Foundry Agent Consumer.
Installer uses existing CLI identity; project MI has Foundry User on its account.
Runtime Consumer calls version-selected agent Responses endpoints, not the project developer Responses route.
Public authenticated TLS endpoints remain intentional; do not weaken identity or substitute API keys.

## Bounds and observable behavior

Maximum 5 stores, two parallel branches then one synthesis, 800 output tokens per call, 90-second shared deadline.
Two close requests per instance and per-user rate guard are not a globally distributed concurrency controller.
SDK transport retries may occur within the deadline; no application-level replanning or action retry exists.
Any branch failure blocks synthesis and completed-close success; recovery never expands permissions.
Source row IDs/versions, response IDs and correlation prove execution without retaining chain-of-thought.
Grounded prose is advisory; decimal structured figures are authoritative.

## Minimum starter and learner decisions

Only an isolated empty resource group is provisionable; exact local fixtures are provided.
No hosting, storage, model, agents, cloud data load or starter app is preprovided.
Learners choose components and retain the approved behavior through progressive checkpoints.
Private Finale holds exact expected figures and recovery guidance.

## Disclosed limitations

Approved response: Approve suitability with disclosed limitations.
Actual reference functional runtime tests passed; new coach/team runtime is not independently verified.
Ten-read p95 2.41 seconds missed 1 second. Ten simultaneous closes: 2 completed, 8 HTTP 409 rejected.
Ten-user close target is not met; 9.50 seconds for one area close is not sustained-load certification.
No actual three-worker scale-out was exercised. Never count rejected work as fast successful work.
Public network/no WAF, non-HA baseline, shared local demo credentials, preview SDK and legacy model remain.
Reported model inference deprecation: 14 April 2027. Any replacement needs a fresh scope/technical review.
Reference illustrative USD 120–270/month is not a destination quote or budget cap.
No historical-attestation exception is used; composition reuses actual reference evidence without exporting it.
