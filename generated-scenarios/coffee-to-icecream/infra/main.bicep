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
param modelName string
@description('Exact approved model version.')
param modelVersion string
@description('Reviewed model deployment capacity; verify exact TPM mapping and subscription quota.')
@minValue(1)
param modelCapacity int = 300

@description('Scenario tags; do not inherit source environment metadata.')
var tags = {
  Environment: environmentName
  ManagedBy: 'Bicep'
  Project: 'coffee-to-icecream'
  SecurityControl: 'Ignore'
}
resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}
module resources 'resources.bicep' = {
  name: 'icecream-resources'
  scope: group
  params: {
    environmentName: environmentName
    location: location
    principalId: principalId
    agentConsumerRoleId: agentConsumerRoleId
    modelName: modelName
    modelVersion: modelVersion
    modelCapacity: modelCapacity
    tags: tags
  }
}
@description('Scenario resource group name.')
output AZURE_RESOURCE_GROUP string = group.name
@description('Destination web application name.')
output AZURE_WEB_NAME string = resources.outputs.webName
@description('Destination web application HTTPS URL.')
output AZURE_WEB_URL string = resources.outputs.webUrl
@description('Direct-child Foundry project endpoint.')
output FOUNDRY_ENDPOINT string = resources.outputs.projectEndpoint
@description('Managed-identity business Table endpoint.')
output STORAGE_ENDPOINT string = resources.outputs.storageEndpoint
@description('Reviewed model deployment name.')
output FOUNDRY_MODEL string = modelName
