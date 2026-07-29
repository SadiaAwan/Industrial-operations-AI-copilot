# ADR-0004: Use MLflow for agent tracing and evaluation

- Status: Accepted
- Date: 2026-07-28

## Context

The project must evaluate more than final text. It needs visibility into graph nodes, retrieval, tool selection, tool arguments, safety decisions, latency, token usage, cost, and regressions across versions.

## Decision

Use MLflow for agent-oriented tracing and evaluation records. Use operational telemetry such as Application Insights and Log Analytics alongside MLflow for service health, infrastructure metrics, and logs.

## Alternatives

### Application Insights only

Strong for application monitoring but not the selected primary store for versioned agent evaluations and AI-specific trace analysis.

### OpenTelemetry with a generic backend only

Provides portable traces but requires additional work to represent evaluation datasets, scorers, and experiment comparisons.

### LangSmith

Offers agent tracing and evaluation but adds another hosted platform and is less aligned with the desired MLflow/MLOps demonstration.

### Custom logging and evaluation database

Maximizes control but creates substantial undifferentiated platform work.

## Consequences

### Positive

- agent behavior and evaluation results share a coherent workflow
- prompt, model, dataset, and application versions can be compared
- confirmed failures can become tracked regression cases
- portfolio evidence includes measurable outcomes

### Negative

- MLflow requires storage, access control, and lifecycle management
- it overlaps partially with operational observability
- instrumentation must avoid sensitive content and hidden reasoning

### Constraints

- every request has a correlation ID shared with operational telemetry
- secrets and hidden chain-of-thought are not logged
- failure of MLflow must not fabricate or change diagnostic output
- retention and access policy are decided before production deployment
