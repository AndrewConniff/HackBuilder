@description('Application region.')
param location string
@description('Governance tags.')
param tags object
@description('Application name.')
param appName string
@description('Internal managed environment resource ID.')
param environmentId string
@description('Real immutable image from the private registry.')
@minLength(1)
param applicationImage string
@description('Private registry server.')
param registryServer string
@description('Runtime identity resource ID.')
param identityId string
@description('Runtime identity client ID.')
param identityClientId string
@description('Tenant ID for issuer validation.')
param tenantId string
@description('Existing public APIM gateway.')
param gatewayName string
@description('APIM user-assigned identity client ID.')
param gatewayClientId string
@description('APIM user-assigned identity object ID.')
param gatewayPrincipalId string
@description('Registered single-tenant backend API audience.')
@minLength(1)
param backendAudience string
@description('Private direct child project endpoint.')
param projectEndpoint string
@description('Operator-installed agent version.')
@minLength(1)
param agentVersion string
@description('Private synthetic FAQ blob.')
param faqBlobUrl string
@description('Nonexportable receipt-signing key.')
param signingKeyUrl string

module app 'br/public:avm/res/app/container-app:0.23.0' = {
  name: 'chat-app'
  params: {
    name: appName
    location: location
    tags: union(tags, { 'azd-service-name': 'web' })
    enableTelemetry: false
    environmentResourceId: environmentId
    managedIdentities: { userAssignedResourceIds: [identityId] }
    workloadProfileName: 'Consumption'
    ingressExternal: true
    ingressAllowInsecure: false
    ingressTargetPort: 8080
    ingressTransport: 'http'
    registries: [{ server: registryServer, identity: identityId }]
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 10
      rules: [{ name: 'http', http: { metadata: { concurrentRequests: '8' } } }]
    }
    containers: [{
      name: 'web'
      image: applicationImage
      resources: { cpu: json('0.5'), memory: '1Gi' }
      env: [
        { name: 'AZURE_CLIENT_ID', value: identityClientId }
        { name: 'AZURE_TENANT_ID', value: tenantId }
        { name: 'GATEWAY_PRINCIPAL_ID', value: gatewayPrincipalId }
        { name: 'BACKEND_AUDIENCE', value: backendAudience }
        { name: 'FOUNDRY_PROJECT_ENDPOINT', value: projectEndpoint }
        { name: 'FOUNDRY_AGENT_NAME', value: 'brokerage-educator' }
        { name: 'FOUNDRY_AGENT_VERSION', value: agentVersion }
        { name: 'MODEL_DEPLOYMENT', value: 'brokerage-model' }
        { name: 'FAQ_BLOB_URL', value: faqBlobUrl }
        { name: 'SIGNING_KEY_URL', value: signingKeyUrl }
      ]
      probes: [
        { type: 'Startup', tcpSocket: { port: 8080 }, periodSeconds: 5, failureThreshold: 30 }
        { type: 'Readiness', tcpSocket: { port: 8080 }, periodSeconds: 10 }
        { type: 'Liveness', tcpSocket: { port: 8080 }, periodSeconds: 30 }
      ]
    }]
  }
}
module routes 'br/public:avm/res/api-management/service/api:0.2.2' = {
  name: 'public-routes'
  params: {
    apiManagementServiceName: gatewayName
    enableTelemetry: false
    name: 'brokerage'
    displayName: 'Brokerage customer education'
    path: ''
    protocols: ['https']
    subscriptionRequired: false
    serviceUrl: 'https://${app.outputs.fqdn}'
    operations: [
      { name: 'home', displayName: 'Customer chat', method: 'GET', urlTemplate: '/' }
      { name: 'styles', displayName: 'Local style', method: 'GET', urlTemplate: '/site.css' }
      { name: 'script', displayName: 'Local script', method: 'GET', urlTemplate: '/chat.js' }
      { name: 'chat', displayName: 'Ask an education question', method: 'POST', urlTemplate: '/api/chat' }
    ]
    policies: [{
      name: 'policy'
      format: 'rawxml'
      value: replace(replace(loadTextContent('../gateway-policy.xml'), '__AUDIENCE__', backendAudience), '__CLIENT_ID__', gatewayClientId)
    }]
  }
}
