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

@description('Immutable API image reference including digest or version tag.')
param apiImage string

@description('Immutable UI image reference including digest or version tag.')
param uiImage string

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

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: monitoring.outputs.logAnalyticsName
}

module containerEnvironment 'modules/container-app-environment.bicep' = {
  name: 'containerAppsEnvironment'
  params: {
    location: location
    environmentName: take('${namePrefix}-cae', 60)
    infrastructureSubnetId: network.outputs.containerAppsSubnetId
    logAnalyticsCustomerId: monitoring.outputs.logAnalyticsCustomerId
    logAnalyticsSharedKey: logAnalytics.listKeys().primarySharedKey
    zoneRedundant: environment == 'prod'
    tags: commonTags
  }
}

module api 'modules/container-app.bicep' = {
  name: 'apiContainerApp'
  params: {
    location: location
    appName: take('${namePrefix}-api', 32)
    managedEnvironmentId: containerEnvironment.outputs.id
    image: apiImage
    targetPort: 8000
    healthPath: '/health'
    environmentVariables: [
      {
        name: 'APP_ENVIRONMENT'
        value: environment
      }
      {
        name: 'AZURE_SEARCH_ENDPOINT'
        value: search.outputs.endpoint
      }
      {
        name: 'AZURE_POSTGRES_HOST'
        value: postgresql.outputs.fullyQualifiedDomainName
      }
      {
        name: 'AZURE_STORAGE_BLOB_ENDPOINT'
        value: storage.outputs.blobEndpoint
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: monitoring.outputs.applicationInsightsConnectionString
      }
    ]
    minReplicas: environment == 'prod' ? 2 : 0
    maxReplicas: environment == 'prod' ? 10 : 3
    tags: commonTags
  }
}

module ui 'modules/container-app.bicep' = {
  name: 'uiContainerApp'
  params: {
    location: location
    appName: take('${namePrefix}-ui', 32)
    managedEnvironmentId: containerEnvironment.outputs.id
    image: uiImage
    targetPort: 8501
    healthPath: '/_stcore/health'
    environmentVariables: [
      {
        name: 'API_BASE_URL'
        value: 'https://${api.outputs.fqdn}'
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: monitoring.outputs.applicationInsightsConnectionString
      }
    ]
    minReplicas: environment == 'prod' ? 2 : 0
    maxReplicas: environment == 'prod' ? 5 : 2
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
output apiFqdn string = api.outputs.fqdn
output uiFqdn string = ui.outputs.fqdn
