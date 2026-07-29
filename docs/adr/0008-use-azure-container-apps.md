# ADR-0008: Use Azure Container Apps for application runtime

- Status: Accepted
- Date: 2026-07-28

## Context

The API and frontend need a managed container runtime with independent deployment, revisions, health probes, scaling, managed identity, and a lower operational burden than managing Kubernetes.

## Decision

Deploy the FastAPI API and Streamlit frontend as separate Azure Container Apps. Use versioned images from Azure Container Registry and promote a verified image through environments.

## Alternatives

### Azure Kubernetes Service

Provides maximum orchestration control but introduces cluster administration and complexity not justified by the MVP.

### Azure App Service

Is a viable managed web runtime, but Container Apps better matches the multi-container local setup and revision-oriented deployment goal.

### Azure Functions

Fits event-driven short-lived workloads but is less natural for the streaming API, frontend, and long-running service processes.

### Virtual machines

Provide control but require operating-system and runtime management.

## Consequences

### Positive

- managed container environment
- independent API and frontend scaling
- revisions support verification and rollback
- integration with ACR, managed identity, and logging

### Negative

- platform-specific limits and networking behavior must be tested
- cold starts may affect latency at scale-to-zero
- Streamlit session behavior requires deployment testing

### Constraints

- containers run as non-root
- health and readiness probes are configured
- secrets are injected at runtime
- production uses a previously tested immutable image
- deployment retains a rollback path
