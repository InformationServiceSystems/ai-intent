"""Intent lifecycle timeline component showing the 5-phase orchestration flow."""

from typing import Any

import streamlit as st

from agents.manifests import CENTRAL_MANIFEST, get_manifest, _MANIFEST_REGISTRY
from mcp.logger import MCPMessage, get_logger


def _find_message(messages: list[MCPMessage], method: str) -> MCPMessage | None:
    """Return the first message matching a method name."""
    for m in messages:
        if m.method == method:
            return m
    return None


def _find_agent_messages(messages: list[MCPMessage], agent_id: str) -> tuple[MCPMessage | None, MCPMessage | None]:
    """Return the outbound and inbound messages for a sub-agent."""
    outbound = None
    inbound = None
    for m in messages:
        if m.method == f"{agent_id}.analyze":
            outbound = m
        elif m.method == f"{agent_id}.result":
            inbound = m
    return outbound, inbound


def _find_compliance_gate(messages: list[MCPMessage], checkpoint: str, agent_id: str | None = None) -> dict[str, Any]:
    """Extract compliance gate status for a checkpoint from MCP messages.

    Returns dict with keys: status ('approved'|'revision'|'blocked'|'pending'),
    revision_count, violated_rules, messages (list of compliance MCPMessages).
    """
    gate: dict[str, Any] = {"status": "pending", "revision_count": 0, "violated_rules": [], "messages": []}

    for m in messages:
        method = m.method

        if checkpoint == "routing":
            if method in ("compliance.approve.central", "compliance.reject.central"):
                # Only count routing-checkpoint messages (from evaluate_routing)
                payload = m.payload or {}
                if payload.get("checkpoint") == "routing":
                    gate["messages"].append(m)
            elif method == "compliance.block.routing":
                gate["messages"].append(m)
                gate["status"] = "blocked"
                return gate

        elif checkpoint == "analysis" and agent_id:
            if method in (f"compliance.approve.{agent_id}", f"compliance.reject.{agent_id}"):
                payload = m.payload or {}
                if payload.get("checkpoint") == "analysis":
                    gate["messages"].append(m)
            elif method == f"compliance.block.{agent_id}":
                gate["messages"].append(m)
                gate["status"] = "blocked"
                gate["violated_rules"] = (m.payload or {}).get("violated_rules", [])
                return gate
            elif method == f"compliance.revision.{agent_id}":
                gate["messages"].append(m)
                gate["revision_count"] += 1

        elif checkpoint == "synthesis":
            if method in ("compliance.approve.central", "compliance.reject.central"):
                payload = m.payload or {}
                if payload.get("checkpoint") == "synthesis":
                    gate["messages"].append(m)
            elif method == "compliance.block.synthesis":
                gate["messages"].append(m)
                gate["status"] = "blocked"
                return gate

    # Determine final status from messages
    if not gate["messages"]:
        return gate

    last = gate["messages"][-1]
    if "approve" in last.method:
        gate["status"] = "approved"
    elif "reject" in last.method:
        gate["status"] = "revision"
    else:
        gate["status"] = "revision"

    # Extract violated rules from last rejection
    for gm in reversed(gate["messages"]):
        payload = gm.payload or {}
        rules = payload.get("violated_rules", [])
        if rules:
            gate["violated_rules"] = rules
            break

    return gate


def _render_gate_badge(gate: dict[str, Any], label: str) -> None:
    """Render a compact compliance gate shield badge."""
    status = gate["status"]
    rev = gate["revision_count"]

    if status == "approved" and rev == 0:
        st.markdown(f"🛡️ :green[**{label}** — Approved]")
    elif status == "approved" and rev > 0:
        st.markdown(f"🛡️ :orange[**{label}** — Approved after {rev} revision(s)]")
    elif status == "revision":
        st.markdown(f"🛡️ :orange[**{label}** — Revision requested]")
    elif status == "blocked":
        st.markdown(f"🛡️ :red[**{label}** — BLOCKED]")
    else:
        st.markdown(f"🛡️ :gray[**{label}** — Pending]")


def _render_gate_indicator(gate: dict[str, Any], label: str) -> None:
    """Render a compact gate indicator for the phase bar."""
    status = gate["status"]
    rev = gate["revision_count"]

    if status == "approved" and rev == 0:
        st.markdown(f"<div style='text-align:center;padding-top:4px'>"
                    f"🛡️<br><span style='color:#22c55e;font-size:0.75em'><b>{label}</b></span></div>",
                    unsafe_allow_html=True)
    elif status == "approved" and rev > 0:
        st.markdown(f"<div style='text-align:center;padding-top:4px'>"
                    f"🛡️<br><span style='color:#f59e0b;font-size:0.75em'><b>{label}</b> ({rev}↻)</span></div>",
                    unsafe_allow_html=True)
    elif status == "revision":
        st.markdown(f"<div style='text-align:center;padding-top:4px'>"
                    f"🛡️<br><span style='color:#f59e0b;font-size:0.75em'><b>{label}</b> ↻</span></div>",
                    unsafe_allow_html=True)
    elif status == "blocked":
        st.markdown(f"<div style='text-align:center;padding-top:4px'>"
                    f"🛡️<br><span style='color:#ef4444;font-size:0.75em'><b>{label}</b> ✕</span></div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:center;padding-top:4px'>"
                    f"🛡️<br><span style='color:#9ca3af;font-size:0.75em'><b>{label}</b></span></div>",
                    unsafe_allow_html=True)


def render_intent_timeline(session_id: str, result: Any | None = None) -> None:
    """Render the 5-phase intent lifecycle timeline for a session."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    if not messages:
        st.caption("No timeline data for this session.")
        return

    # Phase labels and icons
    phases = [
        ("1. Query", "inbox_tray"),
        ("2. Routing", "compass"),
        ("3. Delegation", "arrows_counterclockwise"),
        ("4. Synthesis", "alembic"),
        ("5. Response", "outbox_tray"),
    ]

    # Determine which phases are complete based on messages present
    query_msg = _find_message(messages, "user.query")
    route_msg = _find_message(messages, "intent.route")
    synth_msg = _find_message(messages, "intent.synthesize")
    response_msg = _find_message(messages, "investment.response")

    agent_ids = []
    if route_msg and route_msg.payload.get("agents_to_call"):
        agent_ids = [a for a in route_msg.payload["agents_to_call"] if a in _MANIFEST_REGISTRY]

    phase_complete = [
        query_msg is not None,
        route_msg is not None,
        any(_find_agent_messages(messages, a)[1] is not None for a in agent_ids) if agent_ids else False,
        synth_msg is not None,
        response_msg is not None,
    ]

    # Compliance gate status for each checkpoint
    cp1_gate = _find_compliance_gate(messages, "routing")
    cp2_gates = {aid: _find_compliance_gate(messages, "analysis", aid) for aid in agent_ids}
    cp3_gate = _find_compliance_gate(messages, "synthesis")

    # Render phase indicator bar with compliance gates between phases
    # Layout: Phase | Gate | Phase | Gate | Phase | Gate | Phase | Phase
    #          1     CP1     2      CP2     3      CP3     4       5
    col_spec = [2, 1, 2, 1, 2, 1, 2, 2]
    bar_cols = st.columns(col_spec)

    phase_col_indices = [0, 2, 4, 6, 7]
    gate_col_indices = [1, 3, 5]

    for idx, (label, icon) in enumerate(phases):
        with bar_cols[phase_col_indices[idx]]:
            if phase_complete[idx]:
                st.markdown(f"**:green[{label}]**")
                st.progress(1.0)
            else:
                st.markdown(f":gray[{label}]")
                st.progress(0.0)

    # Gate between Phase 1 (Query) and Phase 2 (Routing) — CP1
    with bar_cols[gate_col_indices[0]]:
        _render_gate_indicator(cp1_gate, "CP1")

    # Gate between Phase 2 (Routing) and Phase 3 (Delegation) — CP2 (aggregate)
    with bar_cols[gate_col_indices[1]]:
        cp2_statuses = [g["status"] for g in cp2_gates.values()]
        if "blocked" in cp2_statuses:
            agg_status = "blocked"
        elif "revision" in cp2_statuses:
            agg_status = "revision"
        elif cp2_statuses and all(s == "approved" for s in cp2_statuses):
            agg_status = "approved"
        else:
            agg_status = "pending"
        agg_revisions = sum(g["revision_count"] for g in cp2_gates.values())
        _render_gate_indicator({"status": agg_status, "revision_count": agg_revisions}, "CP2")

    # Gate between Phase 4 (Synthesis) and Phase 5 (Response) — CP3
    with bar_cols[gate_col_indices[2]]:
        _render_gate_indicator(cp3_gate, "CP3")

    # Expandable detail per phase (includes gate details)
    tab_labels = [p[0] for p in phases]
    tabs = st.tabs(tab_labels)

    # Phase 1: Query Received
    with tabs[0]:
        if query_msg:
            st.markdown(f"**Query:** {query_msg.payload.get('query', '')}")
            st.caption(f"Logged at {query_msg.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        else:
            st.caption("Awaiting query...")

    # Phase 2: Intent Routing + CP1 gate
    with tabs[1]:
        if route_msg:
            _render_gate_badge(cp1_gate, "CP1 — Routing Compliance")
            st.divider()
            _render_routing_phase(route_msg, agent_ids)
        else:
            st.caption("Awaiting routing decision...")

    # Phase 3: Agent Delegation + CP2 gates
    with tabs[2]:
        if agent_ids:
            # Per-agent compliance gate badges
            for aid in agent_ids:
                g = cp2_gates.get(aid, {"status": "pending", "revision_count": 0, "violated_rules": [], "messages": []})
                manifest = get_manifest(aid)
                _render_gate_badge(g, f"CP2 — {manifest.name}")
                if g["violated_rules"]:
                    st.caption(f"Violated: {', '.join(g['violated_rules'][:3])}")
            st.divider()
            _render_delegation_phase(messages, agent_ids, route_msg)
        else:
            st.caption("No agents delegated yet...")

    # Phase 4: Synthesis + CP3 gate
    with tabs[3]:
        if synth_msg:
            _render_gate_badge(cp3_gate, "CP3 — Synthesis Compliance")
            st.divider()
            _render_synthesis_phase(synth_msg, messages, agent_ids, result)
        else:
            st.caption("Awaiting synthesis...")

    # Phase 5: Response
    with tabs[4]:
        if response_msg:
            _render_response_phase(response_msg, messages, result)
        else:
            st.caption("Awaiting final response...")


def _render_routing_phase(route_msg: MCPMessage, agent_ids: list[str]) -> None:
    """Render the routing decision details."""
    payload = route_msg.payload

    # Routing rationale
    rationale = payload.get("routing_rationale", "N/A")
    st.markdown(f"**Routing Rationale:** {rationale}")

    st.divider()

    # Agent selection matrix
    st.markdown("**Agent Selection Matrix:**")
    all_agents = ["stocks", "bonds", "materials"]
    for agent_id in all_agents:
        selected = agent_id in agent_ids
        sub_q = payload.get(f"query_for_{agent_id}")
        manifest = get_manifest(agent_id)

        if selected and sub_q:
            st.markdown(f"  {manifest.emoji} **{manifest.name}** — :green[Selected]")
            st.caption(f"  Sub-question: *{sub_q}*")
        elif selected:
            st.markdown(f"  {manifest.emoji} **{manifest.name}** — :green[Selected]")
            st.caption("  Sub-question: *(original query forwarded)*")
        else:
            st.markdown(f"  {manifest.emoji} **{manifest.name}** — :gray[Not consulted]")

    st.divider()

    # Orchestrator constraint overlay
    st.markdown("**Orchestrator Constraints (Routing Phase):**")
    num_selected = len(agent_ids)
    constraints_status = [
        (CENTRAL_MANIFEST.boundary_constraints[0], f"Satisfied ({num_selected} agents selected)" if num_selected >= 1 else "VIOLATED"),
        (CENTRAL_MANIFEST.boundary_constraints[1], "Will be checked at synthesis"),
        (CENTRAL_MANIFEST.boundary_constraints[2], "Satisfied (all calls logged via MCP)"),
        (CENTRAL_MANIFEST.boundary_constraints[3], "Will be checked at synthesis"),
        (CENTRAL_MANIFEST.boundary_constraints[4], "Will be checked at synthesis"),
    ]
    for constraint, status in constraints_status:
        if "Satisfied" in status:
            st.markdown(f"- :green[{constraint}] — *{status}*")
        elif "VIOLATED" in status:
            st.markdown(f"- :red[{constraint}] — *{status}*")
        else:
            st.markdown(f"- :gray[{constraint}] — *{status}*")


def _render_delegation_phase(messages: list[MCPMessage], agent_ids: list[str], route_msg: MCPMessage | None) -> None:
    """Render per-agent delegation cards."""
    agent_cols = st.columns(len(agent_ids)) if agent_ids else []

    for i, agent_id in enumerate(agent_ids):
        outbound, inbound = _find_agent_messages(messages, agent_id)
        manifest = get_manifest(agent_id)

        with agent_cols[i]:
            with st.container(border=True):
                st.markdown(f"**{manifest.emoji} {manifest.name}**")

                # Sub-question sent
                if outbound:
                    q = outbound.payload.get("query", "")
                    st.caption(f"Query: {q[:120]}{'...' if len(q) > 120 else ''}")

                # Constraints active
                with st.expander("Active Constraints", expanded=False):
                    for c in manifest.boundary_constraints:
                        st.markdown(f"- {c}")

                # Response
                if inbound:
                    result = inbound.payload
                    out_of_scope = result.get("out_of_scope", False)
                    recommendation = result.get("recommendation", "N/A")
                    confidence = result.get("confidence", "N/A")

                    if out_of_scope:
                        st.error(f"Out of scope")
                    else:
                        st.success(f"{recommendation} ({confidence})")

                    flags = inbound.constraint_flags
                    if flags:
                        st.markdown(f":red[Flags: {', '.join(flags)}]")
                else:
                    st.caption("Awaiting response...")


def _render_synthesis_phase(synth_msg: MCPMessage, messages: list[MCPMessage], agent_ids: list[str], result: Any | None) -> None:
    """Render the synthesis phase with side-by-side sub-agent results."""
    st.markdown("**Sub-Agent Results Fed Into Synthesis:**")

    if agent_ids:
        cols = st.columns(len(agent_ids))
        for i, agent_id in enumerate(agent_ids):
            _, inbound = _find_agent_messages(messages, agent_id)
            manifest = get_manifest(agent_id)
            with cols[i]:
                st.markdown(f"**{manifest.emoji} {agent_id}**")
                if inbound:
                    analysis = inbound.payload.get("analysis", "")
                    st.caption(analysis[:200] + ("..." if len(analysis) > 200 else ""))
                    rec = inbound.payload.get("recommendation", "N/A")
                    st.markdown(f"Rec: `{rec}`")
                else:
                    st.caption("No result")

    st.divider()
    st.markdown("**Synthesis Output:**")
    final = synth_msg.payload.get("final_recommendation", "")
    st.info(final[:500] + ("..." if len(final) > 500 else ""))


def _render_response_phase(response_msg: MCPMessage, messages: list[MCPMessage], result: Any | None) -> None:
    """Render the final response phase with accountability summary."""
    payload = response_msg.payload
    st.markdown("**Final Recommendation:**")
    st.success(payload.get("final_recommendation", "N/A"))

    st.markdown("**Accountability Note:**")
    st.info(payload.get("accountability_note", "N/A"))

    # Aggregate constraint check summary
    violation_msgs = [m for m in messages if m.response_status == "constraint_violation"]
    total_flags = sum(len(m.constraint_flags) for m in messages if m.constraint_flags)

    st.divider()
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Messages", len(messages))
    with col_b:
        st.metric("Constraint Flags", total_flags)
    with col_c:
        st.metric("Violations", len(violation_msgs))
