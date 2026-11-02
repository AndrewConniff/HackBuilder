@description('Approved scenario environment.')
param environment string
@description('Verified scenario region.')
param location string
@description('Scenario-only resource tags.')
param tags object
@description('Existing workload VNet containing the dedicated AzureBastionSubnet.')
param vnetResourceId string

module publicIp 'br/public:avm/res/network/public-ip-address:0.13.0' = {
  name: 'human-access-public-ip'
  params: {
    name: 'pip-equip-bastion-${environment}'
    location: location
    tags: tags
    skuName: 'Standard'
    publicIPAllocationMethod: 'Static'
    enableTelemetry: false
  }
}

module bastion 'br/public:avm/res/network/bastion-host:0.8.2' = {
  name: 'human-access-bastion'
  dependsOn: [publicIp]
  params: {
    name: 'bas-equip-${environment}'
    location: location
    tags: tags
    virtualNetworkResourceId: vnetResourceId
    bastionSubnetPublicIpResourceId: resourceId('Microsoft.Network/publicIPAddresses', 'pip-equip-bastion-${environment}')
    skuName: 'Standard'
    scaleUnits: 2
    enableFileCopy: false
    enableIpConnect: false
    enableShareableLink: false
    disableCopyPaste: true
    enableTelemetry: false
  }
}

@description('Approved interactive access resource; Standard enables native-client tunneling.')
output bastionName string = bastion.outputs.name
