@description('Confirmed deployment region.')
param location string

@description('Required scenario tags.')
param tags object

@description('Suffix emitted by shared infrastructure; never calculate a second suffix.')
param uniqueSuffix string

@description('Existing Container Apps environment ID.')
param environmentId string

@description('Scenario registry login server.')
param registryServer string

@description('Locally built and pushed application image pinned by digest. No sample-image fallback.')
@minLength(1)
param image string

@description('Web, chat, worker and scaler identities emitted by shared infrastructure.')
param identities array

@description('Cosmos endpoint emitted by shared infrastructure.')
param cosmosEndpoint string

@description('Key Vault URI emitted by shared infrastructure.')
param keyVaultUri string

@description('Broker fully qualified namespace.')
param serviceBusNamespace string

@description('Real project endpoint returned by the authorized Foundry project lookup.')
param foundryProjectEndpoint string

@description('Installed immutable agent versions emitted by the authorized initializer.')
param agentVersions object

@description('Verified Entra staff tenant ID; no synthetic credentials are deployed.')
param staffTenantId string

@description('Verified staff API v2 audience.')
param staffAudience string

@description('Verified scenario-owned staff client ID.')
param staffClientId string

@description('Workspace-based telemetry configuration.')
param applicationInsightsConnectionString string

@description('Independent executable roles.')
var roles = ['web', 'chat', 'worker']

@description('Shared host suffix supplied by the actual environment deployment output.')
param environmentDomain string

@description('Role-specific environment configuration.')
var sharedEnvironment = [
  { name: 'ASPNETCORE_ENVIRONMENT', value: 'Production' }
  { name: 'ASPNETCORE_HTTP_PORTS', value: '8080' }
  { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
  { name: 'COSMOS_DATABASE', value: 'restaurant' }
  { name: 'KEY_VAULT_URI', value: keyVaultUri }
  { name: 'SERVICE_BUS_NAMESPACE', value: serviceBusNamespace }
  { name: 'SERVICE_BUS_QUEUE', value: 'kitchen' }
  { name: 'FOUNDRY_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
  { name: 'FOUNDRY_MODEL_DEPLOYMENT', value: 'restaurant-model' }
  { name: 'AGENT_GUEST_VERSION', value: agentVersions.guest }
  { name: 'AGENT_STAFF_VERSION', value: agentVersions.staff }
  { name: 'AGENT_KITCHEN_VERSION', value: agentVersions.kitchen }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
  { name: 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING', value: 'Authorization=AAD' }
  { name: 'CHAT_BASE_URL', value: 'https://ca-resto-chat-${uniqueSuffix}.internal.${environmentDomain}' }
  { name: 'TRANSACTION_BASE_URL', value: 'https://ca-resto-web-${uniqueSuffix}.${environmentDomain}' }
]

module apps 'br/public:avm/res/app/container-app:0.23.0' = [for (role, i) in roles: {
  name: 'app-${role}'
  params: {
    name: 'ca-resto-${role}-${uniqueSuffix}'
    location: location
    tags: union(tags, { 'azd-service-name': role })
    environmentResourceId: environmentId
    workloadProfileName: 'Consumption'
    managedIdentities: {
      userAssignedResourceIds: role == 'worker'
        ? [identities[i].resourceId, identities[3].resourceId]
        : [identities[i].resourceId]
    }
    registries: [{
      server: registryServer
      identity: identities[i].resourceId
    }]
    disableIngress: role == 'worker'
    ingressExternal: role == 'web'
    ingressAllowInsecure: false
    ingressTargetPort: 8080
    ingressTransport: 'http'
    scaleSettings: {
      minReplicas: 3
      maxReplicas: role == 'web' ? 12 : (role == 'chat' ? 6 : 10)
      pollingInterval: 5
      rules: role == 'worker' ? [{
        name: 'kitchen'
        custom: {
          type: 'azure-servicebus'
          identity: identities[3].resourceId
          metadata: {
            queueName: 'kitchen'
            namespace: first(split(serviceBusNamespace, '.'))
            messageCount: '20'
          }
        }
      }] : [{
        name: 'requests'
        http: {
          metadata: {
            concurrentRequests: role == 'web' ? '30' : '2'
          }
        }
      }]
    }
    containers: [{
      name: role
      image: image
      resources: {
        cpu: json('0.5')
        memory: '1Gi'
      }
      env: concat(sharedEnvironment, role == 'worker' ? [] : [
        { name: 'STAFF_AUTH_MODE', value: 'entra' }
        { name: 'STAFF_TENANT_ID', value: staffTenantId }
        { name: 'STAFF_AUDIENCE', value: staffAudience }
        { name: 'STAFF_CLIENT_ID', value: staffClientId }
      ], [
        { name: 'APP_ROLE', value: role }
        { name: 'AZURE_CLIENT_ID', value: identities[i].clientId }
      ])
      probes: [{
        type: 'Liveness'
        httpGet: {
          path: '/health/live'
          port: 8080
        }
        initialDelaySeconds: 10
        periodSeconds: 10
      }, {
        type: 'Readiness'
        httpGet: {
          path: '/health/ready'
          port: 8080
        }
        initialDelaySeconds: 10
        periodSeconds: 10
      }]
    }]
  }
}]

@description('Deployed app resource IDs in web, chat, worker order.')
output resourceIds array = [for i in range(0, 3): apps[i].outputs.resourceId]

@description('Deployed app names in web, chat, worker order.')
output resourceNames array = [for i in range(0, 3): apps[i].outputs.name]

@description('Actual public web application URL emitted by Container Apps.')
output applicationUrl string = 'https://${apps[0].outputs.fqdn}'
