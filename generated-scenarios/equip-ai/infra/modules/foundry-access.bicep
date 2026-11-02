@description('AVM-created Foundry account.')
param accountName string
@description('Direct child project.')
param projectName string
@description('Runtime web identity.')
param consumerId string
@description('Installing user object ID.')
param installerId string
@description('Verified built-in Agent Consumer role definition ID.')
param consumerRoleId string
@description('Verified least-privilege Responses runtime role; Consumer alone only allows endpoint interaction.')
param runtimeRoleId string
@description('Verified built-in agent creation role definition ID.')
param installerRoleId string
@description('System-assigned project identity that must invoke models on its parent Foundry account.')
param projectPrincipalId string
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: projectName
}
resource projectModelAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, projectPrincipalId, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  scope: account
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}
resource consumer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, consumerId, consumerRoleId)
  scope: project
  properties: {
    principalId: consumerId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', consumerRoleId)
  }
}
resource runtime 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, consumerId, runtimeRoleId)
  scope: project
  properties: {
    principalId: consumerId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', runtimeRoleId)
  }
}
resource installer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(installerId)) {
  name: guid(project.id, installerId, installerRoleId)
  scope: project
  properties: {
    principalId: installerId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', installerRoleId)
  }
}
@description('Foundry project resource ID.')
output resourceId string = project.id
@description('Foundry project name.')
output resourceName string = projectName
