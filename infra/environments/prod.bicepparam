using '../subscription.bicep'

param resourceGroupName = 'rg-industrial-ai-prod'
param environment = 'prod'
param workloadName = 'industrial-ai'
param location = 'swedencentral'
param apiImageReference = 'replace-at-deploy'
param uiImageReference = 'replace-at-deploy'
param postgresqlAdministratorObjectId = '00000000-0000-0000-0000-000000000000'
param postgresqlAdministratorName = 'replace-at-deploy'
param tags = {
  costCenter: 'operations'
  dataClassification: 'confidential'
  owner: 'platform'
}
