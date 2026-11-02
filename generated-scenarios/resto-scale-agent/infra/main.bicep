targetScope = 'resourceGroup'

@description('Distinct azd environment. Deploy only to rg-{environment} after scoped consent.')
@minLength(3)
@maxLength(32)
param environment string

@description('Region confirmed by live deployment preparation; provisional value is in region evidence.')
param location string

@description('Deployer object ID for explicit data-plane setup access.')
param principalId string

@description('Exact model name from the shared region/model evidence.')
param modelName string

@description('Exact model version from the shared region/model evidence.')
param modelVersion string

@description('Deployment SKU from the shared region/model evidence.')
param modelDeploymentType string

@description('Model capacity in thousands of tokens per minute; verify actual quota before deployment.')
@minValue(1)
param modelCapacity int = 100

@description('Verified built-in Foundry Agent Consumer role ID, resolved during authorized preparation.')
param foundryConsumerRoleId string

@description('Guest signing key expiry in ISO 8601 UTC; rotated keys retain their public verification history.')
param guestSigningKeyExpiration string = dateTimeAdd(utcNow(), 'P180D')

@description('One stable resource suffix derived from this isolated resource group.')
var uniqueSuffix = uniqueString(resourceGroup().id)

@description('Existing Cosmos account name; unchanged during the database-scope repair.')
var cosmosAccountName = 'cosmos-resto-${uniqueSuffix}'

@description('Fully qualified Cosmos data-plane database scope required by ARM role assignments.')
var cosmosDatabaseScope = '${resourceId('Microsoft.DocumentDB/databaseAccounts', cosmosAccountName)}/dbs/restaurant'

@description('Stable legal vault name bound to subscription, environment, scenario and naming generation.')
var vaultName = 'kv-resto-${take(replace(guid(subscription().subscriptionId, environment, 'resto-scale-agent', 'vault-v2'), '-', ''), 15)}'

@description('Stable scenario/environment/subscription-owned Foundry DNS name; v2 avoids the retained legacy domain.')
var foundryAccountName = 'ai-resto-${replace(guid(subscription().subscriptionId, environment, 'resto-scale-agent', 'foundry-v2'), '-', '')}'

@description('Required resource and resource-group tags.')
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'resto-scale-agent'
  SecurityControl: 'Ignore'
}

@description('Runtime identities; web and worker have separate business data scopes from chat.')
var roles = ['web', 'chat', 'worker', 'scaler']

@description('Registry reader grants for the three image-pulling application identities.')
var imagePullRoles = [
  {
    principalId: identities[0].outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionIdOrName: 'AcrPull'
  }
  {
    principalId: identities[1].outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionIdOrName: 'AcrPull'
  }
  {
    principalId: identities[2].outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionIdOrName: 'AcrPull'
  }
]

@description('Business data grants; the chat identity has no direct database role.')
var businessDataRoles = [
  {
    principalId: identities[0].outputs.principalId
    roleDefinitionId: '00000000-0000-0000-0000-000000000002'
    scope: cosmosDatabaseScope
  }
  {
    principalId: identities[2].outputs.principalId
    roleDefinitionId: '00000000-0000-0000-0000-000000000002'
    scope: cosmosDatabaseScope
  }
]

resource groupTags 'Microsoft.Resources/tags@2024-03-01' = {
  name: 'default'
  properties: {
    tags: tags
  }
}

module identities 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = [for role in roles: {
  name: 'identity-${role}'
  params: {
    name: 'id-resto-${role}-${uniqueSuffix}'
    location: location
    tags: tags
  }
}]

module logs 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'logs'
  params: {
    name: 'log-resto-${uniqueSuffix}'
    location: location
    tags: tags
    dataRetention: 30
    forceCmkForQuery: false
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

module insights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'insights'
  params: {
    name: 'appi-resto-${uniqueSuffix}'
    location: location
    tags: tags
    workspaceResourceId: logs.outputs.resourceId
    retentionInDays: 30
    disableIpMasking: false
    disableLocalAuth: true
    samplingPercentage: 20
    roleAssignments: [for i in range(0, 3): {
      principalId: identities[i].outputs.principalId
      principalType: 'ServicePrincipal'
      roleDefinitionIdOrName: 'Monitoring Metrics Publisher'
    }]
  }
}

module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'registry'
  params: {
    name: 'acrresto${uniqueSuffix}'
    location: location
    tags: tags
    acrSku: 'Basic'
    acrAdminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    networkRuleSetDefaultAction: 'Allow'
    zoneRedundancy: 'Disabled'
    retentionPolicyStatus: 'disabled'
    exportPolicyStatus: 'enabled'
    roleAssignments: concat(
      imagePullRoles,
      empty(principalId) ? [] : [{
        principalId: principalId
        principalType: 'User'
        roleDefinitionIdOrName: 'AcrPush'
      }]
    )
  }
}

module network 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'network'
  params: {
    name: 'vnet-resto-${uniqueSuffix}'
    location: location
    tags: tags
    addressPrefixes: ['10.74.0.0/22']
    subnets: [{
      name: 'container-apps'
      addressPrefix: '10.74.0.0/23'
      delegation: 'Microsoft.App/environments'
    }]
  }
}

module cosmos 'br/public:avm/res/document-db/database-account:0.21.1' = {
  name: 'cosmos'
  params: {
    name: cosmosAccountName
    location: location
    tags: tags
    zoneRedundant: true
    enableAutomaticFailover: false
    disableLocalAuthentication: true
    disableKeyBasedMetadataWriteAccess: true
    minimumTlsVersion: 'Tls12'
    backupPolicyType: 'Continuous'
    backupPolicyContinuousTier: 'Continuous7Days'
    networkRestrictions: {
      publicNetworkAccess: 'Enabled'
      networkAclBypass: 'None'
    }
    sqlDatabases: [{
      name: 'restaurant'
      tags: tags
      autoscaleSettingsMaxThroughput: 4000
      containers: [for containerName in ['transactions', 'catalog', 'reporting']: {
        name: containerName
        tags: tags
        paths: ['/aggregateKey']
        version: 2
      }]
    }]
    sqlRoleAssignments: concat(
      businessDataRoles,
      empty(principalId) ? [] : [{
        principalId: principalId
        roleDefinitionId: '00000000-0000-0000-0000-000000000002'
        scope: cosmosDatabaseScope
      }]
    )
    diagnosticSettings: [{
      workspaceResourceId: logs.outputs.resourceId
      logCategoriesAndGroups: [{ categoryGroup: 'allLogs' }]
      metricCategories: [{ category: 'Requests' }]
    }]
  }
}

module broker 'br/public:avm/res/service-bus/namespace:0.17.1' = {
  name: 'broker'
  params: {
    name: 'sb-resto-${uniqueSuffix}'
    location: location
    tags: tags
    skuObject: {
      name: 'Premium'
      capacity: 1
    }
    zoneRedundant: true
    premiumMessagingPartitions: 1
    minimumTlsVersion: '1.2'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    authorizationRules: []
    queues: [{
      name: 'kitchen'
      requiresSession: true
      requiresDuplicateDetection: true
      duplicateDetectionHistoryTimeWindow: 'PT10M'
      deadLetteringOnMessageExpiration: true
      defaultMessageTimeToLive: 'P7D'
      maxDeliveryCount: 5
      lockDuration: 'PT1M'
      roleAssignments: [
        {
          principalId: identities[2].outputs.principalId
          principalType: 'ServicePrincipal'
          roleDefinitionIdOrName: 'Azure Service Bus Data Sender'
        }
        {
          principalId: identities[2].outputs.principalId
          principalType: 'ServicePrincipal'
          roleDefinitionIdOrName: 'Azure Service Bus Data Receiver'
        }
        {
          principalId: identities[3].outputs.principalId
          principalType: 'ServicePrincipal'
          roleDefinitionIdOrName: 'Azure Service Bus Data Receiver'
        }
      ]
    }]
    roleAssignments: empty(principalId) ? [] : [{
      principalId: principalId
      principalType: 'User'
      roleDefinitionIdOrName: 'Azure Service Bus Data Owner'
    }]
    diagnosticSettings: [{
      workspaceResourceId: logs.outputs.resourceId
      logCategoriesAndGroups: [{ categoryGroup: 'allLogs' }]
    }]
  }
}

module vault 'br/public:avm/res/key-vault/vault:0.14.2' = {
  name: 'vault'
  params: {
    name: vaultName
    location: location
    tags: tags
    sku: 'standard'
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
    enableVaultForDeployment: false
    enableVaultForTemplateDeployment: false
    enableVaultForDiskEncryption: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'None'
    }
    keys: [{
      name: 'guest-session'
      tags: tags
      kty: 'RSA'
      keySize: 3072
      keyOps: ['sign', 'verify']
      attributes: {
        enabled: true
        exp: dateTimeToEpoch(guestSigningKeyExpiration)
      }
      rotationPolicy: {
        attributes: {
          expiryTime: 'P180D'
        }
        lifetimeActions: [{
          action: {
            type: 'rotate'
          }
          trigger: {
            timeAfterCreate: 'P90D'
          }
        }]
      }
      roleAssignments: [{
        principalId: identities[0].outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Key Vault Crypto User'
      }]
    }]
    roleAssignments: empty(principalId) ? [] : [{
      principalId: principalId
      principalType: 'User'
      roleDefinitionIdOrName: 'Key Vault Administrator'
    }]
    diagnosticSettings: [{
      workspaceResourceId: logs.outputs.resourceId
      logCategoriesAndGroups: [{ categoryGroup: 'allLogs' }]
    }]
  }
}

module foundry 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  name: 'foundry'
  params: {
    name: foundryAccountName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: 'S0'
    allowProjectManagement: true
    customSubDomainName: foundryAccountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: false
    managedIdentities: {
      systemAssigned: true
    }
    deployments: [{
      name: 'restaurant-model'
      model: {
        format: 'OpenAI'
        name: modelName
        version: modelVersion
      }
      sku: {
        name: modelDeploymentType
        capacity: modelCapacity
      }
      versionUpgradeOption: 'NoAutoUpgrade'
    }]
    diagnosticSettings: [{
      workspaceResourceId: logs.outputs.resourceId
      logCategoriesAndGroups: [{ categoryGroup: 'allLogs' }]
    }]
  }
}

module project 'modules/project.bicep' = {
  name: 'project'
  params: {
    accountName: foundry.outputs.name
    location: location
    tags: tags
    chatPrincipalId: identities[1].outputs.principalId
    principalId: principalId
    consumerRoleId: foundryConsumerRoleId
  }
}

module containerEnvironment 'br/public:avm/res/app/managed-environment:0.16.0' = {
  name: 'environment'
  params: {
    name: 'cae-resto-${uniqueSuffix}'
    location: location
    tags: tags
    infrastructureSubnetResourceId: network.outputs.subnetResourceIds[0]
    zoneRedundant: true
    publicNetworkAccess: 'Enabled'
    peerTrafficEncryption: true
    workloadProfiles: [{
      name: 'Consumption'
      workloadProfileType: 'Consumption'
    }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsWorkspaceResourceId: logs.outputs.resourceId
    }
  }
}

@description('Resource group for the isolated azd environment.')
output AZURE_RESOURCE_GROUP string = resourceGroup().name

@description('Confirmed shared infrastructure region used to prevent mismatched runtime deployment.')
output AZURE_LOCATION string = location

@description('Distinct environment associated with these infrastructure outputs.')
output AZURE_ENV_NAME string = environment

@description('Actual subscription used by this shared infrastructure deployment.')
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId

@description('Actual tenant used by this shared infrastructure deployment.')
output AZURE_TENANT_ID string = subscription().tenantId

@description('Registry login server for authenticated local-build image pushes.')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer

@description('Registry resource name.')
output AZURE_CONTAINER_REGISTRY_NAME string = registry.outputs.name

@description('Container environment ID used by the app deployment module.')
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerEnvironment.outputs.resourceId

@description('Container environment resource name.')
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerEnvironment.outputs.name

@description('Actual managed environment default domain for internal service routing.')
output AZURE_CONTAINER_APPS_ENVIRONMENT_DOMAIN string = containerEnvironment.outputs.defaultDomain

@description('Stable suffix for the separately deployed app resources.')
output RESOURCE_SUFFIX string = uniqueSuffix

@description('Foundry direct child project ID. Resolve the emitted project endpoint during authorized setup.')
output FOUNDRY_PROJECT_ID string = project.outputs.resourceId

@description('Foundry account name for authorized project endpoint lookup.')
output FOUNDRY_ACCOUNT_NAME string = foundry.outputs.name

@description('Foundry project name.')
output FOUNDRY_PROJECT_NAME string = project.outputs.resourceName

@description('Deployed model alias used by the three prompt agent definitions.')
output FOUNDRY_MODEL_DEPLOYMENT string = 'restaurant-model'

@description('Cosmos endpoint; never a connection-string credential.')
output COSMOS_ENDPOINT string = cosmos.outputs.endpoint

@description('Key Vault URI for guest-session signing.')
output KEY_VAULT_URI string = vault.outputs.uri

@description('Service Bus fully qualified namespace for managed identity clients.')
output SERVICE_BUS_NAMESPACE string = '${broker.outputs.name}.servicebus.windows.net'

@description('Runtime identity IDs and client IDs, ordered web, chat, worker, scaler.')
output RUNTIME_IDENTITIES array = [for i in range(0, length(roles)): {
  role: roles[i]
  resourceId: identities[i].outputs.resourceId
  clientId: identities[i].outputs.clientId
}]

@description('Workspace-based Application Insights configuration; not a credential.')
output APPLICATIONINSIGHTS_CONNECTION_STRING string = insights.outputs.connectionString
