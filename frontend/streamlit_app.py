"""Streamlit entry point for the Industrial Operations Copilot."""

from __future__ import annotations

from time import perf_counter
from typing import cast

import streamlit as st

from app.schemas.chat import ChatRequest
from frontend.api_client import APIClientConfig, CopilotAPIClient, CopilotAPIError
from frontend.components import (
    chat_prompt,
    render_chat_history,
    render_machine_dashboard,
)
from frontend.config import FrontendSettings, get_frontend_settings
from frontend.state import CopilotUIState, InteractionMetrics

STATE_KEY = "copilot_ui_state"


@st.cache_resource
def api_client(base_url: str, timeout_seconds: float) -> CopilotAPIClient:
    return CopilotAPIClient(
        APIClientConfig(base_url=base_url, timeout_seconds=timeout_seconds)
    )


def ui_state() -> CopilotUIState:
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = CopilotUIState()
    return cast(CopilotUIState, st.session_state[STATE_KEY])


def render_sidebar(
    settings: FrontendSettings, state: CopilotUIState, client: CopilotAPIClient
) -> None:
    with st.sidebar:
        st.title("Operations Copilot")
        st.caption("Grounded decision support for centrifugal pumps")
        selected_machine = st.selectbox(
            "Machine",
            settings.machine_ids,
            index=settings.machine_ids.index(state.selected_machine_id)
            if state.selected_machine_id in settings.machine_ids
            else 0,
        )
        state.select_machine(selected_machine)
        st.divider()
        try:
            readiness = client.readiness()
        except CopilotAPIError:
            st.error("API unavailable", icon="🚨")
        else:
            if readiness.status == "ready":
                st.success("Systems ready", icon="✅")
            else:
                st.warning("Limited availability", icon="⚠️")
                for dependency in readiness.dependencies:
                    st.caption(f"{dependency.name}: {dependency.status}")
        st.divider()
        st.caption("Advisory only · Human approval required for write actions")


def render_dashboard(client: CopilotAPIClient, state: CopilotUIState) -> None:
    st.title("Industrial Operations Copilot")
    st.write(
        "Monitor machine condition, investigate evidence, and review safe next steps."
    )
    try:
        status = client.get_machine_status(state.selected_machine_id)
    except CopilotAPIError as exception:
        st.error(str(exception))
        if exception.request_id:
            st.caption(f"Request ID: {exception.request_id}")
        return
    render_machine_dashboard(status)

    st.divider()
    st.subheader("Diagnostic copilot")
    render_chat_history(state)
    prompt = chat_prompt()
    if prompt is None:
        return

    started = perf_counter()
    try:
        with st.spinner("Gathering grounded evidence…"):
            response = client.chat(
                ChatRequest(
                    message=prompt,
                    session_id=state.session_id,
                    machine_id=state.selected_machine_id,
                )
            )
    except CopilotAPIError as exception:
        st.error(str(exception))
        if exception.request_id:
            st.caption(f"Request ID: {exception.request_id}")
        return
    state.record_turn(
        prompt,
        response,
        InteractionMetrics(latency_ms=(perf_counter() - started) * 1_000),
    )
    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Industrial Operations Copilot",
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    settings = get_frontend_settings()
    state = ui_state()
    client = api_client(settings.api_base_url, settings.api_timeout_seconds)
    render_sidebar(settings, state, client)
    render_dashboard(client, state)


if __name__ == "__main__":
    main()
