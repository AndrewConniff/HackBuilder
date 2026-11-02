# Fourth Coffee private coach solution

Hospitality & Travel; businessUnits `["sales"]`. This is a sanitized copy of the approved reference.
The app, fixtures, agent instructions and baseline tests retain the approved behavior.
No reference deployment state, target identity, region, installed agent receipt or concrete endpoint is included.

## Local checks

```powershell
dotnet build src/CoffeeShop.Web
dotnet test tests/CoffeeShop.Tests
pwsh -NoProfile -File scripts/Build-Assets.ps1
az bicep build --file infra/main.bicep
az bicep lint --file infra/main.bicep
```

## Future installation

Deployment is not part of composition. Use the separate private deployment guide.
Choose an explicit destination region and complete fresh regional/model/SKU/quota, exact role and what-if review.
Use environment coffee-shop-coach and resource group rg-coffee-shop-coach; never a team or reference group.
Process-only passwords initialize storeman001/001, storeman002/002 and petender/001+002.
These technical usernames are not real directory assignments or fixture-person names.
The Table initializer preserves existing snapshots and verifies existing accounts rather than resetting them.
Do not commit generated agent-installation.json, azd environment files, passwords or local credential receipts.

No live coach environment has been deployed or independently tested by composition.
