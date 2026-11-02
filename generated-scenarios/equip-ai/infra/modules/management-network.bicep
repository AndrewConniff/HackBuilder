@description('Scenario region.')
param location string
@description('Scenario environment.')
param environment string
@description('Common tags.')
param tags object
@description('Allow private desktop only after explicit Bastion scope approval.')
param enableHumanManagement bool = false
@description('Dedicated Bastion subnet; never permit Internet RDP.')
param bastionPrefix string = '10.247.0.192/26'

module egressIp 'br/public:avm/res/network/public-ip-address:0.13.0' = {
  name: 'management-egress-ip'
  params: {
    name: 'pip-equip-management-${environment}'
    location: location
    tags: tags
    skuName: 'Standard'
    publicIPAllocationMethod: 'Static'
    enableTelemetry: false
  }
}
module nat 'br/public:avm/res/network/nat-gateway:2.1.0' = {
  name: 'management-nat'
  params: {
    name: 'nat-equip-management-${environment}'
    location: location
    tags: tags
    availabilityZone: -1
    publicIpResourceIds: [egressIp.outputs.resourceId]
    enableTelemetry: false
  }
}
module nsg 'br/public:avm/res/network/network-security-group:0.5.0' = {
  name: 'management-nsg'
  params: {
    name: 'nsg-equip-management-${environment}'
    location: location
    tags: tags
    securityRules: concat(enableHumanManagement ? [
      {
        name: 'allow-bastion-rdp'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3389'
          sourceAddressPrefix: bastionPrefix
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
    ] : [], [
      {
        name: 'deny-all-inbound'
        properties: {
          priority: enableHumanManagement ? 200 : 100
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ])
    enableTelemetry: false
  }
}
@description('Explicit outbound-only connectivity; not a VM public IP.')
output natId string = nat.outputs.resourceId
@description('No inbound SSH, including from the VNet.')
output nsgId string = nsg.outputs.resourceId
