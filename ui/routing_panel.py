"""Routing decision visualization component."""

import streamlit as st

from agents.manifests import get_manifest
from agents.orchestrator import ROUTING_INSTRUCTION
from mcp.logger import MCPMessage


def render_routing_panel(route_msg: MCPMessage) -> None:
    """Render the full routing decision panel with instruction, matrix, and constraint overlay."""
    payload = route_msg.payload
    agents_to_call = payload.get("agents_to_call", [])

    # A. Routing Instruction Display
    with st.expander("Routing Instruction (sent to orchestrator LLM)", expanded=False):
        st.code(ROUTING_INSTRUCTION, language="text")

    # B. Agent Selection Matrix
    st.markdown("**Agent Selection Matrix:**")

    all_agents = ["stocks", "bonds", "materials"]
    rows = []
    for agent_id in all_agents:
        manifest = get_manifest(agent_id)
        selected = agent_id in agents_to_call
        sub_q = payload.get(f"query_for_{agent_id}")
        rows.append({
            "Agent": f"{manifest.emoji} {manifest.name}",
            "Selected": "Yes" if selected else "No",
            "Sub-Question": sub_q if selected and sub_q else ("*(original query)*" if selected else "---"),
        })

    for row in rows:
        c1, c2, c3 = st.columns([0.25, 0.10, 0.65])
        with c1:
            st.markdown(row["Agent"])
        with c2:
            if row["Selected"] == "Yes":
                st.markdown(":green[Yes]")
            else:
                st.markdown(":gray[No]")
        with c3:
            st.caption(row["Sub-Question"])

    # C. Routing Rationale
    rationale = payload.get("routing_rationale", "N/A")
    st.divider()
    st.markdown(f"**Rationale:** {rationale}")
