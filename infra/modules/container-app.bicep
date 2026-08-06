@description('Azure region for the Container App.')
param location string

@description('Container App resource name.')
param appName string

@description('Container Apps managed environment resource ID.')
param managedEnvironmentId string

@description('Immutable container image reference.')
param image string

@description('Application container target port.')
param targetPort int

@description('HTTP health endpoint.')
param healthPath string

@description('Non-sensitive environment variables.')
param environmentVariables array = []

@description('Minimum application replicas.')
@minValue(0)
param minReplicas int = 0

@description('Maximum application replicas.')
@minValue(1)
param maxReplicas int = 3

@description('Common resource tags.')
param tags object

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        targetPort: targetPort
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
        transport: 'auto'
      }
      maxInactiveRevisions: 5
    }
    template: {
      containers: [
        {
          name: appName
          image: image
          env: environmentVariables
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: healthPath
                port: targetPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: healthPath
                port: targetPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
          ]
          resources: {
            cpu: 0.5
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output id string = app.id
output name string = app.name
output principalId string = app.identity.principalId
