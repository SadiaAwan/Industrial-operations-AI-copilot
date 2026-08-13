# Local development

The containerized local environment runs PostgreSQL, database initialization,
an MLflow tracking server, the FastAPI service, and the Streamlit interface
without Azure credentials or paid model calls.

## Prerequisites

- Docker Engine or Docker Desktop with Docker Compose v2
- Git

## Start from an empty environment

Copy the documented local defaults and start the stack:

```bash
cp .env.example .env
docker compose up --build --wait
```

Compose waits for PostgreSQL, applies every Alembic migration, seeds the
deterministic synthetic dataset, starts the API, and then starts the UI.

Open:

- Streamlit UI: <http://localhost:8501>
- FastAPI documentation: <http://localhost:8000/docs>
- MLflow tracing UI: <http://localhost:5001>
- API liveness: <http://localhost:8000/health>

Inspect container state and logs with:

```bash
docker compose ps
docker compose logs --follow api ui mlflow
```

MLflow stores trace and experiment metadata in an isolated `mlflow` database
inside the local PostgreSQL service. Artifacts are served through the tracking
server and persisted in the `copilot_mlflow_artifacts` Docker volume. FastAPI
uses `http://mlflow:5000` internally and records explicit request spans plus
supported LangChain/LangGraph traces in the `industrial-operations-copilot`
experiment. Tracing fails open, so an MLflow outage cannot change a diagnostic
result.

After submitting a diagnostic request in Streamlit, open MLflow and select the
copilot experiment to inspect its traces. The browser uses port 5000; container
clients must continue using the Compose hostname `mlflow`.

## Configuration

`.env.example` contains local-only defaults. Change host ports if 5432, 5001,
8000, or 8501 are already in use. Compose supplies internal database, MLflow,
and API addresses; do not replace container hostnames with `localhost` inside
Compose.

The local stack intentionally has no Azure Search key or model endpoint. Its
startup, database, health, and interface paths therefore require no paid cloud
access. Cloud-backed diagnostic execution is configured only in deployed
environments.

## Database lifecycle

Migrations and seeding are an explicit, idempotent `database-init` service. Run
that step again after adding a migration:

```bash
docker compose run --rm database-init
```

Stop containers while retaining PostgreSQL data:

```bash
docker compose down
```

To perform a clean-start verification, remove only this project's named volume
and rebuild:

```bash
docker compose down --volumes
docker compose up --build --wait
```

`docker compose down --volumes` deletes the local Copilot database volume. Do
not use it when the local data must be retained.

## Run checks outside containers

With the locked development environment installed:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy app frontend tests evaluation scripts
uv run pytest -q
```

Container-specific smoke checks are documented in the phase 13 smoke-test
module and skip automatically when Docker is unavailable.
