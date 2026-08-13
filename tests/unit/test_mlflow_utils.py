"""Tests for fail-open MLflow application configuration."""

import sys
from types import SimpleNamespace

from pytest import MonkeyPatch

from app.config import Settings
from app.observability.mlflow_utils import configure_mlflow


def test_mlflow_is_disabled_without_tracking_uri() -> None:
    assert configure_mlflow(Settings(mlflow_tracking_uri=None)) is False


def test_mlflow_configures_tracking_experiment_and_langchain(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    fake_mlflow = SimpleNamespace(
        set_tracking_uri=lambda uri: calls.update(tracking_uri=uri),
        set_experiment=lambda name: calls.update(experiment=name),
        langchain=SimpleNamespace(
            autolog=lambda **options: calls.update(autolog=options)
        ),
    )
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    configured = configure_mlflow(
        Settings(
            mlflow_tracking_uri="http://mlflow:5000",
            mlflow_experiment_name="copilot-test",
        )
    )

    assert configured is True
    assert calls == {
        "tracking_uri": "http://mlflow:5000",
        "experiment": "copilot-test",
        "autolog": {
            "log_traces": True,
            "disable_for_unsupported_versions": True,
            "silent": True,
        },
    }
