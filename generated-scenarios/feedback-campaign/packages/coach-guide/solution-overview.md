# Private solution overview

Adatum Corporation; Media & Communications; exact businessUnits `sales`, `marketing`.
Nino Kapanadze is the Marketing campaign operator; Petra Bartosova is the
Marketing Product Manager; Eesha Chatterjee is the Sales conflict specialist.
Airi Ilves, Hasan Ibrahimov and Nemanja Milatovic are synthetic subscribers.

## Proven architecture and authority

One native Foundry prompt agent, campaign-listener, interprets/drafts using
gpt-4.1-mini 2025-04-14, campaign-policy-v1, source post and exact rule snapshot.
It is not a native orchestration workflow and has no deployed native tool.
App-hosted .NET 10 code coordinates durable routing/HITL; humans are not agents.
App MI calls the project Responses API and scoped Tables/Service Bus.

App Service Linux B1 hosts authenticated Razor Pages and one queue worker.
Service Bus Standard posts/replies queues have seven-day duplicate detection,
five max deliveries and DLQ; Tables campaignstate holds state/outbox and rule versions.
Monitor is Log Analytics plus workspace Application Insights.
Tables use PartitionKey/RowKey/Payload, server timestamps and ETag concurrency.
Cases use SHA256(sourceId); reply IDs are deterministic. Stable retries do not
imply unlimited exactly-once delivery. No external email/social adapter is deployed.

## Exact routing and governance

Evaluate overall positive >=0.80 first: auto reply. Otherwise negative >=0.89:
ProductManager. All others: ConflictResolutionSpecialist.
campaign-03 actually scored >=0.89 negative in retained runtime evidence; it is
not guaranteed to demonstrate fallback. Use neutral campaign-04 for that evidence.
Product-aspect/80%-negative rules are proposals until human promotion.
Rules are immutable; active pointer uses ETag, existing cases retain snapshots;
rollback promotes a prior version without editing history.
Humans edit and explicitly send; wrong role, stale revision and repeat send fail.

## Security and evidence boundaries

Local salted framework hashes persist in Tables. Secure session cookies,
CSRF/origin checks, durable session keys, lockout/rate limit and stamp checks
are retained. Coach ControlAdmin credentials remain separate from participant roles.
No Entra consent-dependent login is included.
The old, inactive directory installer and its four legacy tests are excluded;
active installation tests plus destination guards are packaged.
The 32 copied app tests remain the approved implementation's tests.

Reference evidence records actual app-MI grounding, both edited human replies,
queue acceptance, restart persistence and denial/promotion/rollback behavior.
These are retained reference observations, not new package runtime tests.
Live provider outage/DLQ injection was not run; local retry/failure tests exist.
No runtime receipts or reference endpoint are copied.
Future event targets and fresh credentials require separate authorized deployment.

## Minimum starter and pacing

Starter: resource-group isolation/tags, destination/access guard, ten source posts,
policy and unconfigured interface contract only. No completed app or agent.
Learners choose the implementation; do not make them reproduce the full web UI.
Preserve prompt checkpoints and focus the hybrid increment on one durable action.
At an unresolved adapter checkpoint, demo verified prompt work and disclose the gap;
never claim a mock receipt completes real queue acceptance.
