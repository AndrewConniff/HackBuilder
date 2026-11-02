@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Foundry account name.')
param accountName string
@description('Direct child project name.')
param projectName string
@description('Project managed identity object ID.')
param projectPrincipalId string
@description('Service-assigned project workspace identifier.')
param workspaceId string
@description('Standard Storage connection and resource name.')
param storageName string
@description('Standard Cosmos connection and resource name.')
param cosmosName string
@description('Standard Search connection name.')
param searchName string

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: account
  name: projectName
}
resource host 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  parent: project
  name: 'standard-agents'
  properties: {
    // Required by the documented service API, omitted from its published Bicep type.
    #disable-next-line BCP037
    capabilityHostKind: 'Agents'
    storageConnections: [storageName]
    threadStorageConnections: [cosmosName]
    vectorStoreConnections: [searchName]
  }
}

@description('Normalize the private sample workspace ID without assuming an unhyphenated service response.')
var compactId = replace(workspaceId, '-', '')
@description('Workspace prefix used by Standard platform Blob containers.')
var workspaceGuid = '${substring(compactId, 0, 8)}-${substring(compactId, 8, 4)}-${substring(compactId, 12, 4)}-${substring(compactId, 16, 4)}-${substring(compactId, 20, 12)}'
@description('Restrict Blob tag ownership to this project runtime container prefix and suffix.')
var blobCondition = '((!(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read\'}) AND !(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/filter/action\'}) AND !(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write\'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringStartsWithIgnoreCase \'${workspaceGuid}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringLikeIgnoreCase \'*-azureml-agent\'))'

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' existing = {
  name: storageName
}
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = {
  name: cosmosName
}
resource blobOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, projectPrincipalId, 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b', uniqueSuffix)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
    )
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    conditionVersion: '2.0'
    condition: blobCondition
  }
  dependsOn: [host]
}
resource cosmosData 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = {
  parent: cosmos
  name: guid(cosmos.id, projectPrincipalId, 'enterprise_memory', uniqueSuffix)
  properties: {
    principalId: projectPrincipalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: '${cosmos.id}/dbs/enterprise_memory'
  }
  dependsOn: [host]
}

@description('Project capability host ID.')
output resourceId string = host.id
@description('Project capability host name.')
output resourceName string = host.name
