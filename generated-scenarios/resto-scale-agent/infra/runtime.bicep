targetScope = 'resourceGroup'

@description('Confirmed distinct azd environment matching the existing shared infrastructure.')
param environment string

@description('Confirmed deployment region, identical to the shared infrastructure.')
param location string

@description('Unmodified outputs object from this scenario shared infrastructure deployment.')
param infrastructure object

@description('Locally built scenario registry image pinned to its sha256 digest.')
@minLength(1)
param image string

@description('Actual Foundry project endpoint returned by authorized project discovery.')
param foundryProjectEndpoint string

@description('Immutable guest, staff and kitchen versions emitted by the authorized initializer.')
param agentVersions object

@description('Verified single-tenant staff API installation tenant.')
param staffTenantId string

@description('Verified staff API client ID used as the v2 access-token audience.')
param staffAudience string

@description('Verified scenario-owned staff browser client ID.')
param staffClientId string

@description('Required tags retained across shared and application resources.')
var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'resto-scale-agent'
  SecurityControl: 'Ignore'
}

module apps 'modules/apps.bicep' = {
  name: 'restaurant-apps'
  params: {
    location: location
    tags: tags
    uniqueSuffix: infrastructure.RESOURCE_SUFFIX.value
    environmentId: infrastructure.AZURE_CONTAINER_APPS_ENVIRONMENT_ID.value
    environmentDomain: infrastructure.AZURE_CONTAINER_APPS_ENVIRONMENT_DOMAIN.value
    registryServer: infrastructure.AZURE_CONTAINER_REGISTRY_ENDPOINT.value
    image: image
    identities: infrastructure.RUNTIME_IDENTITIES.value
    cosmosEndpoint: infrastructure.COSMOS_ENDPOINT.value
    keyVaultUri: infrastructure.KEY_VAULT_URI.value
    serviceBusNamespace: infrastructure.SERVICE_BUS_NAMESPACE.value
    foundryProjectEndpoint: foundryProjectEndpoint
    agentVersions: agentVersions
    staffTenantId: staffTenantId
    staffAudience: staffAudience
    staffClientId: staffClientId
    applicationInsightsConnectionString: infrastructure.APPLICATIONINSIGHTS_CONNECTION_STRING.value
  }
}

@description('Deployed app resource IDs ordered web, chat, worker.')
output resourceIds array = apps.outputs.resourceIds

@description('Deployed app resource names ordered web, chat, worker.')
output resourceNames array = apps.outputs.resourceNames

@description('Actual web endpoint. Availability and agent invocation require separate acceptance.')
output applicationUrl string = apps.outputs.applicationUrl
