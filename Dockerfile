FROM ghcr.io/astral-sh/uv:0.11.16 AS uv

FROM python:3.12.11-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=uv /uv /uvx /bin/
WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

FROM python:3.12.11-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --system --gid 10001 copilot \
    && adduser --system --uid 10001 --ingroup copilot --home /app copilot \
    && mkdir -p /app/mlartifacts \
    && chown copilot:copilot /app/mlartifacts

WORKDIR /app
COPY --from=builder --chown=copilot:copilot /app/.venv ./.venv
COPY --from=builder --chown=copilot:copilot /build/app ./app
COPY --from=builder --chown=copilot:copilot /build/migrations ./migrations
COPY --from=builder --chown=copilot:copilot /build/scripts ./scripts
COPY --from=builder --chown=copilot:copilot /build/alembic.ini ./alembic.ini

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
