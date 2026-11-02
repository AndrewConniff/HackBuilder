@description('Deployment region.')
param location string
@description('Resource-group-derived unique suffix.')
param uniqueSuffix string
@description('Short scenario/environment stem.')
param stem string
@description('Standard resource tags.')
param tags object
@description('Internal ACA environment ID.')
param environmentId string
@description('APIM outbound integration subnet ID.')
param apimSubnetId string
@description('Private registry login server.')
param registryLoginServer string
@description('Application managed identity resource ID.')
param appIdentityId string
@description('Application managed identity client ID.')
param appClientId string
@description('Application managed identity principal ID.')
param appPrincipalId string
@description('Gateway managed identity resource ID.')
param gatewayIdentityId string
@description('Gateway managed identity client ID.')
param gatewayClientId string
@description('Gateway principal ID; validated in the backend JWT.')
param gatewayPrincipalId string
@description('Foundry account name.')
param accountName string
@description('Direct child project name.')
param projectName string
@description('New project endpoint.')
param projectEndpoint string
@description('Exact model deployment name.')
param modelName string
@description('Private business fixture endpoint.')
param blobEndpoint string
@description('Nonexportable Key Vault signing key URI.')
param signingKeyUri string
@description('Installed immutable Key Vault key version; prevents signing/verification drift on rotation.')
@minLength(32)
@maxLength(32)
param signingKeyVersion string
@description('Operator-supplied real APIM publisher email.')
@minLength(5)
param publisherEmail string
@description('Dedicated backend API application ID, requestedAccessTokenVersion=2.')
@minLength(36)
@maxLength(36)
param backendClientId string
@description('Verified Foundry Agent Consumer role GUID; no write/admin runtime role.')
@minLength(36)
@maxLength(36)
param consumerRoleDefinitionId string
@description('Installed image SHA-256 hex digest; never a mutable tag.')
@minLength(64)
@maxLength(64)
param imageDigest string
@description('Installed Sales Fit version.')
@minLength(1)
param salesAgentVersion string
@description('Installed Marketing Claims version.')
@minLength(1)
param marketingAgentVersion string
@description('Installed Handoff Coordinator version.')
@minLength(1)
param coordinatorAgentVersion string
@description('Installed fixture manifest SHA-256 hex digest.')
@minLength(64)
@maxLength(64)
param fixtureManifestHash string

@description('MI token resource URI; v2 tokens use the application GUID as aud.')
var backendResource = 'api://${backendClientId}'
@description('Pinned role and version settings consumed by the later application.')
var settings = {
  ASPNETCORE_HTTP_PORTS: '8080'
  ASPNETCORE_ENVIRONMENT: 'Production'
  AZURE_CLIENT_ID: appClientId
  Foundry__ProjectEndpoint: projectEndpoint
  Foundry__ModelDeployment: modelName
  Foundry__SalesAgentName: 'sales-fit'
  Foundry__SalesAgentVersion: salesAgentVersion
  Foundry__MarketingAgentName: 'marketing-claims'
  Foundry__MarketingAgentVersion: marketingAgentVersion
  Foundry__CoordinatorAgentName: 'handoff-coordinator'
  Foundry__CoordinatorAgentVersion: coordinatorAgentVersion
  Fixtures__BlobEndpoint: blobEndpoint
  Fixtures__ContainerName: 'synthetic-fixtures'
  Fixtures__ManifestSha256: fixtureManifestHash
  Signing__KeyUri: '${signingKeyUri}/${signingKeyVersion}'
  Signing__Algorithm: 'PS256'
  BackendAuth__TenantId: tenant().tenantId
  BackendAuth__Authority: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
  BackendAuth__Audience: backendClientId
  BackendAuth__GatewayObjectId: gatewayPrincipalId
  Limits__MaxInputCharacters: '4000'
  Limits__MaxOutputTokens: '800'
  Limits__MaxResponsesRequests: '7'
  Limits__MaxCumulativeTokens: '30000'
  Limits__DeadlineSeconds: '90'
  Limits__MaxConcurrentHandoffs: '4'
}

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: account
  name: projectName
}
resource consumer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, appPrincipalId, consumerRoleDefinitionId)
  properties: {
    principalId: appPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', consumerRoleDefinitionId)
  }
}

module app 'br/public:avm/res/app/container-app:0.23.0' = {
  name: 'application-${uniqueSuffix}'
  params: {
    name: 'ca-${stem}'
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    enableTelemetry: false
    environmentResourceId: environmentId
    managedIdentities: { userAssignedResourceIds: [appIdentityId] }
    ingressExternal: true
    ingressAllowInsecure: false
    ingressTargetPort: 8080
    ingressTransport: 'http'
    activeRevisionsMode: 'Single'
    workloadProfileName: 'Consumption'
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 3
      rules: [
        {
          name: 'http'
          http: { metadata: { concurrentRequests: '4' } }
        }
      ]
    }
    registries: [{ server: registryLoginServer, identity: appIdentityId }]
    containers: [
      {
        name: 'web'
        image: '${registryLoginServer}/mobility-commercial@sha256:${imageDigest}'
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [for setting in items(settings): { name: setting.key, value: setting.value }]
        probes: [
          {
            type: 'Startup'
            tcpSocket: { port: 8080 }
            periodSeconds: 5
            failureThreshold: 24
          }
          {
            type: 'Readiness'
            tcpSocket: { port: 8080 }
            periodSeconds: 10
            failureThreshold: 3
          }
          {
            type: 'Liveness'
            tcpSocket: { port: 8080 }
            periodSeconds: 30
            failureThreshold: 3
          }
        ]
      }
    ]
  }
  dependsOn: [consumer]
}

@description('Exact exposed HTTP operations; arbitrary backend endpoints are never proxied.')
var operations = [
  { name: 'home', method: 'GET', urlTemplate: '/', displayName: 'Synthetic demo' }
  { name: 'styles', method: 'GET', urlTemplate: '/app.css', displayName: 'Demo stylesheet' }
  { name: 'script', method: 'GET', urlTemplate: '/app.js', displayName: 'Demo JavaScript' }
  { name: 'opportunities', method: 'GET', urlTemplate: '/api/opportunities', displayName: 'Synthetic opportunities' }
  { name: 'products', method: 'GET', urlTemplate: '/api/products', displayName: 'Synthetic product catalog' }
  { name: 'claims', method: 'GET', urlTemplate: '/api/claims', displayName: 'Approved synthetic claims' }
  { name: 'handoff', method: 'POST', urlTemplate: '/api/handoffs', displayName: 'Create human-review handoff' }
  { name: 'verify', method: 'POST', urlTemplate: '/api/receipts/verify', displayName: 'Verify receipt integrity' }
]
@description('Policy placeholders are substituted only from ARM resource outputs and configured audience.')
var policy = replace(
  replace(loadTextContent('gateway-policy.xml'), '__BACKEND_RESOURCE__', backendResource),
  '__GATEWAY_CLIENT_ID__',
  gatewayClientId
)
module gateway 'br/public:avm/res/api-management/service:0.15.0' = {
  name: 'gateway-${uniqueSuffix}'
  params: {
    name: 'apim-${stem}'
    location: location
    tags: tags
    enableTelemetry: false
    sku: 'StandardV2'
    skuCapacity: 1
    publisherName: 'Adventure Works Cycles'
    publisherEmail: publisherEmail
    managedIdentities: { userAssignedResourceIds: [gatewayIdentityId] }
    publicNetworkAccess: 'Enabled'
    virtualNetworkType: 'External'
    subnetResourceId: apimSubnetId
    availabilityZones: []
    enableDeveloperPortal: false
    customProperties: {}
    apis: [
      {
        name: 'mobility-commercial'
        displayName: 'Adventure Works Cycles Sales-to-Marketing'
        path: ''
        protocols: ['https']
        subscriptionRequired: false
        serviceUrl: 'https://${app.outputs.fqdn}'
        operations: operations
        policies: [{ name: 'policy', format: 'rawxml', value: policy }]
      }
    ]
  }
}

@description('Private application resource ID.')
output resourceId string = app.outputs.resourceId
@description('Application resource name for later azd service wiring.')
output resourceName string = app.outputs.name
@description('Public APIM synthetic entry URL.')
output gatewayUrl string = 'https://${gateway.outputs.name}.azure-api.net'
