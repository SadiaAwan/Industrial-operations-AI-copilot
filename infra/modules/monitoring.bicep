@description('Azure region for observability resources.')
param location string

@description('Resource name prefix, including workload and environment.')
param namePrefix string

@description('Log retention in days.')
@minValue(30)
@maxValue(730)
param retentionInDays int

@description('Common resource tags.')
param tags object

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-log'
  location: location
  tags: tags
  properties: {
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-appi'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    DisableLocalAuth: true
    IngestionMode: 'LogAnalytics'
    RetentionInDays: retentionInDays
    WorkspaceResourceId: logAnalytics.id
  }
}

output logAnalyticsId string = logAnalytics.id
output logAnalyticsCustomerId string = logAnalytics.properties.customerId
output applicationInsightsId string = applicationInsights.id
@secure()
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
