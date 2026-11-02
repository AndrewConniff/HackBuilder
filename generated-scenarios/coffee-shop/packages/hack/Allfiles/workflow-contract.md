# Fourth Coffee workflow contract

## Scope and evidence

Industry: Hospitality & Travel; businessUnits `["sales"]`.
Store managers see one assigned store; north-area manager sees 001/002, never 003.
Finance receives a human-reviewed close, not an implemented finance login or a ledger posting.
Treat local fixture names as synthetic display metadata, not real account entitlements.
Server-owned identity grants decide scope before reading business data or invoking a model.
Separate instructional test data from real inference receipts.

## Internal order

An authenticated read accepts authorized storeId and returns snapshotVersion and source row IDs.
A draft contains storeId, snapshotVersion, draftId, explicit units/quantities and deterministic total.
Use positive shortfalls only and decimal prices. Never ask a model to decide permissions or calculate final money.
An approval supplies draftId, idempotencyKey and explicit human confirmation.
Return the durable approvedBy/approvedAt receipt; repeated approval returns the same receipt.
Reject missing authentication, forged store scope, stale snapshotVersion and conflicting ETag.
Use secure cookies and CSRF if implementing the approved browser session boundary.
Do not log credentials, session cookies or raw personal data.

## Failure and integration

Agent text is advisory and has no order-write authority.
A dependency timeout or partial evidence failure produces no completed close and no approved action.
Preserve the last working read and close checkpoints on failure.
The draft is internal only: no supplier message, payment, reservation or statutory report is sent.
Learners choose an authenticated application/SDK adapter; no portal-only transactional workflow is assumed.
