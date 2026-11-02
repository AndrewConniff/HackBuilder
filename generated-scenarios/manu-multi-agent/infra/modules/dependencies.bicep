@description('Provisional deployment region.')
param location string
@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Short scenario/environment name stem.')
param stem string
@description('Standard resource tags.')
param tags object
@description('Deployer object ID; data-plane installer permissions are explicit.')
param principalId string
@description('Application managed identity object ID.')
param appPrincipalId string
@description('Log Analytics resource ID.')
param workspaceId string

module platformStorage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'platform-storage-${uniqueSuffix}'
  params: {
    name: 'stmmp${uniqueSuffix}'
    location: location
    tags: tags
    enableTelemetry: false
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    roleAssignments: [
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
    ]
  }
}

module businessStorage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'business-storage-${uniqueSuffix}'
  params: {
    name: 'stmmb${uniqueSuffix}'
    location: location
    tags: tags
    enableTelemetry: false
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    blobServices: {
      isVersioningEnabled: true
      deleteRetentionPolicyEnabled: true
      deleteRetentionPolicyDays: 7
      containers: [
        {
          name: 'synthetic-fixtures'
          publicAccess: 'None'
          roleAssignments: [
            {
              principalId: appPrincipalId
              principalType: 'ServicePrincipal'
              roleDefinitionIdOrName: 'Storage Blob Data Reader'
            }
            {
              principalId: principalId
              principalType: 'User'
              roleDefinitionIdOrName: 'Storage Blob Data Contributor'
            }
          ]
        }
      ]
    }
  }
}

module cosmos 'br/public:avm/res/document-db/database-account:0.21.1' = {
  name: 'cosmos-${uniqueSuffix}'
  params: {
    name: 'cosmos-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    defaultConsistencyLevel: 'Session'
    zoneRedundant: false
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    disableLocalAuthentication: true
    minimumTlsVersion: 'Tls12'
    totalThroughputLimit: 5000
    networkRestrictions: {
      publicNetworkAccess: 'Disabled'
      networkAclBypass: 'None'
      ipRules: []
      virtualNetworkRules: []
    }
    sqlRoleAssignments: [
      {
        principalId: principalId
        roleDefinitionId: '00000000-0000-0000-0000-000000000002'
      }
    ]
  }
}

module search 'br/public:avm/res/search/search-service:0.13.0' = {
  name: 'search-${uniqueSuffix}'
  params: {
    name: 'srch-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    sku: 'standard'
    replicaCount: 1
    partitionCount: 1
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    networkRuleSet: { bypass: 'None', ipRules: [] }
    managedIdentities: { systemAssigned: true }
    roleAssignments: [
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'Search Index Data Contributor'
      }
    ]
  }
}

module vault 'br/public:avm/res/key-vault/vault:0.14.2' = {
  name: 'vault-${uniqueSuffix}'
  params: {
    name: 'kv-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    sku: 'standard'
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    enableVaultForDeployment: false
    enableVaultForTemplateDeployment: false
    enableVaultForDiskEncryption: false
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    diagnosticSettings: [
      {
        workspaceResourceId: workspaceId
        logCategoriesAndGroups: [{ category: 'AuditEvent' }]
        metricCategories: [{ category: 'AllMetrics' }]
      }
    ]
    roleAssignments: [
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'Key Vault Administrator'
      }
    ]
    keys: [
      {
        name: 'handoff-receipt'
        kty: 'RSA'
        keySize: 2048
        keyOps: ['sign', 'verify']
        attributes: { enabled: true }
        rotationPolicy: {
          attributes: { expiryTime: 'P180D' }
          lifetimeActions: [
            { action: { type: 'rotate' }, trigger: { timeAfterCreate: 'P90D' } }
          ]
        }
        roleAssignments: [
          {
            principalId: appPrincipalId
            principalType: 'ServicePrincipal'
            roleDefinitionIdOrName: 'Key Vault Crypto User'
          }
        ]
      }
    ]
  }
}

module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'registry-${uniqueSuffix}'
  params: {
    name: 'acrmm${uniqueSuffix}'
    location: location
    tags: tags
    enableTelemetry: false
    acrSku: 'Premium'
    acrAdminUserEnabled: false
    anonymousPullEnabled: false
    dataEndpointEnabled: true
    publicNetworkAccess: 'Disabled'
    networkRuleBypassOptions: 'None'
    networkRuleSetDefaultAction: 'Deny'
    zoneRedundancy: 'Disabled'
    roleAssignmentMode: 'LegacyRegistryPermissions'
    roleAssignments: [
      {
        principalId: appPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'AcrPull'
      }
      {
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'AcrPush'
      }
    ]
  }
}

@description('Platform dependency bundle ID (platform Storage).')
output resourceId string = platformStorage.outputs.resourceId
@description('Platform dependency bundle name (platform Storage).')
output resourceName string = platformStorage.outputs.name
@description('Platform Storage name.')
output platformStorageName string = platformStorage.outputs.name
@description('Platform Blob endpoint.')
output platformBlobEndpoint string = platformStorage.outputs.serviceEndpoints.blob
@description('Business Storage name.')
output businessStorageName string = businessStorage.outputs.name
@description('Business Blob endpoint.')
output businessBlobEndpoint string = businessStorage.outputs.serviceEndpoints.blob
@description('Cosmos account name.')
output cosmosName string = cosmos.outputs.name
@description('Cosmos endpoint.')
output cosmosEndpoint string = cosmos.outputs.endpoint
@description('Search service name.')
output searchName string = search.outputs.name
@description('Key Vault name.')
output vaultName string = vault.outputs.name
@description('Signing key URI; the runtime records the resolved immutable version.')
output signingKeyUri string = '${vault.outputs.uri}keys/handoff-receipt'
@description('Registry name.')
output registryName string = registry.outputs.name
@description('Registry login server.')
output registryLoginServer string = registry.outputs.loginServer
