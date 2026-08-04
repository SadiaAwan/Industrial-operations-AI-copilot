"""Headless smoke test for the complete Streamlit entry point."""

from pytest import MonkeyPatch
from streamlit.testing.v1 import AppTest

from frontend.config import get_frontend_settings


def test_streamlit_app_fails_safely_when_api_is_offline(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("COPILOT_UI_API_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("COPILOT_UI_API_TIMEOUT_SECONDS", "0.1")
    get_frontend_settings.cache_clear()

    app = AppTest.from_file("frontend/streamlit_app.py", default_timeout=5).run()

    assert not app.exception
    assert any(title.value == "Industrial Operations Copilot" for title in app.title)
    assert any(error.value == "API unavailable" for error in app.error)
