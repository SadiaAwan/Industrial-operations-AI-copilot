targetScope = 'resourceGroup'

@description('Deployment environment. Each value uses a separate resource group.')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string

@description('Short workload name used in resource names.')
@minLength(3)
@maxLength(18)
param workloadName string = 'industrial-ai'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Common non-sensitive resource tags.')
param tags object = {}

var suffix = take(uniqueString(subscription().subscriptionId, resourceGroup().id), 6)
var namePrefix = '${workloadName}-${environment}-${suffix}'
var compactPrefix = toLower(replace('${workloadName}${environment}${suffix}', '-', ''))
var commonTags = union(tags, {
  application: workloadName
  environment: environment
  managedBy: 'bicep'
})

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    namePrefix: namePrefix
    retentionInDays: environment == 'prod' ? 90 : 30
    tags: commonTags
  }
}

module registry 'modules/container-registry.bicep' = {
  name: 'containerRegistry'
  params: {
    location: location
    registryName: take('${compactPrefix}acr', 50)
    skuName: environment == 'prod' ? 'Premium' : 'Basic'
    tags: commonTags
  }
}

module vault 'modules/key-vault.bicep' = {
  name: 'keyVault'
  params: {
    location: location
    vaultName: take('${namePrefix}-kv', 24)
    retentionInDays: environment == 'prod' ? 90 : 30
    tags: commonTags
  }
}

module storage 'modules/blob-storage.bicep' = {
  name: 'blobStorage'
  params: {
    location: location
    storageAccountName: take('${compactPrefix}st', 24)
    skuName: environment == 'prod' ? 'Standard_ZRS' : 'Standard_LRS'
    tags: commonTags
  }
}

module network 'modules/network.bicep' = {
  name: 'applicationNetwork'
  params: {
    location: location
    namePrefix: namePrefix
    tags: commonTags
  }
}

module search 'modules/ai-search.bicep' = {
  name: 'azureAiSearch'
  params: {
    location: location
    searchServiceName: take('${namePrefix}-search', 60)
    skuName: environment == 'prod' ? 'standard' : 'basic'
    replicaCount: environment == 'prod' ? 2 : 1
    tags: commonTags
  }
}

module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql'
  params: {
    location: location
    serverName: take('${namePrefix}-pg', 63)
    delegatedSubnetId: network.outputs.postgresqlSubnetId
    privateDnsZoneId: network.outputs.postgresqlPrivateDnsZoneId
    skuName: environment == 'prod' ? 'Standard_D2ds_v5' : 'Standard_B1ms'
    skuTier: environment == 'prod' ? 'GeneralPurpose' : 'Burstable'
    highAvailability: environment == 'prod'
    backupRetentionDays: environment == 'prod' ? 35 : 7
    tags: commonTags
  }
}

output environmentName string = environment
output containerRegistryName string = registry.outputs.name
output keyVaultName string = vault.outputs.name
output storageAccountName string = storage.outputs.name
output applicationInsightsId string = monitoring.outputs.applicationInsightsId
output azureAiSearchName string = search.outputs.name
output postgresqlServerName string = postgresql.outputs.name
output virtualNetworkId string = network.outputs.virtualNetworkId
