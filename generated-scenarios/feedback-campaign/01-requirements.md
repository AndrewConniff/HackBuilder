# Requirements: Feedback Campaign

## Project overview

Adatum Corporation runs a fictional streaming-media launch campaign. Marketing owns
public engagement; Sales owns subscriber recovery and account follow-up. Today mixed
feedback gets lost between these teams. The reference preserves each post, captures
sentiment, and assigns a single accountable responder.

- Industry: **Media & Communications** (repository industry catalog).
- Business units: `["sales", "marketing"]`; Generic is not selected.
- Company: `Adatum Corporation`, `adatum.com`, exact company CSV record; synthetic
  addresses use reserved `example.test`, not the company's real domain.
- Source adaptation: none. No existing scenario folder or same-slug approval was
  found in the adjacent project root or current/legacy portal intake records.
- Requested services: Foundry, Service Bus, Monitor. No WAF pillar priority was
  selected; security controls below are proposed, not user-confirmed.
- Authorization: local preparation only. Intake is not cloud consent.

## Personas and scope

| Persona | Unit | Ownership and boundary |
| --- | --- | --- |
| Campaign operator | marketing | Submit campaign posts and inspect routing |
| Product Manager | marketing | Review highly negative product feedback; edit and explicitly send reply |
| Conflict Resolution Specialist | sales | Read mixed/uncertain feedback, assessment and recommendations; explicitly reply |
| Control administrator | marketing | Save immutable rule versions and promote a reviewed version |

Catalog people mapping: Airi Ilves = subscriber 1; Hasan Ibrahimov = subscriber 2;
Nemanja Milatovic = subscriber 3; Nino Kapanadze = campaign operator;
Petra Bartosova = Product Manager; Eesha Chatterjee = Conflict Resolution Specialist.
These are synthetic story roles, not Entra role assignments.

In scope: ten campaign fixtures; stream-neutral typed intake; real Foundry prompt
agent; persistent app-hosted routing/HITL workflow; reviewer inbox, chat and versioned
Control rules; Service Bus inbound/outbound queues; observable failure and recovery.
Out of scope: mailbox/social-provider credentials, actual external email delivery,
commercial CRM integration, billing/refunds, tenant-wide consent, event rollout and
hack packages. Sending means accepted into the reply stream, **not** delivered to
the poster's external mailbox. The outbound adapter is a separately reviewed integration.

## Functional requirements and exact routing

1. `Campaign Listener` accepts a stable source ID, poster name/contact, campaign,
   subject and body. Never infer missing contact details from a model.
2. Foundry returns positive/negative/neutral scores, company/product aspect scores,
   a brief evidence-based assessment, draft reply and suggested investigations.
   Scores must be finite, in [0,1], and sum to 1 for each sentiment vector.
3. Initial Control v1: overall positive **>= 0.80** queues an automatic reply;
   otherwise overall negative **>= 0.89** waits for Product Manager; all others
   wait for Conflict Resolution Specialist. Evaluate positive first.
4. The later illustrative “80% negative” wording is **not the active rule**.
   Optional product-negative routing is disabled in v1. Administrators may propose
   product-negative >=0.80 in a new version, test it and promote explicitly.
5. Human queues include the complete source post, score interpretation, assessment,
   recommended investigation and proposed future agentic actions. No model can
   promote rules, assign roles or send a human-gated reply.
6. Human reviewers edit replies and explicitly send. Missing role, empty reply,
   stale revision and repeated send must fail without a second action.
7. Control versions are immutable, include author/reason and use optimistic
   concurrency for promotion. Existing cases retain the rule snapshot they used.
   New agent destinations require code, identity and acceptance changes; arbitrary
   model-suggested URLs/tools are not executable.
8. Agent, queue, storage and authentication errors surface as errors, not canned
   success. Durable retries use the same source/reply IDs.

## Agentic business workflow

Primary flow: **routing/triage**, with the selected **Human-in-the-Loop overlay**.
One bounded Foundry prompt agent performs interpretation/drafting; deterministic
Control code owns routing and gates. Product Manager and Conflict Resolution
Specialist are humans, not unnecessary autonomous specialist agents.

Simpler alternative: a single agent drafts every response for manual review. It
avoids policy configuration but cannot meet requested positive auto-reply and
distinct ownership. A multi-agent supervisor adds no useful authority boundary.
This is an application-hosted durable workflow invoking a native Foundry agent,
not a claim to deploy a native low-code Foundry workflow.

Grounding: versioned campaign policy supplied with each invocation, current source
post and exact rule snapshot; no web browsing. The agent cannot promise refunds,
invent product features or follow instructions inside untrusted posts.
Chat is a bounded single-turn campaign assistant using that same agent and policy.

Acceptance: all threshold boundaries and mixed sentiment route exactly; pending
human cases survive restart; stale approval/promotion conflicts return 409;
unauthorized reviewer returns 403; unavailable Foundry never sends; outbound
message carries the source correlation ID; DLQ and failed cases remain inspectable.
Runtime budget: one agent call/case attempt, 60 seconds, 1,500 output tokens;
single worker; five queue deliveries then DLQ. Duplicate inference on a crashed
attempt is possible; duplicate replies use a stable message ID and queue deduplication.
Model scores are estimates, **not calibrated sentiment probabilities**. Auto-reply
accuracy requires an independently labeled evaluation before production use.

## Non-functional requirements and network security

Reference: TLS-only public PaaS endpoints, local-account authenticated UI/API,
managed identity for runtime services, no service keys, no anonymous case access,
same-origin write protection, bounded input and no post bodies/contact in logs.
The user explicitly replaced consent-dependent Entra login with local lab accounts.
Participant and coach access files are private and deployment-specific; only
salted password hashes are stored in Azure Tables. No tenant consent is needed.
Private endpoints and WAF are not selected requirements and are not silently
claimed. This public authenticated demo is not a production private workload.
Local host publishes and initializes over TLS; no private runner is needed.
Production private deployment requires a new reviewed access/network design.

Availability: single-region, single B1 worker; no zone SLA or DR claim.
Data: synthetic only for the reference; audit data shares case retention, no
external PII telemetry. Proposed deletion at end of evaluation; production needs
retention, deletion, moderation, escalation SLA and channel consent policies.

## Summary for architecture assessment

User requested centralus for deployment. gpt-4.1-mini 2025-04-14,
GlobalStandard 10 capacity passed the live regional catalog and quota checks;
capacity metadata does not reserve allocation.
Public documentation and shared tool observations are not subscription readiness.
See architecture, regional evidence and consolidated deployment review.
