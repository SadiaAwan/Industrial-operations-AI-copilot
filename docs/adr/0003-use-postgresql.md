# ADR-0003: Use PostgreSQL for operational persistence

- Status: Accepted
- Date: 2026-07-28

## Context

Machines, sensor readings, maintenance records, incidents, sessions, feedback, approvals, and work orders are relational data with integrity and transactional requirements. Approval state and future write execution require reliable constraints and transactions.

## Decision

Use PostgreSQL with SQLAlchemy repositories and Alembic migrations. The agent accesses data only through bounded application tools and never receives unrestricted SQL access.

## Alternatives

### SQLite

Convenient for small local tests but not representative of concurrent, deployed operation or Azure PostgreSQL.

### Document database

Offers flexible records, but the core entities have stable relationships and transactional requirements that fit a relational model.

### Separate time-series database

Could optimize large sensor workloads, but the MVP uses bounded synthetic data and does not justify an additional datastore.

### Direct model-generated SQL

Flexible but conflicts with least privilege, predictable performance, and safety requirements.

## Consequences

### Positive

- strong relational integrity and transactions
- mature migration and tooling ecosystem
- consistent local and Azure deployment models
- approval and feedback records can be audited

### Negative

- schema evolution must be planned
- integration tests require PostgreSQL
- sensor-scale assumptions must be revisited before real streaming ingestion

### Constraints

- all schema changes use migrations
- repositories limit query scope and result size
- writes use transactions
- session and approval data use explicit retention policies before production
