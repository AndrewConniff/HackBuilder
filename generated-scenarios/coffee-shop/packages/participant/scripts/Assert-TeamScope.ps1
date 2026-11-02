[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if ($env:COFFEE_TEAM_DEPLOY_AUTHORIZED -ne 'yes') { throw 'Separate team rollout authorization required.' }
if ($env:AZURE_ENV_NAME -notmatch '^(0[1-9]|1[0-9]|20)-coffee-shop-hack$') { throw 'Invalid team environment.' }
if ($env:AZURE_RESOURCE_GROUP -ne "rg-$($env:AZURE_ENV_NAME)") { throw 'Wrong team group.' }
if (-not $env:AZURE_LOCATION -or -not $env:AZURE_SUBSCRIPTION_ID) { throw 'Explicit destination required.' }
