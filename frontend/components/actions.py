"""Explicit human review controls for pending operational actions."""

from __future__ import annotations

import streamlit as st

from app.domain.approval import ApprovalAction
from app.domain.common import ApprovalStatus
from app.schemas.actions import ApprovalDecisionRequest
from frontend.api_client import CopilotAPIClient, CopilotAPIError
from frontend.state import CopilotUIState


def render_action_review(
    action: ApprovalAction,
    client: CopilotAPIClient,
    state: CopilotUIState,
) -> None:
    st.markdown("#### Human approval required")
    st.warning(
        "This is a proposed write action. Nothing is executed by these controls; "
        "the backend approval gate remains authoritative.",
        icon="⚠️",
    )
    st.write(f"**Action:** {action.action_type.replace('_', ' ').title()}")
    st.json(action.payload, expanded=True)
    st.caption(f"Action ID: {action.action_id}")
    st.code(action.payload_hash, language=None)
    st.caption(f"Approval expires: {action.expires_at.isoformat()}")

    if action.status != ApprovalStatus.PENDING:
        st.info(f"This action is already {action.status.value}.")
        return
    if action.action_id in state.decided_action_ids:
        st.info("A decision has already been submitted in this UI session.")
        return

    operator_id = st.text_input(
        "Operator ID",
        key=f"operator-{action.action_id}",
        placeholder="Required for an auditable decision",
    ).strip()
    approve_column, reject_column = st.columns(2)
    approve = approve_column.button(
        "Approve proposal",
        type="primary",
        disabled=not operator_id,
        key=f"approve-{action.action_id}",
        use_container_width=True,
    )
    reject = reject_column.button(
        "Reject proposal",
        disabled=not operator_id,
        key=f"reject-{action.action_id}",
        use_container_width=True,
    )
    if not approve and not reject:
        return

    try:
        decision = client.decide_action(
            action.action_id,
            ApprovalDecisionRequest(
                user_id=operator_id,
                payload_hash=action.payload_hash,
            ),
            approve=approve,
        )
    except CopilotAPIError as exception:
        st.error(str(exception))
        if exception.request_id:
            st.caption(f"Request ID: {exception.request_id}")
        return
    state.mark_action_decided(action.action_id)
    if decision.status == ApprovalStatus.APPROVED:
        st.success(
            "Proposal approved. Execution remains controlled by the backend gate."
        )
    else:
        st.info("Proposal rejected.")
