targetScope = 'subscription'

@description('Dedicated resource group name for this environment.')
param resourceGroupName string

@description('Deployment environment.')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string

@description('Short workload name used in resource names.')
param workloadName string

@description('Azure region for the resource group and workload.')
param location string

@description('Immutable image tag, normally a Git SHA.')
param imageTag string

@description('Microsoft Entra object ID for the PostgreSQL administrator group.')
param postgresqlAdministratorObjectId string

@description('Display name for the PostgreSQL administrator group.')
param postgresqlAdministratorName string

@description('Common non-sensitive resource tags.')
param tags object

resource environmentResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: union(tags, {
    application: workloadName
    environment: environment
    managedBy: 'bicep'
  })
}

module application 'main.bicep' = {
  name: 'industrialOperationsCopilot'
  scope: environmentResourceGroup
  params: {
    environment: environment
    workloadName: workloadName
    location: location
    imageTag: imageTag
    postgresqlAdministratorObjectId: postgresqlAdministratorObjectId
    postgresqlAdministratorName: postgresqlAdministratorName
    tags: tags
  }
}

output apiFqdn string = application.outputs.apiFqdn
output resourceGroupId string = environmentResourceGroup.id
output uiFqdn string = application.outputs.uiFqdn
