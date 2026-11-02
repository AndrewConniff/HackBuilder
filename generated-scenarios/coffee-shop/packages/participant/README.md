# Fourth Coffee minimum starter

Build a sales-readiness agent for Hospitality & Travel; businessUnits `["sales"]`.
Store managers work within one assigned store; the north-area manager sees 001/002, never 003.
Finance receives a reviewed managerial close only. No supplier order, payment or ledger posting is included.

## Starter architecture

Team operator -> isolated empty resource group on separately authorized rollout.
Local files in data/ provide exact synthetic stores, behavior constraints and evaluation probes.
No app, Azure data service, Foundry resource, completed agent logic or hosted URL is provided.

## Intended status

```powershell
python scripts/status.py
```

Expect not-configured, chatAvailable false and applicationUrl null; this is not a failing app or simulated success.
Choose and implement the remaining components through the public challenges.
The JSON snapshots are local payloads, not a storage service or preloaded agent.
Do not upload all stores into an unscoped shared conversation.

## Future team rollout

Rollout needs a separate request and exact target review.
Use 01-coffee-shop-hack / rg-01-coffee-shop-hack for the default team; never coffee-shop-coach.
Supply an explicit destination region; no reference subscription, tenant, region or approval is inherited.
The group has no deployed app or ingestion hook. Learners own subsequent component selection and safe fixture loading.
