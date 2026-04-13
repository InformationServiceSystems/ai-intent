"""Agent intent manifest display component with dialog pop-up."""

import streamlit as st
import pandas as pd

from agents.manifests import get_manifest
from mcp.logger import get_logger


@st.dialog("Agent Intent Manifest", width="large")
def show_agent_dialog(agent_id: str, session_id: str | None = None) -> None:
    """Pop-up dialog showing the agent's full manifest with constraint status."""
    try:
        manifest = get_manifest(agent_id)
    except KeyError:
        st.warning(f"Unknown agent: {agent_id}")
        return

    constraint_status = _get_constraint_status(agent_id, session_id) if session_id else None

    # Header
    st.markdown(f"## {manifest.emoji} {manifest.name}")
    st.markdown(f"**Role:** {manifest.role}")

    st.divider()

    # Intent Scope
    st.markdown("### Intent Scope")
    st.info(manifest.intent_scope)

    # Boundary Constraints
    st.markdown("### Boundary Constraints")
    for i, c in enumerate(manifest.boundary_constraints):
        if constraint_status and i < len(constraint_status):
            icon, color = constraint_status[i]
            st.markdown(f"{icon} :{color}[{c}]")
        else:
            st.markdown(f"- {c}")

    st.divider()

    # Risk Parameters
    st.markdown("### Risk Parameters")
    params_df = pd.DataFrame(
        [{"Parameter": k, "Value": str(v)} for k, v in manifest.risk_parameters.items()]
    )
    st.dataframe(params_df, use_container_width=True, hide_index=True)

    st.divider()

    # Plain Language Summary
    st.markdown("### Plain Language Summary")
    st.success(manifest.plain_language_summary)

    # Active Disposition (if any)
    active_disps = st.session_state.get("active_dispositions", {})
    disp = active_disps.get(agent_id)
    if disp:
        active_vals = {k: v for k, v in disp.model_dump().items() if v > 0}
        if active_vals:
            st.divider()
            st.markdown("### Active Disposition")
            st.warning("This agent has behavioral dispositions that may cause it to drift from its mandate.")
            for factor, value in active_vals.items():
                label = factor.replace("_", " ").title()
                bar_color = "normal" if value < 0.7 else "inverse" if value < 0.9 else "inverse"
                st.markdown(f"**{label}:** {value:.1f}")
                st.progress(value)


def render_intent_panel(agent_id: str, session_id: str | None = None) -> None:
    """Render a compact agent card; clicking it opens the full dialog."""
    try:
        manifest = get_manifest(agent_id)
    except KeyError:
        return

    with st.container(border=True):
        st.markdown(f"**{manifest.emoji} {manifest.name}**")
        st.caption(manifest.role)
        st.caption(f"Intent: {manifest.intent_scope[:80]}...")
        st.caption(f"{len(manifest.boundary_constraints)} constraints | {len(manifest.risk_parameters)} risk params")

        if st.button("View Full Manifest", key=f"dialog_{agent_id}"):
            show_agent_dialog(agent_id, session_id)


def _get_constraint_status(agent_id: str, session_id: str) -> list[tuple[str, str]] | None:
    """Look up constraint enforcement status for an agent from MCP log."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    result_msg = None
    for msg in messages:
        if msg.method == f"{agent_id}.result":
            result_msg = msg
            break

    if result_msg is None:
        return None

    manifest = get_manifest(agent_id)
    flags = result_msg.constraint_flags
    out_of_scope = result_msg.payload.get("out_of_scope", False)

    statuses = []
    for constraint in manifest.boundary_constraints:
        if out_of_scope:
            statuses.append((":x:", "red"))
        elif any(_keyword_overlap(constraint, f) for f in flags):
            statuses.append((":warning:", "orange"))
        else:
            statuses.append((":white_check_mark:", "green"))

    return statuses


def _keyword_overlap(constraint: str, flag: str) -> bool:
    """Check if a flag relates to a constraint via keyword overlap."""
    c_words = set(w.lower().strip(",:;()") for w in constraint.split() if len(w) > 3)
    f_words = set(w.lower().strip(",:;()_-") for w in flag.replace("_", " ").split() if len(w) > 3)
    return bool(c_words & f_words)
