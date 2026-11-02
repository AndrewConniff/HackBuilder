targetScope = 'resourceGroup'

@description('Distinct azd environment; requires the resource group rg-{environment}.')
@minLength(3)
@maxLength(32)
param environment string
@description('Provisional public-evidence region, not live capacity evidence.')
param location string = loadJsonContent('../00-region-availability.json').provisionalRegion
@description('Deployer/installer object ID, resolved only during authorized preparation.')
@minLength(36)
@maxLength(36)
param principalId string
@description('Foundation first, workload only after private image/fixture/agent installation.')
@allowed(['foundation', 'workload'])
param deploymentPhase string = 'foundation'
@description('Exact evidence-backed model.')
param modelName string = loadJsonContent('../00-region-availability.json').model.name
@description('Exact evidence-backed model version.')
param modelVersion string = loadJsonContent('../00-region-availability.json').model.version
@description('Exact evidence-backed deployment type.')
param modelSku string = loadJsonContent('../00-region-availability.json').model.sku
@description('Provisional capacity units; actual quota/capacity requires authorized checks.')
@minValue(1)
param modelCapacity int = 30
@description('Actual APIM publisher email, supplied for authorized workload deployment.')
param publisherEmail string = ''
@description('Dedicated secretless single-tenant backend Entra API application ID.')
param backendClientId string = ''
@description('Verified Foundry Agent Consumer built-in role GUID; no broader runtime fallback.')
param consumerRoleDefinitionId string = ''
@description('Immutable mobility-commercial image SHA-256 hex digest, without sha256 prefix.')
param imageDigest string = ''
@description('Installed Sales Fit agent version.')
param salesAgentVersion string = ''
@description('Installed Marketing Claims agent version.')
param marketingAgentVersion string = ''
@description('Installed Handoff Coordinator agent version.')
param coordinatorAgentVersion string = ''
@description('SHA-256 of the installed versioned fixture manifest.')
param fixtureManifestHash string = ''
@description('Installed immutable Key Vault key version; required only for the workload phase.')
param signingKeyVersion string = ''

@description('Generate the sole resource-group-derived suffix and pass it to every local module.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Length-bounded scenario/environment naming stem.')
var stem = 'mm-${take(toLower(environment), 8)}-${take(uniqueSuffix, 6)}'
@description('Standard tags for every tag-capable resource.')
var tags = {
  Environment: resourceGroup().name == 'rg-${environment}'
    ? environment
    : fail('Use the scenario-owned resource group rg-{environment}; review targets in the portal.')
  ManagedBy: 'Bicep'
  Project: 'manu-multi-agent'
  SecurityControl: 'Ignore'
}

resource groupTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: { tags: tags }
}

module network 'modules/network.bicep' = {
  name: 'network-${uniqueSuffix}'
  params: { location: location, uniqueSuffix: uniqueSuffix, stem: stem, tags: tags }
}
module appIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'app-identity-${uniqueSuffix}'
  params: {
    name: 'id-${stem}-app'
    location: location
    tags: tags
    enableTelemetry: false
  }
}
module gatewayIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'gateway-identity-${uniqueSuffix}'
  params: {
    name: 'id-${stem}-gateway'
    location: location
    tags: tags
    enableTelemetry: false
  }
}
module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs-${uniqueSuffix}'
  params: {
    name: 'log-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    skuName: 'PerGB2018'
    dataRetention: 30
    dailyQuotaGb: '1'
    forceCmkForQuery: false
  }
}
module dependencies 'modules/dependencies.bicep' = {
  name: 'dependencies-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    stem: stem
    tags: tags
    principalId: principalId
    appPrincipalId: appIdentity.outputs.principalId
    workspaceId: logs.outputs.resourceId
  }
}
module foundry 'modules/foundry.bicep' = {
  name: 'foundry-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    stem: stem
    tags: tags
    agentSubnetId: network.outputs.agentSubnetId
    modelName: modelName
    modelVersion: modelVersion
    modelSku: modelSku
    modelCapacity: modelCapacity
    principalId: principalId
    storageName: dependencies.outputs.platformStorageName
    blobEndpoint: dependencies.outputs.platformBlobEndpoint
    cosmosName: dependencies.outputs.cosmosName
    cosmosEndpoint: dependencies.outputs.cosmosEndpoint
    searchName: dependencies.outputs.searchName
  }
}
module privateLinks 'modules/private-links.bicep' = {
  name: 'private-links-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    tags: tags
    subnetId: network.outputs.endpointSubnetId
    vnetId: network.outputs.resourceId
    accountName: foundry.outputs.accountName
    platformStorageName: dependencies.outputs.platformStorageName
    businessStorageName: dependencies.outputs.businessStorageName
    cosmosName: dependencies.outputs.cosmosName
    searchName: dependencies.outputs.searchName
    vaultName: dependencies.outputs.vaultName
    registryName: dependencies.outputs.registryName
  }
}
module access 'modules/access.bicep' = {
  name: 'provisioning-access-${uniqueSuffix}'
  params: {
    uniqueSuffix: uniqueSuffix
    projectPrincipalId: foundry.outputs.principalId
    storageName: dependencies.outputs.platformStorageName
    cosmosName: dependencies.outputs.cosmosName
    searchName: dependencies.outputs.searchName
  }
}
module capability 'modules/capability.bicep' = {
  name: 'capability-${uniqueSuffix}'
  params: {
    uniqueSuffix: uniqueSuffix
    accountName: foundry.outputs.accountName
    projectName: foundry.outputs.resourceName
    projectPrincipalId: foundry.outputs.principalId
    workspaceId: foundry.outputs.workspaceId
    storageName: foundry.outputs.storageConnectionName
    cosmosName: foundry.outputs.cosmosConnectionName
    searchName: foundry.outputs.searchConnectionName
  }
  dependsOn: [access, privateLinks]
}
module appEnvironment 'br/public:avm/res/app/managed-environment:0.16.0' = {
  name: 'app-environment-${uniqueSuffix}'
  params: {
    name: 'cae-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    internal: true
    publicNetworkAccess: 'Disabled'
    infrastructureSubnetResourceId: network.outputs.appSubnetId
    infrastructureResourceGroupName: 'rg-${environment}-aca-${take(uniqueSuffix, 6)}'
    zoneRedundant: false
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: { destination: 'azure-monitor' }
    diagnosticSettings: [
      {
        workspaceResourceId: logs.outputs.resourceId
        logCategoriesAndGroups: [
          { category: 'ContainerAppConsoleLogs' }
          { category: 'ContainerAppSystemLogs' }
        ]
        metricCategories: [{ category: 'AllMetrics' }]
      }
    ]
  }
}
module appDns 'br/public:avm/res/network/private-dns-zone:0.8.1' = {
  name: 'app-dns-${uniqueSuffix}'
  params: {
    name: appEnvironment.outputs.defaultDomain
    tags: tags
    enableTelemetry: false
    virtualNetworkLinks: [
      {
        name: 'apps-${uniqueSuffix}'
        virtualNetworkResourceId: network.outputs.resourceId
        registrationEnabled: false
        tags: tags
      }
    ]
    a: [
      { name: '@', ttl: 60, aRecords: [{ ipv4Address: appEnvironment.outputs.staticIp! }] }
      { name: '*', ttl: 60, aRecords: [{ ipv4Address: appEnvironment.outputs.staticIp! }] }
    ]
  }
}
module workload 'modules/workload.bicep' = if (deploymentPhase == 'workload') {
  name: 'workload-${uniqueSuffix}'
  params: {
    location: location
    uniqueSuffix: uniqueSuffix
    stem: stem
    tags: tags
    environmentId: appEnvironment.outputs.resourceId
    apimSubnetId: network.outputs.apimSubnetId
    registryLoginServer: dependencies.outputs.registryLoginServer
    appIdentityId: appIdentity.outputs.resourceId
    appClientId: appIdentity.outputs.clientId
    appPrincipalId: appIdentity.outputs.principalId
    gatewayIdentityId: gatewayIdentity.outputs.resourceId
    gatewayClientId: gatewayIdentity.outputs.clientId
    gatewayPrincipalId: gatewayIdentity.outputs.principalId
    accountName: foundry.outputs.accountName
    projectName: foundry.outputs.resourceName
    projectEndpoint: foundry.outputs.projectEndpoint
    modelName: modelName
    blobEndpoint: dependencies.outputs.businessBlobEndpoint
    signingKeyUri: dependencies.outputs.signingKeyUri
    signingKeyVersion: signingKeyVersion
    publisherEmail: publisherEmail
    backendClientId: backendClientId
    consumerRoleDefinitionId: consumerRoleDefinitionId
    imageDigest: imageDigest
    salesAgentVersion: salesAgentVersion
    marketingAgentVersion: marketingAgentVersion
    coordinatorAgentVersion: coordinatorAgentVersion
    fixtureManifestHash: fixtureManifestHash
  }
  dependsOn: [capability, appDns]
}

@description('Resource group ID.')
output resourceId string = resourceGroup().id
@description('Resource group name.')
output resourceName string = resourceGroup().name
@description('Explicit target resource group for future azd operations.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name
@description('Registry resource name.')
output AZURE_CONTAINER_REGISTRY_NAME string = dependencies.outputs.registryName
@description('Private registry endpoint.')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = dependencies.outputs.registryLoginServer
@description('Internal Container Apps environment ID.')
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = appEnvironment.outputs.resourceId
@description('New project endpoint consumed by later application/installer.')
output AZURE_AI_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
@description('Foundry account name.')
output AZURE_AI_ACCOUNT_NAME string = foundry.outputs.accountName
@description('Exact model deployment name.')
output AZURE_AI_MODEL_DEPLOYMENT string = modelName
@description('Application user-assigned identity client ID.')
output AZURE_CLIENT_ID string = appIdentity.outputs.clientId
@description('Gateway identity object ID, required by backend authorization.')
output GATEWAY_PRINCIPAL_ID string = gatewayIdentity.outputs.principalId
@description('Private business fixture Blob endpoint.')
output FIXTURE_BLOB_ENDPOINT string = dependencies.outputs.businessBlobEndpoint
@description('Signing key URI, never key material.')
output SIGNING_KEY_URI string = dependencies.outputs.signingKeyUri
@description('Application resource name; null until workload phase.')
output AZURE_CONTAINER_APP_NAME string? = deploymentPhase == 'workload' ? workload!.outputs.resourceName : null
@description('Public gateway URL; null until workload phase, never a fabricated endpoint.')
output APP_PUBLIC_URL string? = deploymentPhase == 'workload' ? workload!.outputs.gatewayUrl : null
