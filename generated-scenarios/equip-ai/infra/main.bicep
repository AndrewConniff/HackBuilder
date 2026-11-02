targetScope = 'resourceGroup'

@description('Distinct azd environment; equip-ai for the reference, never a shared environment.')
@minLength(3)
@maxLength(28)
param environment string

@description('Region selected from 00-region-availability.json after authorized capacity checks.')
param location string

@description('Deploying user object ID; azd supplies AZURE_PRINCIPAL_ID.')
param principalId string

@description('Foundry Agent Consumer built-in role ID, resolved and verified during authorized preparation.')
param agentConsumerRoleId string
@description('Foundry Project Runtime User built-in role ID, verified for the app Responses API calls.')
param agentRuntimeRoleId string

@description('Foundry agent installer role ID, resolved and verified during authorized preparation.')
param agentInstallerRoleId string

@description('Model name from the dated region/model evidence.')
param modelName string

@description('Exact model version from the dated region/model evidence.')
param modelVersion string

@description('Model deployment name consumed by agent installation.')
param modelDeploymentName string

@description('Model deployment SKU from the confirmed design/evidence.')
param modelSku string

@description('Model deployment capacity; verify actual quota before deployment.')
@minValue(1)
param modelCapacity int = 10
@description('Restore only this same-target soft-deleted Foundry account, as observed by the authorized preprovision hook.')
param restoreFoundry bool = false

@description('Scenario-only VNet CIDR; confirm no conflicting network before deployment.')
param vnetPrefix string

@description('App Service integration subnet CIDR, inside vnetPrefix.')
param integrationPrefix string

@description('Private endpoint subnet CIDR, inside vnetPrefix.')
param endpointPrefix string

@description('New management scope: enable only after the consolidated scope/cost approval.')
param enableManagement bool = false
@description('Scenario management subnet; validate /27 availability before enabling.')
param managementPrefix string = '10.247.0.128/27'
@description('Locally generated SSH public key; VM exposes no SSH endpoint.')
param managementPublicKey string = ''
@description('Approved Bastion and desktop scope; false until explicit human-access review approval.')
param enableHumanManagement bool = false
@description('Dedicated Bastion /26 subnet verified free inside the existing VNet.')
param bastionPrefix string = '10.247.0.192/26'

@description('One suffix reused for globally unique names.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Required resource tags.')
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'equip-ai'
  SecurityControl: 'Ignore'
}
@description('Short environment label for constrained Azure resource names.')
var shortEnv = take(replace(environment, '-', ''), 7)
@description('Unique Storage account name, at most 24 lowercase alphanumerics.')
var storageName = 'stequip${shortEnv}${take(uniqueSuffix, 8)}'
@description('Unique Foundry account name.')
var foundryName = 'ai-equip-${shortEnv}-${take(uniqueSuffix, 6)}'
@description('Direct child project name.')
var projectName = 'equipment-operations'
@description('Stable names independent of generated identity outputs or default hostnames.')
var appNames = [
  'app-equip-web-${shortEnv}-${take(uniqueSuffix, 6)}'
  'app-equip-cleaner-${shortEnv}-${take(uniqueSuffix, 6)}'
]
@description('Shared sanitized diagnostics; metrics only to avoid captured payloads.')
var metrics = [
  {
    workspaceResourceId: workspace.outputs.resourceId
    metricCategories: [
      { category: 'AllMetrics' }
    ]
  }
]

@description('Common keyless runtime settings; identity configuration is applied after site creation.')
var runtimeSettings = {
  StorageEndpoint: 'https://${storageName}.blob.${az.environment().suffixes.storage}'
  AZURE_AI_PROJECT_ENDPOINT: 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
  AgentName: 'equipment-operations'
  AZURE_MODEL_DEPLOYMENT_NAME: modelDeploymentName
  APPLICATIONINSIGHTS_CONNECTION_STRING: insights.outputs.connectionString
  WEBSITE_RUN_FROM_PACKAGE: '1'
  WEBSITE_WARMUP_PATH: '/health'
  WEBSITES_CONTAINER_START_TIME_LIMIT: '600'
}

resource rgTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: { tags: tags }
}

module workspace 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'monitoring'
  params: {
    name: 'log-equip-${environment}'
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
    dailyQuotaGb: '1'
    enableTelemetry: false
  }
}

module insights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'insights'
  params: {
    name: 'appi-equip-${environment}'
    location: location
    tags: tags
    workspaceResourceId: workspace.outputs.resourceId
    enableTelemetry: false
  }
}

module managementNetwork 'modules/management-network.bicep' = if (enableManagement) {
  name: 'management-network'
  params: {
    location: location
    environment: environment
    tags: tags
    enableHumanManagement: enableHumanManagement
    bastionPrefix: bastionPrefix
  }
}

module network 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network'
  params: {
    name: 'vnet-equip-${environment}'
    location: location
    tags: tags
    addressPrefixes: [vnetPrefix]
    subnets: concat([
      {
        name: 'integration'
        addressPrefix: integrationPrefix
        delegation: 'Microsoft.Web/serverFarms'
      }
      {
        name: 'endpoints'
        addressPrefix: endpointPrefix
        privateEndpointNetworkPolicies: 'Disabled'
      }
    ], enableManagement ? [
      {
        name: 'management'
        addressPrefix: managementPrefix
        defaultOutboundAccess: false
        natGatewayResourceId: managementNetwork!.outputs.natId
        networkSecurityGroupResourceId: managementNetwork!.outputs.nsgId
      }
    ] : [], enableHumanManagement ? [
      {
        name: 'AzureBastionSubnet'
        addressPrefix: bastionPrefix
      }
    ] : [])
    enableTelemetry: false
  }
}

module dns 'br/public:avm/res/network/private-dns-zone:0.8.1' = [for zone in [
  'privatelink.blob.${az.environment().suffixes.storage}'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.azurewebsites.net'
]: {
  name: 'dns-${uniqueString(zone)}'
  params: {
    name: zone
    tags: tags
    virtualNetworkLinks: [
      { virtualNetworkResourceId: network.outputs.resourceId, registrationEnabled: false }
    ]
    enableTelemetry: false
  }
}]

module management 'management.bicep' = if (enableManagement) {
  name: 'management-host'
  dependsOn: [network, apps, project]
  params: {
    environment: environment
    location: location
    adminPublicKey: managementPublicKey
    agentInstallerRoleId: agentInstallerRoleId
  }
}

module humanAccess 'modules/human-access.bicep' = if (enableHumanManagement) {
  name: 'human-management-access'
  params: {
    environment: environment
    location: location
    tags: tags
    vnetResourceId: network.outputs.resourceId
  }
}

module routeIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'iot-route-identity'
  params: {
    name: 'id-equip-iot-${environment}'
    location: location
    tags: tags
    enableTelemetry: false
  }
}

module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'telemetry-storage'
  params: {
    name: storageName
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
    blobServices: {
      deleteRetentionPolicyEnabled: false
      containerDeleteRetentionPolicyEnabled: false
      isVersioningEnabled: false
      containers: [
        { name: 'telemetry', publicAccess: 'None' }
        { name: 'accounts', publicAccess: 'None' }
      ]
    }
    diagnosticSettings: metrics
    privateEndpoints: [
      {
        name: 'pe-equip-blob-${environment}'
        service: 'blob'
        subnetResourceId: '${network.outputs.resourceId}/subnets/endpoints'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            { privateDnsZoneResourceId: dns[0].outputs.resourceId }
          ]
        }
      }
    ]
    enableTelemetry: false
  }
}

module routeAccess 'modules/blob-access.bicep' = {
  name: 'iot-container-access'
  dependsOn: [storage]
  params: {
    storageName: storageName
    assignments: [
      {
        principalId: routeIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
      }
    ]
  }
}

module hub 'br/public:avm/res/devices/iot-hub:0.4.0' = {
  name: 'certified-ingress'
  dependsOn: [routeAccess]
  params: {
    name: 'iot-equip-${shortEnv}-${take(uniqueSuffix, 6)}'
    location: location
    tags: tags
    skuName: 'B2'
    skuCapacity: 1
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
    disableDeviceSAS: true
    disableModuleSAS: true
    roleAssignments: empty(principalId) ? [] : concat([
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: '4ea46cd5-c1b2-4a8e-910b-273211f9ce47'
      }
    ], enableHumanManagement ? [
      {
        name: guid(resourceId('Microsoft.Devices/IotHubs', 'iot-equip-${shortEnv}-${take(uniqueSuffix, 6)}'), principalId, 'human-data-administrator')
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: '4fc6c259-987e-4a07-842e-c321cc9d413f'
      }
    ] : [])
    minTlsVersion: '1.2'
    restrictOutboundNetworkAccess: true
    allowedFqdnList: ['${storageName}.blob.${az.environment().suffixes.storage}']
    managedIdentities: { userAssignedResourceIds: [routeIdentity.outputs.resourceId] }
    eventHubEndpoints: { events: { partitionCount: 4, retentionTimeInDays: 1 } }
    routing: {
      endpoints: {
        storageContainers: [
          {
            name: 'volatile-blob'
            endpointUri: 'https://${storageName}.blob.${az.environment().suffixes.storage}'
            containerName: 'telemetry'
            authenticationType: 'identityBased'
            identity: { userAssignedIdentity: routeIdentity.outputs.resourceId }
            encoding: 'JSON'
            batchFrequencyInSeconds: 60
            maxChunkSizeInBytes: 10485760
            fileNameFormat: '{YYYY}/{MM}/{DD}/{HH}/{mm}/{iothub}/{partition}'
          }
        ]
      }
      routes: [
        {
          name: 'all-certified-telemetry'
          source: 'DeviceMessages'
          condition: 'true'
          endpointNames: ['volatile-blob']
          isEnabled: true
        }
      ]
      fallbackRoute: { name: '$fallback', source: 'DeviceMessages', endpointNames: ['events'], isEnabled: false }
    }
    diagnosticSettings: metrics
    enableTelemetry: false
  }
}

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry-account'
  params: {
    name: foundryName
    location: location
    tags: tags
    kind: 'AIServices'
    restore: restoreFoundry
    sku: 'S0'
    customSubDomainName: foundryName
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    restrictOutboundNetworkAccess: true
    managedIdentities: { systemAssigned: true }
    deployments: [
      {
        name: modelDeploymentName
        model: { format: 'OpenAI', name: modelName, version: modelVersion }
        sku: { name: modelSku, capacity: modelCapacity }
      }
    ]
    diagnosticSettings: metrics
    privateEndpoints: [
      {
        name: 'pe-equip-foundry-${environment}'
        subnetResourceId: '${network.outputs.resourceId}/subnets/endpoints'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            for i in range(1, 3): { privateDnsZoneResourceId: dns[i].outputs.resourceId }
          ]
        }
      }
    ]
    enableTelemetry: false
  }
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  dependsOn: [foundry]
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: { displayName: 'Adatum Corporation equipment Operations', description: 'Bounded telemetry read tools' }
}

module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'hosting-plan'
  params: {
    name: 'asp-equip-${environment}'
    location: location
    tags: tags
    kind: 'linux'
    reserved: true
    skuName: 'B2'
    skuCapacity: 1
    zoneRedundant: false
    enableTelemetry: false
  }
}

module apps 'br/public:avm/res/web/site:0.24.0' = [for (role, index) in ['web', 'cleaner']: {
  name: 'app-${role}'
  params: {
    name: appNames[index]
    location: location
    tags: union(tags, { 'azd-service-name': role })
    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId
    managedIdentities: { systemAssigned: true }
    publicNetworkAccess: role == 'web' ? 'Enabled' : 'Disabled'
    httpsOnly: true
    virtualNetworkSubnetResourceId: '${network.outputs.resourceId}/subnets/integration'
    siteConfig: {
      alwaysOn: true
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
      linuxFxVersion: 'DOTNETCORE|10.0'
      appCommandLine: 'dotnet EquipAI.Web.dll'
    }
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
    configs: [
      {
        name: 'logs'
        properties: { applicationLogs: { fileSystem: { level: 'Information' } } }
      }
    ]
    diagnosticSettings: [
      {
        workspaceResourceId: workspace.outputs.resourceId
        logCategoriesAndGroups: [{ category: 'AppServiceConsoleLogs' }]
        metricCategories: [{ category: 'AllMetrics' }]
      }
    ]
    enableTelemetry: false
  }
}]

  module runtimeConfiguration 'modules/app-settings.bicep' = {
    name: 'runtime-configuration'
    params: {
      webName: apps[0].outputs.name
      cleanerName: apps[1].outputs.name
      settings: runtimeSettings
    }
  }

  module cleanerEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = {
    name: 'cleaner-private-endpoint'
    dependsOn: [apps, network, dns]
    params: {
      name: 'pe-equip-cleaner-${environment}'
      location: location
      tags: tags
      subnetResourceId: resourceId('Microsoft.Network/virtualNetworks/subnets', 'vnet-equip-${environment}', 'endpoints')
      privateLinkServiceConnections: [
        {
          name: 'cleaner'
          properties: {
            privateLinkServiceId: resourceId('Microsoft.Web/sites', appNames[1])
            groupIds: ['sites']
          }
        }
      ]
      privateDnsZoneGroup: {
        privateDnsZoneGroupConfigs: [
          { privateDnsZoneResourceId: resourceId('Microsoft.Network/privateDnsZones', 'privatelink.azurewebsites.net') }
        ]
      }
      enableTelemetry: false
    }
  }

resource cleanerRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, 'equip-ai-expired-blob-cleaner')
  properties: {
    roleName: 'equip-ai-expired-blob-cleaner-${take(uniqueSuffix, 6)}'
    description: 'Read and delete volatile telemetry without blob creation or modification.'
    type: 'CustomRole'
    assignableScopes: [resourceGroup().id]
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'
        ]
        notDataActions: []
      }
    ]
  }
}

module appBlobAccess 'modules/blob-access.bicep' = {
  name: 'application-container-access'
  params: {
    storageName: storage.outputs.name
    assignments: concat([
      {
        principalId: apps[0].outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
        roleId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
      }
      {
        principalId: apps[1].outputs.systemAssignedMIPrincipalId!
        principalType: 'ServicePrincipal'
        roleId: cleanerRole.id
      }
    ], empty(principalId) ? [] : [
      {
        principalId: principalId
        principalType: 'User'
        roleId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
      }
    ])
  }
}

module agentAccess 'modules/foundry-access.bicep' = {
  name: 'project-access'
  params: {
    accountName: account.name
    projectName: project.name
    consumerId: apps[0].outputs.systemAssignedMIPrincipalId!
    installerId: principalId
    consumerRoleId: agentConsumerRoleId
    runtimeRoleId: agentRuntimeRoleId
    installerRoleId: agentInstallerRoleId
    projectPrincipalId: project.identity.principalId!
  }
}

module accountAccess 'modules/blob-access.bicep' = {
    name: 'local-account-container-access'
    params: {
      storageName: storage.outputs.name
      containerName: 'accounts'
      assignments: concat([
        {
          principalId: apps[0].outputs.systemAssignedMIPrincipalId!
          principalType: 'ServicePrincipal'
          roleId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
        }
      ], enableManagement ? [
        {
          principalId: management!.outputs.MANAGEMENT_PRINCIPAL_ID
          principalType: 'ServicePrincipal'
          roleId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
        }
      ] : [], empty(principalId) ? [] : [
        {
          principalId: principalId
          principalType: 'User'
          roleId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
        }
      ])
  }
}

@description('Actual web app resource name for azd.')
output AZURE_WEB_NAME string = apps[0].outputs.name
@description('Actual web resource ID consumed by exact redirect verification.')
output AZURE_WEB_RESOURCE_ID string = apps[0].outputs.resourceId
@description('Actual cleanup app resource name for azd.')
output AZURE_CLEANER_NAME string = apps[1].outputs.name
@description('Generated cleaner HTTPS hostname; reachable only through the private endpoint.')
output CLEANER_URL string = 'https://${apps[1].outputs.defaultHostname}'
@description('Generated cleaner private endpoint ID for installation connectivity verification.')
output CLEANER_PRIVATE_ENDPOINT_ID string = cleanerEndpoint.outputs.resourceId
@description('Deployed HTTPS URL; exists only after authorized provisioning.')
output APPLICATION_URL string = 'https://${apps[0].outputs.defaultHostname}'
@description('Direct child Foundry project endpoint.')
output AZURE_AI_PROJECT_ENDPOINT string = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
@description('Configured model deployment.')
output AZURE_MODEL_DEPLOYMENT_NAME string = modelDeploymentName
@description('IoT hub resource name.')
output IOT_HUB_NAME string = hub.outputs.name
@description('Telemetry Storage account name.')
output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
