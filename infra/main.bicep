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

output environmentName string = environment
output containerRegistryName string = registry.outputs.name
output keyVaultName string = vault.outputs.name
output storageAccountName string = storage.outputs.name
output applicationInsightsId string = monitoring.outputs.applicationInsightsId
