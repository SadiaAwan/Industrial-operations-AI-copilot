# Industrial AI Operations Copilot

Industrial AI Operations Copilot is a production-like decision-support project for troubleshooting centrifugal pumps. It combines approved technical documentation, simulated sensor data, maintenance history, and historical incidents to produce transparent recommendations with verifiable sources.

The system is not an industrial control system. It does not control equipment, and every write action requires explicit human approval.

## Project status

Phase 0 — requirements and architecture.

No application functionality has been implemented yet.

## Phase 0 documentation

- [Functional requirements](docs/requirements/functional-requirements.md)
- [Non-functional requirements](docs/requirements/non-functional-requirements.md)
- [Architecture principles](docs/architecture/architecture-principles.md)
- [System overview](docs/architecture/system-overview.md)
- [Sequence diagrams](docs/architecture/sequence-diagrams.md)
- [Azure architecture](docs/architecture/azure-architecture.md)
- [Development roadmap](docs/roadmap/development-roadmap.md)
- [Future work](docs/roadmap/future-work.md)
- [Architecture Decision Records](docs/adr/)

## Core principles

- Grounded by design
- Human-in-the-loop
- Safety first
- Observable by default
- Evaluation-driven development
- Least privilege
- Safe failure behavior

## MVP boundary

The MVP supports one equipment type, synthetic data, hybrid document retrieval, bounded tools, a controlled LangGraph agent, citations, and work-order drafts.

It excludes real equipment control, autonomous decisions, production SAP or IoT Hub integration, predictive maintenance, and multi-agent orchestration.

Implementation and local setup instructions will be added as the corresponding phases are completed.
