# Fourth Coffee sales readiness and daily close

Build a Microsoft Foundry agent that supports scoped store readiness and a reviewed daily close.
**180 minutes: 10-minute kickoff + 150-minute build + 20-minute wrap/demo.**

## Scenario

Fourth Coffee sales managers need stores ready to sell tomorrow and a defensible daily margin review.
Help store managers inspect only their own store and the north-area manager compare 001/002, never 003.
Prepare an internal replenishment proposal for human approval and a reviewed managerial close for finance;
do not transmit supplier orders, spend money or post a ledger.

**Business scope:** Hospitality & Travel; businessUnits `["sales"]`. Store managers: Airi Ilves (001),
Hasan Ibrahimov (002), Nino Kapanadze (003); north-area manager: Nemanja Milatovic.
Finance is a reviewed-report recipient only, not a selected unit or implemented login.

## Schedule

| Page | Minutes | Build running total |
| --- | --- | --- |
| [Secure Foundation](Instructions/hospitality-travel/00-secure-foundation.md) | 25 | 25 |
| [Build the MVP](Instructions/hospitality-travel/01-build-the-agent.md) | 30 | 55 |
| [Ground It](Instructions/hospitality-travel/02-ground-it.md) | 35 | 90 |
| [Give It Tools](Instructions/hospitality-travel/03-give-it-tools.md) | 35 | 125 |
| [Harden & Demo](Instructions/hospitality-travel/04-harden-and-demo.md) | 25 | 150 |
| **Build total** | **150** | **150** |

## Prerequisites

| Requirement | Validation |
| --- | --- |
| Isolated target and identity | Facilitator confirms team access, no pasted keys. |
| Minimum starter | Local synthetic files; no prebuilt agent, app or cloud data service. |
| SDK work when needed | Deterministic access, arithmetic, durable actions and coordination need application code. |

Use the first 10 minutes to inspect the starter, choose roles and review safe action boundaries.
Reserve the last 20 minutes for a three-minute demo per selected team, regression review and debrief.
Choose components from outcomes; no completed solution architecture is supplied.
Low-code agent tests are valid, but do not claim that the portal implements application-level guarantees.

## Security

Use synthetic data and managed identity or DefaultAzureCredential for backend access.
Never paste passwords, session cookies, keys, subscription/tenant identifiers or concrete endpoints into evidence.
Do not infer identity grants from synthetic person names. Use only server-controlled assignments.

## Resources

Use [resources.md](resources.md) and the [local payloads](Allfiles/README.md).
