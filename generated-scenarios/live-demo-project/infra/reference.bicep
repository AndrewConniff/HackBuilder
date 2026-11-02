@description('Scenario environment.')
param environment string
@description('Reviewed common region.')
param location string
@description('Deploying human principal.')
param principalId string
@description('Verified built-in consumer role ID.')
param consumerRoleId string
@description('Create human role grants when verified inherited administration and data access are absent.')
param assignDeployerRoles bool
@description('Model name.')
param modelName string
@description('Model version.')
param modelVersion string
@description('Model deployment SKU.')
param modelSku string
@description('Model deployment capacity.')
param modelCapacity int
@secure()
@description('Management VM password.')
param managementPassword string
@description('Required resource tags.')
param tags object

@description('Single stable globally unique suffix derived from this resource group.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Compact environment prefix.')
var prefix = '${take(environment, 18)}-${take(uniqueSuffix, 6)}'
@description('Foundry resource name.')
var foundryName = 'ai-${prefix}'
@description('Foundry child project name.')
var projectName = 'brokerage'
@description('Private project runtime endpoint.')
var foundryProjectEndpoint = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
@description('Foundry User built-in role.')
var foundryUserRole = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs'
  params: {
    name: 'log-${prefix}'
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
  }
}

module network 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network'
  params: {
    name: 'vnet-${prefix}'
    location: location
    tags: tags
    addressPrefixes: ['10.84.0.0/16']
    subnets: [
      {
        name: 'app'
        addressPrefix: '10.84.0.0/24'
        delegation: 'Microsoft.Web/serverFarms'
      }
      {
        name: 'private'
        addressPrefix: '10.84.1.0/24'
        privateEndpointNetworkPolicies: 'Disabled'
      }
      {
        name: 'management'
        addressPrefix: '10.84.2.0/24'
        networkSecurityGroupResourceId: managementNsg.outputs.resourceId
        defaultOutboundAccess: true
      }
      {
        name: 'AzureBastionSubnet'
        addressPrefix: '10.84.3.0/26'
      }
    ]
  }
}

module managementNsg 'br/public:avm/res/network/network-security-group:0.5.4' = {
  name: 'management-nsg'
  params: {
    name: 'nsg-${prefix}'
    location: location
    tags: tags
    securityRules: [
      {
        name: 'BastionRdp'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3389'
          sourceAddressPrefix: '10.84.3.0/26'
          destinationAddressPrefix: '10.84.2.0/24'
        }
      }
      {
        name: 'DenyOtherInbound'
        properties: {
          priority: 200
          direction: 'Inbound'
          access: 'Deny'
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

module dns 'br/public:avm/res/network/private-dns-zone:0.8.1' = [for name in [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
]: {
  name: 'dns-${uniqueString(name)}'
  params: {
    name: name
    tags: tags
    virtualNetworkLinks: [
      {
        name: 'scenario'
        virtualNetworkResourceId: network.outputs.resourceId
        registrationEnabled: false
      }
    ]
  }
}]

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: foundryName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: 'S0'
    allowProjectManagement: true
    customSubDomainName: foundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    restrictOutboundNetworkAccess: true
    managedIdentities: { systemAssigned: true }
    deployments: [
      {
        name: 'company-selector'
        model: {
          format: 'OpenAI'
          name: modelName
          version: modelVersion
        }
        sku: {
          name: modelSku
          capacity: modelCapacity
        }
      }
    ]
    roleAssignments: assignDeployerRoles ? [
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: foundryUserRole
      }
    ] : []
    diagnosticSettings: [
      {
        name: 'scenario'
        workspaceResourceId: logs.outputs.resourceId
      }
    ]
  }
}

@description('Existing parent exported by AVM; direct child project has no standalone AVM module.')
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}
@description('Current Foundry direct child project; not a legacy ML workspace.')
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: { displayName: 'Adatum Corporation service desk' }
  dependsOn: [foundry]
}

module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.12.1' = {
  name: 'private-endpoint'
  params: {
    name: 'pe-${prefix}'
    location: location
    tags: tags
    subnetResourceId: network.outputs.subnetResourceIds[1]
    privateLinkServiceConnections: [
      {
        name: 'foundry'
        properties: {
          privateLinkServiceId: foundry.outputs.resourceId
          groupIds: ['account']
        }
      }
    ]
    privateDnsZoneGroup: {
      name: 'default'
      privateDnsZoneGroupConfigs: [
        for (name, index) in [
          'cognitive'
          'openai'
          'services'
        ]: {
          name: name
          privateDnsZoneResourceId: dns[index].outputs.resourceId
        }
      ]
    }
  }
}

module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'hosting'
  params: {
    name: 'asp-${prefix}'
    location: location
    tags: tags
    skuName: 'B2'
    skuCapacity: 1
    kind: 'linux'
    reserved: true
  }
}

module web 'br/public:avm/res/web/site:0.24.0' = {
  name: 'web'
  params: {
    name: 'app-${prefix}'
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    kind: 'app,linux'
    serverFarmResourceId: plan.outputs.resourceId
    publicNetworkAccess: 'Enabled'
    managedIdentities: { systemAssigned: true }
    virtualNetworkSubnetResourceId: network.outputs.subnetResourceIds[0]
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'DataPath'
          value: '/home/data/brokerage'
        }
        {
          name: 'PrivateAccessPath'
          value: '/home/data/.private'
        }
        {
          name: 'Foundry__ProjectEndpoint'
          value: foundryProjectEndpoint
        }
        {
          name: 'Foundry__AgentName'
          value: 'brokerage-company-selector'
        }
        {
          name: 'BootstrapAccounts'
          value: 'true'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
      ]
    }
    basicPublishingCredentialsPolicies: [
      {
        name: 'ftp'
        allow: false
      }
      {
        name: 'scm'
        allow: false
      }
    ]
    diagnosticSettings: [
      {
        name: 'scenario'
        workspaceResourceId: logs.outputs.resourceId
      }
    ]
  }
}

module management 'br/public:avm/res/compute/virtual-machine:0.22.3' = {
  name: 'management'
  params: {
    name: 'vm-${prefix}'
    computerName: 'brokerage-admin'
    location: location
    tags: tags
    vmSize: 'Standard_D2s_v5'
    availabilityZone: 1
    osType: 'Windows'
    imageReference: {
      publisher: 'MicrosoftWindowsServer'
      offer: 'WindowsServer'
      sku: '2022-datacenter-azure-edition'
      version: 'latest'
    }
    adminUsername: 'scenarioadmin'
    adminPassword: managementPassword
    osDisk: {
      diskSizeGB: 128
      managedDisk: {
        storageAccountType: 'StandardSSD_LRS'
      }
    }
    nicConfigurations: [
      {
        ipConfigurations: [
          {
            name: 'private'
            subnetResourceId: network.outputs.subnetResourceIds[2]
          }
        ]
      }
    ]
    managedIdentities: { systemAssigned: true }
    securityType: 'TrustedLaunch'
    secureBootEnabled: true
    vTpmEnabled: true
  }
}

module bastion 'br/public:avm/res/network/bastion-host:0.8.2' = {
  name: 'bastion'
  params: {
    name: 'bas-${prefix}'
    location: location
    tags: tags
    virtualNetworkResourceId: network.outputs.resourceId
    skuName: 'Basic'
    enableFileCopy: false
    diagnosticSettings: [
      {
        name: 'scenario'
        workspaceResourceId: logs.outputs.resourceId
      }
    ]
  }
}

@description('Full scenario administration for the human deployment user, never the app identity.')
resource administrator 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignDeployerRoles) {
  name: guid(resourceGroup().id, principalId, 'owner')
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8e3af657-a8ff-443c-a75c-2fe8c4bcb635')
  }
}

@description('Runtime app consumer access, scoped only to this project.')
resource appConsumer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, 'web-consumer', consumerRoleId)
  scope: project
  properties: {
    principalId: web.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', consumerRoleId)
  }
}

@description('Private installer can author this project, not administer the subscription.')
resource installer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, 'management-installer', foundryUserRole)
  scope: project
  properties: {
    principalId: management.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRole)
  }
}

@description('Project service identity can use its own parent account.')
resource projectUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, projectName, foundryUserRole)
  scope: account
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRole)
  }
}

@description('Customer app URL; real reachability is checked after deployment.')
output applicationUrl string = 'https://${web.outputs.defaultHostname}'
@description('Private Foundry project endpoint.')
output projectEndpoint string = foundryProjectEndpoint
@description('Private Windows desktop and installer host.')
output managementVmName string = management.outputs.name
@description('App Service name.')
output webName string = web.outputs.name
