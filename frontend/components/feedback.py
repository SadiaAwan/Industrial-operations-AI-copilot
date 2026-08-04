"""Per-response helpfulness feedback controls."""

from __future__ import annotations

import streamlit as st

from app.domain.common import FeedbackRating
from app.schemas.chat import ChatResponse
from app.schemas.feedback import FeedbackCreate
from frontend.api_client import CopilotAPIClient, CopilotAPIError
from frontend.state import CopilotUIState


def render_feedback(
    response: ChatResponse,
    client: CopilotAPIClient,
    state: CopilotUIState,
) -> None:
    if response.request_id in state.submitted_feedback_request_ids:
        st.caption("Feedback submitted · Thank you")
        return

    with st.expander("Was this response helpful?"):
        comment = st.text_area(
            "Optional comment",
            max_chars=2_000,
            key=f"feedback-comment-{response.request_id}",
        )
        helpful_column, unhelpful_column = st.columns(2)
        helpful = helpful_column.button(
            "Helpful",
            key=f"helpful-{response.request_id}",
            use_container_width=True,
        )
        unhelpful = unhelpful_column.button(
            "Not helpful",
            key=f"unhelpful-{response.request_id}",
            use_container_width=True,
        )
        if not helpful and not unhelpful:
            return
        rating = FeedbackRating.HELPFUL if helpful else FeedbackRating.NOT_HELPFUL
        try:
            client.submit_feedback(
                FeedbackCreate(
                    session_id=response.session_id,
                    request_id=response.request_id,
                    rating=rating,
                    comment=comment or None,
                )
            )
        except CopilotAPIError as exception:
            st.error(str(exception))
            if exception.request_id:
                st.caption(f"Request ID: {exception.request_id}")
            return
        state.mark_feedback_submitted(response.request_id)
        st.success("Feedback submitted")
