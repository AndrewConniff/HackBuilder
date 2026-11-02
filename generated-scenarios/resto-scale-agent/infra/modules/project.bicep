@description('AVM-created Foundry account name.')
param accountName string

@description('Confirmed deployment region.')
param location string

@description('Required scenario tags.')
param tags object

@description('Chat managed identity principal ID; consumption only.')
param chatPrincipalId string

@description('Deployer identity used to install versioned prompt agents.')
param principalId string

@description('Verified Foundry Agent Consumer built-in role ID.')
param consumerRoleId string

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-09-01' = {
  parent: account
  name: 'restaurant'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Fourth Coffee restaurant'
    description: 'Generic Hospitality & Travel reference. Synthetic data and settlement only.'
  }
}

resource chatConsumer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, chatPrincipalId, consumerRoleId)
  scope: project
  properties: {
    principalId: chatPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', consumerRoleId)
  }
}

resource initializer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(project.id, principalId, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: project
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d'
    )
  }
}

@description('Direct child project ID.')
output resourceId string = project.id

@description('Direct child project name.')
output resourceName string = project.name
