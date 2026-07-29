# ADR-0009: Use a Microsoft Foundry-hosted model

- Status: Accepted
- Date: 2026-07-28

## Context

The agent needs a hosted language model capable of structured output and tool-oriented reasoning. The portfolio is intended to demonstrate Azure AI integration while retaining application-owned orchestration, safety, and evaluation.

## Decision

Use a model deployment accessed through Microsoft Foundry for the deployed environment. Isolate the model client behind an application adapter and provide a deterministic mock for local tests and CI. LangGraph remains responsible for workflow orchestration.

## Alternatives

### Direct non-Azure hosted model API

Could provide equivalent model capabilities but would weaken the intended Azure architecture and identity integration.

### Self-hosted open model

Offers model control but adds GPU, serving, scaling, and evaluation work outside the MVP focus.

### Fully managed Foundry agent orchestration

Reduces application orchestration work but hides graph behavior and creates stronger coupling to the managed agent runtime.

### Local model for all environments

Reduces external dependency but makes quality, hardware, and reproducibility harder to guarantee for this project scope.

## Consequences

### Positive

- aligns model access with the Azure target architecture
- supports managed identity and centralized Azure governance where available
- application retains explicit graph, tools, guardrails, and approvals
- model deployment versions can be traced and evaluated

### Negative

- cost, quota, region, and model availability affect deployment
- model upgrades may change behavior
- deterministic CI requires a mock rather than live calls

### Constraints

- the model has no direct database or infrastructure credentials
- model output is schema-, citation-, and safety-validated
- model and deployment versions are recorded
- live model calls are cost-bounded in evaluation
- application behavior must remain testable without network access
