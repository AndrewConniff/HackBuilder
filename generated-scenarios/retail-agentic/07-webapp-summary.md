# Step 4b: Web Application Summary - retail-agentic

> Local application and UI validation | 2026-10-28 | Not deployed

## Application Overview

| Property | Value |
| --- | --- |
| App | `Woodgrove.Web` |
| Framework | .NET 10 ASP.NET Core Razor Pages |
| Source | [Application source](./src/Woodgrove.Web/) |
| Storage | Native Azure Table; private Blob session keys; no in-memory runtime fallback |
| Authentication | Local accounts, salted hashes, durable lockout, secure bounded cookies and CSRF |
| Agent path | Three real version-pinned Foundry agents; managed identity; deterministic typed tools |

### Visual direction

The grocery journey uses a restrained green/neutral theme rather than generic Azure-blue branding.
Semantic CSS tokens control surfaces, text, state, borders and focus.
The desktop workspace separates cart/order selection from the timeline and assistant.
Narrow layouts stack those regions without horizontal scrolling.
Visible current-page navigation, skip navigation and text status supplement color.

Navigation and chat use official Microsoft Fluent System Icons, with their MIT license retained:
[cart source][cart-icon], [chat source][chat-icon] and [upstream license][icon-license].
Icons are decorative beside visible labels, not unnamed controls.

## Business Industry Context

| Property | Value |
| --- | --- |
| Industry | `Retail & Consumer Goods` |
| Business units | `["generic"]`: typical grocery workflow, no department targeting |
| Company | Woodgrove Groceries; catalog provenance in [requirements](./01-requirements.md) |
| Customers | Separate server-owned `customer-001` and `customer-002` accounts and order boundaries |
| Operator | Separate `operator-001`; overview and synthetic exception controls, not customer impersonation |
| Runtime handoffs | Order Assistance -> Fulfillment -> Delivery Coordination |

The browser covers groceries, declared allergen exclusions, substitutions and delivery windows.
Every commerce/payment/carrier action is synthetic; model and agent calls must be real when deployed.
There is no native mobile app or production dietary/medical certification.

## Data Model

| Record | Purpose |
| --- | --- |
| Product | Integer ID, price in cents, stock and explicit allergen metadata |
| GroceryOrder | Customer-bound commitment, checkpoint, counters, synthetic payment totals and events |
| CartLine/Proposal | Product quantities and exact expiring customer-reviewed commitment |
| TimelineEvent | Inspectable action and real response ID, never hidden chain-of-thought |

Twelve products cover ordinary purchases, substitutions, allergens, out-of-stock pasta and unknown metadata.
JSON is installation input, never a runtime persistence fallback.
Orders start empty and are created by customers; no seeded order pretends that an agent ran.
The three account display names use the exact recorded company/person catalog mapping.

## Pages and Endpoints

| Route/action | Boundary and behavior |
| --- | --- |
| `/Login` | Anonymous sign-in page; CSRF-protected POST and durable five-failure lockout |
| `/Logout` | Authenticated CSRF-protected POST; GET returns 405 |
| `/` | Authenticated customer-scoped orders/catalog or operator overview |
| `/?id={order}` | Only visible authorized orders; explicit rejection without another customer's content |
| Create/Confirm | Customer only; exact draft version and server-owned prices |
| Decide/Cancel/Retry | Customer only; exact proposal, safe cancellation or bounded failed-stage retry |
| Chat | Customer only; read-only real-agent question, separate daily budget |
| Disrupt | Operator only; inject/clear synthetic delay or adapter failure |
| `/Denied`, `/Error` | Explicit access/error handling; no anonymous bypass |

The workflow never treats chat prose as permission to alter an order.
Proposal rejection/expiry holds the workflow; changed items, charges or slots remain uncommitted.
The operator can inject a pre-dispatch delivery delay or tool failure, but cannot approve for the customer.

## Deployment Target

| Property | Value |
| --- | --- |
| Compute | Public authenticated Linux B1 App Service; private outbound data path |
| Container | Not needed; portable framework-dependent .NET publish |
| azd service/host | `web` / `appservice` |
| Private initialization | Checksummed runtime transfer through Bastion; VM managed identity |
| Human administration | Private VM browser/CLI using the deploying user's own Azure credentials |
| Actual URL | Unavailable: nothing deployed |

See [deployment wiring](./azure.yaml) and [implementation gates](./05-implementation-reference.md).

## Build Validation

| Check | Actual local result |
| --- | --- |
| Build | Zero warnings/errors, with warnings treated as errors |
| Tests | 28 passed; policy, exact limits, concurrency, payments, expiry, auth, role and isolation cases |
| Locked restore/publish | Passed; runtime DLL, seed JSON and static assets included |
| Configuration failures | Missing/insecure endpoints fail explicitly before startup |
| Empty/error states | Empty order list distinguished from a missing backend catalog |
| Desktop customer/login | Rendered fixture checked at 1440px |
| Narrow customer layout | 390px and 320px; no horizontal overflow |
| Narrow login | 390px; no horizontal overflow; password input remains masked |
| Navigation/keyboard | Visible current page; first Tab focuses Skip to content |
| Fluent assets | Both SVGs load; no external CDN dependency |
| Measured text contrast | Body 13.74:1; muted 6.75:1; primary button 7.74:1; error 10.49:1 |
| Cloud/model acceptance | Not performed or authorized |

The browser checks used static HTML rendered from actual Razor pages with isolated test-only services.
An explicit fixture banner prevented confusion with a deployed scenario.
Static previews did not execute form handlers, model calls or installation.
HTTP tests separately exercised real Razor handlers, cookies, CSRF, local auth and role boundaries.
No test doubles or preview routes are registered in the production application.

Loading delays, full Azure journeys, real telemetry exports and runtime MI/network behavior still need live validation.
These local results are not a WCAG certification, production-readiness claim or scenario suitability approval.

[cart-icon]:
  https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Cart/SVG/ic_fluent_cart_24_regular.svg
[chat-icon]:
  https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Chat/SVG/ic_fluent_chat_24_regular.svg
[icon-license]: https://github.com/microsoft/fluentui-system-icons/blob/main/LICENSE
