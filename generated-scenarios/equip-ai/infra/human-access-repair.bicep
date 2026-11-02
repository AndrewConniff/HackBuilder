targetScope = 'resourceGroup'

@description('Existing approved environment only.')
@allowed(['equip-ai'])
param environment string = 'equip-ai'
@description('Retain the approved region.')
@allowed(['centralus'])
param location string = 'centralus'
@description('Actual deploying user; never a workload identity.')
param principalId string

@description('Shared naming suffix for existing scenario resources.')
var uniqueSuffix = uniqueString(resourceGroup().id)
@description('Existing constrained resource name label.')
var shortEnv = take(replace(environment, '-', ''), 7)
@description('Tags for the approved management addition.')
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'equip-ai'
  SecurityControl: 'Ignore'
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: 'vnet-equip-${environment}'
}
resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'AzureBastionSubnet'
  properties: { addressPrefix: '10.247.0.192/26' }
}
resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' existing = {
  name: 'nsg-equip-management-${environment}'
}
resource denyInbound 'Microsoft.Network/networkSecurityGroups/securityRules@2024-05-01' = {
  parent: nsg
  name: 'deny-all-inbound'
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
resource desktop 'Microsoft.Network/networkSecurityGroups/securityRules@2024-05-01' = {
  parent: nsg
  name: 'allow-bastion-rdp'
  dependsOn: [denyInbound]
  properties: {
    priority: 100
    direction: 'Inbound'
    access: 'Allow'
    protocol: 'Tcp'
    sourcePortRange: '*'
    destinationPortRange: '3389'
    sourceAddressPrefix: '10.247.0.192/26'
    destinationAddressPrefix: 'VirtualNetwork'
  }
}
module humanAccess 'modules/human-access.bicep' = {
  name: 'human-management-access'
  dependsOn: [subnet, desktop]
  params: {
    environment: environment
    location: location
    tags: tags
    vnetResourceId: vnet.id
  }
}
resource hub 'Microsoft.Devices/IotHubs@2023-06-30' existing = {
  name: 'iot-equip-${shortEnv}-${take(uniqueSuffix, 6)}'
}
resource hubDataAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hub.id, principalId, 'human-data-administrator')
  scope: hub
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4fc6c259-987e-4a07-842e-c321cc9d413f')
  }
}

@description('Approved Bastion host used by native client tunneling.')
output bastionName string = humanAccess.outputs.bastionName
