@description('Azure region for PostgreSQL Flexible Server.')
param location string

@description('Globally unique PostgreSQL server name.')
param serverName string

@description('Delegated subnet resource ID.')
param delegatedSubnetId string

@description('Private DNS zone resource ID.')
param privateDnsZoneId string

@description('PostgreSQL compute SKU name.')
param skuName string

@description('PostgreSQL compute tier.')
@allowed([
  'Burstable'
  'GeneralPurpose'
])
param skuTier string

@description('Enable zone-redundant high availability.')
param highAvailability bool = false

@description('Backup retention in days.')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('Common resource tags.')
param tags object

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenant().tenantId
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: highAvailability ? 'ZoneRedundant' : 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: delegatedSubnetId
      privateDnsZoneArmResourceId: privateDnsZoneId
      publicNetworkAccess: 'Disabled'
    }
    storage: {
      autoGrow: 'Enabled'
      storageSizeGB: 32
    }
    version: '16'
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: 'industrial_operations'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

output databaseName string = database.name
output fullyQualifiedDomainName string = server.properties.fullyQualifiedDomainName
output id string = server.id
output name string = server.name
output principalId string = server.identity.principalId
