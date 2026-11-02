targetScope = 'resourceGroup'

@description('Confirmed deployment region. Read the provisional recommendation in 00-region-availability.json.')
param location string
@description('Confirmed azd environment. Use resource group rg-{environment}.')
param environment string
@description('Deploying user object ID for installation permissions, never the runtime identity.')
param principalId string
@description('Operator email for API Management service notifications.')
param publisherEmail string
@description('Application ID URI of a single-tenant Entra API registration. No client secret is needed.')
param backendAudience string
@description('Live-verified Foundry Agent Consumer role GUID; resolve by name before deployment.')
param agentConsumerRoleId string
@description('Exact live-verified model name.')
param modelName string
@description('Exact live-verified model version.')
param modelVersion string
@description('Live-verified model deployment type.')
param modelSku string
@description('Model deployment quota units; local sizing only until quota checks pass.')
@minValue(1)
param modelCapacity int = 10
@description('Enable workload only after a private image push and operator agent initialization.')
param deployWorkload bool = false
@description('Immutable image digest from this deployment private ACR. Required when deployWorkload is true.')
param applicationImage string = ''
@description('Installed immutable agent version, emitted by --initialize. Required for workload deployment.')
param agentVersion string = ''
@description('Nonoverlapping VNet address space; check against connected operator networks before deployment.')
param vnetCidr string = '10.73.0.0/16'
@description('Container Apps delegated subnet.')
param appSubnetCidr string = '10.73.0.0/23'
@description('Foundry agent delegated subnet.')
param agentSubnetCidr string = '10.73.2.0/24'
@description('API Management outbound integration subnet.')
param gatewaySubnetCidr string = '10.73.3.0/24'
@description('Private endpoint subnet.')
param endpointSubnetCidr string = '10.73.4.0/24'

@description('Stable suffix shared by every module.')
var suffix = uniqueString(resourceGroup().id)
@description('Required governance tags.')
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'finance-security-hack'
  SecurityControl: 'Ignore'
}
@description('Resource names independent of synthetic company domains.')
var names = {
  vnet: 'vnet-fin-${suffix}'
  foundry: 'ai-fin-${suffix}'
  storage: 'stfin${suffix}'
  cosmos: 'cosmos-fin-${suffix}'
  search: 'srch-fin-${suffix}'
  vault: 'kv-fin-${suffix}'
  registry: 'acrfin${suffix}'
  logs: 'log-fin-${suffix}'
  gateway: 'apim-fin-${suffix}'
  appEnvironment: 'cae-fin-${suffix}'
  app: 'ca-fin-${suffix}'
}
@description('Private DNS zones, in endpoint order.')
var zoneNames = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.blob.${az.environment().suffixes.storage}'
  'privatelink.documents.azure.com'
  'privatelink.search.windows.net'
  'privatelink.vaultcore.azure.net'
  'privatelink.azurecr.io'
]
@description('Common Log Analytics diagnostic export, with content logging excluded in app/gateway.')
var diagnostics = [{ name: 'operations', workspaceResourceId: logs.outputs.resourceId }]

resource rgTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: { tags: tags }
}
module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs'
  params: { name: names.logs, location: location, tags: tags, enableTelemetry: false, dataRetention: 30 }
}
module appIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'app-identity'
  params: { name: 'id-fin-app-${suffix}', location: location, tags: tags, enableTelemetry: false }
}
module gatewayIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'gateway-identity'
  params: { name: 'id-fin-gateway-${suffix}', location: location, tags: tags, enableTelemetry: false }
}
module gatewayNsg 'br/public:avm/res/network/network-security-group:0.5.4' = {
  name: 'gateway-nsg'
  params: {
    name: 'nsg-fin-gateway-${suffix}'
    location: location
    tags: tags
    enableTelemetry: false
    securityRules: [{
      name: 'AllowKeyVaultPlatformDependency'
      properties: {
        priority: 100
        direction: 'Outbound'
        access: 'Allow'
        protocol: 'Tcp'
        sourcePortRange: '*'
        destinationPortRange: '443'
        sourceAddressPrefix: 'VirtualNetwork'
        destinationAddressPrefix: 'AzureKeyVault'
      }
    }]
  }
}
module network 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network'
  params: {
    name: names.vnet
    location: location
    tags: tags
    enableTelemetry: false
    addressPrefixes: [vnetCidr]
    subnets: [
      { name: 'apps', addressPrefix: appSubnetCidr, delegation: 'Microsoft.App/environments' }
      { name: 'agents', addressPrefix: agentSubnetCidr, delegation: 'Microsoft.App/environments' }
      {
        name: 'gateway'
        addressPrefix: gatewaySubnetCidr
        delegation: 'Microsoft.Web/serverFarms'
        networkSecurityGroupResourceId: gatewayNsg.outputs.resourceId
      }
      { name: 'endpoints', addressPrefix: endpointSubnetCidr, privateEndpointNetworkPolicies: 'Disabled' }
    ]
  }
}
module zones 'br/public:avm/res/network/private-dns-zone:0.8.1' = [for zone in zoneNames: {
  name: 'dns-${uniqueString(zone)}'
  params: {
    name: zone
    tags: tags
    enableTelemetry: false
    virtualNetworkLinks: [{
      name: 'scenario'
      virtualNetworkResourceId: network.outputs.resourceId
      registrationEnabled: false
    }]
  }
}]
module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'storage'
  params: {
    name: names.storage
    location: location
    tags: tags
    enableTelemetry: false
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    blobServices: { containers: [{ name: 'knowledge', publicAccess: 'None' }] }
    roleAssignments: [{
      principalId: principalId
      principalType: 'User'
      roleDefinitionIdOrName: 'Storage Blob Data Contributor'
    }]
  }
}
module cosmos 'br/public:avm/res/document-db/database-account:0.21.1' = {
  name: 'cosmos'
  params: {
    name: names.cosmos
    location: location
    tags: tags
    enableTelemetry: false
    zoneRedundant: false
    enableAutomaticFailover: false
    disableLocalAuthentication: true
    networkRestrictions: { publicNetworkAccess: 'Disabled', networkAclBypass: 'None' }
    diagnosticSettings: diagnostics
  }
}
module search 'br/public:avm/res/search/search-service:0.13.0' = {
  name: 'search'
  params: {
    name: names.search
    location: location
    tags: tags
    enableTelemetry: false
    sku: 'standard'
    replicaCount: 1
    partitionCount: 1
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    diagnosticSettings: diagnostics
  }
}
module vault 'br/public:avm/res/key-vault/vault:0.14.2' = {
  name: 'vault'
  params: {
    name: names.vault
    location: location
    tags: tags
    enableTelemetry: false
    sku: 'standard'
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableVaultForDeployment: false
    enableVaultForTemplateDeployment: false
    enableVaultForDiskEncryption: false
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    keys: [{
      name: 'response-receipt'
      kty: 'RSA'
      keySize: 2048
      keyOps: ['sign', 'verify']
      roleAssignments: [{
        principalId: appIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Key Vault Crypto User'
      }]
    }]
    roleAssignments: [{
      principalId: principalId
      principalType: 'User'
      roleDefinitionIdOrName: 'Key Vault Crypto Officer'
    }]
    diagnosticSettings: diagnostics
  }
}
module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'registry'
  params: {
    name: names.registry
    location: location
    tags: tags
    enableTelemetry: false
    acrSku: 'Premium'
    acrAdminUserEnabled: false
    dataEndpointEnabled: true
    networkRuleBypassOptions: 'None'
    azureADAuthenticationAsArmPolicyStatus: 'enabled'
    publicNetworkAccess: 'Disabled'
    roleAssignments: [
      {
        principalId: appIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'AcrPull'
      }
      { principalId: principalId, principalType: 'User', roleDefinitionIdOrName: 'AcrPush' }
    ]
    diagnosticSettings: diagnostics
  }
}
module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: names.foundry
    kind: 'AIServices'
    sku: 'S0'
    location: location
    tags: tags
    enableTelemetry: false
    allowProjectManagement: true
    customSubDomainName: names.foundry
    managedIdentities: { systemAssigned: true }
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    networkInjections: {
      scenario: 'agent'
      subnetResourceId: '${network.outputs.resourceId}/subnets/agents'
      useMicrosoftManagedNetwork: false
    }
    deployments: [{
      name: 'brokerage-model'
      model: { name: modelName, format: 'OpenAI', version: modelVersion }
      sku: { name: modelSku, capacity: modelCapacity }
    }]
    diagnosticSettings: diagnostics
  }
}
@description('Private endpoint targets and DNS groups.')
var endpointSpecs = [
  {
    name: 'foundry'
    id: resourceId('Microsoft.CognitiveServices/accounts', names.foundry)
    group: 'account'
    dns: [
      resourceId('Microsoft.Network/privateDnsZones', zoneNames[0])
      resourceId('Microsoft.Network/privateDnsZones', zoneNames[1])
      resourceId('Microsoft.Network/privateDnsZones', zoneNames[2])
    ]
  }
  {
    name: 'blob'
    id: resourceId('Microsoft.Storage/storageAccounts', names.storage)
    group: 'blob'
    dns: [resourceId('Microsoft.Network/privateDnsZones', zoneNames[3])]
  }
  {
    name: 'cosmos'
    id: resourceId('Microsoft.DocumentDB/databaseAccounts', names.cosmos)
    group: 'Sql'
    dns: [resourceId('Microsoft.Network/privateDnsZones', zoneNames[4])]
  }
  {
    name: 'search'
    id: resourceId('Microsoft.Search/searchServices', names.search)
    group: 'searchService'
    dns: [resourceId('Microsoft.Network/privateDnsZones', zoneNames[5])]
  }
  {
    name: 'vault'
    id: resourceId('Microsoft.KeyVault/vaults', names.vault)
    group: 'vault'
    dns: [resourceId('Microsoft.Network/privateDnsZones', zoneNames[6])]
  }
  {
    name: 'registry'
    id: resourceId('Microsoft.ContainerRegistry/registries', names.registry)
    group: 'registry'
    dns: [resourceId('Microsoft.Network/privateDnsZones', zoneNames[7])]
  }
]
module endpoints 'br/public:avm/res/network/private-endpoint:0.12.1' = [for spec in endpointSpecs: {
  name: 'endpoint-${spec.name}'
  params: {
    name: 'pe-fin-${spec.name}-${suffix}'
    location: location
    tags: tags
    enableTelemetry: false
    subnetResourceId: '${network.outputs.resourceId}/subnets/endpoints'
    privateLinkServiceConnections: [{
      name: spec.name
      properties: { privateLinkServiceId: spec.id, groupIds: [spec.group] }
    }]
    privateDnsZoneGroup: {
      name: 'default'
      privateDnsZoneGroupConfigs: [for id in spec.dns: { privateDnsZoneResourceId: id }]
    }
  }
  dependsOn: [foundry, storage, cosmos, search, vault, registry, zones]
}]
module project 'modules/project.bicep' = {
  name: 'project'
  params: {
    accountName: names.foundry
    location: location
    tags: tags
    storageName: names.storage
    cosmosName: names.cosmos
    searchName: names.search
    applicationPrincipalId: appIdentity.outputs.principalId
    deployerPrincipalId: principalId
    agentConsumerRoleId: agentConsumerRoleId
  }
  dependsOn: [foundry, endpoints]
}
module appEnvironment 'br/public:avm/res/app/managed-environment:0.16.0' = {
  name: 'app-environment'
  params: {
    name: names.appEnvironment
    location: location
    tags: tags
    enableTelemetry: false
    infrastructureSubnetResourceId: '${network.outputs.resourceId}/subnets/apps'
    internal: true
    publicNetworkAccess: 'Disabled'
    zoneRedundant: false
    peerTrafficEncryption: true
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: { destination: 'azure-monitor' }
    diagnosticSettings: diagnostics
  }
}
module appDns 'br/public:avm/res/network/private-dns-zone:0.8.1' = {
  name: 'app-dns'
  params: {
    name: appEnvironment.outputs.defaultDomain
    tags: tags
    enableTelemetry: false
    virtualNetworkLinks: [{ name: 'scenario', virtualNetworkResourceId: network.outputs.resourceId }]
    a: [{ name: '*', aRecords: [{ ipv4Address: appEnvironment.outputs.staticIp! }] }]
  }
}
module gateway 'br/public:avm/res/api-management/service:0.15.0' = {
  name: 'gateway'
  params: {
    name: names.gateway
    location: location
    tags: tags
    enableTelemetry: false
    publisherName: 'Adatum Corporation synthetic brokerage reference'
    publisherEmail: publisherEmail
    sku: 'StandardV2'
    skuCapacity: 1
    availabilityZones: []
    virtualNetworkType: 'External'
    subnetResourceId: '${network.outputs.resourceId}/subnets/gateway'
    managedIdentities: { userAssignedResourceIds: [gatewayIdentity.outputs.resourceId] }
    enableDeveloperPortal: false
    diagnosticSettings: diagnostics
  }
}
module workload 'modules/workload.bicep' = if (deployWorkload) {
  name: 'workload'
  params: {
    location: location
    tags: tags
    appName: names.app
    environmentId: appEnvironment.outputs.resourceId
    applicationImage: applicationImage
    registryServer: '${names.registry}.azurecr.io'
    identityId: appIdentity.outputs.resourceId
    identityClientId: appIdentity.outputs.clientId
    tenantId: tenant().tenantId
    gatewayName: names.gateway
    gatewayClientId: gatewayIdentity.outputs.clientId
    gatewayPrincipalId: gatewayIdentity.outputs.principalId
    backendAudience: backendAudience
    projectEndpoint: 'https://${names.foundry}.services.ai.azure.com/api/projects/brokerage'
    agentVersion: agentVersion
    faqBlobUrl: 'https://${names.storage}.blob.${az.environment().suffixes.storage}/knowledge/brokerage-faq.md'
    signingKeyUrl: 'https://${names.vault}${az.environment().suffixes.keyvaultDns}/keys/response-receipt'
  }
  dependsOn: [gateway, project, appDns]
}

@description('Public entry after workload installation; not evidence that an app is deployed.')
output APPLICATION_URL string = 'https://${names.gateway}.azure-api.net'
@description('Private project endpoint.')
output FOUNDRY_PROJECT_ENDPOINT string = 'https://${names.foundry}.services.ai.azure.com/api/projects/brokerage'
@description('Image delivery registry name.')
output AZURE_CONTAINER_REGISTRY_NAME string = names.registry
@description('Private image registry endpoint.')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = '${names.registry}.azurecr.io'
@description('azd Container Apps environment name.')
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = names.appEnvironment
@description('azd service application name.')
output SERVICE_WEB_NAME string = names.app
@description('Application managed identity client ID.')
output AZURE_CLIENT_ID string = appIdentity.outputs.clientId
@description('Gateway identity allowed to call the private application.')
output GATEWAY_PRINCIPAL_ID string = gatewayIdentity.outputs.principalId
@description('Synthetic source installation URL.')
output FAQ_BLOB_URL string = 'https://${names.storage}.blob.${az.environment().suffixes.storage}/knowledge/brokerage-faq.md'
@description('Private response signing key URL.')
output SIGNING_KEY_URL string = 'https://${names.vault}${az.environment().suffixes.keyvaultDns}/keys/response-receipt'
@description('Whether the application was requested, not a runtime health assertion.')
output workloadRequested bool = deployWorkload
