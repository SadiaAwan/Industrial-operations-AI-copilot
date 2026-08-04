"""Chat history and diagnostic prompt presentation."""

from __future__ import annotations

import streamlit as st

from frontend.components.recommendation import render_recommendation
from frontend.state import CopilotUIState


def render_chat_history(state: CopilotUIState) -> None:
    if not state.turns:
        st.info(
            "Ask about current condition, recent incidents, maintenance history, "
            "or a safety procedure."
        )
        return

    for turn in state.turns:
        with st.chat_message("user"):
            st.write(turn.user_message)
        with st.chat_message("assistant"):
            render_recommendation(turn.response.result, turn.metrics)
            st.caption(f"Request ID: {turn.response.request_id}")


def chat_prompt() -> str | None:
    return st.chat_input(
        "Ask about this machine…",
        max_chars=10_000,
    )
