targetScope = 'resourceGroup'

@description('Explicit azd environment name.')
@minLength(1)
param environmentName string

@description('Region validated for the complete resource/model set before deployment. No default.')
param location string

@description('Confirmed human deploying administrator object ID, supplied by azd.')
@minLength(36)
@maxLength(36)
param principalId string

@description('Provisional model preference; validate and review before deployment.')
param modelName string = 'gpt-4.1-mini'

@description('Exact provisional model version.')
param modelVersion string = '2025-04-14'

@description('Validated deployment type; GlobalStandard does not guarantee regional processing residency.')
param modelSku string = 'GlobalStandard'

@description('Model quota capacity units; exact subscription headroom must be verified.')
@minValue(1)
param modelCapacity int = 10

@description('Single suffix shared by globally unique resources.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Static Foundry name, also used for child resource scopes.')
var foundryName = 'ai-bank-${uniqueSuffix}'
@description('Static storage name for scoped grants.')
var storageName = 'stbank${uniqueSuffix}'
@description('Static monitoring name for scoped grants.')
var insightsName = 'appi-bank-${uniqueSuffix}'
@description('Static application identity owner name for stable role-assignment IDs.')
var webName = 'app-bank-${uniqueSuffix}'
@description('Scenario resource tags.')
var tags = {
  Environment: environmentName
  ManagedBy: 'Bicep'
  Project: 'finance-customer-hack'
  SecurityControl: 'Ignore'
}
@description('Stable scoped role definitions, checked against published role definitions.')
var roles = {
  contributor: 'b24988ac-6180-42a0-ab88-20f7382dd24c'
  rbacAdministrator: 'f58310d9-a9f6-439a-9e8d-f62e7b41a168'
  tableContributor: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
  foundryUser: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
  foundryOwner: 'c883944f-8b7b-4483-af10-35834be79c4a'
  metricsPublisher: '3913510d-42f4-4e42-8a64-420c390055eb'
}

@description('Tag the azd-created resource group.')
resource rgTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: { tags: tags }
}

module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs'
  params: {
    name: 'log-bank-${uniqueSuffix}'
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
    dailyQuotaGb: '1'
  }
}

module insights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'insights'
  params: {
    name: insightsName
    location: location
    tags: tags
    kind: 'web'
    applicationType: 'web'
    workspaceResourceId: logs.outputs.resourceId
    disableLocalAuth: true
    disableIpMasking: false
  }
}

module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'storage'
  params: {
    name: storageName
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    publicNetworkAccess: 'Enabled'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    tableServices: {
      tables: [{ name: 'bankstate' }]
      diagnosticSettings: [{
        name: 'table-diagnostics'
        workspaceResourceId: logs.outputs.resourceId
      }]
    }
    diagnosticSettings: [{
      name: 'storage-metrics'
      workspaceResourceId: logs.outputs.resourceId
    }]
  }
}

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: foundryName
    customSubDomainName: foundryName
    kind: 'AIServices'
    sku: 'S0'
    location: location
    tags: tags
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    managedIdentities: { systemAssigned: true }
    deployments: [{
      name: 'bank-model'
      model: { format: 'OpenAI', name: modelName, version: modelVersion }
      sku: { name: modelSku, capacity: modelCapacity }
    }]
    diagnosticSettings: [{
      name: 'foundry-diagnostics'
      workspaceResourceId: logs.outputs.resourceId
    }]
  }
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

@description('Direct child project; no separate project AVM exists in the queried registry.')
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundryAccount
  name: 'banking'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Adatum Corporation banking service'
    description: 'Synthetic banking triage, grounded answers and human-owned escalations.'
  }
  dependsOn: [foundry]
}

module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'plan'
  params: {
    name: 'asp-bank-${uniqueSuffix}'
    location: location
    tags: tags
    kind: 'linux'
    reserved: true
    skuName: 'B1'
    skuCapacity: 1
    zoneRedundant: false
    diagnosticSettings: [{
      name: 'plan-metrics'
      workspaceResourceId: logs.outputs.resourceId
    }]
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
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
    }
    configs: [{
      name: 'appsettings'
      properties: {
        STORAGE_TABLE_ENDPOINT: 'https://${storage.outputs.name}.table.${environment().suffixes.storage}'
        FOUNDRY_PROJECT_ENDPOINT: 'https://${foundry.outputs.name}.services.ai.azure.com/api/projects/${project.name}'
        SESSION_KEYS_PATH: '/home/data/bank-keys'
        APPLICATIONINSIGHTS_CONNECTION_STRING: insights.outputs.connectionString
        ASPNETCORE_ENVIRONMENT: 'Production'
      }
    }]
    diagnosticSettings: [{
      name: 'web-diagnostics'
      workspaceResourceId: logs.outputs.resourceId
    }]
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-01-01' existing = {
  name: storageName
}
resource monitoring 'Microsoft.Insights/components@2020-02-02' existing = {
  name: insightsName
}

resource workloadTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, webName, roles.tableContributor)
  scope: storageAccount
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.tableContributor)
  }
}
resource workloadFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, webName, roles.foundryUser)
  scope: project
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.foundryUser)
  }
}
resource workloadTelemetry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(monitoring.id, webName, roles.metricsPublisher)
  scope: monitoring
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.metricsPublisher)
  }
}
resource deployerTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, principalId, roles.tableContributor)
  scope: storageAccount
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.tableContributor)
  }
  dependsOn: [storage]
}
resource deployerFoundry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccount.id, principalId, roles.foundryOwner)
  scope: foundryAccount
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.foundryOwner)
  }
  dependsOn: [foundry]
}
resource deployerAdministration 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for role in [roles.contributor, roles.rbacAdministrator]: {
    name: guid(resourceGroup().id, principalId, role)
    properties: {
      principalId: principalId
      principalType: 'User'
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', role)
    }
  }
]

@description('Application URL; not evidence of runtime success.')
output APPLICATION_URL string = 'https://${web.outputs.defaultHostname}'
@description('Actual App Service name for operator administration.')
output AZURE_WEBAPP_NAME string = web.outputs.name
@description('Confirmed scenario resource group.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name
@description('Keyless table service endpoint.')
output STORAGE_TABLE_ENDPOINT string = 'https://${storage.outputs.name}.table.${environment().suffixes.storage}'
@description('Foundry direct-child project endpoint for installation and runtime.')
output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundry.outputs.name}.services.ai.azure.com/api/projects/${project.name}'
@description('Installed model deployment name.')
output FOUNDRY_MODEL_DEPLOYMENT string = 'bank-model'
@description('Foundry account name for scoped access verification.')
output FOUNDRY_ACCOUNT_NAME string = foundry.outputs.name
