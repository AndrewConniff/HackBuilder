@description('Explicit reviewed deployment region.')
param location string
@description('Mandatory scenario resource tags.')
param tags object
@description('Actual deploying human administrator object ID.')
param principalId string
@description('Private Windows local administrator username.')
param managementUsername string
@description('Reviewed private operator VM size; passed explicitly from the subscription entry point.')
param managementVmSize string
@description('Whether effective inherited human control-plane administration has been verified.')
param reuseAdminControlAccess bool
@description('Whether effective inherited human Foundry administration/data access has been verified.')
param reuseAdminFoundryAccess bool
@secure()
@description('Unique private Windows local administrator password.')
param managementPassword string
@description('Reviewed configurable model.')
param modelName string
@description('Reviewed configurable model version.')
param modelVersion string
@description('Reviewed model deployment type.')
param modelDeploymentType string
@description('Reviewed model quota capacity.')
param modelCapacity int

@description('Single suffix shared by globally unique resource names.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Short scenario resource stem.')
var stem = 'woodgrove-${take(uniqueSuffix, 8)}'
@description('Foundry resource name, also used as its custom subdomain.')
var foundryName = 'ai-${stem}'
@description('Direct project endpoint; contains no credential.')
var derivedProjectEndpoint = 'https://${foundryName}.services.ai.azure.com/api/projects/retail'
@description('Required endpoint DNS zones, confirmed against current official Foundry Basic sample.')
var zones = [
  'privatelink.services.ai.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.table.${environment().suffixes.storage}'
  'privatelink.blob.${environment().suffixes.storage}'
]

module workspace 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs'
  params: {
    name: 'log-${stem}'
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
    dailyQuotaGb: '1'
    enableTelemetry: false
  }
}

module insights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'telemetry'
  params: {
    name: 'appi-${stem}'
    location: location
    tags: tags
    workspaceResourceId: workspace.outputs.resourceId
    applicationType: 'web'
    enableTelemetry: false
  }
}

module managementNsg 'br/public:avm/res/network/network-security-group:0.5.4' = {
  name: 'management-ingress'
  params: {
    name: 'nsg-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    securityRules: [
      {
        name: 'BastionRdpSshOnly'
        properties: {
          priority: 100
          access: 'Allow'
          direction: 'Inbound'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRanges: ['22', '3389']
          sourceAddressPrefix: '10.42.3.0/26'
          destinationAddressPrefix: '10.42.2.0/24'
        }
      }
      {
        name: 'DenyOtherInbound'
        properties: {
          priority: 200
          access: 'Deny'
          direction: 'Inbound'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

module natIp 'br/public:avm/res/network/public-ip-address:0.13.0' = {
  name: 'management-egress-ip'
  params: {
    name: 'pip-egress-${stem}'
    location: location
    tags: tags
    skuName: 'Standard'
    publicIPAllocationMethod: 'Static'
    enableTelemetry: false
  }
}

module nat 'br/public:avm/res/network/nat-gateway:2.1.1' = {
  name: 'explicit-management-egress'
  params: {
    name: 'nat-${stem}'
    location: location
    tags: tags
    availabilityZone: -1
    natGatewaySku: 'Standard'
    publicIpResourceIds: [natIp.outputs.resourceId]
    enableTelemetry: false
  }
}

module network 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network'
  params: {
    name: 'vnet-${stem}'
    location: location
    tags: tags
    addressPrefixes: ['10.42.0.0/16']
    enableTelemetry: false
    subnets: [
      {
        name: 'app'
        addressPrefix: '10.42.0.0/26'
        delegation: 'Microsoft.Web/serverFarms'
      }
      {
        name: 'endpoints'
        addressPrefix: '10.42.1.0/24'
        privateEndpointNetworkPolicies: 'Disabled'
      }
      {
        name: 'management'
        addressPrefix: '10.42.2.0/24'
        defaultOutboundAccess: false
        natGatewayResourceId: nat.outputs.resourceId
        networkSecurityGroupResourceId: managementNsg.outputs.resourceId
      }
      {
        name: 'AzureBastionSubnet'
        addressPrefix: '10.42.3.0/26'
      }
    ]
  }
}

module dns 'br/public:avm/res/network/private-dns-zone:0.8.1' = [for zone in zones: {
  name: 'dns-${uniqueString(zone)}'
  params: {
    name: zone
    tags: tags
    enableTelemetry: false
    virtualNetworkLinks: [
      {
        name: 'scenario-network'
        virtualNetworkResourceId: network.outputs.resourceId
        registrationEnabled: false
      }
    ]
  }
}]

module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'business-state'
  params: {
    name: 'stwoodgrove${take(uniqueSuffix, 10)}'
    location: location
    tags: tags
    skuName: 'Standard_LRS'
    kind: 'StorageV2'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Disabled'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    defaultToOAuthAuthentication: true
    enableTelemetry: false
    tableServices: {
      tables: [
        { name: 'Commerce' }
        { name: 'Accounts' }
      ]
    }
    blobServices: {
      containers: [
        { name: 'session-keys' }
      ]
    }
    privateEndpoints: [
      {
        name: 'pe-table-${stem}'
        service: 'table'
        subnetResourceId: '${network.outputs.resourceId}/subnets/endpoints'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            { privateDnsZoneResourceId: dns[3].outputs.resourceId }
          ]
        }
      }
      {
        name: 'pe-blob-${stem}'
        service: 'blob'
        subnetResourceId: '${network.outputs.resourceId}/subnets/endpoints'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            { privateDnsZoneResourceId: dns[4].outputs.resourceId }
          ]
        }
      }
    ]
  }
}

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry-account'
  params: {
    name: foundryName
    customSubDomainName: foundryName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: 'S0'
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    restrictOutboundNetworkAccess: false
    managedIdentities: { systemAssigned: true }
    enableTelemetry: false
    deployments: [
      {
        name: 'retail-reasoning'
        model: {
          name: modelName
          version: modelVersion
          format: 'OpenAI'
        }
        sku: {
          name: modelDeploymentType
          capacity: modelCapacity
        }
      }
    ]
  }
}

@description('Existing parent declaration for the direct project; no AVM project module is exposed by account 0.19.1.')
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

@description('Current direct child Foundry project; no hub resources are created.')
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundryAccount
  name: 'retail'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {}
  dependsOn: [foundry]
}

module foundryEndpoint 'br/public:avm/res/network/private-endpoint:0.12.1' = {
  name: 'foundry-private-access'
  params: {
    name: 'pe-foundry-${stem}'
    location: location
    tags: tags
    subnetResourceId: '${network.outputs.resourceId}/subnets/endpoints'
    enableTelemetry: false
    privateLinkServiceConnections: [
      {
        name: 'foundry-account'
        properties: {
          privateLinkServiceId: foundry.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        { privateDnsZoneResourceId: dns[0].outputs.resourceId }
        { privateDnsZoneResourceId: dns[1].outputs.resourceId }
        { privateDnsZoneResourceId: dns[2].outputs.resourceId }
      ]
    }
  }
  dependsOn: [project]
}

module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'linux-plan'
  params: {
    name: 'asp-${stem}'
    location: location
    tags: tags
    skuName: 'B1'
    skuCapacity: 1
    kind: 'linux'
    reserved: true
    zoneRedundant: false
    enableTelemetry: false
  }
}

module web 'br/public:avm/res/web/site:0.24.0' = {
  name: 'grocery-console'
  params: {
    name: 'app-${stem}'
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId
    managedIdentities: { systemAssigned: true }
    publicNetworkAccess: 'Enabled'
    httpsOnly: true
    virtualNetworkSubnetResourceId: '${network.outputs.resourceId}/subnets/app'
    enableTelemetry: false
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      http20Enabled: true
      appSettings: [
        { name: 'StorageTableEndpoint', value: 'https://${storage.outputs.name}.table.${environment().suffixes.storage}/' }
        { name: 'StorageBlobEndpoint', value: 'https://${storage.outputs.name}.blob.${environment().suffixes.storage}/' }
        { name: 'FoundryProjectEndpoint', value: derivedProjectEndpoint }
        { name: 'FoundryModelDeployment', value: 'retail-reasoning' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.outputs.connectionString }
        { name: 'ASPNETCORE_FORWARDEDHEADERS_ENABLED', value: 'true' }
      ]
    }
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
  }
}

module bastionIp 'br/public:avm/res/network/public-ip-address:0.13.0' = {
  name: 'bastion-ip'
  params: {
    name: 'pip-bastion-${stem}'
    location: location
    tags: tags
    skuName: 'Standard'
    publicIPAllocationMethod: 'Static'
    enableTelemetry: false
  }
}

module bastion 'br/public:avm/res/network/bastion-host:0.8.2' = {
  name: 'operator-entry'
  params: {
    name: 'bas-${stem}'
    location: location
    tags: tags
    virtualNetworkResourceId: network.outputs.resourceId
    bastionSubnetPublicIpResourceId: bastionIp.outputs.resourceId
    skuName: 'Standard'
    enableFileCopy: true
    enableTelemetry: false
  }
}

module management 'br/public:avm/res/compute/virtual-machine:0.22.3' = {
  name: 'private-operator-host'
  params: {
    name: 'vm-${stem}'
    computerName: 'retailoperator'
    location: location
    tags: tags
    vmSize: managementVmSize
    availabilityZone: -1
    osType: 'Windows'
    adminUsername: managementUsername
    adminPassword: managementPassword
    imageReference: {
      publisher: 'MicrosoftWindowsServer'
      offer: 'WindowsServer'
      sku: '2022-datacenter-g2'
      version: 'latest'
    }
    osDisk: {
      createOption: 'FromImage'
      deleteOption: 'Delete'
      managedDisk: { storageAccountType: 'StandardSSD_LRS' }
    }
    nicConfigurations: [
      {
        name: 'nic-${stem}'
        ipConfigurations: [
          {
            name: 'private'
            subnetResourceId: '${network.outputs.resourceId}/subnets/management'
          }
        ]
      }
    ]
    managedIdentities: { systemAssigned: true }
    enableTelemetry: false
  }
}

module roles 'roles.bicep' = {
  name: 'explicit-data-and-operator-access'
  params: {
    adminId: principalId
    reuseAdminControlAccess: reuseAdminControlAccess
    reuseAdminFoundryAccess: reuseAdminFoundryAccess
    appId: web.outputs.systemAssignedMIPrincipalId!
    automationId: management.outputs.systemAssignedMIPrincipalId!
    storageName: storage.outputs.name
    foundryName: foundry.outputs.name
  }
  dependsOn: [project]
}

@description('App URL; requires installation, publishing and acceptance before claiming it works.')
output applicationUrl string = 'https://${web.outputs.defaultHostname}'
@description('App resource name.')
output webName string = web.outputs.name
@description('Provisioned direct-project endpoint.')
output projectEndpoint string = derivedProjectEndpoint
@description('Provisioned private Table endpoint.')
output tableEndpoint string = 'https://${storage.outputs.name}.table.${environment().suffixes.storage}/'
@description('Provisioned private Blob endpoint.')
output blobEndpoint string = 'https://${storage.outputs.name}.blob.${environment().suffixes.storage}/'
@description('Management VM name.')
output vmName string = management.outputs.name
@description('Management VM resource ID.')
output vmId string = management.outputs.resourceId
@description('Bastion entry resource name.')
output bastionName string = bastion.outputs.name
