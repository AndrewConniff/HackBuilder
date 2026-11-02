targetScope = 'subscription'

@description('Exact isolated participant environment; never the coach environment.')
@minLength(3)
@maxLength(60)
param environmentName string

@description('Location selected during separately authorized event preparation.')
param location string

resource teamGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: {
    purpose: 'adatum-brokerage-learning'
    environment: environmentName
  }
}

output AZURE_RESOURCE_GROUP string = teamGroup.name
output STARTER_STATUS string = 'not-configured'
