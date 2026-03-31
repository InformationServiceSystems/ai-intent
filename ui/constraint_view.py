"""Per-agent and aggregate constraint enforcement display."""

from typing import Any

import streamlit as st

from agents.manifests import get_manifest
from mcp.logger import MCPMessage, get_logger


def _classify_constraint(constraint: str, flags: list[str], out_of_scope: bool, analysis: str) -> tuple[str, str]:
    """Classify a constraint as passed, flagged, violated, or not applicable."""
    constraint_lower = constraint.lower()
    analysis_lower = analysis.lower()

    # Check if this constraint was explicitly mentioned in flags or analysis
    flag_match = any(
        _fuzzy_match(constraint_lower, f.lower()) for f in flags
    )
    analysis_match = _fuzzy_match(constraint_lower, analysis_lower)

    if out_of_scope and (flag_match or analysis_match):
        return "violated", "Violated — agent declined request citing this constraint"
    elif flag_match:
        return "flagged", "Flagged — agent raised this as a concern"
    elif out_of_scope:
        return "violated", "Violated — request was out of scope"
    else:
        return "passed", "Passed"


def _fuzzy_match(constraint: str, text: str) -> bool:
    """Check if key terms from a constraint appear in text."""
    # Extract significant words from constraint
    keywords = []
    for word in constraint.split():
        word = word.strip(",:;()").lower()
        if len(word) > 3 and word not in ("must", "only", "than", "more", "less", "that", "this", "with", "from", "have", "each", "every", "should"):
            keywords.append(word)
    if not keywords:
        return False
    matches = sum(1 for kw in keywords if kw in text)
    return matches >= max(1, len(keywords) // 3)


def render_constraint_view(session_id: str, sub_agent_results: dict[str, Any] | None = None) -> None:
    """Render the constraint enforcement view with per-agent tabs."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    if not messages:
        st.caption("No constraint data for this session.")
        return

    # Find which agents were consulted
    agent_results: dict[str, MCPMessage] = {}
    for msg in messages:
        if msg.method.endswith(".result"):
            agent_id = msg.method.replace(".result", "")
            agent_results[agent_id] = msg

    if not agent_results:
        st.caption("No agent results to analyze.")
        return

    agent_ids = list(agent_results.keys())
    tab_labels = [f"{get_manifest(a).emoji} {a.title()}" for a in agent_ids] + ["All Agents"]
    tabs = st.tabs(tab_labels)

    # Per-agent tabs
    for i, agent_id in enumerate(agent_ids):
        with tabs[i]:
            _render_agent_constraints(agent_id, agent_results[agent_id])

    # All Agents summary tab
    with tabs[-1]:
        _render_summary_matrix(agent_ids, agent_results)


def _render_agent_constraints(agent_id: str, result_msg: MCPMessage) -> None:
    """Render constraint audit for a single agent."""
    manifest = get_manifest(agent_id)
    payload = result_msg.payload
    flags = result_msg.constraint_flags
    out_of_scope = payload.get("out_of_scope", False)
    analysis = payload.get("analysis", "")

    st.markdown(f"**{manifest.emoji} {manifest.name}**")
    st.caption(f"Intent Scope: {manifest.intent_scope}")

    st.divider()

    # Boundary Constraints with status
    st.markdown("**Boundary Constraints:**")
    for constraint in manifest.boundary_constraints:
        status, detail = _classify_constraint(constraint, flags, out_of_scope, analysis)
        icon = {"passed": ":white_check_mark:", "flagged": ":warning:", "violated": ":x:", "na": ":heavy_minus_sign:"}[status]
        color = {"passed": "green", "flagged": "orange", "violated": "red", "na": "gray"}[status]
        st.markdown(f"{icon} :{color}[{constraint}]")
        if status != "passed":
            st.caption(f"    *{detail}*")

    st.divider()

    # Risk Parameters
    st.markdown("**Risk Parameters:**")
    for param, value in manifest.risk_parameters.items():
        st.markdown(f"- `{param}`: **{value}**")

    st.divider()

    # Agent Response Summary
    st.markdown("**Agent Response:**")
    rec = payload.get("recommendation", "N/A")
    conf = payload.get("confidence", "N/A")
    col_r, col_c, col_o = st.columns(3)
    with col_r:
        st.metric("Recommendation", rec)
    with col_c:
        st.metric("Confidence", conf)
    with col_o:
        if out_of_scope:
            st.error("Out of Scope")
        else:
            st.success("In Scope")


def _render_summary_matrix(agent_ids: list[str], agent_results: dict[str, MCPMessage]) -> None:
    """Render aggregate constraint matrix across all agents."""
    st.markdown("**Constraint Enforcement Summary:**")

    for agent_id in agent_ids:
        manifest = get_manifest(agent_id)
        msg = agent_results[agent_id]
        flags = msg.constraint_flags
        out_of_scope = msg.payload.get("out_of_scope", False)
        analysis = msg.payload.get("analysis", "")

        violations = 0
        flagged = 0
        passed = 0

        for constraint in manifest.boundary_constraints:
            status, _ = _classify_constraint(constraint, flags, out_of_scope, analysis)
            if status == "violated":
                violations += 1
            elif status == "flagged":
                flagged += 1
            else:
                passed += 1

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.35, 0.20, 0.20, 0.25])
            with c1:
                st.markdown(f"**{manifest.emoji} {manifest.name}**")
            with c2:
                st.markdown(f":green[{passed} passed]")
            with c3:
                if flagged:
                    st.markdown(f":orange[{flagged} flagged]")
                else:
                    st.markdown(":gray[0 flagged]")
            with c4:
                if violations:
                    st.markdown(f":red[{violations} violated]")
                else:
                    st.markdown(":gray[0 violated]")
