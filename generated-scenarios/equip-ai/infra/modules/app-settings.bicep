@description('AVM-created public authenticated application name.')
param webName string
@description('AVM-created private cleanup application name.')
param cleanerName string
@description('Complete common keyless runtime settings.')
param settings object

resource web 'Microsoft.Web/sites@2025-03-01' existing = { name: webName }
resource cleaner 'Microsoft.Web/sites@2025-03-01' existing = { name: cleanerName }
resource webSettings 'Microsoft.Web/sites/config@2025-03-01' = {
  parent: web
  name: 'appsettings'
  properties: union(settings, {
    WorkerRole: 'web'
  })
}
resource cleanerSettings 'Microsoft.Web/sites/config@2025-03-01' = {
  parent: cleaner
  name: 'appsettings'
  properties: union(settings, { WorkerRole: 'cleaner' })
}
@description('Configured web resource ID.')
output resourceId string = web.id
@description('Configured web name.')
output resourceName string = web.name
