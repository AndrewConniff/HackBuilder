@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Project managed identity object ID.')
param projectPrincipalId string
@description('Platform Storage name; never the business fixture account.')
param storageName string
@description('Platform Cosmos account name.')
param cosmosName string
@description('Platform Search name.')
param searchName string

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' existing = {
  name: storageName
}
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = {
  name: cosmosName
}
resource search 'Microsoft.Search/searchServices@2025-05-01' existing = {
  name: searchName
}

resource storageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, projectPrincipalId, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe', uniqueSuffix)
  scope: storage
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    )
  }
}
resource cosmosOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cosmos.id, projectPrincipalId, '230815da-be43-4aae-9cb4-875f7bd000aa', uniqueSuffix)
  scope: cosmos
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', '230815da-be43-4aae-9cb4-875f7bd000aa'
    )
  }
}
@description('Official private Standard Search service/data roles.')
var searchRoleIds = ['7ca78c08-252a-4471-8644-bb5ff32d4ba0', '8ebe5a00-799e-43f5-93ac-243d3dce84a7']
resource searchRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for roleId in searchRoleIds: {
  name: guid(search.id, projectPrincipalId, roleId, uniqueSuffix)
  scope: search
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId)
  }
}]

@description('Provisioning access bundle representative ID.')
output resourceId string = storageContributor.id
@description('Provisioning access bundle representative name.')
output resourceName string = storageContributor.name
