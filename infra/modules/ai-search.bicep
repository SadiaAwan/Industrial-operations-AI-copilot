@description('Azure region for Azure AI Search.')
param location string

@description('Globally unique Azure AI Search service name.')
@minLength(2)
@maxLength(60)
param searchServiceName string

@description('Azure AI Search SKU.')
@allowed([
  'basic'
  'standard'
])
param skuName string = 'basic'

@description('Number of replicas.')
@minValue(1)
@maxValue(12)
param replicaCount int = 1

@description('Common resource tags.')
param tags object

resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: searchServiceName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: skuName
  }
  properties: {
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: true
    hostingMode: 'Default'
    networkRuleSet: {
      bypass: 'None'
      ipRules: []
    }
    partitionCount: 1
    publicNetworkAccess: 'Enabled'
    replicaCount: replicaCount
    semanticSearch: 'free'
  }
}

output endpoint string = 'https://${search.name}.search.windows.net'
output id string = search.id
output name string = search.name
output principalId string = search.identity.principalId
