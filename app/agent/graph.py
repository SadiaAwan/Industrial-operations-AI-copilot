"""Construction of the controlled LangGraph diagnostic workflow."""

from __future__ import annotations

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

AgentGraph = CompiledStateGraph[AgentState, None, AgentState, AgentState]


def build_agent_graph(dependencies: AgentDependencies) -> AgentGraph:
    """Build a graph whose tool and model dependencies are explicitly injected."""

    nodes = AgentNodes(dependencies)
    graph = StateGraph(AgentState)
    graph.add_node("validate", nodes.validate_request)
    graph.add_node("classify", nodes.classify_request)
    graph.add_node("sensor", nodes.read_sensor_data)
    graph.add_node("documents", nodes.search_documents)
    graph.add_node("incidents", nodes.search_incidents)
    graph.add_node("maintenance", nodes.read_maintenance)
    graph.add_node("assess", nodes.assess_evidence)
    graph.add_node("generate", nodes.generate_recommendation)
    graph.add_node("draft", nodes.create_work_order_draft)
    graph.add_node("finalize", nodes.finalize)
    graph.add_node("loop_limit", nodes.loop_limit)

    graph.add_edge(START, "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "classify": "classify",
            "clarification": END,
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
        {"draft": "draft", "finalize": "finalize"},
    )
    graph.add_edge("draft", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("loop_limit", END)
    return graph.compile(name="industrial-operations-copilot")
