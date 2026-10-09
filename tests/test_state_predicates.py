"""State predicates (ROADMAP 1.1): drift and concentration against the session state, with the snapshot in the result.

Runnable without pytest:  python tests/test_state_predicates.py
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from agents.compliance import _evaluate_boundary_constraint  # noqa: E402
from agents.domain import SessionState, get_domain  # noqa: E402


def _bc(agent_id, rule_id):
    return next(b for b in get_domain().boundary_constraints(agent_id) if b.rule_id == rule_id)


EXPOSURE = _bc("stocks", "MANIFEST_STOCKS_EXPOSURE")
REBALANCE = _bc("materials", "MANIFEST_MATERIALS_REBALANCE")
STK = get_domain().manifest("stocks")
MAT = get_domain().manifest("materials")
STATE = SessionState(label="t", current={"equities": 0.35, "materials": 0.05}, target={"equities": 0.35, "materials": 0.05})


def test_specs_have_five_and_six_predicates():
    """The Materials Mandate now has five predicates and the Stocks Mandate five (ROADMAP 1.1 acceptance)."""
    d = get_domain()
    assert len(d.boundary_constraints("materials")) == 5
    assert len(d.boundary_constraints("stocks")) == 5
    assert EXPOSURE.predicate.kind == "state_max" and REBALANCE.predicate.kind == "state_drift"


def test_concentration_breach_only_visible_with_state():
    """A 10% position passes the position cap but breaches the 40% exposure cap on 35% current equities."""
    payload = {"analysis": "x", "positions": [{"name": "Microsoft", "allocation": 0.10}]}
    r = _evaluate_boundary_constraint(EXPOSURE, payload, STK, STATE)
    assert r.passed is False and "45.0%" in r.detail and r.state_snapshot["label"] == "t"
    empty = SessionState(label="empty", current={"equities": 0.0})
    assert _evaluate_boundary_constraint(EXPOSURE, payload, STK, empty).passed is True


def test_exposure_falls_back_to_proposed_allocation():
    """Without positions the proposed_allocation list is summed; without either the prohibition is not triggered."""
    r = _evaluate_boundary_constraint(EXPOSURE, {"analysis": "x", "proposed_allocation": [0.04, 0.03]}, STK, STATE)
    assert r.passed is False and "42.0%" in r.detail
    r = _evaluate_boundary_constraint(EXPOSURE, {"analysis": "x", "proposed_allocation": [0.02, 0.03]}, STK, STATE)
    assert r.passed is True and "40.0%" in r.detail
    r = _evaluate_boundary_constraint(EXPOSURE, {"analysis": "x"}, STK, STATE)
    assert r.passed is True and "No proposed allocation" in r.detail


def test_drift_obligation_satisfied_by_threshold_or_flag():
    """O(|proposed - target| <= threshold or flagged): within threshold passes, beyond it needs the flag."""
    within = {"analysis": "x", "commodities": [{"name": "Gold", "allocation": 0.08}], "rebalance_flag": False}
    assert _evaluate_boundary_constraint(REBALANCE, within, MAT, STATE).passed is True
    beyond = {"analysis": "x", "commodities": [{"name": "Gold", "allocation": 0.14}], "rebalance_flag": False}
    r = _evaluate_boundary_constraint(REBALANCE, beyond, MAT, STATE)
    assert r.passed is False and "9.0% drift" in r.detail and "not flagged" in r.detail
    flagged = dict(beyond, rebalance_flag=True)
    assert _evaluate_boundary_constraint(REBALANCE, flagged, MAT, STATE).passed is True
    via_flags = dict(beyond, constraint_flags=["Rebalancing trigger: allocation drifts from target"])
    assert _evaluate_boundary_constraint(REBALANCE, via_flags, MAT, STATE).passed is True


def test_drift_without_target_or_proposal_is_vacuous():
    """No target or no proposal: the obligation cannot be breached and the detail says why."""
    no_target = SessionState(label="nt", current={}, target={})
    r = _evaluate_boundary_constraint(REBALANCE, {"analysis": "x", "commodities": [{"name": "Gold", "allocation": 0.14}]}, MAT, no_target)
    assert r.passed is True and "not applicable" in r.detail
    r = _evaluate_boundary_constraint(REBALANCE, {"analysis": "x"}, MAT, STATE)
    assert r.passed is True and "No proposed allocation" in r.detail


def test_default_state_keeps_er2026_cases_unchanged():
    """The finance default state is the empty portfolio, so exposure reduces to the proposed total."""
    d = get_domain()
    assert d.default_state.current == {"equities": 0.0, "bonds": 0.0, "materials": 0.0}
    payload = {"analysis": "x", "positions": [{"name": "A", "allocation": 0.08}, {"name": "B", "allocation": 0.08}, {"name": "C", "allocation": 0.08}]}
    assert _evaluate_boundary_constraint(EXPOSURE, payload, STK, None).passed is True


def test_total_materials_cap_is_a_sum():
    """'Maximum 15% of total portfolio' is now checked on the sum of the commodities, not per item."""
    cap = _bc("materials", "MANIFEST_MATERIALS_MAX_ALLOC")
    two = {"analysis": "x", "commodities": [{"name": "Gold", "allocation": 0.10}, {"name": "Silver", "allocation": 0.10}]}
    r = _evaluate_boundary_constraint(cap, two, MAT)
    assert r.passed is False and "total: 20.0%" in r.detail
    one = {"analysis": "x", "commodities": [{"name": "Gold", "allocation": 0.10}, {"name": "Silver", "allocation": 0.05}]}
    assert _evaluate_boundary_constraint(cap, one, MAT).passed is True


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
