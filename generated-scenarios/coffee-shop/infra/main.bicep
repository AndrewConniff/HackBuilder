targetScope = 'subscription'

@description('Scenario environment; review before deployment.')
param environmentName string
@description('Confirmed common region from authorized readiness.')
param location string
@description('Actual deploying user object ID, captured from configured identity.')
param principalId string
@description('Foundry Agent Consumer built-in role GUID, resolved during authorized readiness.')
param agentConsumerRoleId string
@description('Exact approved model name.')
param modelName string = 'gpt-4.1-mini'
@description('Exact approved model version.')
param modelVersion string = '2025-04-14'

var tags = {
  Environment: environmentName
  ManagedBy: 'azd'
  Project: 'coffee-shop'
  SecurityControl: 'Ignore'
}
resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}
module resources 'resources.bicep' = {
  name: 'coffee-shop-resources'
  scope: group
  params: {
    environmentName: environmentName
    location: location
    principalId: principalId
    agentConsumerRoleId: agentConsumerRoleId
    modelName: modelName
    modelVersion: modelVersion
    tags: tags
  }
}
output AZURE_RESOURCE_GROUP string = group.name
output AZURE_WEB_NAME string = resources.outputs.webName
output AZURE_WEB_URL string = resources.outputs.webUrl
output FOUNDRY_ENDPOINT string = resources.outputs.projectEndpoint
output STORAGE_ENDPOINT string = resources.outputs.storageEndpoint
output FOUNDRY_MODEL string = modelName
