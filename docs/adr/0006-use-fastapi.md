# ADR-0006: Use FastAPI for the application API

- Status: Accepted
- Date: 2026-07-28

## Context

The application needs typed HTTP contracts, streaming, generated API documentation, dependency injection, health checks, and strong integration with Python domain and agent code.

## Decision

Use FastAPI with Pydantic request and response models. Keep routing thin and delegate domain behavior to application services, the agent, and tools.

## Alternatives

### Flask

Flexible and lightweight, but requires more manual work for typed validation, OpenAPI, and modern async endpoints.

### Django and Django REST Framework

Mature and feature rich, but heavier than required for the focused service and duplicates persistence patterns already selected.

### gRPC

Efficient for service-to-service calls but less convenient for the browser-facing MVP and interactive API documentation.

### Streamlit-only backend

Fast for a demo but mixes UI and application boundaries and weakens independent API testing and deployment.

## Consequences

### Positive

- shared Pydantic contracts
- automatic OpenAPI documentation
- async and streaming support
- straightforward health, readiness, and test clients

### Negative

- async code can be blocked by incorrectly implemented synchronous dependencies
- generated documentation does not replace contract tests
- authentication and rate limiting still require explicit design

### Constraints

- route handlers contain no core safety policy
- external errors are mapped to structured safe responses
- liveness and readiness are separate
- internal stack traces and secrets are not returned to clients
