targetScope = 'subscription'

@description('Exact scenario environment for whole-scope what-if.')
param environmentName string
@description('Reviewed region, not an automatically changed CLI default.')
param location string
@description('Setup-captured installer object ID.')
param installerObjectId string

resource group 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: {
    Environment: environmentName
    ManagedBy: 'azd'
    Project: 'feedback-campaign'
    SecurityControl: 'Ignore'
  }
}
module reference 'main.bicep' = {
  name: 'feedback-campaign-reference'
  scope: group
  params: {
    environmentName: environmentName
    location: location
    installerObjectId: installerObjectId
  }
}
