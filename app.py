"""Streamlit entry point for the AI-Intent Investment System."""

import asyncio
import json
from uuid import uuid4

import streamlit as st

from agents.orchestrator import run
from mcp.logger import get_logger
from ui.agent_graph import render_agent_graph
from ui.constraint_view import render_constraint_view
from ui.intent_flow import render_intent_flow
from ui.intent_panel import render_intent_panel
from ui.intent_timeline import render_intent_timeline
from ui.manifest_diff import render_manifest_diff
from ui.mcp_stream import render_mcp_stream

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
    lines.append(f"MCP MESSAGES: {trace['mcp_message_count']}")
    lines.append("")
    lines.append("RECOMMENDATION:")
    lines.append(f"  {trace['final_recommendation_summary']}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


# --- Sidebar ---
with st.sidebar:
    st.title("\U0001f9e0 AI-Intent Investment System")
    st.markdown(
        "The **AI-Intent framework** ensures that every agent action is "
        "**explicit** (governed by a machine-readable mandate), "
        "**bounded** (constrained by verifiable rules the agent cannot silently violate), "
        "and **auditable** (every inter-agent message is logged and retrievable). "
        "This application demonstrates the framework through a private investment use case "
        "with a central LLM orchestrator delegating to specialist sub-agents via a "
        "simulated MCP message bus."
    )

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
if result:
    for agent_id, agent_result in result.sub_agent_results.items():
        if agent_result.get("out_of_scope"):
            violation_agents.append(agent_id)

# --- Main layout ---
col1, col2, col3 = st.columns([0.30, 0.40, 0.30])

with col1:
    st.subheader("Agent Network")
    render_agent_graph(
        agents_consulted=agents_consulted,
        violations=violation_agents if violation_agents else None,
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

            with st.status("Running orchestration pipeline...", expanded=True) as status:
                st.write("Phase 1: Logging user query...")
                st.write("Phase 2: Routing to specialist agents...")
                result = asyncio.run(run(query_clean, session_id))
                st.write(f"Phase 3: Delegated to: {', '.join(result.agents_consulted)}")
                st.write("Phase 4: Synthesizing results...")
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
        results_tab, flow_tab, violations_tab = st.tabs(["Results", "Intent Flow", "Violations"])

        with results_tab:
            st.success(result.final_recommendation)

            if result.constraint_violations:
                st.warning("Constraint violations detected:")
                for v in result.constraint_violations:
                    st.markdown(f"- {v}")

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
