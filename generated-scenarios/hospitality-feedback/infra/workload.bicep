@description('Validated location passed from the root.')
param location string
param tags object
param modelName string
param modelVersion string
param modelFormat string
param modelDeploymentSku string
param modelCapacity int
param modelDeploymentName string
param apiAudience string
param operatorObjectIds array
param principalId string
param principalType string
param appServiceSku string

var suffix = uniqueString(resourceGroup().id)
var foundryName = 'ai-hotel-${take(suffix, 12)}'
var runtimeIdentityName = 'id-hotel-${take(suffix, 10)}'
// Includes a hash of the definition's semantic version and selected model.
// Increment definition version if instructions or wire contract change.
var agentName = 'hotel-feedback-${take(uniqueString('definition-v1', modelName, modelVersion), 10)}'

module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'runtime-identity'
  params: {
    name: runtimeIdentityName
    location: location
    tags: tags
    enableTelemetry: false
  }
}

module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'storage'
  params: {
    name: 'sthotel${take(suffix, 16)}'
    location: location
    tags: tags
    enableTelemetry: false
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Allow', bypass: 'None' }
    blobServices: {
      deleteRetentionPolicyEnabled: true
      deleteRetentionPolicyDays: 7
      containerDeleteRetentionPolicyEnabled: true
      containerDeleteRetentionPolicyDays: 7
      isVersioningEnabled: true
      containers: [
        { name: 'raw', publicAccess: 'None' }
        { name: 'processed', publicAccess: 'None' }
        { name: 'status', publicAccess: 'None' }
        { name: 'audit', publicAccess: 'None' }
      ]
    }
    queueServices: {
      queues: [
        { name: 'feedback-ingest' }
        { name: 'feedback-poison' }
      ]
    }
    roleAssignments: [
      {
        principalId: identity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
      {
        principalId: identity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Storage Queue Data Contributor'
      }
      {
        principalId: principalId
        principalType: principalType
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
      {
        principalId: principalId
        principalType: principalType
        roleDefinitionIdOrName: 'Storage Queue Data Contributor'
      }
    ]
  }
}

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: foundryName
    customSubDomainName: foundryName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: 'S0'
    enableTelemetry: false
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: false
    managedIdentities: { systemAssigned: true }
    deployments: [
      {
        name: modelDeploymentName
        model: { format: modelFormat, name: modelName, version: modelVersion }
        sku: { name: modelDeploymentSku, capacity: modelCapacity }
        versionUpgradeOption: 'NoAutoUpgrade'
      }
    ]
  }
}

// Native direct-child resource: no standalone published AVM project resource module.
// No capabilitySettings/BYO state resources: this is Foundry Basic, not Standard.
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: 'hotel-feedback'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Hotel service feedback'
    description: 'Synthetic multilingual hotel feedback; Basic agent state managed by Microsoft.'
  }
  dependsOn: [foundry]
}

// Native extension assignments on the direct child project. Current official role definition:
// Foundry User 53ca6127-db72-4b80-b1b0-d745d6d5456d (verify in the selected target during preflight).
// Registration + invocation are both app responsibilities; this grants agent creation, not only consumption.
var foundryRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
resource runtimeFoundryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, resourceId('Microsoft.ManagedIdentity/userAssignedIdentities', runtimeIdentityName), foundryRole)
  scope: project
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: foundryRole
  }
}
resource deployerFoundryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, principalId, foundryRole)
  scope: project
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: foundryRole
  }
}

module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'app-plan'
  params: {
    name: 'plan-hotel-${take(suffix, 10)}'
    location: location
    tags: tags
    enableTelemetry: false
    kind: 'linux'
    reserved: true
    skuName: appServiceSku
    skuCapacity: 1
    zoneRedundant: false
  }
}

var projectEndpoint = 'https://${foundry.outputs.name}.services.ai.azure.com/api/projects/${project.name}'
module web 'br/public:avm/res/web/site:0.24.0' = {
  name: 'web'
  params: {
    name: 'app-hotel-${take(suffix, 12)}'
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    enableTelemetry: false
    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    managedIdentities: { userAssignedResourceIds: [identity.outputs.resourceId] }
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
      use32BitWorkerProcess: false
    }
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
    configs: [
      {
        name: 'appsettings'
        properties: union({
          ASPNETCORE_ENVIRONMENT: 'Production'
          AZURE_CLIENT_ID: identity.outputs.clientId
          Feedback__UseAzurite: 'false'
          Feedback__LocalAnonymous: 'false'
          Feedback__BlobEndpoint: storage.outputs.serviceEndpoints.blob
          Feedback__QueueEndpoint: storage.outputs.serviceEndpoints.queue
          Feedback__ProjectEndpoint: projectEndpoint
          Feedback__ModelDeployment: modelDeploymentName
          Feedback__AgentName: agentName
          Feedback__TenantId: tenant().tenantId
          Feedback__Audience: apiAudience
          Feedback__MaxEvidenceRecords: '100'
          Feedback__MaxDeliveryAttempts: '5'
          WEBSITE_RUN_FROM_PACKAGE: '1'
        }, toObject(range(0, length(operatorObjectIds)), i => 'Feedback__OperatorObjectIds__${i}', i => operatorObjectIds[i]))
      }
      {
        name: 'logs'
        properties: {
          applicationLogs: { fileSystem: { level: 'Information' } }
          httpLogs: { fileSystem: { enabled: true, retentionInDays: 3, retentionInMb: 25 } }
          detailedErrorMessages: { enabled: false }
          failedRequestsTracing: { enabled: false }
        }
      }
    ]
  }
  dependsOn: [runtimeFoundryRole]
}

output clientId string = identity.outputs.clientId
output storageName string = storage.outputs.name
output projectEndpoint string = projectEndpoint
output agentName string = agentName
output appName string = web.outputs.name
output applicationUrl string = 'https://${web.outputs.defaultHostname}'
output blobEndpoint string = storage.outputs.serviceEndpoints.blob
output queueEndpoint string = storage.outputs.serviceEndpoints.queue
