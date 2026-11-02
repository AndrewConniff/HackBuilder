@description('Provisional deployment region.')
param location string
@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Short scenario/environment name stem.')
param stem string
@description('Standard resource tags.')
param tags object
@description('Dedicated delegated agent subnet.')
param agentSubnetId string
@description('Exact model name from region evidence.')
param modelName string
@description('Exact model version from region evidence.')
param modelVersion string
@description('Model deployment type from region evidence.')
param modelSku string
@description('Provisional model capacity units; live capacity must be checked.')
param modelCapacity int
@description('Deployer/agent installer object ID.')
param principalId string
@description('Private Standard platform Storage name.')
param storageName string
@description('Platform Blob endpoint.')
param blobEndpoint string
@description('Private Standard Cosmos name.')
param cosmosName string
@description('Cosmos endpoint.')
param cosmosEndpoint string
@description('Private Standard Search name.')
param searchName string

module account 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'account-${uniqueSuffix}'
  params: {
    name: 'aif-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    kind: 'AIServices'
    sku: 'S0'
    customSubDomainName: 'aif-${stem}'
    allowProjectManagement: true
    managedIdentities: { systemAssigned: true }
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'None' }
    networkInjections: {
      scenario: 'agent'
      subnetResourceId: agentSubnetId
      useMicrosoftManagedNetwork: false
    }
    restrictOutboundNetworkAccess: true
    deployments: [
      {
        name: modelName
        model: { format: 'OpenAI', name: modelName, version: modelVersion }
        sku: { name: modelSku, capacity: modelCapacity }
        versionUpgradeOption: 'NoAutoUpgrade'
      }
    ]
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: 'aif-${stem}'
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: 'mobility-commercial'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Adventure Works Cycles Sales-to-Marketing'
    description: 'Three prompt agents; private Standard runtime; synthetic sales and marketing data.'
  }
  dependsOn: [account]
}

resource storageConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: storageName
  properties: {
    category: 'AzureStorageAccount'
    target: blobEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: resourceId('Microsoft.Storage/storageAccounts', storageName)
      location: location
    }
  }
}
resource cosmosConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: cosmosName
  properties: {
    category: 'CosmosDB'
    target: cosmosEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: resourceId('Microsoft.DocumentDB/databaseAccounts', cosmosName)
      location: location
    }
  }
}
resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: searchName
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchName}.search.windows.net'
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: resourceId('Microsoft.Search/searchServices', searchName)
      location: location
    }
  }
}
resource installerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, principalId, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d'
    )
    principalId: principalId
    principalType: 'User'
  }
}
resource projectInferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundry
  name: guid(foundry.id, project.id, '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d'
    )
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

@description('Direct child project ID.')
output resourceId string = project.id
@description('Direct child project name.')
output resourceName string = project.name
@description('Foundry account name.')
output accountName string = account.outputs.name
@description('Project managed identity object ID.')
output principalId string = project.identity.principalId
@description('Service-assigned workspace identifier used by the official private setup sample.')
#disable-next-line BCP053
output workspaceId string = project.properties.internalId
@description('New Foundry project endpoint.')
output projectEndpoint string = 'https://${account.outputs.name}.services.ai.azure.com/api/projects/${project.name}'
@description('Standard storage connection name.')
output storageConnectionName string = storageConnection.name
@description('Standard Cosmos connection name.')
output cosmosConnectionName string = cosmosConnection.name
@description('Standard Search connection name.')
output searchConnectionName string = searchConnection.name
