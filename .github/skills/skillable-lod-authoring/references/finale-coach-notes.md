# Finale coach notes

## Purpose

`99-finale.md` is the mandatory coach-facing Skillable instructions page. It is
the single canonical location for notes covering every challenge and the event
wrap-up.

Finale is not a sixth participant challenge. It does not change the 150-minute
build total and is excluded from challenge-page parity checks.

## Required mapping

Create one H2 section for each visible challenge number and exact title:

1. Challenge 0 — Secure Foundation
1. Challenge 1 — Build the MVP
1. Challenge 2 — Ground It
1. Challenge 3 — Give It Tools
1. Challenge 4 — Harden & Demo

Under each section, include these bold labels:

- **Objective and expected outcome**
- **Completion evidence**
- **Coach talking points**
- **Common blockers and recovery**
- **Hint escalation**
- **Fallback checkpoint**
- **Demo and debrief prompts**
- **Security and governance reminders**

Use concise bullets beneath each label. Keep recovery advice actionable, but do
not include credentials, deployed values, customer data, or environment-specific
identifiers.

## Coach guidance quality

Coach notes must help a coach answer three questions quickly:

1. What should be working now?
1. What evidence proves completion?
1. How can a blocked team continue without losing the last working checkpoint?

Do not restate the entire learner page. Focus on observation, facilitation,
recovery, and debrief value.

## Answer handling

Finale may contain coach-only expected outcomes and troubleshooting details. It
must remain in the private coach source. Never copy it to `packages/hack/`, link
to it from learner pages, or include its content in participant hints.

## Event wrap-up

After the five challenge sections, include:

- A three-minute demonstration sequence.
- Cross-challenge regression checks.
- Security and least-privilege review prompts.
- Participant reflection and debrief questions.
- Cleanup, artifact handoff, and follow-up actions.

The wrap-up may summarize judging criteria when the event uses judging, but it
must not expose confidential scoring notes in learner content.
