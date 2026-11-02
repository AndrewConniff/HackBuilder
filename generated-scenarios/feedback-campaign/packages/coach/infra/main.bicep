targetScope = 'resourceGroup'

@description('Explicit isolated destination coach environment.')
param environmentName string
@description('Explicit destination region; perform fresh model, quota and SKU checks before rollout.')
param location string
@description('Object ID of signed-in installer, captured automatically; used only for scoped initialization.')
param installerObjectId string
@description('Reference model contract; verify destination eligibility before rollout.')
param modelVersion string = '2025-04-14'

var suffix = uniqueString(resourceGroup().id)
var tags = {
  Environment: environmentName
  ManagedBy: 'azd'
  Project: 'feedback-campaign'
  SecurityControl: 'Ignore'
}

resource rgTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: { tags: tags }
}

module foundry 'br/public:avm/res/cognitive-services/account:0.14.3' = {
  name: 'foundry'
  params: {
    name: 'fc-ai-${suffix}'
    location: location
    kind: 'AIServices'
    sku: 'S0'
    customSubDomainName: 'fc-ai-${suffix}'
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    managedIdentities: { systemAssigned: true }
    deployments: [{
      name: 'campaign-model'
      model: { format: 'OpenAI', name: 'gpt-4.1-mini', version: modelVersion }
      sku: { name: 'GlobalStandard', capacity: 10 }
    }]
    tags: tags
    enableTelemetry: false
  }
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: 'fc-ai-${suffix}'
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundryAccount
  name: 'campaign'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: { displayName: 'Campaign Control', description: 'Marketing and Sales HITL reference' }
  tags: tags
  dependsOn: [foundry]
}

module storage 'br/public:avm/res/storage/storage-account:0.31.0' = {
  name: 'storage'
  params: {
    name: 'stfc${suffix}'
    location: location
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Allow', bypass: 'None' }
    minimumTlsVersion: 'TLS1_2'
    tableServices: { tables: [{ name: 'campaignstate' }] }
    tags: tags
    enableTelemetry: false
  }
}

module bus 'br/public:avm/res/service-bus/namespace:0.17.1' = {
  name: 'bus'
  params: {
    name: 'fc-bus-${suffix}'
    location: location
    skuObject: { name: 'Standard', capacity: 0 }
    zoneRedundant: false
    requireInfrastructureEncryption: false
    disableLocalAuth: true
    authorizationRules: []
    publicNetworkAccess: 'Enabled'
    queues: [for name in ['posts', 'replies']: {
      name: name
      requiresDuplicateDetection: true
      duplicateDetectionHistoryTimeWindow: 'P7D'
      maxDeliveryCount: 5
      defaultMessageTimeToLive: 'P14D'
      deadLetteringOnMessageExpiration: true
    }]
    tags: tags
    enableTelemetry: false
  }
}

module logs 'br/public:avm/res/operational-insights/workspace:0.15.0' = {
  name: 'logs'
  params: {
    name: 'fc-log-${suffix}'
    location: location
    skuName: 'PerGB2018'
    dataRetention: 30
    dailyQuotaGb: '1'
    tags: tags
    enableTelemetry: false
  }
}
module insights 'br/public:avm/res/insights/component:0.7.1' = {
  name: 'insights'
  params: {
    name: 'fc-insights-${suffix}'
    location: location
    kind: 'web'
    applicationType: 'web'
    workspaceResourceId: logs.outputs.resourceId
    tags: tags
    enableTelemetry: false
  }
}
module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'plan'
  params: {
    name: 'fc-plan-${suffix}'
    location: location
    kind: 'linux'
    reserved: true
    skuName: 'B1'
    skuCapacity: 1
    tags: tags
    enableTelemetry: false
  }
}
module web 'br/public:avm/res/web/site:0.24.0' = {
  name: 'web'
  params: {
    name: 'fc-web-${suffix}'
    location: location
    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId
    managedIdentities: { systemAssigned: true }
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
      appSettings: [
        { name: 'TABLE_ENDPOINT', value: 'https://stfc${suffix}.table.${environment().suffixes.storage}' }
        { name: 'SERVICEBUS_NAMESPACE', value: 'fc-bus-${suffix}.servicebus.windows.net' }
        { name: 'FOUNDRY_PROJECT_ENDPOINT', value: 'https://fc-ai-${suffix}.services.ai.azure.com/api/projects/campaign' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.outputs.connectionString }
        { name: 'ASPNETCORE_ENVIRONMENT', value: 'Production' }
      ]
    }
    tags: union(tags, { 'azd-service-name': 'web' })
    enableTelemetry: false
  }
}

resource site 'Microsoft.Web/sites@2025-03-01' existing = { name: 'fc-web-${suffix}' }
resource auth 'Microsoft.Web/sites/config@2025-03-01' = {
  parent: site
  name: 'authsettingsV2'
  properties: {
    platform: { enabled: false, runtimeVersion: '~1' }
    httpSettings: { requireHttps: true }
    globalValidation: { requireAuthentication: false }
    login: { tokenStore: { enabled: false } }
  }
  dependsOn: [web]
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = { name: 'stfc${suffix}' }
resource namespace 'Microsoft.ServiceBus/namespaces@2024-01-01' existing = { name: 'fc-bus-${suffix}' }
resource posts 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' existing = { parent: namespace, name: 'posts' }
resource replies 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' existing = { parent: namespace, name: 'replies' }
var tableRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
var aiUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
resource tableAppRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, site.id, tableRole)
  scope: storageAccount
  properties: { principalId: web.outputs.systemAssignedMIPrincipalId!, roleDefinitionId: tableRole, principalType: 'ServicePrincipal' }
  dependsOn: [storage]
}
resource tableInstallerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, installerObjectId, tableRole)
  scope: storageAccount
  properties: { principalId: installerObjectId, roleDefinitionId: tableRole, principalType: 'User' }
  dependsOn: [storage]
}
resource aiAppRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, site.id, aiUserRole)
  scope: project
  properties: { principalId: web.outputs.systemAssignedMIPrincipalId!, roleDefinitionId: aiUserRole, principalType: 'ServicePrincipal' }
}
resource aiInstallerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, installerObjectId, aiUserRole)
  scope: project
  properties: { principalId: installerObjectId, roleDefinitionId: aiUserRole, principalType: 'User' }
}
resource postsReceiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(posts.id, site.id, 'receive')
  scope: posts
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0')
    principalType: 'ServicePrincipal'
  }
  dependsOn: [bus]
}
resource repliesSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(replies.id, site.id, 'send')
  scope: replies
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39')
    principalType: 'ServicePrincipal'
  }
  dependsOn: [bus]
}

resource postsInstallerSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(posts.id, installerObjectId, 'send')
  scope: posts
  properties: {
    principalId: installerObjectId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39')
    principalType: 'User'
  }
  dependsOn: [bus]
}
resource postsInstallerReceiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(posts.id, installerObjectId, 'receive')
  scope: posts
  properties: {
    principalId: installerObjectId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0')
    principalType: 'User'
  }
  dependsOn: [bus]
}
resource repliesInstallerReceiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(replies.id, installerObjectId, 'receive')
  scope: replies
  properties: {
    principalId: installerObjectId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0')
    principalType: 'User'
  }
  dependsOn: [bus]
}

output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_WEBAPP_NAME string = site.name
output APP_URL string = 'https://${site.name}.azurewebsites.net'
output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundryAccount.name}.services.ai.azure.com/api/projects/campaign'
output FOUNDRY_MODEL_ENDPOINT string = 'https://${foundryAccount.name}.openai.azure.com'
output FOUNDRY_MODEL_DEPLOYMENT string = 'campaign-model'
output TABLE_ENDPOINT string = 'https://${storageAccount.name}.table.${environment().suffixes.storage}'
output SERVICEBUS_NAMESPACE string = '${namespace.name}.servicebus.windows.net'
