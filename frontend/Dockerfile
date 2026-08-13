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
COPY frontend ./frontend
RUN uv sync --frozen --no-dev

FROM python:3.12.11-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501

RUN addgroup --system --gid 10001 copilot \
    && adduser --system --uid 10001 --ingroup copilot --home /app copilot

WORKDIR /app
COPY --from=builder --chown=copilot:copilot /app/.venv ./.venv
COPY --from=builder --chown=copilot:copilot /build/app ./app
COPY --from=builder --chown=copilot:copilot /build/frontend ./frontend

USER 10001:10001
EXPOSE 8501

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)"]

CMD ["streamlit", "run", "frontend/streamlit_app.py"]
