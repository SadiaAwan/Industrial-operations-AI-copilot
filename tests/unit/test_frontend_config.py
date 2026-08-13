"""Tests for environment-driven frontend configuration."""

from pytest import MonkeyPatch

from frontend.config import FrontendSettings


def test_machine_ids_accept_comma_separated_environment_value(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("COPILOT_UI_MACHINE_IDS", "P-104, P-205,P-307")

    settings = FrontendSettings(_env_file=None)

    assert settings.machine_ids == ("P-104", "P-205", "P-307")


def test_default_machine_ids_match_seeded_dataset(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("COPILOT_UI_MACHINE_IDS", raising=False)

    settings = FrontendSettings(_env_file=None)

    assert settings.machine_ids == ("P-101", "P-102", "P-103", "P-104", "P-105")


def test_machine_ids_accept_json_environment_value(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_UI_MACHINE_IDS", '["P-104", "P-205"]')

    settings = FrontendSettings(_env_file=None)

    assert settings.machine_ids == ("P-104", "P-205")
