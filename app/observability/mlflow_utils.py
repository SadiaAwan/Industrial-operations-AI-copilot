"""Fail-open MLflow configuration for application and agent tracing."""

from __future__ import annotations

from app.config import Settings


def configure_mlflow(settings: Settings) -> bool:
    """Configure remote tracking and LangChain tracing when explicitly enabled."""

    if not settings.mlflow_tracking_uri:
        return False

    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        if settings.mlflow_langchain_autolog:
            mlflow.langchain.autolog(
                log_traces=True,
                disable_for_unsupported_versions=True,
                silent=True,
            )
    except Exception:
        # Observability must never prevent the protected business operation.
        return False
    return True
