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
@description('Reviewed model capacity units; quota is validated separately.')
param modelCapacity int
@description('Common resource tags.')
param tags object

@description('One stable unique suffix for destination resources.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Destination Foundry resource name.')
var foundryName = 'ic-${take(environmentName, 11)}-${take(uniqueSuffix, 8)}'
@description('Direct child project name.')
var projectName = 'backoffice'
@description('Destination storage name.')
var storageName = 'stic${take(uniqueSuffix, 16)}'
@description('Destination web app name.')
var webName = 'web-ic-${uniqueSuffix}'
@description('Direct project endpoint; no classic hub.')
var projectEndpoint = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
@description('Full Table data management role.')
var tableContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
@description('Foundry data administration role; verify effective permissions at readiness.')
var foundryUser = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs'
  params: {
    name: 'log-ic-${uniqueSuffix}'
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
    dailyQuotaGb: '1'
    forceCmkForQuery: false
    roleAssignments: [{
      principalId: principalId
      principalType: 'User'
      roleDefinitionIdOrName: 'Log Analytics Contributor'
    }]
  }
}

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
    diagnosticSettings: [{ workspaceResourceId: logs.outputs.resourceId }]
    managedIdentities: { systemAssigned: true }
    deployments: [{
      name: modelName
      model: { format: 'OpenAI', name: modelName, version: modelVersion }
      sku: { name: 'GlobalStandard', capacity: modelCapacity }
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
    displayName: 'Northwind Traders ice-cream operations'
    description: 'coffee-to-icecream owned recipe stock and managerial-close workers'
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
    tableServices: {
      tables: [{ name: 'IceCreamBackOffice' }]
      diagnosticSettings: [{ workspaceResourceId: logs.outputs.resourceId }]
    }
    roleAssignments: [
      { principalId: principalId, principalType: 'User', roleDefinitionIdOrName: tableContributor }
    ]
  }
}
module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'plan'
  params: {
    name: 'plan-ic-${uniqueSuffix}'
    location: location
    tags: tags
    kind: 'linux'
    skuName: 'P0v3'
    skuCapacity: 1
    zoneRedundant: false
    maximumElasticWorkerCount: 3
    elasticScaleEnabled: true
    diagnosticSettings: [{ workspaceResourceId: logs.outputs.resourceId }]
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
    diagnosticSettings: [{ workspaceResourceId: logs.outputs.resourceId }]
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
@description('Destination web app name.')
output webName string = webName
@description('Destination web app URL.')
output webUrl string = 'https://${web.outputs.defaultHostname}'
@description('Direct child project endpoint.')
output projectEndpoint string = projectEndpoint
@description('Business Table endpoint.')
output storageEndpoint string = 'https://${storageName}.table.${environment().suffixes.storage}'
