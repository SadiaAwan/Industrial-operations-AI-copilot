"""Construction of the controlled LangGraph diagnostic workflow."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import AgentDependencies, AgentNodes
from app.agent.routing import (
    route_after_assessment,
    route_after_documents,
    route_after_generation,
    route_after_incidents,
    route_after_sensor,
    route_after_validation,
    route_from_intent,
)
from app.agent.state import AgentState
from app.observability.tracing import NullTracer, SafeAttribute, Tracer

AgentGraph = CompiledStateGraph[AgentState, None, AgentState, AgentState]


def _traced_node(
    name: str,
    node: Callable[[AgentState], dict[str, object] | Awaitable[dict[str, object]]],
    tracer: Tracer,
) -> Callable[..., Any]:
    @wraps(node)
    async def traced(state: AgentState) -> dict[str, object]:
        attributes: dict[str, SafeAttribute] = {"graph.node": name}
        for state_key in ("session_id", "machine_id"):
            value = state.get(state_key)
            if isinstance(value, str):
                attributes[f"agent.{state_key}"] = value
        with tracer.start_span(
            f"graph.{name}", span_type="CHAIN", attributes=attributes
        ) as span:
            result = node(state)
            if inspect.isawaitable(result):
                result = await result
            outcome = result.get("outcome")
            if outcome is not None:
                span.set_attribute("agent.outcome", str(outcome))
            return result

    return traced


def build_agent_graph(
    dependencies: AgentDependencies,
    *,
    tracer: Tracer | None = None,
) -> AgentGraph:
    """Build a graph whose tool and model dependencies are explicitly injected."""

    nodes = AgentNodes(dependencies)
    active_tracer = tracer or NullTracer()
    graph = StateGraph(AgentState)
    graph.add_node(
        "validate", _traced_node("validate", nodes.validate_request, active_tracer)
    )
    graph.add_node(
        "classify", _traced_node("classify", nodes.classify_request, active_tracer)
    )
    graph.add_node(
        "sensor", _traced_node("sensor", nodes.read_sensor_data, active_tracer)
    )
    graph.add_node(
        "documents", _traced_node("documents", nodes.search_documents, active_tracer)
    )
    graph.add_node(
        "incidents", _traced_node("incidents", nodes.search_incidents, active_tracer)
    )
    graph.add_node(
        "maintenance",
        _traced_node("maintenance", nodes.read_maintenance, active_tracer),
    )
    graph.add_node(
        "assess", _traced_node("assess", nodes.assess_evidence, active_tracer)
    )
    graph.add_node(
        "generate",
        _traced_node("generate", nodes.generate_recommendation, active_tracer),
    )
    graph.add_node(
        "draft", _traced_node("draft", nodes.create_work_order_draft, active_tracer)
    )
    graph.add_node("finalize", _traced_node("finalize", nodes.finalize, active_tracer))
    graph.add_node(
        "loop_limit", _traced_node("loop_limit", nodes.loop_limit, active_tracer)
    )

    graph.add_edge(START, "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "classify": "classify",
            "clarification": END,
            "safety_blocked": END,
            "loop_limit": "loop_limit",
        },
    )
    graph.add_conditional_edges(
        "classify",
        route_from_intent,
        {
            "sensor": "sensor",
            "documents": "documents",
            "incidents": "incidents",
            "maintenance": "maintenance",
        },
    )
    graph.add_conditional_edges(
        "sensor",
        route_after_sensor,
        {
            "documents": "documents",
            "assess": "assess",
            "finalize": "finalize",
        },
    )
    graph.add_conditional_edges(
        "documents",
        route_after_documents,
        {"incidents": "incidents", "assess": "assess"},
    )
    graph.add_conditional_edges(
        "incidents",
        route_after_incidents,
        {"maintenance": "maintenance", "assess": "assess"},
    )
    graph.add_edge("maintenance", "assess")
    graph.add_conditional_edges(
        "assess",
        route_after_assessment,
        {"generate": "generate", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "generate",
        route_after_generation,
        {
            "draft": "draft",
            "finalize": "finalize",
            "safety_blocked": END,
        },
    )
    graph.add_edge("draft", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("loop_limit", END)
    return graph.compile(name="industrial-operations-copilot")
