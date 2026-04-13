"""Per-agent and aggregate constraint enforcement display."""

from typing import Any

import streamlit as st

from agents.manifests import get_manifest, _MANIFEST_REGISTRY
from mcp.logger import MCPMessage, get_logger


def _get_compliance_verdict(messages: list[MCPMessage], agent_id: str) -> dict[str, Any] | None:
    """Find the final compliance verdict message for a given agent from the MCP log."""
    for msg in reversed(messages):
        # Match both old format (compliance.check.X) and new format (compliance.approve.X, compliance.reject.X)
        if msg.method in (
            f"compliance.check.{agent_id}",
            f"compliance.approve.{agent_id}",
            f"compliance.reject.{agent_id}",
            f"compliance.approve.{agent_id}.final",
            f"compliance.block.{agent_id}",
        ):
            return msg.payload
    return None


def _get_revision_trail(messages: list[MCPMessage], agent_id: str) -> list[dict[str, Any]]:
    """Build the chronological revision trail for an agent.

    Uses timestamps to pair each compliance check with the most recent
    preceding agent response, avoiding index-based mismatches caused by
    parse retries that add extra .result messages.
    """
    trail: list[dict[str, Any]] = []
    checks = []
    revisions = []
    responses = []

    for msg in messages:
        if msg.method in (
            f"compliance.check.{agent_id}",
            f"compliance.approve.{agent_id}",
            f"compliance.reject.{agent_id}",
        ):
            checks.append(msg)
        elif msg.method == f"compliance.revision.{agent_id}":
            revisions.append(msg)
        elif msg.method == f"{agent_id}.result":
            responses.append(msg)

    for i, check in enumerate(checks):
        step: dict[str, Any] = {
            "step": i + 1,
            "verdict": check.payload,
            "timestamp": check.timestamp,
        }
        # Find the most recent response BEFORE this check (by timestamp)
        preceding_responses = [r for r in responses if r.timestamp <= check.timestamp]
        if preceding_responses:
            step["response"] = preceding_responses[-1].payload

        # Find the revision feedback that follows this check (if any)
        following_revisions = [r for r in revisions if r.timestamp > check.timestamp]
        if following_revisions:
            rev = following_revisions[0]
            # Only include if this revision is before the next check
            next_check_time = checks[i + 1].timestamp if i + 1 < len(checks) else None
            if next_check_time is None or rev.timestamp < next_check_time:
                step["revision_feedback"] = rev.payload.get("revision_feedback", "")
                step["violated_constraints"] = rev.payload.get("violated_constraints", [])

        trail.append(step)

    return trail


def _classify_constraint_with_verdict(
    constraint: str,
    flags: list[str],
    out_of_scope: bool,
    analysis: str,
    verdict: dict[str, Any] | None,
) -> tuple[str, str]:
    """Classify a constraint using both self-report and compliance verdict."""
    constraint_lower = constraint.lower()

    # First, check compliance verdict deterministic + semantic results
    if verdict:
        for result in verdict.get("deterministic_results", []) + verdict.get("semantic_results", []):
            rule_lower = result.get("rule", "").lower()
            # Match by fuzzy overlap between the constraint text and the rule name
            if _fuzzy_match(constraint_lower, rule_lower) or _fuzzy_match(rule_lower, constraint_lower):
                if not result.get("passed", True):
                    source = result.get("source", "deterministic")
                    detail = result.get("detail", "Violation detected")
                    return "violated", f"[{source}] {detail}"

    # If the compliance verdict exists and all checks passed, trust the verdict
    if verdict and verdict.get("overall_status") in ("pass", "approved"):
        if out_of_scope:
            return "na", "N/A — agent correctly declined (out of scope)"
        return "passed", "Passed (verified by compliance gate)"

    # Fall back to self-report checks when no verdict available
    analysis_lower = analysis.lower()
    flag_match = any(_fuzzy_match(constraint_lower, f.lower()) for f in flags)
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
            if agent_id in _MANIFEST_REGISTRY:
                agent_results[agent_id] = msg

    if not agent_results:
        st.caption("No agent results to analyze.")
        return

    agent_ids = list(agent_results.keys())
    tab_labels = [f"{get_manifest(a).emoji} {a.title()}" for a in agent_ids] + ["All Agents"]
    tabs = st.tabs(tab_labels)

    # Per-agent tabs
    for i, agent_id in enumerate(agent_ids):
        verdict = _get_compliance_verdict(messages, agent_id)
        trail = _get_revision_trail(messages, agent_id)
        with tabs[i]:
            _render_agent_constraints(agent_id, agent_results[agent_id], verdict, trail)

    # All Agents summary tab
    with tabs[-1]:
        _render_summary_matrix(agent_ids, agent_results, messages)


def _render_agent_constraints(
    agent_id: str,
    result_msg: MCPMessage,
    verdict: dict[str, Any] | None,
    trail: list[dict[str, Any]] | None = None,
) -> None:
    """Render constraint audit for a single agent."""
    manifest = get_manifest(agent_id)
    payload = result_msg.payload
    flags = result_msg.constraint_flags
    out_of_scope = payload.get("out_of_scope", False)
    analysis = payload.get("analysis", "")

    st.markdown(f"**{manifest.emoji} {manifest.name}**")
    st.caption(f"Intent Scope: {manifest.intent_scope}")

    # Show compliance verdict status if available
    if verdict:
        overall = verdict.get("overall_status", "unknown")
        rev_count = verdict.get("revision_count", 0)
        if overall in ("pass", "approved"):
            st.success(f"Compliance Gate: **APPROVED**{f' (after {rev_count} revision(s))' if rev_count else ''}")
        elif overall in ("forced_pass", "forced_block"):
            st.error(f"Compliance Gate: **BLOCKED** — max revisions ({rev_count}) exceeded, message dropped")
        elif overall in ("revision_requested", "rejected"):
            st.warning(f"Compliance Gate: **REJECTED** — revision required (attempt {rev_count})")

    st.divider()

    # Boundary Constraints with status
    st.markdown("**Boundary Constraints:**")
    for constraint in manifest.boundary_constraints:
        status, detail = _classify_constraint_with_verdict(constraint, flags, out_of_scope, analysis, verdict)
        icon = {"passed": ":white_check_mark:", "flagged": ":warning:", "violated": ":x:", "na": ":heavy_minus_sign:"}[status]
        color = {"passed": "green", "flagged": "orange", "violated": "red", "na": "gray"}[status]
        st.markdown(f"{icon} :{color}[{constraint}]")
        if status != "passed":
            st.caption(f"    *{detail}*")

    # Show any additional compliance check results not matched to boundary constraints
    if verdict:
        unmatched = _get_unmatched_failures(manifest.boundary_constraints, verdict)
        if unmatched:
            st.divider()
            st.markdown("**Additional Compliance Findings:**")
            for result in unmatched:
                source = result.get("source", "deterministic")
                st.markdown(f":x: :red[{result['rule']}]")
                st.caption(f"    *[{source}] {result.get('detail', '')}*")

    st.divider()

    # Revision Trail — show how violations were detected and fixed
    if trail and len(trail) > 1:
        st.markdown("**Revision History:**")
        for step in trail:
            step_num = step["step"]
            step_verdict = step.get("verdict", {})
            step_status = step_verdict.get("overall_status", "unknown")
            step_response = step.get("response", {})
            revision_fb = step.get("revision_feedback", "")
            violated_list = step.get("violated_constraints", [])
            ts = step.get("timestamp")
            ts_str = ts.strftime("%H:%M:%S.%f")[:-3] if ts else ""

            is_final = step_num == len(trail)

            if step_status in ("pass", "approved"):
                step_icon = ":white_check_mark:"
                step_label = f"Attempt {step_num} — **Approved**"
            elif step_status in ("forced_pass", "forced_block"):
                step_icon = ":red_circle:"
                step_label = f"Attempt {step_num} — **Blocked**"
            else:
                step_icon = ":x:"
                step_label = f"Attempt {step_num} — **Rejected**"

            with st.expander(f"{step_icon} {step_label}  ({ts_str})", expanded=not is_final if step_status not in ("pass", "approved") else False):
                # What the agent said
                step_analysis = step_response.get("analysis", "")
                if step_analysis:
                    st.markdown("**Agent response (excerpt):**")
                    st.caption(step_analysis[:300] + ("..." if len(step_analysis) > 300 else ""))

                # What failed in this attempt
                det_results = step_verdict.get("deterministic_results", [])
                sem_results = step_verdict.get("semantic_results", [])
                failures = [r for r in det_results + sem_results if not r.get("passed", True)]
                if failures:
                    st.markdown("**Violations detected:**")
                    for f in failures:
                        st.markdown(f"- :red[{f['rule']}] — {f.get('detail', '')}")

                # Revision feedback sent to agent
                if revision_fb:
                    st.markdown("**Feedback sent to agent:**")
                    st.warning(revision_fb)

                # If this was the final step and it passed, highlight the fix
                if is_final and step_status in ("pass", "approved") and len(trail) > 1:
                    st.success("Agent successfully revised its response to comply with all constraints.")
                elif is_final and step_status in ("forced_pass", "forced_block"):
                    st.error("Agent could not comply after maximum revisions. Message permanently BLOCKED.")

        st.divider()
    elif trail and len(trail) == 1:
        # Single check, no revisions needed
        step_verdict = trail[0].get("verdict", {})
        det_results = step_verdict.get("deterministic_results", [])
        is_decline = any(r.get("rule", "").startswith("Out-of-scope") for r in det_results)
        if is_decline:
            st.caption("Agent correctly declined this query as outside its mandate.")
        elif step_verdict.get("overall_status") in ("pass", "approved"):
            st.caption("No revisions needed — approved on first attempt.")
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
    rec = str(rec) if not isinstance(rec, str) else rec
    conf = str(conf) if not isinstance(conf, str) else conf
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


def _get_unmatched_failures(boundary_constraints: list[str], verdict: dict[str, Any]) -> list[dict]:
    """Return compliance failures that didn't match any boundary constraint."""
    unmatched = []
    for result in verdict.get("deterministic_results", []) + verdict.get("semantic_results", []):
        if result.get("passed", True):
            continue
        rule_lower = result.get("rule", "").lower()
        matched = False
        for constraint in boundary_constraints:
            if _fuzzy_match(constraint.lower(), rule_lower) or _fuzzy_match(rule_lower, constraint.lower()):
                matched = True
                break
        if not matched:
            unmatched.append(result)
    return unmatched


def _render_summary_matrix(agent_ids: list[str], agent_results: dict[str, MCPMessage], messages: list[MCPMessage]) -> None:
    """Render aggregate constraint matrix across all agents."""
    st.markdown("**Constraint Enforcement Summary:**")

    for agent_id in agent_ids:
        manifest = get_manifest(agent_id)
        msg = agent_results[agent_id]
        flags = msg.constraint_flags
        out_of_scope = msg.payload.get("out_of_scope", False)
        analysis = msg.payload.get("analysis", "")
        verdict = _get_compliance_verdict(messages, agent_id)

        violations = 0
        flagged = 0
        passed = 0

        for constraint in manifest.boundary_constraints:
            status, _ = _classify_constraint_with_verdict(constraint, flags, out_of_scope, analysis, verdict)
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
