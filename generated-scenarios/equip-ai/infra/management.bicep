targetScope = 'resourceGroup'

@description('Existing scenario environment; no shared resources are modified.')
param environment string = 'equip-ai'
@description('Retain the approved region.')
@allowed(['centralus'])
param location string = 'centralus'
@description('Generated local ephemeral SSH public key. No inbound SSH rule is created.')
param adminPublicKey string
@description('Exact project installer role already resolved for the retained reference.')
param agentInstallerRoleId string

var tags = {
  Environment: environment
  ManagedBy: 'Bicep'
  Project: 'equip-ai'
  SecurityControl: 'Ignore'
}
var uniqueSuffix = uniqueString(resourceGroup().id)
var shortEnv = take(replace(environment, '-', ''), 7)
var foundryName = 'ai-equip-${shortEnv}-${take(uniqueSuffix, 6)}'
var appNames = [
  'app-equip-web-${shortEnv}-${take(uniqueSuffix, 6)}'
  'app-equip-cleaner-${shortEnv}-${take(uniqueSuffix, 6)}'
]

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: 'vnet-equip-${environment}'
}
resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: vnet
  name: 'management'
}
module runner 'br/public:avm/res/compute/virtual-machine:0.22.0' = {
  name: 'private-management-runner'
  params: {
    name: 'vm-equip-management-${environment}'
    location: location
    tags: tags
    vmSize: 'Standard_D2als_v7'
    availabilityZone: -1
    osType: 'Linux'
    adminUsername: 'equipoperator'
    disablePasswordAuthentication: true
    publicKeys: [
      { path: '/home/equipoperator/.ssh/authorized_keys', keyData: adminPublicKey }
    ]
    imageReference: {
      publisher: 'Canonical'
      offer: 'ubuntu-24_04-lts'
      sku: 'server'
      version: 'latest'
    }
    osDisk: {
      diskSizeGB: 32
      createOption: 'FromImage'
      deleteOption: 'Delete'
      managedDisk: { storageAccountType: 'StandardSSD_LRS' }
    }
    nicConfigurations: [
      {
        name: 'nic-equip-management-${environment}'
        deleteOption: 'Delete'
        ipConfigurations: [
          {
            name: 'private'
            subnetResourceId: subnet.id
          }
        ]
      }
    ]
    managedIdentities: { systemAssigned: true }
    securityType: 'TrustedLaunch'
    secureBootEnabled: true
    vTpmEnabled: true
    bootDiagnostics: true
    patchMode: 'AutomaticByPlatform'
    patchAssessmentMode: 'AutomaticByPlatform'
    enableTelemetry: false
  }
}
resource publishRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, 'equip-management-publish')
  properties: {
    roleName: 'equip-ai-management-publish-${take(uniqueSuffix, 6)}'
    description: 'Read site and publish packages; no site configuration, credentials or role management.'
    type: 'CustomRole'
    assignableScopes: [resourceGroup().id]
    permissions: [
      {
        actions: ['Microsoft.Web/sites/read', 'Microsoft.Web/sites/publish/action']
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
  }
}
resource sites 'Microsoft.Web/sites@2024-11-01' existing = [for name in appNames: {
  name: name
}]
resource publishAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (name, i) in appNames: {
  scope: sites[i]
  name: guid(resourceId('Microsoft.Web/sites', name), 'management-publisher')
  properties: {
    principalId: runner.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: publishRole.id
  }
}]
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: 'equipment-operations'
}
resource agentAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, 'management-agent-installer')
  properties: {
    principalId: runner.outputs.systemAssignedMIPrincipalId!
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', agentInstallerRoleId)
  }
}
@description('ARM-operated private execution host, never a public SSH endpoint.')
output MANAGEMENT_VM_NAME string = runner.outputs.name
@description('Identity used by private publishing and agent initialization.')
output MANAGEMENT_PRINCIPAL_ID string = runner.outputs.systemAssignedMIPrincipalId!
