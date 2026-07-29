# ADR-0001: Use LangGraph for agent orchestration

- Status: Accepted
- Date: 2026-07-28

## Context

The diagnostic workflow has explicit states and safety-sensitive transitions: validate the request, identify the machine, gather evidence, assess sufficiency, produce a recommendation, validate citations and safety, and pause for approval when required. The flow must be traceable, testable, and protected from uncontrolled tool loops.

## Decision

Use LangGraph to implement the operations-agent workflow. Keep domain logic, tools, and validation outside graph definitions so they can be tested independently. Represent request state with typed contracts and make routing decisions explicit.

## Alternatives

### Direct imperative Python orchestration

Simpler initially, but state transitions, retries, pause/resume, and approval routing would become custom framework code.

### General LangChain agent executor

Provides fast tool-calling setup, but offers less explicit control over deterministic states and safety-sensitive transitions.

### Microsoft Foundry managed agent orchestration

Reduces runtime management, but hides more orchestration behavior and increases provider coupling. Foundry remains the selected model runtime, not the source of application control policy.

### Multi-agent framework

Adds delegation complexity without improving the bounded centrifugal-pump MVP.

## Consequences

### Positive

- graph state and transitions are visible
- deterministic routes can be unit tested
- approval and recovery states can be represented explicitly
- node and tool tracing can be correlated
- the portfolio demonstrates orchestration rather than only prompt construction

### Negative

- the team must learn LangGraph concepts
- graph changes require schema and migration discipline for persisted sessions
- over-fragmenting nodes can make the flow harder to follow

### Constraints

- no hidden chain-of-thought is persisted
- retry and tool-call counts are bounded
- the graph may call only allow-listed application tools
- safety and approval controls cannot be delegated solely to prompts
