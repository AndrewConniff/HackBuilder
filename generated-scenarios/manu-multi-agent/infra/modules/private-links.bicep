@description('Deployment region.')
param location string
@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Standard resource tags.')
param tags object
@description('Private endpoint subnet ID.')
param subnetId string
@description('VNet ID for private zone links.')
param vnetId string
@description('Foundry account name.')
param accountName string
@description('Platform Storage name.')
param platformStorageName string
@description('Business Storage name.')
param businessStorageName string
@description('Cosmos account name.')
param cosmosName string
@description('Search service name.')
param searchName string
@description('Key Vault name.')
param vaultName string
@description('Registry name.')
param registryName string

@description('Service-specific private DNS zones, including all three Foundry account domains.')
var zoneNames = [
  'privatelink.services.ai.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.blob.${environment().suffixes.storage}'
  'privatelink.documents.azure.com'
  'privatelink.search.windows.net'
  'privatelink.vaultcore.azure.net'
  'privatelink.azurecr.io'
]
module zones 'br/public:avm/res/network/private-dns-zone:0.8.1' = [for (zone, index) in zoneNames: {
  name: 'private-dns-${index}-${uniqueSuffix}'
  params: {
    name: zone
    tags: tags
    enableTelemetry: false
    virtualNetworkLinks: [
      {
        name: 'scenario-${uniqueSuffix}'
        virtualNetworkResourceId: vnetId
        registrationEnabled: false
        tags: tags
      }
    ]
  }
}]

@description('Distinct endpoints and their private DNS zone group memberships.')
var targets = [
  {
    name: accountName
    id: resourceId('Microsoft.CognitiveServices/accounts', accountName)
    group: 'account'
    zones: [0, 1, 2]
  }
  {
    name: platformStorageName
    id: resourceId('Microsoft.Storage/storageAccounts', platformStorageName)
    group: 'blob'
    zones: [3]
  }
  {
    name: businessStorageName
    id: resourceId('Microsoft.Storage/storageAccounts', businessStorageName)
    group: 'blob'
    zones: [3]
  }
  {
    name: cosmosName
    id: resourceId('Microsoft.DocumentDB/databaseAccounts', cosmosName)
    group: 'Sql'
    zones: [4]
  }
  {
    name: searchName
    id: resourceId('Microsoft.Search/searchServices', searchName)
    group: 'searchService'
    zones: [5]
  }
  {
    name: vaultName
    id: resourceId('Microsoft.KeyVault/vaults', vaultName)
    group: 'vault'
    zones: [6]
  }
  {
    name: registryName
    id: resourceId('Microsoft.ContainerRegistry/registries', registryName)
    group: 'registry'
    zones: [7]
  }
]
module endpoints 'br/public:avm/res/network/private-endpoint:0.12.1' = [for (target, index) in targets: {
  name: 'endpoint-${index}-${uniqueSuffix}'
  params: {
    name: 'pe-${target.name}'
    location: location
    tags: tags
    enableTelemetry: false
    subnetResourceId: subnetId
    privateLinkServiceConnections: [
      {
        name: 'connection-${index}'
        properties: {
          privateLinkServiceId: target.id
          groupIds: [target.group]
        }
      }
    ]
    privateDnsZoneGroup: {
      name: 'default'
      privateDnsZoneGroupConfigs: [
        for zoneIndex in target.zones: {
          name: 'zone-${zoneIndex}'
          privateDnsZoneResourceId: zones[zoneIndex].outputs.resourceId
        }
      ]
    }
  }
}]

@description('Representative private endpoint ID.')
output resourceId string = endpoints[0].outputs.resourceId
@description('Representative private endpoint name.')
output resourceName string = endpoints[0].outputs.name
