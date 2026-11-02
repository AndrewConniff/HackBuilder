@description('Existing private Foundry resource name.')
param accountName string
@description('Region shared with the Foundry delegated subnet.')
param location string
@description('Governance tags.')
param tags object
@description('Existing agent storage account.')
param storageName string
@description('Existing thread storage Cosmos account.')
param cosmosName string
@description('Existing vector search service.')
param searchName string
@description('Application managed identity object ID.')
param applicationPrincipalId string
@description('Operator user object ID for explicit agent installation.')
param deployerPrincipalId string
@description('Live-resolved built-in Foundry Agent Consumer role GUID.')
param agentConsumerRoleId string

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = { name: accountName }
resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' existing = { name: storageName }
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = { name: cosmosName }
resource search 'Microsoft.Search/searchServices@2025-05-01' existing = { name: searchName }
resource knowledge 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' existing = {
  name: '${storageName}/default/knowledge'
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: 'brokerage'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Adatum Corporation brokerage education'
    description: 'Private, keyless brokerage education reference; synthetic content only.'
  }
}
@description('Documented Standard setup AAD connections.')
var connections = [
  {
    name: 'agent-storage'
    category: 'AzureStorageAccount'
    target: 'https://${storageName}.blob.${environment().suffixes.storage}/'
    id: storage.id
  }
  {
    name: 'agent-threads'
    category: 'CosmosDB'
    target: 'https://${cosmosName}.documents.azure.com:443/'
    id: cosmos.id
  }
  {
    name: 'agent-vectors'
    category: 'CognitiveSearch'
    target: 'https://${searchName}.search.windows.net'
    id: search.id
  }
]
resource connection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = [
  for spec in connections: {
    parent: project
    name: spec.name
    properties: {
      category: spec.category
      target: spec.target
      authType: 'AAD'
      metadata: { ApiType: 'Azure', ResourceId: spec.id, location: location }
    }
  }
]
resource projectStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, project.id, 'blob-contributor')
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}
resource projectCosmosOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: cosmos
  name: guid(cosmos.id, project.id, 'cosmos-operator')
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '230815da-be43-4aae-9cb4-875f7bd000aa')
  }
}
resource projectSearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for roleId in ['8ebe5a00-799e-43f5-93ac-243d3dce84a7', '7ca78c08-252a-4471-8644-bb5ff32d4ba0']: {
    scope: search
    name: guid(search.id, project.id, roleId)
    properties: {
      principalId: project.identity.principalId
      principalType: 'ServicePrincipal'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
    }
  }
]
resource projectInference 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, project.id, 'inference')
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}
resource operatorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, deployerPrincipalId, 'installer')
  properties: {
    principalId: deployerPrincipalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}
resource consumerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, applicationPrincipalId, 'consumer')
  properties: {
    principalId: applicationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', agentConsumerRoleId)
  }
}
resource faqReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: knowledge
  name: guid(knowledge.id, applicationPrincipalId, 'reader')
  properties: {
    principalId: applicationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
  }
}
resource host 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  parent: project
  name: 'agents'
  properties: {
    #disable-next-line BCP037
    capabilityHostKind: 'Agents'
    storageConnections: ['agent-storage']
    threadStorageConnections: ['agent-threads']
    vectorStoreConnections: ['agent-vectors']
  }
  dependsOn: [connection, projectStorage, projectSearch, projectCosmosOperator, projectInference]
}
module postHost 'post-host.bicep' = {
  name: 'post-host-data-access'
  params: {
    cosmosName: cosmosName
    storageName: storageName
    projectPrincipalId: project.identity.principalId
    #disable-next-line BCP053
    projectInternalId: project.properties.internalId
    deployerPrincipalId: deployerPrincipalId
  }
  dependsOn: [host]
}
@description('Direct child project resource ID.')
output resourceId string = project.id
@description('Direct child project name.')
output resourceName string = project.name
@description('Runtime project managed identity.')
output principalId string = project.identity.principalId
