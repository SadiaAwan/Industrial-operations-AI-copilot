# Industrial AI Operations Copilot

Industrial AI Operations Copilot is a production-like decision-support project for troubleshooting centrifugal pumps. It combines approved technical documentation, simulated sensor data, maintenance history, and historical incidents to produce transparent recommendations with verifiable sources.

The system is not an industrial control system. It does not control equipment, and every write action requires explicit human approval.

## Project status

Phases 0–13 include the domain model, synthetic data, PostgreSQL persistence,
retrieval, bounded agent tools, the LangGraph workflow, safety and approval
guardrails, API and UI delivery, observability, evaluation, feedback lifecycle,
and a containerized local environment.

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

## Run the operations interface

For the complete containerized environment, follow the
[local development guide](docs/operations/local-development.md). The short
version is:

```bash
cp .env.example .env
docker compose up --build --wait
```

For process-level development, start the services directly as described below.

Start the FastAPI service in one terminal:

```bash
uv run uvicorn app.main:app --reload
```

Start Streamlit in a second terminal:

```bash
uv run streamlit run frontend/streamlit_app.py
```

The UI uses `http://localhost:8000` by default. Copy `.env.example` to `.env`
to configure the API URL, timeout, and allow-listed machine IDs. The interface
is advisory: approval controls submit a human decision, while backend gates
remain authoritative for every write action.
