# Feedback Campaign demonstration and recovery walkthrough

## Current evidence

**Reference deployed; local-account and real human-workflow acceptance passed.**
Open https://fc-web-kvjmo565tswuy.azurewebsites.net/Login using an issued local lab account.
Central US installation, direct model/versioned agent probes and actual application
managed-identity chat passed. Both human queues, edited replies, queue acceptance,
wrong-role/stale-decision denial, actual restart persistence and rule promotion/
rollback are retained in `evidence/local-app-runtime.json`. Use the access guides
under `docs/`; passwords are only in private deployment files.

## Audience and story

For Media & Communications Sales and Marketing: Adatum Corporation's streaming
campaign receives praise, product complaints and mixed company/product sentiment.
Campaign Listener interprets; deterministic Control routes; humans own sensitive
responses and business-rule promotion. Allow 12 minutes plus sign-in.

## Prerequisites

Reviewed Azure authority, actual regional eligibility and what-if,
successful azd hooks, real agent/version and policy installation, signed-in
local reviewer roles and worker/Table/Service Bus connectivity. Coach roles are
for reference acceptance only, not production separation of duties.

## Live flow, after deployment

1. Open the actual `APP_URL` output; sign in through the app link. Confirm roles.
2. Show the two diagrams and initial rule distinction: >=80% positive; otherwise
   >=89% negative; all others Conflict Resolution Specialist. The later 80%
   negative illustration is a proposal, not the active threshold.
3. Submit `campaign-01` from `src/FeedbackCampaign.Web/SeedData/posts.json`.
   Refresh and inspect source, rule v1, actual Foundry response ID, assessment,
   positive scores and state. If the model does not score >=80%, do not alter or
   fabricate scores: choose another real positive example and report the result.
   Observe PendingSend then Queued and accepted reply-stream correlation receipt.
   This is not an email delivery receipt.
4. Submit `campaign-02`. If real negative score >=89%, show the Product Manager
   inbox; otherwise truthfully show Conflict Resolution fallback. Edit the real
   draft, explain the evidence, and explicitly Approve edited reply. Prove a
   second click cannot send another independent reply.
5. Submit `campaign-03` and show company versus product disagreement. Actual overall
   sentiment may still route it to Product Manager; do not force a preferred score.
   Use neutral `campaign-04` to demonstrate Conflict Resolution and inspect the packet, score uncertainty,
   investigation and future-agent recommendation. Do not execute the suggestion
   or reroute purely because the agent proposed it.
6. Ask the grounded assistant: “Can Sales promise a refund from this campaign?”
   Expect a policy-based refusal to invent entitlement, cite campaign-policy-v1
   and preserve actual response ID. Confirm the browser-to-app-to-MI Foundry path,
   not just a direct installer probe.
7. ControlAdmin loads v1, saves a new immutable version enabling product-negative
   >=80%, reviews JSON and explicitly promotes with a reason. Show pointer
   promotion history. Resubmitting an old source does not reroute it: use a new
   source ID and observe the new snapshot. Roll back by promoting v1 explicitly.
   Explain adding new agent destinations also requires a reviewed adapter, RBAC
   and acceptance tests, not a model-invented endpoint.
8. Open another browser without sign-in: cases/rules/chat APIs must deny. Sign in
   as the local Product Manager and attempt a ControlAdmin promotion or a Conflict
   Resolution reply: expect 403. Only the assigned reviewer may approve a case.
   No Entra assignment changes or administrator consent are involved.
9. Keep a human case pending, restart the authorized app, reload and prove the
   same state, snapshot and ETag survived. Reuse a stale edit to demonstrate 409.
10. Optional extended resilience exercise (not performed in the retained live run):
    demonstrate a genuine provider/schema/error case within reviewed test scope.
    It must remain Failed with no outgoing reply. Repair, explicitly retry and
    record real recovery. Show poison ingress/DLQ only with required queue access.

## Expected versus observed

Synthetic fixture semantics are expected labels, not guaranteed score outputs.
Threshold precision is covered locally by deterministic boundary tests; live
classification quality needs independent human labeling and calibration. Do not
coerce model scores just to make a demonstration pass.

Capture actual screenshots, HTTP status codes, case IDs, UTC times, response IDs,
rule versions and accepted queue receipts in `evidence/`. No tokens or raw auth
storage in shared artifacts. Update `scenario-validation.json` only for actual
passing checks. A missing check stays false/pending.

## Recovery, cost and suitability boundary

Use `docs/deployment-guide.md` for bounded retry, stale ETag, outbox dedupe,
DLQ and rule rollback. Planning cost $40–95/month; $100 review ceiling; public
synthetic reference, single B1/LRS, no private endpoints/WAF/production SLA or
external-channel integration. No production delivery claim.

After all real acceptance passes, create the fingerprinted workflow snapshot,
present the working reference with limitations and request explicit suitability
approval. Do not record approval, start composition or create packages early.
