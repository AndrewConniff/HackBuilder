targetScope = 'resourceGroup'
@description('Explicit isolated participant azd environment.')
param environmentName string
@description('Explicit destination region; no reference-region default.')
param location string
resource isolationTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: {
    tags: {
      Environment: environmentName
      Location: location
      Project: 'feedback-campaign'
      ManagedBy: 'azd'
      BusinessUnits: 'sales,marketing'
    }
  }
}
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output STARTER_STATUS string = 'not-configured: learner agent and action are intentionally absent'
