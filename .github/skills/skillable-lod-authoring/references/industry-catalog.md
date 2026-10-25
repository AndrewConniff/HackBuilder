# Industry catalog

## Canonical industries

Use one industry per generated scenario package.

| Industry | Slug | Positioning |
| --- | --- | --- |
| Financial Services | `financial-services` | Large accounts and mature AI governance |
| Healthcare | `healthcare` | High-visibility agentic outcomes |
| Manufacturing | `manufacturing` | Deep Azure and IoT integration |
| Retail | `retail` | High-volume data and fast ROI cycles |
| Energy / Oil & Gas | `energy-oil-gas` | High-value knowledge mining |
| Government / Public Sector | `government-public-sector` | Mission and constituent services |
| Hospitality & Travel | `hospitality-travel` | Service readiness and reviewed business handoffs |
| Media & Communications | `media-communications` | Campaign engagement and subscriber recovery |

The machine-readable source is `../assets/industry-catalog.json`.

## Authoring guidance

Industry positioning guides scenario selection; it does not authorize invented
claims, customer names, regulations, or datasets.

### Financial Services

Emphasize governed knowledge, analyst workflows, servicing, compliance review,
or risk operations. Use synthetic account and transaction data. Never imply
regulatory approval or provide financial advice.

### Healthcare

Emphasize administrative workflows, care-team knowledge access, operations, or
research support. Use synthetic records only. Avoid diagnosis, treatment, or
patient-specific recommendations unless the scenario explicitly includes an
approved safety framework.

### Manufacturing

Emphasize maintenance knowledge, quality, supply operations, plant procedures,
or IoT-supported decisions. Separate simulated telemetry from real control
systems and require human confirmation before consequential actions.

### Retail

Emphasize catalog, inventory, merchandising, service, or store operations. Use
synthetic customer and sales data. Avoid exposing personal data or allowing an
agent to execute high-impact commercial changes without approval.

### Energy / Oil & Gas

Emphasize field knowledge, maintenance records, safety procedures, document
mining, or operational handoffs. Treat control-system actions as read-only or
human-approved simulations unless an approved architecture says otherwise.

### Government / Public Sector

Emphasize constituent service, caseworker knowledge, grants, permitting,
records, or internal operations. Include accessibility, records handling,
transparency, and human review appropriate to the scenario.

### Hospitality & Travel

Preserve the approved hospitality workflow and exact selected business units.
Use synthetic store, service, stock and managerial-close evidence as applicable.
Separate advisory narratives from authoritative calculations and human-approved
actions. A sales-led coffee-shop scenario is not a Retail mapping or permission
to add Operations or Finance; a reviewed finance handoff does not add a selected unit.
Do not imply supplier transmission, payments, ledger posting, or guest-data access
unless the approved scenario implements them. Use the shared challenge and Finale
templates unchanged with `Hospitality & Travel` and `hospitality-travel`.

### Media & Communications

Preserve the approved media workflow, selected business units and explicit human
handoffs. Use synthetic campaign posts, subscriber contacts and versioned policy.
Keep model interpretation distinct from deterministic routing and human authority.
Queue acceptance is not external email or social delivery. Do not imply provider
integration, calibrated sentiment probabilities, native workflow coordination or
native agent tools unless the approved reference actually proves them.
Use the shared templates unchanged with `Media & Communications` and
`media-communications`; never alias this industry to Retail or another slug.

## Stable naming rule

Do not create abbreviated or alternate slugs such as `finance`, `oilgas`, or
`public-sector`. Stable paths are necessary for Skillable page references and
release automation.
