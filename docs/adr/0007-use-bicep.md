# ADR-0007: Use Bicep for Azure infrastructure

- Status: Accepted
- Date: 2026-07-28

## Context

The target cloud is Azure, and the project must demonstrate reproducible Infrastructure as Code for Container Apps, AI Search, PostgreSQL, storage, identity, secrets, and observability.

## Decision

Use modular Bicep templates with separate non-secret parameter files for dev, staging, and production. Validate templates in CI and review deployment changes before applying them.

## Alternatives

### Terraform

Provides cloud-neutral workflows and a broad ecosystem, but adds state-management decisions and is not necessary for an Azure-focused portfolio.

### Pulumi

Allows general-purpose languages but introduces another runtime and dependency model for infrastructure.

### ARM JSON templates

Native to Azure but more verbose and less maintainable than Bicep.

### Manual Azure Portal configuration

Rejected because it is not reproducible, reviewable, or suitable for CI/CD.

## Consequences

### Positive

- native Azure resource coverage
- readable modules and compile-time validation
- no separate infrastructure state file
- clear alignment with the selected cloud

### Negative

- less portable to other cloud providers
- Azure resource APIs and deployment behavior still require specialist knowledge
- some runtime configuration cannot be validated until deployment

### Constraints

- no secrets in committed parameter files
- modules expose minimal outputs
- identity and role assignments use least privilege
- CI runs Bicep validation and deployment changes are reviewed
