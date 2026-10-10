"""Governance controls and view: session state, Mandate amendments, applied norm exceptions, warnings and design checks (ROADMAP 1.1, 1.3, 2.2)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from agents.domain import SessionState, get_domain
from agents.norms import MandateAmendment

_STATE_KEY = "gov_state"
_AMEND_KEY = "gov_amendments"


def reset_governance_inputs() -> None:
    """Forget state and amendments, e.g. when the domain changes."""
    for key in (_STATE_KEY, _AMEND_KEY):
        st.session_state.pop(key, None)


def render_governance_inputs(session_principal: str) -> None:
    """Sidebar inputs: the session state the state predicates compare with, and the Principal's Mandate amendments."""
    domain = get_domain()
    st.subheader("Governance")

    with st.expander("Session state", expanded=False):
        st.caption("The current position the state predicates compare proposals with; it is logged as "
                   "`state.snapshot` and cited in every state verdict.")
        default = domain.default_state
        saved = st.session_state.get(_STATE_KEY) or {"current": dict(default.current), "target": dict(default.target), "label": default.label}
        label = st.text_input("State label", value=saved.get("label", default.label), key="gov_state_label")
        current: dict[str, float] = {}
        target: dict[str, float] = {}
        for key in sorted(set(default.current) | set(default.target)):
            cols = st.columns(2)
            with cols[0]:
                current[key] = st.number_input(f"{key}: current", value=float(saved["current"].get(key, 0.0)),
                                               key=f"gov_cur_{domain.domain_id}_{key}", format="%.3f")
            with cols[1]:
                if key in default.target or key in saved.get("target", {}):
                    target[key] = st.number_input(f"{key}: target", value=float(saved["target"].get(key, 0.0)),
                                                  key=f"gov_tgt_{domain.domain_id}_{key}", format="%.3f")
        edited = current != {k: float(v) for k, v in default.current.items()} or target != {k: float(v) for k, v in default.target.items()}
        if edited and label == default.label:
            label = "custom"          # an edited state must not carry the default's name into the trace
        st.session_state[_STATE_KEY] = {"label": label or "custom", "current": current, "target": target}
        if st.button("Reset to the domain's default state", key="gov_state_reset"):
            st.session_state.pop(_STATE_KEY, None)
            st.rerun()

    with st.expander("Mandate amendments", expanded=False):
        owner = domain.principal.principal_id
        st.caption(f"The Principal may change one risk parameter of a Mandate it owns. The gate admits an amendment "
                   f"only if the issuer owns the Mandate (here: `{owner}`), containment holds and the design checks stay clean; "
                   f"the session's Mandate changes, the registered one does not.")
        agents = [a for a in domain.manifests if a != domain.compliance_id]
        agent_id = st.selectbox("Mandate", agents, key="gov_am_agent")
        params = {k: v for k, v in domain.manifest(agent_id).risk_parameters.items() if isinstance(v, (int, float))}
        if params:
            parameter = st.selectbox("Parameter", list(params), key="gov_am_param")
            current_value = params[parameter]
            if isinstance(current_value, bool):
                new_value: Any = st.checkbox(f"New value (now {current_value})", value=not current_value, key="gov_am_bool")
            else:
                new_value = st.number_input(f"New value (now {current_value})", value=float(current_value), key="gov_am_value", format="%.3f")
                if isinstance(current_value, int) and float(new_value).is_integer():
                    new_value = int(new_value)
            issuer = st.radio("Issued by", [f"Mandate owner ({owner})", f"Session principal ({session_principal})"],
                              key="gov_am_issuer", horizontal=False)
            phase = st.radio("Phase", ["start", "before_synthesis"], key="gov_am_phase", horizontal=True)
            reason = st.text_input("Reason", key="gov_am_reason", placeholder="e.g. client risk profile updated")
            if st.button("Add amendment", key="gov_am_add"):
                items = st.session_state.get(_AMEND_KEY, [])
                items.append({
                    "amendment_id": f"AM-{len(items) + 1}",
                    "principal_id": owner if issuer.startswith("Mandate owner") else session_principal,
                    "agent_id": agent_id, "parameter": parameter, "new_value": new_value,
                    "reason": reason or "(no reason given)", "phase": phase,
                })
                st.session_state[_AMEND_KEY] = items
        else:
            st.caption("This Mandate has no numeric or boolean parameter.")
        items = st.session_state.get(_AMEND_KEY, [])
        for i, a in enumerate(items):
            cols = st.columns([5, 1])
            with cols[0]:
                st.caption(f"{a['amendment_id']}: {a['agent_id']}.{a['parameter']} → {a['new_value']} "
                           f"({a['phase']}, by {a['principal_id']})")
            with cols[1]:
                if st.button("✕", key=f"gov_am_del_{i}"):
                    items.pop(i)
                    st.session_state[_AMEND_KEY] = items
                    st.rerun()


def session_inputs() -> tuple[SessionState | None, list[MandateAmendment]]:
    """The state and amendments to pass to the orchestrator for the next run."""
    raw = st.session_state.get(_STATE_KEY)
    state = SessionState(label=raw["label"], current=raw["current"], target=raw["target"]) if raw else None
    amendments = [MandateAmendment(**a) for a in st.session_state.get(_AMEND_KEY, [])]
    return state, amendments


def render_governance_tab(result: Any) -> None:
    """Result tab: amendment decisions, applied exceptions, warnings, the state used, and the design checks of the domain."""
    st.markdown("**Mandate amendments**")
    if result.amendments:
        rows = []
        for d in result.amendments:
            a = d.get("amendment", {})
            rows.append({
                "Amendment": a.get("amendment_id"), "Mandate": a.get("agent_id"), "Parameter": a.get("parameter"),
                "Old": d.get("old_value"), "New": a.get("new_value"), "Phase": a.get("phase"), "Issuer": a.get("principal_id"),
                "Admitted": "yes" if d.get("admitted") else "no", "Reasons": "; ".join(d.get("reasons") or []),
            })
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.caption("No amendment was issued in this session.")

    st.markdown("**Norm exceptions applied by the gate**")
    applied = []
    for v in result.compliance_verdicts:
        for a in v.get("exceptions_applied") or []:
            applied.append({"Agent": v.get("target_agent"), "Exception": a.get("exception_id"), "Defeats": a.get("defeats"),
                            "Item": a.get("item"), "Effect": a.get("effect"), "Bound": a.get("bound"),
                            "Verdict": v.get("overall_status")})
    if applied:
        st.dataframe(applied, width="stretch", hide_index=True)
    else:
        st.caption("No exception was applied.")

    warnings = [(v.get("target_agent"), w) for v in result.compliance_verdicts for w in (v.get("warnings") or [])]
    st.markdown("**Warnings (warn-severity rules, recorded but not blocking)**")
    if warnings:
        for agent, w in warnings:
            st.warning(f"{agent}: {w}")
    else:
        st.caption("None.")

    st.markdown("**Session state used by the state predicates**")
    if result.state_snapshot:
        snap = result.state_snapshot
        st.caption(f"`{snap.get('label')}` — current {snap.get('current')}, target {snap.get('target')}")
    else:
        st.caption("Not recorded.")

    st.markdown("**Design-time checks of the active domain (D1 to D8)**")
    if st.button("Run design checks", key="gov_design_checks"):
        from evaluation.design_checks import run_design_checks
        findings = run_design_checks(get_domain())
        if findings:
            st.dataframe([f.model_dump() for f in findings], width="stretch", hide_index=True)
        else:
            st.success(f"No finding on the {get_domain().domain_id} Mandates.")
