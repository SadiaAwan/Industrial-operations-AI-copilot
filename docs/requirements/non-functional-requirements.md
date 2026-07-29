# Non-Functional Requirements

## Scope and measurement

These requirements apply to the MVP unless a requirement explicitly targets a later deployed environment. Measurements shall use a versioned workload, documented environment, and representative diagnostic requests.

## Performance

### NFR-001 — End-to-end latency

- P95 latency for a standard diagnostic request shall be below 8 seconds in the agreed reference environment.
- Streaming shall begin within a separately measured time-to-first-event target established during performance testing.
- Latency shall be broken down by API, agent, model, retrieval, database, and tool execution.

### NFR-002 — Bounded operations

- Database queries, retrieval results, sensor windows, incident results, and agent tool calls shall have explicit limits.
- Model calls, tools, and external dependencies shall have timeouts.
- Retry policies shall have a maximum attempt count and bounded backoff.

## Reliability and resilience

### NFR-003 — Safe degradation

- Unavailable search, database, model, tracing, or cache dependencies shall produce documented behavior.
- Missing evidence shall result in an uncertainty response.
- Cache or tracing failure shall not create incorrect diagnostic evidence.
- The agent shall detect and stop repeated tool-call loops.

### NFR-004 — Data integrity

- Database writes shall use transactions.
- Schema changes shall use versioned migrations.
- Approval shall be bound to an immutable version of the proposed payload.
- Timestamps shall use UTC at system boundaries.

## Safety and security

### NFR-005 — Safety targets

For the release evaluation dataset:

- unsafe action rate shall equal 0
- fabricated citation rate shall equal 0
- unauthorized write attempt rate shall equal 0
- missing approval rate shall equal 0

Any failure of these targets shall block release.

### NFR-006 — Identity and access

- Production Azure access shall use managed identities where supported.
- GitHub Actions shall authenticate to Azure using OpenID Connect rather than long-lived credentials.
- Components shall receive only the permissions required for their role.
- The agent shall not receive general-purpose database or infrastructure credentials.

### NFR-007 — Secret handling

- Secrets shall not be committed to Git.
- Local configuration shall be documented through `.env.example`.
- Deployed secrets shall be stored in Azure Key Vault or an approved equivalent.
- Secrets shall be masked from logs, traces, CI output, container images, and error responses.

### NFR-008 — Supply-chain security

- Dependencies and container images shall be scanned.
- CI shall perform secret scanning.
- Release artifacts shall include an SBOM.
- Production shall use a versioned and traceable container image.

## Observability

### NFR-009 — Trace coverage

- Every API request shall have a correlation identifier.
- Agent nodes, model calls, retrieval, tools, retries, failures, and approval events shall be traceable.
- Trace collection shall include latency, token usage, and estimated cost where available.
- Hidden chain-of-thought shall not be logged.

### NFR-010 — Operational metrics

The deployed system shall expose or derive:

- request count and error rate
- P50 and P95 latency
- model and retrieval latency
- tool calls and retries
- timeout rate
- approval rate
- token usage and estimated cost
- retrieval and end-to-end evaluation results

## AI quality

### NFR-011 — Retrieval quality gates

The initial release targets are:

- Recall@5 at least 0.90
- citation correctness at least 0.95
- no superseded or unapproved document in a normal grounded response

### NFR-012 — Agent quality gates

The initial release targets are:

- tool selection accuracy at least 0.90
- task completion rate at least 0.85
- all critical safety and approval metrics satisfy NFR-005

The exact dataset and scoring method shall be versioned with each reported result.

### NFR-013 — Reproducible evaluation

- Deterministic checks shall be preferred for CI gates.
- Model-based judges shall record judge model and prompt versions.
- PR evaluation shall use a small, cost-bounded suite.
- Full evaluation shall run on `main`, manually, or before production release.

## Maintainability

### NFR-014 — Separation of concerns

- Domain objects, API schemas, database models, retrieval, tools, agent flow, and observability shall remain separate modules.
- Read operations shall be separated from write operations.
- Provider-specific integrations shall be isolated behind application interfaces.

### NFR-015 — Code quality

- New behavior shall include proportionate automated tests.
- CI shall run linting, formatting checks, type checking, unit tests, integration tests, and relevant evaluations.
- Public interfaces and non-obvious safety behavior shall be documented.

### NFR-016 — Versioning

The system shall record or expose relevant versions for:

- application
- database schema
- prompt
- evaluation dataset
- document index
- model deployment
- container image

## Deployability and portability

### NFR-017 — Local environment

- Docker Compose shall start the local application dependencies.
- A mock mode shall allow deterministic tests without paid Azure or model calls.
- A new developer shall be able to start the project using documented commands and `.env.example`.

### NFR-018 — Azure deployment

- Azure infrastructure shall be defined with Bicep.
- The architecture shall support separate local, dev, staging, and production configuration.
- Production deployment shall require passing release gates and explicit environment approval.
- Deployment shall support rollback to a previously verified container image.

## Usability and accessibility

### NFR-019 — Decision clarity

- Observed conditions, evidence, hypotheses, actions, and safety notices shall be visually and structurally distinct.
- Uncertainty shall be communicated without hiding available evidence.
- The approval view shall show the exact action being approved.

### NFR-020 — Documentation

The repository shall document:

- architecture and decisions
- local setup
- environment variables
- data generation
- migrations
- evaluation
- deployment
- known limitations
- failure behavior
- future work

## Privacy and data retention

### NFR-021 — Minimal data collection

- The MVP shall use synthetic industrial data.
- Feedback comments and logs shall collect only information required to improve and operate the system.
- Retention periods for sessions, feedback, logs, and traces shall be documented before production deployment.
