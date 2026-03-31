"""Side-by-side manifest constraint vs. agent response view for violations."""

from typing import Any

import streamlit as st

from agents.manifests import get_manifest
from mcp.logger import MCPMessage, get_logger


def render_manifest_diff(session_id: str) -> None:
    """Render constraint violation drill-down for all violations in a session."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    violation_msgs = [m for m in messages if m.response_status == "constraint_violation"]

    if not violation_msgs:
        st.caption("No constraint violations in this session.")
        return

    st.markdown(f"**{len(violation_msgs)} Constraint Violation(s) Detected:**")

    for msg in violation_msgs:
        agent_id = msg.from_agent
        try:
            manifest = get_manifest(agent_id)
        except KeyError:
            continue

        payload = msg.payload
        analysis = payload.get("analysis", "N/A")
        flags = msg.constraint_flags

        with st.container(border=True):
            st.markdown(f"### {manifest.emoji} {manifest.name}")

            left, right = st.columns(2)

            with left:
                st.markdown("**Manifest Constraints:**")
                for c in manifest.boundary_constraints:
                    st.markdown(f"- {c}")

                st.divider()
                st.markdown("**Risk Parameters:**")
                for k, v in manifest.risk_parameters.items():
                    st.markdown(f"- `{k}`: **{v}**")

            with right:
                st.markdown("**Agent Response:**")
                st.error(analysis)

                st.divider()
                st.markdown("**Constraint Flags Raised:**")
                if flags:
                    for f in flags:
                        st.markdown(f"- :red[{f}]")
                else:
                    st.caption("No specific flags (general out-of-scope)")

                st.divider()
                st.markdown("**Status Fields:**")
                st.markdown(f"- `out_of_scope`: **{payload.get('out_of_scope', 'N/A')}**")
                st.markdown(f"- `recommendation`: **{payload.get('recommendation', 'N/A')}**")
                st.markdown(f"- `confidence`: **{payload.get('confidence', 'N/A')}**")
