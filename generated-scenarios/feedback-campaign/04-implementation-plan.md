# Implementation plan

1. Preserve original request and catalog provenance; implement routing/HITL without cloud access.
2. AVM-first infrastructure for account, storage, queue namespace, plan/site; direct
   ARM child project/auth configuration and monitoring when precise wiring is needed.
3. .NET 10 Razor app, Azure Tables checkpoints, Service Bus inbox/outbox and real
   managed-identity Foundry REST invocation. No silent local/mock runtime fallback.
4. Deterministic rules, reviewer entitlements, concurrency, bounded agent output,
   policy grounding and UI error paths. Unit and HTTP negative tests run locally.
5. Generate architecture/runtime diagrams. Build/lint infrastructure and build/test app.
6. Present consolidated target/operations/cost/security review. Readiness and
   what-if remain pending missing authority, not failed machine prerequisites.
7. Only after scoped authorization: refresh CLI identity via shared helper;
   validate region/quota/policy, run reviewed what-if; use azd hooks for dedicated
   directory installation, provision, publish and agent initialization.
8. Prove real model, agent, chat, grounding, human review, queue, restart and
   negative cases. Persist runtime receipts, then fingerprint for suitability
   review. Never record approval or produce hack packages before actual approval.
