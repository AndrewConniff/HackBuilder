targetScope = 'subscription'

@minLength(1)
@description('Explicitly confirmed reference azd environment. No default target.')
param environmentName string

@minLength(1)
@description('Explicitly confirmed reference resource group. May be rg-{environmentName} if authorized.')
param resourceGroupName string

@minLength(1)
@description('Region selected only after live target-specific resource/model checks.')
param location string

@minLength(1)
@description('Exact authorized model name. No inferred model preference.')
param modelName string

@minLength(1)
@description('Exact validated model version.')
param modelVersion string

@minLength(1)
@description('Exact validated deployment SKU, for example a target-supported Standard or GlobalStandard.')
param modelDeploymentSku string

@minValue(1)
@description('Validated capacity in deployment-SKU units, not an assumed tokens-per-minute value.')
param modelCapacity int

@description('Provider format supported by the chosen model and API.')
param modelFormat string = 'OpenAI'

@description('Technical deployment identifier; not a model selection.')
param modelDeploymentName string = 'hotel-analysis'

@description('Existing API app registration audience, matching issued Entra access tokens.')
@minLength(1)
param apiAudience string

@description('Allowed operator Entra object IDs, not email addresses.')
@minLength(1)
param operatorObjectIds array

@description('Explicit deployer object ID for fixture loading and local authenticated probes.')
@minLength(1)
param principalId string

@allowed(['User', 'ServicePrincipal'])
@description('Actual deployer principal type.')
param principalType string = 'User'

@description('Small Linux App Service candidate; must be checked in the selected target.')
param appServiceSku string = 'B1'

var tags = {
  Environment: environmentName
  ManagedBy: 'Bicep'
  Project: 'hospitality-feedback'
  SecurityControl: 'Ignore'
}

module resourceGroup 'br/public:avm/res/resources/resource-group:0.4.4' = {
  name: 'reference-resource-group'
  params: {
    name: resourceGroupName
    location: location
    tags: tags
    enableTelemetry: false
  }
}

resource rg 'Microsoft.Resources/resourceGroups@2025-04-01' existing = {
  name: resourceGroupName
}

module workload 'workload.bicep' = {
  name: 'hospitality-${uniqueString(environmentName, resourceGroupName)}'
  scope: rg
  params: {
    location: location
    tags: tags
    modelName: modelName
    modelVersion: modelVersion
    modelFormat: modelFormat
    modelDeploymentSku: modelDeploymentSku
    modelCapacity: modelCapacity
    modelDeploymentName: modelDeploymentName
    apiAudience: apiAudience
    operatorObjectIds: operatorObjectIds
    principalId: principalId
    principalType: principalType
    appServiceSku: appServiceSku
  }
  dependsOn: [resourceGroup]
}

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_CLIENT_ID string = workload.outputs.clientId
output AZURE_STORAGE_ACCOUNT_NAME string = workload.outputs.storageName
output AZURE_AI_PROJECT_ENDPOINT string = workload.outputs.projectEndpoint
output AZURE_MODEL_DEPLOYMENT_NAME string = modelDeploymentName
output AZURE_AI_AGENT_NAME string = workload.outputs.agentName
output AZURE_WEBAPP_NAME string = workload.outputs.appName
output SERVICE_WEB_ENDPOINT string = workload.outputs.applicationUrl
output AZURE_STORAGE_BLOB_ENDPOINT string = workload.outputs.blobEndpoint
output AZURE_STORAGE_QUEUE_ENDPOINT string = workload.outputs.queueEndpoint
