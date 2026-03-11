"""Agent network visualization component using streamlit-agraph."""

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from agents.manifests import CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST


_AGENTS = [CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST]
_COLORS = {"central": "#FF6B6B", "stocks": "#4ECDC4", "bonds": "#45B7D1", "materials": "#F9A825"}


def render_agent_graph() -> None:
    """Render the four-agent network graph with clickable nodes."""
    nodes = []
    edges = []

    for m in _AGENTS:
        size = 30 if m.agent_id == "central" else 20
        nodes.append(Node(
            id=m.agent_id,
            label=f"{m.emoji} {m.name}",
            size=size,
            color=_COLORS.get(m.agent_id, "#999"),
        ))

    for m in _AGENTS:
        if m.agent_id != "central":
            edges.append(Edge(source="central", target=m.agent_id, color="#888"))

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
