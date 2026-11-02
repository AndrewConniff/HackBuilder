# Local release notes

This release derives from the unchanged, user-approved Adatum Corporation reference.
Industry: Media & Communications (`media-communications`).
Exact business units: `sales`, `marketing`; no additional unit or pattern is introduced.

## Evidence boundaries

The reference's retained evidence reports real app-MI Foundry grounding, both edited
human replies, positive auto-routing, queue acceptance, restart persistence, role/CSRF/
stale/duplicate denials and immutable rule promotion/rollback. These are prior reference
observations, not new event-runtime checks.

Live provider-outage and DLQ injection were not run. The package retains local
provider-failure/retry tests. Queue acceptance is not external email or social delivery.
Mixed campaign-03 actually scored at least 89% negative; neutral campaign-04 is the
fallback demonstration. Product-aspect/80%-negative proposals are inactive until
explicit human promotion. No native tool or native durable Foundry workflow is claimed.

## Local checks and source preservation

The 32 .NET application tests are copied unchanged. Four active installation tests
are retained; four obsolete tests for the inactive Entra installer are omitted along
with that installer. Four destination-guard tests and a bearer-token wire guard
replace that obsolete coverage.
The local record distinguishes current installation/guard tests from the
reference's original eight installation tests; the package now runs nine script tests.

NuGet.org was inaccessible from this host during the first build attempt. Local restore
uses the existing repository-configured package-feed proxy, then build/test use
`--no-restore`. The deployable archive keeps a public NuGet configuration.
Failed attempts and the final exact command results remain in local-checks.json.
A transient Windows file-lock cleanup failure in workflow tests was retried without
altering tests or stopping another process.

## Delivery and pending rollout work

Four source roots and four separate ZIPs preserve learner/private boundaries.
No private credential file was opened or copied. No reference endpoints, target IDs,
authorization state, runtime receipts, `.azure` state or deployment credentials ship
in those ZIPs. Local validation logs stay outside exported archives.

The minimum starter intentionally has no app or Foundry resources and reports
not-configured. Portal-first prompt work is supported; the bounded durable action
requires a hybrid/code adapter, not a nonexistent low-code native tool.

All deployment-critical inventory entries are packaged, not azure-verified.
Destination regions, subscriptions and tenants remain unselected. A future rollout
must obtain separate consent, choose explicit destinations, check current model/SKU/
quota availability, run exact what-if, generate fresh private credentials and prove
destination runtime behavior. No deployment, Entra change, publication or commit was
performed in this local composition phase.
