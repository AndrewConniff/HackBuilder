@description('Provisional region; must match authorized region at deployment.')
param location string
@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Short scenario/environment name stem.')
param stem string
@description('Standard resource tags.')
param tags object

@description('Subnet purposes in output order.')
var purposes = ['apps', 'agents', 'apim', 'endpoints']

module nsg 'br/public:avm/res/network/network-security-group:0.5.4' = [for purpose in purposes: {
  name: 'nsg-${purpose}-${uniqueSuffix}'
  params: {
    name: 'nsg-${stem}-${purpose}'
    location: location
    tags: tags
    enableTelemetry: false
    securityRules: purpose == 'apim' ? [
      {
        name: 'AllowKeyVaultDependency'
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
      }
    ] : []
  }
}]

module vnet 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network-${uniqueSuffix}'
  params: {
    name: 'vnet-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    addressPrefixes: ['10.84.0.0/16']
    subnets: [
      {
        name: 'apps'
        addressPrefix: '10.84.0.0/23'
        delegation: 'Microsoft.App/environments'
        networkSecurityGroupResourceId: nsg[0].outputs.resourceId
      }
      {
        name: 'agents'
        addressPrefix: '10.84.2.0/24'
        delegation: 'Microsoft.App/environments'
        networkSecurityGroupResourceId: nsg[1].outputs.resourceId
      }
      {
        name: 'apim'
        addressPrefix: '10.84.3.0/24'
        delegation: 'Microsoft.Web/serverFarms'
        networkSecurityGroupResourceId: nsg[2].outputs.resourceId
      }
      {
        name: 'endpoints'
        addressPrefix: '10.84.4.0/24'
        privateEndpointNetworkPolicies: 'Disabled'
        networkSecurityGroupResourceId: nsg[3].outputs.resourceId
      }
    ]
  }
}

@description('Virtual network ID.')
output resourceId string = vnet.outputs.resourceId
@description('Virtual network name.')
output resourceName string = vnet.outputs.name
@description('Application subnet ID.')
output appSubnetId string = vnet.outputs.subnetResourceIds[0]
@description('Dedicated agent subnet ID.')
output agentSubnetId string = vnet.outputs.subnetResourceIds[1]
@description('Dedicated gateway integration subnet ID.')
output apimSubnetId string = vnet.outputs.subnetResourceIds[2]
@description('Private endpoint subnet ID.')
output endpointSubnetId string = vnet.outputs.subnetResourceIds[3]
