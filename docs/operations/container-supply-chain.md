# Container supply chain

Phase 15 builds the API and UI once from a commit that has passed the `CI`
workflow on `main`. The workflow scans the local images before publication,
generates SPDX SBOMs, and then pushes the same verified images to Azure Container
Registry (ACR).

## Trust boundaries

- Pull requests cannot publish images.
- The publisher runs only after a successful `CI` workflow on `main`.
- GitHub authenticates to Azure with OIDC; no Azure client secret or ACR password
  is stored in GitHub.
- Every third-party action in the security and publication workflows is pinned to
  an exact commit SHA.
- ACR local administrator access remains disabled by Bicep.
- High or critical Trivy findings block publication.
- SBOM and release-manifest artifacts are retained for 90 days.

## Required GitHub configuration

Configure the `development` environment with these non-secret variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_CONTAINER_REGISTRY_NAME`

The federated Azure identity needs only permission to read registry metadata and
push images to the development ACR. Do not configure `AZURE_CLIENT_SECRET` or ACR
admin credentials.

## Image identity

Each API and UI image receives two immutable identifiers:

- the full Git commit SHA, for source traceability;
- `build-<workflow-run-id>`, for CI run traceability.

The uploaded `release-manifest-<sha>` artifact records the full repository digest
for each image. Deployment workflows consume repository digests, not rebuilt
images or mutable environment tags.

## Pull-request security

The dedicated security workflow:

- rejects newly introduced dependencies with high or critical advisories;
- rejects AGPL dependencies that conflict with the distribution policy;
- scans complete Git history for committed secrets.

Repository branch protection should require both the `CI` and dependency/secret
security workflows before merge.

## Failure behavior

If build, vulnerability scanning, SBOM generation, OIDC login, or any push fails,
the workflow fails and no release manifest is produced. A partial registry push is
not eligible for deployment because deployment requires the complete manifest
containing both verified digests.
