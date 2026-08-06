@description('Azure region for the Container Apps environment.')
param location string

@description('Container Apps environment name.')
param environmentName string

@description('Delegated infrastructure subnet resource ID.')
param infrastructureSubnetId string

@description('Log Analytics workspace customer ID.')
param logAnalyticsCustomerId string

@secure()
@description('Log Analytics shared key resolved at deployment time.')
param logAnalyticsSharedKey string

@description('Enable zone redundancy where supported.')
param zoneRedundant bool = false

@description('Common resource tags.')
param tags object

resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    peerAuthentication: {
      mtls: {
        enabled: true
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    zoneRedundant: zoneRedundant
  }
}

output defaultDomain string = managedEnvironment.properties.defaultDomain
output id string = managedEnvironment.id
output name string = managedEnvironment.name
