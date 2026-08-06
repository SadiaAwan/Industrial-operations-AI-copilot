# Azure infrastructure deployment

Phase 14 provisions one isolated resource group per environment through
subscription-scope Bicep. Development, staging, and production must use separate
GitHub environments and may use separate Azure subscriptions when required by
organizational policy.

## Resource topology

The deployment creates:

- Azure Container Registry with local admin access disabled;
- separate user-assigned identities for API and UI;
- a VNet with delegated Container Apps and PostgreSQL subnets;
- PostgreSQL Flexible Server with private networking and Entra-only auth;
- Azure AI Search with local API-key authentication disabled;
- Key Vault using Azure RBAC and purge protection;
- Blob Storage using OAuth, with shared-key and public blob access disabled;
- Log Analytics and workspace-based Application Insights;
- a VNet-integrated Container Apps environment;
- independently scalable API and UI Container Apps with health probes.

Resource groups are fixed by the reviewed parameter files:

| Environment | Resource group |
|---|---|
| Development | `rg-industrial-ai-dev` |
| Staging | `rg-industrial-ai-staging` |
| Production | `rg-industrial-ai-prod` |

Parameter files contain no credentials. The zero GUID, placeholder administrator
name, and placeholder image tag are intentionally overridden by the deployment
workflow. Deployments must fail rather than use these placeholders.

## GitHub configuration

Configure these repository or environment variables:

- `AZURE_CLIENT_ID`: federated deployment identity application/client ID;
- `AZURE_TENANT_ID`: Microsoft Entra tenant ID;
- `AZURE_SUBSCRIPTION_ID`: target Azure subscription;
- `POSTGRES_ADMIN_OBJECT_ID`: object ID of a dedicated database-admin group;
- `POSTGRES_ADMIN_NAME`: display name of that group.

Azure authentication uses GitHub OIDC. Do not create a client secret. Give the
deployment identity only the permissions needed to deploy the declared resource
types and role assignments at the target scope.

Configure the GitHub `production` environment with required reviewers. Production
images must use the same immutable Git SHA tag that passed development/staging
verification.

## Validation and what-if

Every pull request runs:

```bash
az bicep lint --file infra/main.bicep
az bicep build --file infra/main.bicep --stdout
az bicep lint --file infra/subscription.bicep
az bicep build --file infra/subscription.bicep --stdout
az bicep build-params --file infra/environments/dev.bicepparam --stdout
```

The CI workflow repeats module and parameter compilation for every file. Static
tests reject secrets, broad role names, local authentication, shared storage keys,
public blobs, and missing environment isolation.

Run `deploy-dev.yml` in `what-if` mode first. Download and review the retained
what-if artifact before selecting deploy mode. For production, `deploy-prod.yml`
always creates and uploads a what-if artifact before the protected deployment job
can be approved.

Review the what-if for unexpected deletes, replacement of stateful resources,
public-network changes, role-scope expansion, SKU changes, and changes outside the
selected environment resource group.

## Least privilege

Runtime roles are intentionally limited:

| Identity | Scope | Role |
|---|---|---|
| API | ACR | AcrPull |
| API | Blob Storage | Storage Blob Data Reader |
| API | Key Vault | Key Vault Secrets User |
| API | Azure AI Search | Search Index Data Reader |
| UI | ACR | AcrPull |

The UI receives no database, search, storage, or Key Vault role. PostgreSQL
administration belongs to a dedicated Entra group, not the application identity.
After deployment, a database administrator creates a constrained application
database role for the API identity; the API must not run as the Entra administrator.

## Rollback

Container Apps use single-revision traffic with retained inactive revisions. Roll
back by redeploying the last approved immutable image tag. Database and network
resource replacement requires an explicit recovery plan and must never be approved
solely because a template compiles.
