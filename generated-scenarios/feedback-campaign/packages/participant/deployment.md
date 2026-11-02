# Participant destination preparation

This is a local package, not permission to deploy. A separate event request must
authorize each target. No location is preselected and no CLI default is inherited.
The organizer provides group-scoped deployment access. Use a different group and
azd environment from the coach. For Team 01, after authorization:

```powershell
azd env new 01-feedback-campaign-hack
azd env set AZURE_RESOURCE_GROUP rg-01-feedback-campaign-hack
azd env set AZURE_SUBSCRIPTION_ID "[chosen-destination-subscription]"
azd env set AZURE_TENANT_ID "[chosen-destination-tenant]"
azd env set AZURE_LOCATION "[explicitly-chosen-destination-region]"
```

Resolve these placeholders and verify the matching signed-in identity. The
destination guard fails on missing choices, mismatched CLI identity or another group.
It never changes shared defaults. IDs 01–20 use the same zero-padded naming rule.
Do not share the coach's `.azure` directory or grant participants coach group access.

The starter provisions only group tags, not services or an app.
`azd up` is mandatory for future destination deployment acceptance, but is not
executed during this local phase. After isolated provision the starter still reports
not-configured. Run `python scripts/status.py` locally without Azure access.

Choose the smallest Foundry foundation for Challenge 0; check current destination
model/SKU/region/quota and obtain scoped resource permissions before provisioning it.
Use the same approved model contract when available: gpt-4.1-mini 2025-04-14.
Do not substitute a different model silently after a capacity failure.
Use managed identity for Azure-hosted runtime calls; use scoped developer credentials
for local SDK work. Assign only the data roles at the resources you actually build.
No Entra application registration or sample-login admin consent is required.

Human action roles are application authorization, not Azure deployment permissions.
If you build a login UI, use destination-only local accounts with salted hashes,
secure cookies, durable session keys, CSRF/origin checks, lockout/rate limits and
separate coach administration. No UI rebuild is required for the bounded action task.
Actual credentials are generated during destination installation and delivered
privately, never committed to this starter or public challenge files.
