@description('Scenario environment.')
param environmentName string
@description('Confirmed deployment region.')
param location string
@description('Installer object ID.')
param principalId string
@description('Resolved Foundry Agent Consumer role GUID.')
param agentConsumerRoleId string
@description('Approved model.')
param modelName string
@description('Approved model version.')
param modelVersion string
@description('Common resource tags.')
param tags object

var uniqueSuffix = uniqueString(resourceGroup().id)
var foundryName = 'fc-${take(environmentName, 11)}-${take(uniqueSuffix, 8)}'
var projectName = 'backoffice'
var storageName = 'stfc${take(uniqueSuffix, 16)}'
var webName = 'web-fc-${uniqueSuffix}'
var projectEndpoint = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
var tableContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var foundryUser = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: foundryName
    kind: 'AIServices'
    sku: 'S0'
    location: location
    tags: tags
    customSubDomainName: foundryName
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: false
    managedIdentities: { systemAssigned: true }
    deployments: [{
      name: modelName
      model: { format: 'OpenAI', name: modelName, version: modelVersion }
      sku: { name: 'GlobalStandard', capacity: 30 }
      versionUpgradeOption: 'NoAutoUpgrade'
    }]
  }
}
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Fourth Coffee back office'
    description: 'coffee-shop owned sales-readiness and daily-close agents'
  }
  dependsOn: [foundry]
}
module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'storage'
  params: {
    name: storageName
    location: location
    tags: tags
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'None'
    }
    defaultToOAuthAuthentication: true
    tableServices: { tables: [{ name: 'CoffeeBackOffice' }] }
    blobServices: {}
    fileServices: {}
    queueServices: {}
    roleAssignments: [
      { principalId: principalId, principalType: 'User', roleDefinitionIdOrName: tableContributor }
    ]
  }
}
module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'plan'
  params: {
    name: 'plan-fc-${uniqueSuffix}'
    location: location
    tags: tags
    kind: 'linux'
    skuName: 'P0v3'
    skuCapacity: 1
    zoneRedundant: false
    maximumElasticWorkerCount: 3
    elasticScaleEnabled: true
  }
}
module web 'br/public:avm/res/web/site:0.24.0' = {
  name: 'web'
  params: {
    name: webName
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId
    managedIdentities: { systemAssigned: true }
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    clientAffinityEnabled: false
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      minimumElasticInstanceCount: 1
      elasticWebAppScaleLimit: 3
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'Storage__Endpoint', value: 'https://${storageName}.table.${environment().suffixes.storage}' }
        { name: 'Foundry__Endpoint', value: projectEndpoint }
        { name: 'Foundry__Model', value: modelName }
        { name: 'ASPNETCORE_ENVIRONMENT', value: 'Production' }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'false' }
      ]
    }
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
  }
}
resource storageAccount 'Microsoft.Storage/storageAccounts@2025-01-01' existing = {
  name: storageName
}
resource appTableRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, webName, tableContributor)
  scope: storageAccount
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', tableContributor)
  }
  dependsOn: [storage]
}
resource installerFoundryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, principalId, foundryUser)
  scope: account
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUser)
  }
  dependsOn: [foundry]
}
resource projectFoundryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, project.id, foundryUser)
  scope: account
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUser)
  }
}
resource runtimeFoundryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, webName, agentConsumerRoleId)
  scope: project
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', agentConsumerRoleId)
  }
}
output webName string = webName
output webUrl string = 'https://${web.outputs.defaultHostname}'
output projectEndpoint string = projectEndpoint
output storageEndpoint string = 'https://${storageName}.table.${environment().suffixes.storage}'
