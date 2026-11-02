targetScope = 'subscription'

@description('Scenario azd environment name.')
param environment string

@description('Reviewed common Azure region; no implicit region default.')
param location string

@description('Signed-in human deployer object ID; resolved automatically before provisioning.')
param principalId string

@description('Current built-in Foundry Agent Consumer role ID, resolved during authorized preparation.')
param consumerRoleId string

@description('Assign human administrator roles only when equivalent inherited access has not been verified.')
@allowed(['assign', 'inherited'])
param deployerRoleMode string = 'assign'

@description('Reviewed model name.')
param modelName string

@description('Reviewed exact model version.')
param modelVersion string

@description('Reviewed model deployment type.')
param modelSku string

@description('Reviewed model deployment capacity.')
param modelCapacity int = 10

@secure()
@description('Unique scenario management VM password, generated into private deployment state.')
param managementPassword string

@description('Common scenario resource tags.')
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'live-demo-project'
  SecurityControl: 'Ignore'
}

@description('Scenario-owned resource group.')
resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environment}'
  location: location
  tags: tags
}

module reference 'reference.bicep' = {
  name: 'brokerage-reference'
  scope: group
  params: {
    environment: environment
    location: location
    principalId: principalId
    consumerRoleId: consumerRoleId
    assignDeployerRoles: deployerRoleMode == 'assign'
    modelName: modelName
    modelVersion: modelVersion
    modelSku: modelSku
    modelCapacity: modelCapacity
    managementPassword: managementPassword
    tags: tags
  }
}

@description('Reference resource group.')
output AZURE_RESOURCE_GROUP string = group.name

@description('Published website URL after azd deployment.')
output APPLICATION_URL string = reference.outputs.applicationUrl

@description('Private Foundry project endpoint.')
output FOUNDRY_PROJECT_ENDPOINT string = reference.outputs.projectEndpoint

@description('Scenario management VM name.')
output MANAGEMENT_VM_NAME string = reference.outputs.managementVmName

@description('Model deployment name used by the agent installer.')
output FOUNDRY_MODEL_DEPLOYMENT string = 'company-selector'

@description('Stable scenario-owned prompt agent name.')
output FOUNDRY_AGENT_NAME string = 'brokerage-company-selector'

@description('App Service resource name.')
output WEBAPP_NAME string = reference.outputs.webName
