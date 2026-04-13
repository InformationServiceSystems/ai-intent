"""Streamlit entry point for the AI-Intent Investment System."""

import asyncio
import json
from uuid import uuid4

import streamlit as st

from agents.manifests import DispositionProfile
from agents.orchestrator import run
from mcp.logger import get_logger
from ui.agent_graph import render_agent_graph
from ui.constraint_view import render_constraint_view
from ui.intent_flow import render_intent_flow
from ui.intent_panel import render_intent_panel
from ui.intent_timeline import render_intent_timeline
from ui.manifest_diff import render_manifest_diff
from ui.mcp_stream import render_mcp_stream
from ui.revision_history import render_revision_history

st.set_page_config(
    layout="wide",
    page_title="AI-Intent Investment System",
    page_icon="\U0001f9e0",
)


def _generate_trace(result) -> dict:
    """Build the accountability trace dict from an OrchestrationResult."""
    logger = get_logger()
    messages = logger.get_session(result.session_id)

    all_constraints = []
    constraint_checks = []
    for agent_id, agent_result in result.sub_agent_results.items():
        flags = agent_result.get("constraint_flags", [])
        violations = []
        if agent_result.get("out_of_scope"):
            violations.append(agent_result.get("analysis", "out of scope"))
        constraint_checks.append({"agent": agent_id, "constraints_applied": flags, "violations": violations})
        all_constraints.extend(flags)

    return {
        "session_id": result.session_id,
        "generated_at": messages[-1].timestamp.isoformat() if messages else "",
        "framework": "AI-Intent v1.0",
        "query": result.query,
        "agents_consulted": result.agents_consulted,
        "routing_rationale": result.routing_rationale,
        "constraint_checks": constraint_checks,
        "compliance_verdicts": result.compliance_verdicts,
        "total_revisions": result.total_revisions,
        "forced_blocks": result.forced_blocks,
        "mcp_message_count": len(messages),
        "final_recommendation_summary": result.final_recommendation,
        "full_mcp_log": [m.model_dump(mode="json") for m in messages],
    }


def _format_trace_text(trace: dict) -> str:
    """Format an accountability trace dict as a human-readable text report."""
    lines = [
        "=" * 60,
        "AI-INTENT ACCOUNTABILITY TRACE",
        "=" * 60,
        f"Framework: {trace['framework']}",
        f"Session:   {trace['session_id']}",
        f"Generated: {trace['generated_at']}",
        "",
        "QUERY:",
        f"  {trace['query']}",
        "",
        "AGENTS CONSULTED:",
    ]
    for a in trace["agents_consulted"]:
        lines.append(f"  - {a}")
    lines.append("")
    lines.append("ROUTING RATIONALE:")
    lines.append(f"  {trace['routing_rationale']}")
    lines.append("")
    lines.append("CONSTRAINT CHECKS:")
    for check in trace["constraint_checks"]:
        lines.append(f"  Agent: {check['agent']}")
        lines.append(f"    Applied: {', '.join(check['constraints_applied']) or 'none'}")
        lines.append(f"    Violations: {', '.join(check['violations']) or 'none'}")
    lines.append("")
    lines.append("COMPLIANCE GATE:")
    lines.append(f"  Total revisions: {trace['total_revisions']}")
    lines.append(f"  Forced blocks: {', '.join(trace['forced_blocks']) or 'none'}")
    lines.append(f"  Checkpoints evaluated: {len(trace['compliance_verdicts'])}")
    lines.append("")
    lines.append(f"MCP MESSAGES: {trace['mcp_message_count']}")
    lines.append("")
    lines.append("RECOMMENDATION:")
    lines.append(f"  {trace['final_recommendation_summary']}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_compliance_log(session_id: str) -> None:
    """Render a regulator-readable log of compliance verdicts only."""
    from mcp.logger import get_logger
    from agents.manifests import get_manifest, _MANIFEST_REGISTRY
    logger = get_logger()
    messages = logger.get_session(session_id)

    # Filter to compliance approve/reject/block/revision messages only
    compliance_msgs = [
        m for m in messages
        if m.method.startswith("compliance.approve")
        or m.method.startswith("compliance.reject")
        or m.method.startswith("compliance.block")
        or m.method.startswith("compliance.revision")
    ]

    if not compliance_msgs:
        st.caption("No compliance verdicts for this session.")
        return

    # Summary counts
    approvals = [m for m in compliance_msgs if m.method.startswith("compliance.approve")]
    rejections = [m for m in compliance_msgs if m.method.startswith("compliance.reject")]
    blocks = [m for m in compliance_msgs if m.method.startswith("compliance.block")]
    revisions = [m for m in compliance_msgs if m.method.startswith("compliance.revision")]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Approved", len(approvals))
    with c2:
        st.metric("Rejected", len(rejections))
    with c3:
        st.metric("Blocked", len(blocks))
    with c4:
        st.metric("Revisions", len(revisions))

    st.divider()

    for msg in compliance_msgs:
        ts = msg.timestamp.strftime("%H:%M:%S.%f")[:-3]
        method = msg.method

        if method.startswith("compliance.approve"):
            icon = ":white_check_mark:"
            color = "green"
            label = "APPROVED"
        elif method.startswith("compliance.block"):
            icon = ":red_circle:"
            color = "red"
            label = "BLOCKED"
        elif method.startswith("compliance.reject"):
            icon = ":x:"
            color = "orange"
            label = "REJECTED"
        elif method.startswith("compliance.revision"):
            icon = ":warning:"
            color = "orange"
            label = "REVISION REQUEST"
        else:
            icon = ":heavy_minus_sign:"
            color = "gray"
            label = method

        agent_id = method.split(".")[-1]
        try:
            manifest = get_manifest(agent_id) if agent_id in _MANIFEST_REGISTRY else None
            agent_label = f"{manifest.emoji} {manifest.name}" if manifest else agent_id
        except KeyError:
            agent_label = agent_id

        with st.expander(f"{icon} [{ts}] :{color}[{label}] — {agent_label}"):
            payload = msg.payload

            # Show violated rules if present
            violated = payload.get("violated_rules", [])
            if violated:
                st.markdown("**Violated Rules:**")
                for rule_id in violated:
                    st.markdown(f"- `{rule_id}`")

            # Show regulatory basis
            basis = payload.get("regulatory_basis", [])
            if basis:
                st.markdown(f"**Regulatory Basis:** {', '.join(basis)}")

            # Show rejection reasons
            reasons = payload.get("rejection_reasons", [])
            if reasons:
                st.markdown("**Rejection Reasons:**")
                for r in reasons[:5]:
                    st.caption(r[:200])

            # Show revision instruction
            instruction = payload.get("revision_instruction") or payload.get("revision_feedback")
            if instruction:
                st.warning(instruction[:500])

            # Expandable full payload
            with st.expander("Full Payload", expanded=False):
                st.json(payload)


# --- Sidebar ---
with st.sidebar:
    st.title("\U0001f9e0 AI-Intent Investment System")
    st.markdown(
        "The **AI-Intent framework** ensures that every agent action is "
        "**explicit** (governed by a machine-readable mandate), "
        "**bounded** (constrained by verifiable rules the agent cannot silently violate), "
        "and **auditable** (every inter-agent message is logged and retrievable). "
        "A **Compliance Gate Agent** intercepts all inter-agent messages, "
        "evaluating them against manifest constraints before forwarding."
    )

    st.divider()

    # Disposition controls
    st.subheader("Agent Dispositions")
    st.caption("Adjust behavioral dispositions to test how agents drift from their mandates. Higher values create stronger pressure toward constraint breaches.")

    def _on_preset_change():
        """Clear cached results when disposition preset changes."""
        for key in ("last_result", "current_session_id", "view_session_id"):
            st.session_state.pop(key, None)

    disposition_preset = st.selectbox(
        "Preset",
        ["Neutral", "Aggressive Broker", "Reckless Portfolio", "Groupthink", "Custom"],
        key="disposition_preset",
        on_change=_on_preset_change,
    )

    _PRESETS = {
        "Neutral": {},
        "Aggressive Broker": {
            "stocks": DispositionProfile(self_serving=0.9, risk_seeking=0.8, overconfident=0.7),
            "bonds": DispositionProfile(risk_seeking=0.9, self_serving=0.8, overconfident=0.7),
            "materials": DispositionProfile(risk_seeking=0.9, self_serving=0.8, overconfident=0.7),
        },
        "Reckless Portfolio": {
            "central": DispositionProfile(risk_seeking=0.8, conformist=0.6),
            "stocks": DispositionProfile(risk_seeking=0.9, overconfident=0.8),
            "bonds": DispositionProfile(risk_seeking=0.7, anti_customer=0.6),
            "materials": DispositionProfile(risk_seeking=0.9, self_serving=0.7),
        },
        "Groupthink": {
            "central": DispositionProfile(conformist=0.9, anti_customer=0.5),
            "stocks": DispositionProfile(conformist=0.8, overconfident=0.6),
            "bonds": DispositionProfile(conformist=0.8),
            "materials": DispositionProfile(conformist=0.8),
        },
    }

    if disposition_preset == "Custom":
        with st.expander("Custom Disposition Settings", expanded=True):
            agent_to_configure = st.selectbox(
                "Agent", ["stocks", "bonds", "materials", "central"], key="disp_agent"
            )
            d_self = st.slider("Self-serving", 0.0, 1.0, 0.0, 0.1, key=f"d_self_{agent_to_configure}")
            d_risk = st.slider("Risk-seeking", 0.0, 1.0, 0.0, 0.1, key=f"d_risk_{agent_to_configure}")
            d_conf = st.slider("Overconfident", 0.0, 1.0, 0.0, 0.1, key=f"d_conf_{agent_to_configure}")
            d_anti = st.slider("Anti-customer", 0.0, 1.0, 0.0, 0.1, key=f"d_anti_{agent_to_configure}")
            d_group = st.slider("Conformist", 0.0, 1.0, 0.0, 0.1, key=f"d_group_{agent_to_configure}")

            custom_disps = st.session_state.get("custom_dispositions", {})
            custom_disps[agent_to_configure] = DispositionProfile(
                self_serving=d_self,
                risk_seeking=d_risk,
                overconfident=d_conf,
                anti_customer=d_anti,
                conformist=d_group,
            )
            st.session_state["custom_dispositions"] = custom_disps

        dispositions = st.session_state.get("custom_dispositions", {})
    else:
        dispositions = _PRESETS.get(disposition_preset, {})

    st.session_state["active_dispositions"] = dispositions

    # Show active dispositions summary
    active = {k: v for k, v in dispositions.items() if any(val > 0 for val in v.model_dump().values())}
    if active:
        for agent_id, disp in active.items():
            vals = {k: v for k, v in disp.model_dump().items() if v > 0}
            st.caption(f"  {agent_id}: {vals}")
    else:
        st.caption("  All agents neutral")

    st.divider()

    # Session history
    st.subheader("Session History")
    logger = get_logger()
    sessions = logger.get_all_sessions()
    if sessions:
        selected_history = st.selectbox("Past sessions", sessions, index=None, placeholder="Select a session...")
        if selected_history:
            st.session_state["view_session_id"] = selected_history
    else:
        st.caption("No sessions yet.")

# --- Determine active session and result ---
result = st.session_state.get("last_result")
active_session = st.session_state.get("current_session_id") or st.session_state.get("view_session_id")

# Extract post-execution state for graph styling
agents_consulted = result.agents_consulted if result else None
violation_agents = []
compliance_status = None
if result:
    for agent_id, agent_result in result.sub_agent_results.items():
        if agent_result.get("out_of_scope"):
            violation_agents.append(agent_id)
    if result.forced_blocks:
        compliance_status = "forced_block"
    elif result.total_revisions > 0:
        compliance_status = "revision_requested"
    else:
        compliance_status = "approved"

# --- Main layout ---
col1, col2, col3 = st.columns([0.30, 0.40, 0.30])

with col1:
    st.subheader("Agent Network")
    render_agent_graph(
        agents_consulted=agents_consulted,
        violations=violation_agents if violation_agents else None,
        compliance_status=compliance_status,
    )

    selected_agent = st.session_state.get("selected_agent")
    if selected_agent:
        render_intent_panel(selected_agent, session_id=active_session)

with col2:
    st.subheader("Investment Query")

    def _select_sample_query(sq: str):
        """Set the query input to a sample query."""
        st.session_state["query_input"] = sq

    query = st.text_area("Enter your investment query:", height=100, key="query_input")

    st.caption("Or try a sample query:")
    sample_queries = [
        "Should I add gold to my portfolio as an inflation hedge?",
        "What large-cap equities look attractive for a conservative investor?",
        "How should I structure a bond ladder for the next 5 years?",
        "Design a diversified portfolio split across all three asset classes.",
        "Is it appropriate to put 50% of the portfolio into crypto futures?",
    ]
    for i, sq in enumerate(sample_queries):
        st.button(sq, key=f"sample_{i}", on_click=_select_sample_query, args=(sq,))

    query_clean = (query or "").strip()
    if st.button("Run Analysis", type="primary", disabled=not query_clean):
        if not query_clean:
            st.warning("Please enter a non-empty query before running analysis.")
        else:
            session_id = str(uuid4())
            st.session_state["current_session_id"] = session_id

            active_dispositions = st.session_state.get("active_dispositions", {})

            with st.status("Running orchestration pipeline...", expanded=True) as status:
                if active_dispositions:
                    st.write(f"Dispositions active: {list(active_dispositions.keys())}")
                st.write("Phase 1: Logging user query...")
                st.write("Phase 2: Routing with compliance check (CP1)...")
                result = asyncio.run(run(query_clean, session_id, dispositions=active_dispositions))
                st.write(f"Phase 3: Delegated to: {', '.join(result.agents_consulted)} (with CP2 compliance)")
                st.write("Phase 4: Synthesizing with compliance check (CP3)...")
                if result.total_revisions > 0:
                    st.write(f"Compliance gate triggered {result.total_revisions} revision(s)")
                if result.forced_blocks:
                    st.write(f"Forced blocks: {', '.join(result.forced_blocks)}")
                if result.agents_blocked:
                    st.write(f"Agents blocked by compliance: {', '.join(result.agents_blocked)}")
                st.write("Phase 5: Response ready.")
                status.update(label="Orchestration complete", state="complete")

            st.session_state["last_result"] = result
            st.rerun()

    # --- Intent Lifecycle Timeline ---
    if active_session:
        st.divider()
        st.subheader("Intent Lifecycle")
        render_intent_timeline(active_session, result)

    # Display results in tabs
    if result:
        st.divider()
        results_tab, flow_tab, compliance_tab, compliance_log_tab, violations_tab = st.tabs(
            ["Results", "Intent Flow", "Compliance", "Compliance Log", "Violations"]
        )

        with results_tab:
            st.success(result.final_recommendation)

            if result.constraint_violations:
                st.warning("Constraint violations detected:")
                for v in result.constraint_violations:
                    st.markdown(f"- {v}")

            # Compliance summary
            if result.total_revisions > 0 or result.forced_blocks:
                with st.container(border=True):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.metric("Compliance Revisions", result.total_revisions)
                    with rc2:
                        st.metric("Forced Blocks", len(result.forced_blocks))

            with st.expander("Accountability Note"):
                st.text(result.accountability_note)

            with st.expander("Routing Rationale"):
                st.text(result.routing_rationale)

            # Download buttons
            trace = _generate_trace(result)
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    "\U0001f4e5 Download JSON Trace",
                    data=json.dumps(trace, indent=2, default=str),
                    file_name=f"trace_{result.session_id[:8]}.json",
                    mime="application/json",
                )
            with dl2:
                st.download_button(
                    "\U0001f4c4 Download Text Report",
                    data=_format_trace_text(trace),
                    file_name=f"trace_{result.session_id[:8]}.txt",
                    mime="text/plain",
                )

        with flow_tab:
            render_intent_flow(active_session)

        with compliance_tab:
            render_revision_history(
                active_session,
                compliance_verdicts=result.compliance_verdicts,
            )

        with compliance_log_tab:
            _render_compliance_log(active_session)

        with violations_tab:
            render_manifest_diff(active_session)

with col3:
    st.subheader("MCP Stream & Constraints")

    if active_session:
        stream_tab, constraint_tab = st.tabs(["MCP Stream", "Constraint Audit"])

        with stream_tab:
            render_mcp_stream(active_session)

        with constraint_tab:
            render_constraint_view(
                active_session,
                sub_agent_results=result.sub_agent_results if result else None,
            )
    else:
        st.caption("Run a query to see the message stream.")
