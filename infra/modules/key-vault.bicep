@description('Azure region for Key Vault.')
param location string

@description('Globally unique Key Vault name.')
@minLength(3)
@maxLength(24)
param vaultName string

@description('Microsoft Entra tenant ID.')
param tenantId string = tenant().tenantId

@description('Days to retain deleted vaults and secrets.')
@minValue(7)
@maxValue(90)
param retentionInDays int = 90

@description('Common resource tags.')
param tags object

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: retentionInDays
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

output id string = vault.id
output name string = vault.name
output uri string = vault.properties.vaultUri
