@description('Azure region for managed identities.')
param location string

@description('Resource name prefix.')
param namePrefix string

@description('Common resource tags.')
param tags object

resource apiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-api-id'
  location: location
  tags: tags
}

resource uiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-ui-id'
  location: location
  tags: tags
}

output apiClientId string = apiIdentity.properties.clientId
output apiPrincipalId string = apiIdentity.properties.principalId
output apiResourceId string = apiIdentity.id
output apiName string = apiIdentity.name
output uiClientId string = uiIdentity.properties.clientId
output uiPrincipalId string = uiIdentity.properties.principalId
output uiResourceId string = uiIdentity.id
output uiName string = uiIdentity.name
