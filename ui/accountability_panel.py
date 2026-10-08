"""Accountability panel: delegation chain, commitment breaches, disposition manifestations and trace invariants of a session."""

from __future__ import annotations

from typing import Any

import streamlit as st

from mcp.logger import MCPMessage, get_logger


def _first(messages: list[MCPMessage], method: str) -> MCPMessage | None:
    """Return the first message with the given method, if any."""
    return next((m for m in messages if m.method == method), None)


def _render_chain(establish: MCPMessage | None) -> None:
    """Render the delegation chain and its containment checks."""
    st.subheader("Delegation chain")
    if establish is None:
        st.caption("No delegation chain was logged for this session (session predates the delegation hooks).")
        return
    chain = establish.payload.get("chain") or []
    checks = establish.payload.get("containment_checks") or []
    all_ok = establish.payload.get("all_contained", True)
    st.markdown(
        " → ".join(f"**{d['delegator']}**" if i == 0 else f"**{d['delegatee']}**" for i, d in enumerate(chain[:1]))
        + " → " + ", ".join(f"**{d['delegatee']}**" for d in chain[1:])
    )
    st.table([
        {
            "delegation": d["delegation_id"],
            "commitment of": d["commitment"]["committed_party"],
            "claim held by": d["claim"]["holder"],
            "rules in commitment": len(d["commitment"].get("rule_ids") or []),
        }
        for d in chain
    ])
    if all_ok:
        st.success(f"Containment: every sub-mandate is contained in its parent ({len(checks)} checks).")
    else:
        failing = [c for c in checks if not c.get("contained")]
        st.error(f"Containment violated in {len(failing)} check(s).")
        st.table(failing)


def _render_breaches(messages: list[MCPMessage]) -> None:
    """Render commitment breaches with the parties answerable for them."""
    st.subheader("Commitment breaches")
    breaches = [m for m in messages if m.method.startswith("delegation.breach.")]
    if not breaches:
        st.caption("No commitment was breached: no agent was permanently blocked.")
        return
    for m in breaches:
        p = m.payload
        with st.container(border=True):
            st.markdown(f"**{p.get('agent')}** breached `{p.get('breached_commitment')}`")
            st.markdown("Answerable to: " + " → ".join(f"**{x}**" for x in p.get("answerable_to") or []))
            rules = p.get("violated_rules") or []
            covered = p.get("rules_in_commitment") or []
            st.markdown("Violated rules: " + ", ".join(f"`{r}`" for r in rules) if rules else "Violated rules: none recorded")
            if set(rules) - set(covered):
                st.warning("Some violated rules are not part of the agent's commitment: " + ", ".join(sorted(set(rules) - set(covered))))


def _render_manifestations(messages: list[MCPMessage], active: MCPMessage | None) -> None:
    """Render disposition manifestations attributed in this session."""
    st.subheader("Disposition manifestations")
    preset = (active.payload.get("preset") if active else None) or "neutral"
    st.caption(f"Disposition preset in force: **{preset}**")
    rows: list[dict[str, Any]] = []
    for m in messages:
        if m.method.startswith("disposition.manifest."):
            for mf in m.payload.get("manifestations") or []:
                rows.append({
                    "agent": mf["agent_id"],
                    "kind": mf["kind"],
                    "degree": mf["degree"],
                    "rules": ", ".join(mf["rule_ids"]),
                    "event": mf["event_method"],
                    "revision": mf["revision_count"],
                })
    if not rows:
        st.caption("No rejection was attributed to a disposition.")
        return
    st.table(rows)


def _render_invariants(session_id: str, with_gufo: bool) -> None:
    """Run the trace invariants on the session graph and render the outcome."""
    st.subheader("Trace invariants")
    try:
        from evaluation.sparql_checks import run_checks
        from mcp.gufo_export import export_session_graph
    except Exception as e:  # rdflib or owlrl missing
        st.caption(f"Invariant checks unavailable: {e}")
        return
    with st.spinner("Exporting the session to gUFO and running the checks..."):
        graph = export_session_graph(session_id)
        results = run_checks(graph, with_gufo=with_gufo)
    st.caption(f"Session graph: {len(graph)} triples.")
    for r in results:
        if r.passed:
            st.markdown(f"✅ **{r.check_id}**: {r.claim}")
        else:
            st.markdown(f"❌ **{r.check_id}**: {r.claim}")
            st.table(r.violations[:10])
    st.download_button(
        "Download session graph (Turtle)",
        data=graph.serialize(format="turtle"),
        file_name=f"session_{session_id[:8]}.ttl",
        mime="text/turtle",
    )


def render_accountability_panel(session_id: str) -> None:
    """Render the accountability view of a session from the MCP log alone."""
    messages = get_logger().get_session(session_id)
    if not messages:
        st.caption("No messages for this session.")
        return
    _render_chain(_first(messages, "delegation.establish"))
    st.divider()
    _render_breaches(messages)
    st.divider()
    _render_manifestations(messages, _first(messages, "disposition.active"))
    st.divider()
    with_gufo = st.toggle("Also run the OWL-RL check against the gUFO axioms (slower)", value=False, key=f"gufo_{session_id}")
    _render_invariants(session_id, with_gufo)
