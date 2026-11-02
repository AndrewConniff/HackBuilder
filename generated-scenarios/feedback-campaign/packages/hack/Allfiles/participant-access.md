# Participant application access

Open `[destination-app-url]/Login` after a separately authorized deployment.
The organizer privately delivers freshly generated destination credentials;
never use a corporate password. No Entra sign-in or admin consent is needed.

| Username | Role | Boundary |
| --- | --- | --- |
| campaign-operator | CampaignOperator | Marketing intake, inspection and explicit retry |
| product-manager | ProductManager | Marketing assigned negative reviews and edited send |
| conflict-specialist | ConflictResolutionSpecialist | Sales recovery reviews and edited send |

Password: `[privately-delivered-destination-password]`. Passwords are absent
from this guide. The three accounts are not Azure credentials.
Participants receive only their designated participant access details,
never administrator access. Five failed attempts lock an account for 15 minutes.
Sessions expire after four hours; sign out when finished.
HTTPS-only cookies, CSRF/origin checks and server-side roles remain required.
Runtime Azure calls use managed identity with resource-scoped RBAC.
Sending means acceptance into a reply queue, not external delivery.
The minimum starter has no application login until you build that capability.
