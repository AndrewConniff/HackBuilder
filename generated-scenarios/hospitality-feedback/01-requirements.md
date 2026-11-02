# Requirements — hospitality-feedback

## Project Overview

**Resume status, 2026-10-24: intake recovered; design confirmation required.**
Existing implementation and dated results are retained, not imported as current completion or authorization.
Local construction does not require an Azure target. Cloud preparation and deployment require separate exact-target
authorization; neither is recorded in the current portal state.

| Field | Value |
| --- | --- |
| Project | `hospitality-feedback` |
| Industry | Hospitality & Travel |
| Business units | `["generic"]`: documented legacy fallback; no department targeting |
| Vertical | Hotels |
| Primary stakeholder | Hotel service-quality manager |
| Story | Multilingual customer-service feedback analysis with traceable hotel-service evidence |
| Phase | A only; no package planning, participant setup, event rollout or publishing |

The synthetic operating story uses **Margie's Travel** reviewing hotel-service feedback.
Do not invent a separate hotel company or claim the catalog declares this company's industry.
Managers compare housekeeping, check-in, noise, breakfast and staff-service feedback across languages.
They ask a real Foundry agent for grounded summaries and specific operational improvements.
The application must retain original-language text and link every conclusion to stable feedback identifiers.
The service-quality manager owns evidence review and proposed operational improvements, not automated hotel changes.
Authorized operators can submit synthetic feedback and inspect evidence/status; unauthenticated callers cannot use APIs.
Revenue/occupancy analysis, all-department targeting, production guest data
and autonomous corrective actions are excluded.

### Synthetic identity provenance

| Property | Value |
| --- | --- |
| companyName | Margie's Travel |
| companyDomain | margiestravel.com |
| companySlug | margie-s-travel |
| Source | `C:\HackBuilder\fictitious_company_names.csv` |
| CSV record | 21, excluding header |

The catalog has no industry column. Domain values are reference data, not deployable endpoints.
CSV validation rejected malformed company records 7, 11, 25 and 33 because they have extra fields.
No catalog was repaired. All person records had the expected field count.
Twelve fixtures now use exact `FullName` values from records 1–12 of
`C:\HackBuilder\fictitious_people_names.csv`, with a stable guest-ID-to-record mapping in `data/provenance.json`.
Never use invented names or anonymous person-name placeholders.

## Functional Requirements

| Capability | Priority | Acceptance criterion |
| --- | --- | --- |
| Real chat | Must | Deployed application invokes a real Foundry agent using managed identity |
| Language-aware analysis | Must | English, Spanish, French and Japanese fixtures retain original text and language |
| Traceable grounding | Must | Answers cite only feedback IDs retrieved from Storage with original-language excerpts |
| Main data platform | Must | Azure Blob Storage stores source feedback, processed evidence and audit records |
| No Cosmos DB | Must | No customer-deployed Cosmos resource; Basic service internals are a documented caveat |
| Queued ingestion | Must | Producer enqueues blob references and a worker exposes observable processing state |
| Delivery safety | Must | Duplicate message does not create duplicate accepted evidence |
| Processing visibility | Must | Correlation ID links enqueue, receive, processing, retry and terminal outcome |
| Negative case | Must | Invalid envelope enters explicit failure handling; unsupported questions do not fabricate |
| Runtime security | Must | Managed identity for Storage and Foundry; no account keys or source secrets |
| Proven deployment | Must | Live URL, model inference, agent invocation, chat and grounding all verified |

### Acceptance prompts and evidence

1. "Compare check-in complaints in Spanish and Japanese. Cite feedback IDs and original-language excerpts."
   Verify every cited ID exists in the processed fixture set and that the interpretation preserves source meaning.
1. "Résume les problèmes de propreté et propose deux améliorations, avec des preuves."
   Verify French response, factual source links and distinction between observed complaints and suggested actions.
1. Submit a valid synthetic feedback event and observe queued → processing → completed with a correlation ID.
   Verify raw and processed blobs through the actual runtime identity, not only a developer credential.
1. Resend the same event ID. Verify idempotency with stable accepted evidence.
1. Submit an invalid language/empty-text envelope. Verify visible validation error or poison handling, never success.
1. Ask about occupancy or revenue not present in feedback. Verify explicit insufficient evidence.

### Agentic business workflow

Use pattern **02, Sequential / Pipeline**, with one bounded Foundry prompt agent for evidence-based synthesis.
The application hosts deterministic ingestion, evidence selection and citation validation; these are not extra agents.
The manager's question triggers a draft summary and specific operational recommendations,
never a committed hotel action.
The simpler single-agent baseline is retained; multi-agent coordination and model-controlled ingestion
add no required value.

Typed handoffs are feedback input, raw feedback plus payload hash/correlation ID, queue blob reference,
processed evidence, chat request and answer with source-ID/excerpt citations.
Storage owns raw, processed, status and audit records. Guest names are not sent in the agent evidence projection.
Only the manager decides whether to act on recommendations; there is no automated operational write tool.
Positive acceptance requires valid source IDs and exact original-language excerpts
in every supported service conclusion.
Unsupported revenue/occupancy questions require an explicit insufficient-evidence result.
Coordination negatives include conflicting reuse of an ID, enqueue failure recovery,
invalid envelopes and retry exhaustion.
Five deliveries, bounded evidence retrieval and explicit poison disposition prevent indefinite background work.
Local contract tests cannot prove live model grounding, translation quality or authenticated Azure operation.

### Network Security

Network and data-residency requirements were not supplied. Public ingress, private endpoints and private-network
Foundry requirements are unresolved, not user-approved defaults.
Use authenticated chat and ingestion endpoints, HTTPS, private blob containers and least-privilege runtime RBAC.
Do not disable authentication or weaken networking to complete a dry run.

### Recommended Security Controls

Managed identity is explicitly required. TLS, encryption at rest, restricted evidence access and diagnostics are
recommended. Select private endpoints and network integration only after target policy and requirements are known.
Do not add a Key Vault unless actual secret requirements justify it.

## Non-Functional Requirements (NFRs)

User requests autonomous execution, but missing authorization is a stop condition.
No interactive questions, account switching, guessed region, model substitution or consent inference is allowed.
Record phase duration, failures, retries, commands and negative results.
No WAF priority ordering was supplied. Address all five pillars without inventing user selections.
No technical domains were selected. Generic is exclusive of specific units and does not mean every department.

| Requirement | Target | Acceptance evidence |
| --- | --- | --- |
| Authenticated APIs | Tenant/audience, allowlisted operator, required scope or role | Live allow/deny token cases |
| Payload-aware idempotency | Same ID/content accepted once; changed content returns 409 | Ingestion/collision tests |
| Durable recovery | Reconcile pending raw outbox; at most five deliveries before poison | Outbox and exhaustion tests |
| Bounded chat | At most 100 evidence records; dependency timeout 75 seconds | Limit and dependency-failure cases |
| Provenance | Twelve stable IDs, four source languages, catalog-backed guest names | Catalog/fixture validation |

## Summary for Architecture Assessment

Queue Storage is the selected simplest messaging choice; the workload needs a backlog, not ordered sessions,
transactions, topic fan-out or a replayable event stream. It is near-real-time queued ingestion, not Event Hubs.
Storage is the evidence system of record. Avoid Search, Cosmos and multi-agent complexity unless requirements change.
Foundry Standard setup conflicts with the no-customer-Cosmos constraint; Basic is selected.
Basic uses Microsoft-managed agent state; it does not promise an absence of Cosmos in service internals.
The user clarified that internal services are not a blocker.

### Requirements Completeness

| Section | Status |
| --- | --- |
| Story and required capabilities | Recorded |
| Company identity | Validated against local catalog |
| Exact Azure account/subscription/tenant | Missing |
| Resource groups and azd environments | Missing |
| Region/model/quota/capacity | Not queried; no target authorization |
| Post-what-if target approval | Missing |
| Basic persistence choice | Selected; no customer-deployed Cosmos |
| Network/policy suitability | Live preflight pending |

Hospitality & Travel / Hotels is valid repository intake, but unsupported by the current six-industry
Skillable composition catalog. Any later composition needs an explicit support-extension decision or a revised,
reapproved scenario. Do not silently map to retail.

## References

- Canonical procedure: `.github/skills/hack-builder-workflow/SKILL.md`
- Live evidence index: `00-region-availability.json`
- Provisional design: `02-architecture-assessment.md`
- Resume instructions and actual results: `06-deployment-summary.md`
- Local code and resource mapping: `04-implementation-plan.md`
