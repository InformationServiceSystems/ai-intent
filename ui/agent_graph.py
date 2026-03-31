"""Agent network visualization component using streamlit-agraph."""

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from agents.manifests import CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST


_AGENTS = [CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST]
_COLORS = {"central": "#FF6B6B", "stocks": "#4ECDC4", "bonds": "#45B7D1", "materials": "#F9A825"}
_DIMMED = "#CCCCCC"


def render_agent_graph(
    agents_consulted: list[str] | None = None,
    violations: list[str] | None = None,
) -> None:
    """Render the four-agent network graph with post-execution styling."""
    has_result = agents_consulted is not None
    consulted = set(agents_consulted or [])
    violated = set(violations or [])

    nodes = []
    edges = []

    for m in _AGENTS:
        size = 30 if m.agent_id == "central" else 20
        is_consulted = m.agent_id == "central" or m.agent_id in consulted

        if has_result and not is_consulted:
            color = _DIMMED
            opacity = 0.4
            label = f"{m.emoji} {m.name}"
        elif has_result and m.agent_id in violated:
            color = "#FF5722"
            opacity = 1.0
            label = f"{m.emoji} {m.name} [!]"
        else:
            color = _COLORS.get(m.agent_id, "#999")
            opacity = 1.0
            label = f"{m.emoji} {m.name}"

        nodes.append(Node(
            id=m.agent_id,
            label=label,
            size=size,
            color=color,
            opacity=opacity,
        ))

    for m in _AGENTS:
        if m.agent_id != "central":
            if has_result and m.agent_id not in consulted:
                edge_color = "#DDDDDD"
                dashes = True
            else:
                edge_color = "#888"
                dashes = False

            edges.append(Edge(
                source="central",
                target=m.agent_id,
                color=edge_color,
                dashes=dashes,
            ))

    config = Config(
        width=500,
        height=350,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
    )

    selected = agraph(nodes=nodes, edges=edges, config=config)
    if selected:
        st.session_state["selected_agent"] = selected
