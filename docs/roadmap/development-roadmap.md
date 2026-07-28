# Development Roadmap

## Delivery model

Work is delivered through short-lived branches and pull requests. No implementation is committed directly to `main`. Each phase ends with tests, documentation, observability where applicable, and verified exit criteria.

The roadmap is ordered by dependency: contracts and evidence foundations are completed before the agent, and measurable quality is established before deployment.

## Phase 0 — Requirements and architecture

Branch:

```text
docs/phase-00-requirements-architecture
```

Deliverables:

- functional and non-functional requirements
- architecture principles
- system and Azure architecture
- diagnostic, failure, feedback, and approval sequence diagrams
- Architecture Decision Records
- MVP scope and future-work boundary
- development roadmap

Exit criteria:

- requirements are testable
- central technical decisions have accepted ADRs
- diagrams agree with the intended trust and authorization boundaries
- no application implementation is required for this phase

## Phase 1 — Domain model and contracts

Branch:

```text
feature/phase-01-domain-model
```

Deliverables:

- domain entities and shared value objects
- Pydantic API, tool, and agent contracts
- units, timestamps, identifiers, enums, and validation
- structured diagnostic output
- contract tests

Exit criteria:

- database, tools, API, and agent can depend on stable contracts
- invalid boundary data is rejected

## Phase 2 — Synthetic data

Branch:

```text
feature/phase-02-synthetic-data
```

Deliverables:

- machine registry
- deterministic sensor scenarios
- manuals, procedures, and safety instructions
- incidents and maintenance records
- document metadata and revision conflicts
- initial evaluation questions

Exit criteria:

- generation is reproducible
- data validates against contracts
- normal, failure, and adversarial scenarios exist

## Phase 3 — PostgreSQL

Branch:

```text
feature/phase-03-postgresql-schema
```

Deliverables:

- SQLAlchemy models and repositories
- Alembic migrations
- seed workflow
- constraints and indexes
- database integration tests

Exit criteria:

- a clean database can be migrated and seeded without manual changes

## Phase 4 — Document pipeline and retrieval

Primary branch:

```text
feature/phase-04-retrieval-pipeline
```

Deliverables:

- extraction, normalization, section chunking, and metadata
- embeddings and Azure AI Search index
- hybrid retrieval and revision filtering
- structured citations
- retrieval evaluation

Initial gates:

- Recall@5 at least 0.90
- citation correctness at least 0.95
- no unapproved or superseded document in a normal response

Exit criteria:

- retrieval passes its gates before agent integration

## Phase 5 — Tool layer

Primary branch:

```text
feature/phase-05-tool-layer
```

Deliverables:

- document, sensor, incident, maintenance, and draft tools
- typed inputs and outputs
- limits, timeouts, retries, errors, and tracing
- tool behavior evaluation

Exit criteria:

- each tool works independently
- write proposals cannot bypass approval

## Phase 6 — LangGraph agent

Primary branch:

```text
feature/phase-06-langgraph-agent
```

Deliverables:

- state, nodes, graph, and routing
- evidence planning and assessment
- session state
- structured recommendations
- uncertainty and loop handling

Exit criteria:

- core diagnostic scenarios complete with correct tools and structured evidence

## Phase 7 — Guardrails and approval

Primary branch:

```text
feature/phase-07-guardrails-approval
```

Deliverables:

- citation and safety validation
- document revision enforcement
- pending, approved, rejected, and expired actions
- payload-bound approval and replay protection
- adversarial safety tests

Exit criteria:

- unsafe action, fabricated citation, unauthorized write, and missing approval rates are zero on the release dataset

## Phase 8 — FastAPI

Primary branch:

```text
feature/phase-08-fastapi
```

Deliverables:

- chat and streaming
- machine status and sessions
- approval, rejection, and feedback
- health and readiness
- request correlation and error mapping
- OpenAPI and contract tests

Exit criteria:

- clients can complete diagnostic and approval workflows through documented contracts

## Phase 9 — Streamlit UI

Primary branch:

```text
feature/phase-09-streamlit-ui
```

Deliverables:

- machine dashboard and sensor trends
- chat and evidence display
- risk, latency, tokens, and cost
- approval/rejection and feedback controls

Exit criteria:

- the end-to-end workflow is usable without direct API or database access

## Phase 10 — Observability

Primary branch:

```text
feature/phase-10-observability
```

Deliverables:

- MLflow traces
- structured logging and correlation
- metrics and dashboard
- token and cost tracking
- privacy and retention controls

Exit criteria:

- a request can be traced across API, agent, model, retrieval, tools, and approval

## Phase 11 — Evaluation framework

Primary branch:

```text
test/phase-11-evaluation-framework
```

Deliverables:

- at least 50 versioned cases
- retrieval, tool, safety, groundedness, citation, approval, latency, cost, and end-to-end scorers
- deterministic PR suite and full release suite
- CI-compatible gates and MLflow reporting

Exit criteria:

- regressions are reproducible and critical gates can block release

## Phase 12 — Feedback and prompt lifecycle

Branch:

```text
feature/phase-12-feedback-prompt-lifecycle
```

Deliverables:

- feedback linked to traces and versions
- prompt versioning
- curated feedback-to-evaluation workflow
- prompt comparison and release gate

Exit criteria:

- confirmed production failures can become regression tests and verified improvements

## Phase 13 — Local containers

Primary branch:

```text
infra/phase-13-local-containers
```

Deliverables:

- non-root application images
- Docker Compose services and health checks
- `.env.example`
- deterministic local mock mode
- startup documentation

Exit criteria:

- a new developer can start the system from a clean clone

## Phase 14 — Azure infrastructure

Primary branch:

```text
infra/phase-14-azure-bicep
```

Deliverables:

- modular Bicep
- environment parameters
- container, search, database, storage, identity, secrets, and monitoring resources
- Bicep validation and deployment review

Exit criteria:

- an environment can be reproduced without manual portal configuration

## Phase 15 — CI/CD

Primary branch:

```text
ci/phase-15-ci-cd-pipelines
```

Deliverables:

- PR lint, types, tests, eval, scans, image build, and SBOM
- full release evaluation
- OIDC-based deployment
- dev/staging smoke tests
- protected production approval
- rollback

Exit criteria:

- unreviewed, unsafe, untested, or untraceable changes cannot reach production

## Phase 16 — Failure handling

Primary branch:

```text
feature/phase-16-failure-resilience
```

Deliverables:

- bounded retry and timeout policy
- graceful degradation and readiness behavior
- dependency fallbacks
- automated failure-scenario tests

Exit criteria:

- every documented failure has a safe, tested outcome

## Phase 17 — Performance and cost

Primary branch:

```text
feature/phase-17-performance-cost
```

Deliverables:

- load and latency tests
- component latency budget
- token and cost report
- context and tool-call optimization
- caching with an invalidation policy when justified

Exit criteria:

- P95 target is met in the reference environment without quality-gate regression

## Phase 18 — Portfolio delivery

Primary branch:

```text
docs/phase-18-portfolio-delivery
```

Deliverables:

- complete README
- architecture and sequence diagrams
- demo and screenshots
- evaluation, latency, and cost results
- deployment instructions
- limitations, lessons learned, and future work
- final Definition of Done review

Exit criteria:

- another developer can understand, run, test, and assess the project from the repository

## Definition of Done summary

The project is complete when:

- at least three real bounded tools are used
- all document claims have verifiable citations
- retrieval and tool behavior satisfy defined gates
- unsafe and unauthorized action metrics are zero
- all writes require valid human approval
- MLflow traces the end-to-end agent flow
- at least 50 evaluation cases run in CI/release evaluation
- Docker Compose starts the local system
- Azure infrastructure is deployed with Bicep
- GitHub Actions provides gated CI/CD
- README documents architecture, results, limitations, and operation
