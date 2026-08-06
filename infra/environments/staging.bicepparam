using '../main.bicep'

param environment = 'staging'
param workloadName = 'industrial-ai'
param location = 'swedencentral'
param imageTag = 'sha-replace-at-deploy'
param postgresqlAdministratorObjectId = '00000000-0000-0000-0000-000000000000'
param postgresqlAdministratorName = 'replace-at-deploy'
param tags = {
  costCenter: 'engineering'
  dataClassification: 'internal'
  owner: 'platform'
}
