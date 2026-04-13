"""Revision history panel showing compliance check results and revision loops."""

from typing import Any

import streamlit as st

from agents.manifests import get_manifest
from mcp.logger import get_logger


def render_revision_history(session_id: str, compliance_verdicts: list[dict[str, Any]] | None = None) -> None:
    """Render the compliance check history for a session."""
    if not compliance_verdicts:
        st.caption("No compliance data available.")
        return

    # Summary metrics
    total = len(compliance_verdicts)
    approved = sum(1 for v in compliance_verdicts if v.get("overall_status") in ("pass", "approved"))
    revised = sum(1 for v in compliance_verdicts if v.get("revision_count", 0) > 0)
    blocked = sum(1 for v in compliance_verdicts if v.get("overall_status") in ("forced_pass", "forced_block"))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Checks", total)
    with c2:
        st.metric("Approved", approved)
    with c3:
        st.metric("Revised", revised)
    with c4:
        st.metric("Blocked", blocked)

    st.divider()

    # Per-verdict detail
    for verdict in compliance_verdicts:
        checkpoint = verdict.get("checkpoint", "unknown")
        agent_id = verdict.get("target_agent", "unknown")
        status = verdict.get("overall_status", "unknown")
        revision_count = verdict.get("revision_count", 0)

        # Header styling
        if status in ("pass", "approved"):
            icon = ":white_check_mark:"
            color = "green"
        elif status in ("forced_pass", "forced_block"):
            icon = ":red_circle:"
            color = "red"
        else:
            icon = ":warning:"
            color = "orange"

        try:
            manifest = get_manifest(agent_id)
            agent_label = f"{manifest.emoji} {manifest.name}"
        except KeyError:
            agent_label = agent_id

        label = f"{icon} {checkpoint} — {agent_label}"
        if revision_count > 0:
            label += f" ({revision_count} revision{'s' if revision_count > 1 else ''})"

        with st.expander(label, expanded=(status not in ("pass", "approved"))):
            st.markdown(f"**Status:** :{color}[{status}]")
            st.markdown(f"**Checkpoint:** `{checkpoint}`")

            # Deterministic results
            det_results = verdict.get("deterministic_results", [])
            if det_results:
                st.markdown("**Deterministic Checks:**")
                for r in det_results:
                    r_icon = ":white_check_mark:" if r["passed"] else ":x:"
                    st.markdown(f"  {r_icon} **{r['rule']}**")
                    st.caption(f"    {r['detail']}")

            # Semantic results
            sem_results = verdict.get("semantic_results", [])
            if sem_results:
                st.markdown("**Semantic Checks:**")
                for r in sem_results:
                    r_icon = ":white_check_mark:" if r["passed"] else ":x:"
                    st.markdown(f"  {r_icon} **{r['rule']}**")
                    st.caption(f"    {r['detail']}")

            # Revision feedback
            feedback = verdict.get("revision_feedback")
            if feedback:
                st.markdown("**Revision Feedback Sent:**")
                st.error(feedback)

    # Show revision messages from MCP log
    logger = get_logger()
    messages = logger.get_session(session_id)
    revision_msgs = [m for m in messages if "compliance.revision" in m.method]

    if revision_msgs:
        st.divider()
        st.markdown("**Revision Request Log:**")
        for msg in revision_msgs:
            agent_id = msg.method.replace("compliance.revision.", "")
            try:
                manifest = get_manifest(agent_id)
                agent_label = f"{manifest.emoji} {manifest.name}"
            except KeyError:
                agent_label = agent_id

            with st.container(border=True):
                payload = msg.payload
                rev_num = payload.get("revision_number", "?")
                max_rev = payload.get("max_revisions", "?")
                st.markdown(f"**{agent_label}** — Revision {rev_num}/{max_rev}")
                st.caption(msg.timestamp.strftime("%H:%M:%S.%f")[:-3])

                violated = payload.get("violated_constraints", [])
                if violated:
                    for vc in violated:
                        st.markdown(f"- :red[{vc}]")

                feedback = payload.get("revision_feedback", "")
                if feedback:
                    st.caption(feedback)
