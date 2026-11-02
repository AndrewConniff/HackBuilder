@description('Existing AVM-created Storage account.')
param storageName string
@description('Container whose scoped assignments are managed; telemetry remains read-only for the web app.')
param containerName string = 'telemetry'
@description('Container-only role assignments with explicit principal type and fully qualified role definition ID.')
param assignments array

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' existing = { name: storageName }
resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' existing = {
  name: '${storage.name}/default/${containerName}'
}
resource access 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for item in assignments: {
  name: guid(container.id, item.principalId, item.roleId)
  scope: container
  properties: {
    principalId: item.principalId
    principalType: item.principalType
    roleDefinitionId: item.roleId
  }
}]
@description('Scoped telemetry container resource ID.')
output resourceId string = container.id
@description('Telemetry container name.')
output resourceName string = containerName
