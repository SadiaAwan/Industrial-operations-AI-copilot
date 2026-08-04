"""Structured recommendation, evidence, and runtime metadata presentation."""

from __future__ import annotations

import streamlit as st

from app.schemas.recommendations import AgentRecommendation
from frontend.state import InteractionMetrics


def _optional_metric(value: int | float | None, *, suffix: str = "") -> str:
    if value is None:
        return "Not reported"
    if isinstance(value, float):
        return f"{value:,.3f}{suffix}"
    return f"{value:,}{suffix}"


def render_recommendation(
    recommendation: AgentRecommendation, metrics: InteractionMetrics
) -> None:
    st.markdown(f"**Current condition:** {recommendation.current_condition}")

    severity, confidence, latency, cost = st.columns(4)
    severity.metric("Risk", recommendation.severity.value.title())
    confidence.metric("Confidence", f"{recommendation.confidence:.0%}")
    latency.metric("Latency", f"{metrics.latency_ms:,.0f} ms")
    cost.metric(
        "Estimated cost", _optional_metric(metrics.estimated_cost_usd, suffix=" USD")
    )

    token_caption = (
        f"Tokens: {_optional_metric(metrics.input_tokens)} input · "
        f"{_optional_metric(metrics.output_tokens)} output"
    )
    st.caption(token_caption)

    if recommendation.severity.value in {"high", "critical"}:
        st.error(recommendation.safety_notice, icon="🚨")
    else:
        st.warning(recommendation.safety_notice, icon="⚠️")

    if recommendation.observations:
        st.markdown("#### Observations")
        for observation in recommendation.observations:
            st.markdown(
                f"- {observation.statement}  \n"
                f"  _Source: {observation.source_type} · "
                f"{observation.source_reference}_"
            )

    if recommendation.possible_causes:
        st.markdown("#### Possible causes")
        for hypothesis in recommendation.possible_causes:
            st.markdown(f"**{hypothesis.cause}** · {hypothesis.confidence:.0%}")
            st.progress(hypothesis.confidence)

    if recommendation.recommended_checks:
        st.markdown("#### Recommended checks")
        for index, check in enumerate(recommendation.recommended_checks, start=1):
            safety_label = " · Safety-critical" if check.safety_critical else ""
            st.markdown(
                f"{index}. **{check.instruction}**{safety_label}  \n"
                f"   {check.rationale}"
            )

    with st.expander(f"Evidence and sources ({len(recommendation.citations)})"):
        if not recommendation.citations:
            st.info("No document citations were returned for this response.")
        for citation in recommendation.citations:
            st.markdown(
                f"**{citation.title}** · revision {citation.revision}  \n"
                f"Section: {citation.section}  \n"
                f"Document: `{citation.document_id}` · Chunk: `{citation.chunk_id}`"
            )

    with st.expander(f"Tools used ({len(recommendation.tool_calls)})"):
        if not recommendation.tool_calls:
            st.caption("No tools were reported.")
        for tool_call in recommendation.tool_calls:
            icon = "✅" if tool_call.status == "succeeded" else "⚠️"
            st.write(f"{icon} {tool_call.tool_name} · {tool_call.status}")
