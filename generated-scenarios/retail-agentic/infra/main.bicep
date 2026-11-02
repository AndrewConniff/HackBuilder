targetScope = 'subscription'

@description('Explicit azd environment name; also determines the scenario resource group.')
@minLength(3)
@maxLength(20)
param environmentName string

@description('Explicit reviewed Azure region; no region is silently selected.')
param location string

@description('Actual deploying human user object ID, resolved from the confirmed CLI context.')
@minLength(36)
@maxLength(36)
param principalId string

@description('Private Windows management VM local administrator name, distinct from Azure sign-in.')
param managementUsername string = 'scenarioadmin'

@description('Reviewed private operator VM size; an alternative must pass subscription eligibility before use.')
param managementVmSize string = 'Standard_B2ms'

@description('Reuse verified effective inherited human control-plane administration instead of assigning Contributor.')
param reuseAdminControlAccess bool = false

@description('Reuse verified effective inherited human Foundry administration/data access instead of assigning Owner.')
param reuseAdminFoundryAccess bool = false

@secure()
@description('Unique private management VM password, supplied securely during authorized installation.')
@minLength(16)
param managementPassword string

@description('Configurable model name; lifecycle, regional support and quota require live validation.')
param modelName string = 'gpt-4.1-mini'

@description('Explicit model version from current evidence.')
param modelVersion string = '2025-04-14'

@description('Reviewed inference deployment type; GlobalStandard is not region-only inference.')
param modelDeploymentType string = 'GlobalStandard'

@description('Model quota capacity units; exact capacity must be reviewed before deployment.')
@minValue(1)
param modelCapacity int = 10

@description('Tags required on every taggable scenario resource.')
var tags = {
  Environment: environmentName
  ManagedBy: 'Bicep'
  Project: 'retail-agentic'
  SecurityControl: 'Ignore'
}

@description('Dedicated resource group, named after the azd environment.')
resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  name: 'retail-reference'
  scope: group
  params: {
    location: location
    principalId: principalId
    managementUsername: managementUsername
    managementVmSize: managementVmSize
    reuseAdminControlAccess: reuseAdminControlAccess
    reuseAdminFoundryAccess: reuseAdminFoundryAccess
    managementPassword: managementPassword
    tags: tags
    modelName: modelName
    modelVersion: modelVersion
    modelDeploymentType: modelDeploymentType
    modelCapacity: modelCapacity
  }
}

@description('Resource group containing this reference only.')
output AZURE_RESOURCE_GROUP string = group.name
@description('Provisioned public authenticated web application URL.')
output APPLICATION_URL string = resources.outputs.applicationUrl
@description('Provisioned app name used by azd.')
output AZURE_WEB_NAME string = resources.outputs.webName
@description('Provisioned Foundry direct-project endpoint.')
output FOUNDRY_PROJECT_ENDPOINT string = resources.outputs.projectEndpoint
@description('Provisioned model deployment name.')
output FOUNDRY_MODEL_DEPLOYMENT string = 'retail-reasoning'
@description('Private Table endpoint for the connected installation host.')
output STORAGE_TABLE_ENDPOINT string = resources.outputs.tableEndpoint
@description('Private Blob endpoint for the connected installation host.')
output STORAGE_BLOB_ENDPOINT string = resources.outputs.blobEndpoint
@description('Private management VM name.')
output MANAGEMENT_VM_NAME string = resources.outputs.vmName
@description('Private management VM resource ID.')
output MANAGEMENT_VM_ID string = resources.outputs.vmId
@description('Bastion name used for verified RDP and native tunnel entry.')
output BASTION_NAME string = resources.outputs.bastionName
