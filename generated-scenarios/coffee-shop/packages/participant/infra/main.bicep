targetScope = 'subscription'

@description('Isolated team environment such as 01-coffee-shop-hack.')
param environmentName string
@description('Explicit destination region; no reference default.')
param location string

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: {
    Environment: environmentName
    ManagedBy: 'azd'
    Project: 'coffee-shop'
    SecurityControl: 'Ignore'
  }
}
output AZURE_RESOURCE_GROUP string = group.name
