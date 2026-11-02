@description('Deploying human administrator ID, distinct from workload identities.')
param adminId string
@description('Reuse verified inherited control-plane access; defaults preserve explicit grants for other targets.')
param reuseAdminControlAccess bool = false
@description('Reuse verified inherited Foundry access; does not suppress either Storage or workload grants.')
param reuseAdminFoundryAccess bool = false
@description('Application managed-identity principal.')
param appId string
@description('Private-host unattended managed-identity principal.')
param automationId string
@description('Existing scenario Storage account name.')
param storageName string
@description('Existing scenario Foundry resource name.')
param foundryName string

@description('Scenario Storage scope.')
resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' existing = {
  name: storageName
}
@description('Scenario Foundry scope.')
resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}
@description('Direct project scope for workload invocation.')
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundry
  name: 'retail'
}
@description('Scoped storage operations, with distinct human and workload principals.')
var storageGrants = [
  { principal: adminId, type: 'User', role: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3' }
  { principal: adminId, type: 'User', role: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' }
  { principal: appId, type: 'ServicePrincipal', role: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3' }
  { principal: appId, type: 'ServicePrincipal', role: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' }
  { principal: automationId, type: 'ServicePrincipal', role: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3' }
  { principal: automationId, type: 'ServicePrincipal', role: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe' }
]

@description('No standalone AVM role-assignment module is published; explicit extension resources use stable IDs.')
resource storageRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for grant in storageGrants: {
  name: guid(storage.id, grant.principal, grant.role)
  scope: storage
  properties: {
    principalId: grant.principal
    principalType: grant.type
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', grant.role)
  }
}]

@description('Foundry Owner grants the deployment user project/data administration within this resource only.')
resource adminFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!reuseAdminFoundryAccess) {
  name: guid(foundry.id, adminId, 'c883944f-8b7b-4483-af10-35834be79c4a')
  scope: foundry
  properties: {
    principalId: adminId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'c883944f-8b7b-4483-af10-35834be79c4a')
  }
}

@description('Stable Foundry User role ID, formerly Azure AI User; project-scoped workload invocation.')
resource workloadFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for id in [appId, automationId]: {
  name: guid(project.id, id, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: project
  properties: {
    principalId: id
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}]

@description('Scenario-only control-plane administration; does not imply data access or grant authority.')
resource adminControl 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!reuseAdminControlAccess) {
  name: guid(resourceGroup().id, adminId, 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  properties: {
    principalId: adminId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  }
}

@description('Resource ID of the Storage grant scope.')
output resourceId string = storage.id
@description('Name of the Storage grant scope.')
output resourceName string = storage.name
