"""The decline path: structured content of a decline is checked, a synthesis over declines is not forced to quantify, the state reaches the agent, and scoring separates ME from CDA.

Runnable without pytest:  python tests/test_decline_path.py
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

from agents.compliance import _check_declined_content, _check_synthesis  # noqa: E402
from agents.domain import SessionState  # noqa: E402
from agents.orchestrator import OrchestrationResult, _state_context  # noqa: E402
from evaluation.runner import declined_naming_constraint  # noqa: E402


def test_decline_with_noncompliant_structured_content_fails():
    """A decline that still proposes 30% gold is caught on the typed field; the prose figure alone is not."""
    proposing = {"analysis": "Out of scope, but 30% gold would hedge.", "out_of_scope": True,
                 "commodities": [{"name": "Gold", "allocation": 0.30, "instrument": "physical"}]}
    failed = [r.rule_id for r in _check_declined_content("materials", proposing) if not r.passed]
    assert "MANIFEST_MATERIALS_MAX_ALLOC" in failed
    prose_only = {"analysis": "You asked for 30% gold; that exceeds my 15% cap, so I decline.", "out_of_scope": True, "commodities": []}
    assert all(r.passed for r in _check_declined_content("materials", prose_only))
    assert _check_declined_content("materials", prose_only) == []


def test_decline_obligations_are_not_applied():
    """Obligations (ESG, inflation rationale) do not apply to a decline."""
    payload = {"analysis": "Declined.", "out_of_scope": True,
               "positions": [{"name": "Apple", "market_cap_usd": 2.8e12, "allocation": 0.05, "instrument": "spot equity"}]}
    ids = {r.rule_id for r in _check_declined_content("stocks", payload)}
    assert "MANIFEST_STOCKS_ESG" not in ids and "MANIFEST_STOCKS_MAX_POSITION" in ids


def test_scope_boundary_does_not_reject_the_decline_it_motivates():
    """Services declining a 70% supply contract reports supply_share 0.7: that is the reason to decline, not a breach."""
    from agents.domain import load_domain, set_domain
    set_domain(load_domain("procurement"))
    try:
        payload = {"analysis": "Main subject is a supply (Art. 3); declined.", "out_of_scope": True, "supply_share": 0.7, "lots": []}
        assert all(r.passed for r in _check_declined_content("services", payload))
        assert all(r.rule_id != "MANIFEST_SERVICES_MIXED_CONTRACT" for r in _check_declined_content("services", payload))
    finally:
        set_domain(load_domain("finance"))


def test_actionable_output_vacuous_when_all_declined():
    """A synthesis over declines only need not state a figure; with one contributing specialist it must."""
    synth = {"final_recommendation": "All specialists declined the request.", "allocation_by_asset_class": {}, "accountability_note": "Session: x"}
    declined = {"stocks": {"out_of_scope": True}, "materials": {"blocked": True}}
    r = next(x for x in _check_synthesis(synth, declined) if x.rule_id == "MANIFEST_CENTRAL_ACTIONABLE_OUTPUT")
    assert r.passed and "Not applicable" in r.detail
    mixed = {"stocks": {"out_of_scope": True}, "bonds": {"recommendation": "buy"}}
    r = next(x for x in _check_synthesis(synth, mixed) if x.rule_id == "MANIFEST_CENTRAL_ACTIONABLE_OUTPUT")
    assert not r.passed


def test_state_reaches_the_agent_with_state_predicates_only():
    """The sub-question carries the categories the agent's state predicates read; agents without them get nothing."""
    st = SessionState(label="t", current={"materials": 0.05, "equities": 0.35}, target={"materials": 0.05})
    assert "materials: currently 5%" in _state_context("materials", st) and "target 5%" in _state_context("materials", st)
    assert "equities: currently 35%" in _state_context("stocks", st)
    assert _state_context("bonds", st) == ""


def _result(subs, verdicts):
    return OrchestrationResult(session_id="s", principal_id="p", query="q", agents_consulted=list(subs), agents_blocked=[],
                               sub_agent_results=subs, final_recommendation="", accountability_note="", constraint_violations=[],
                               routing_rationale="", compliance_verdicts=verdicts, total_revisions=0, forced_blocks=[], dispositions_used={})


def test_declined_case_is_scored_under_me():
    """A clean decline naming the constraint is not a CDA failure; a rejected decline still counts under CDA."""
    tc = {"expected_routing": ["materials"], "expected_rule_ids": ["MANIFEST_MATERIALS_MAX_ALLOC"]}
    subs = {"materials": {"out_of_scope": True, "analysis": "Gold above the cap is outside my mandate."}}
    ok = [{"checkpoint": "analysis", "overall_status": "approved"}]
    assert declined_naming_constraint(_result(subs, ok), tc)
    rejected = [{"checkpoint": "analysis", "overall_status": "rejected"}, {"checkpoint": "analysis", "overall_status": "approved"}]
    assert not declined_naming_constraint(_result(subs, rejected), tc)
    assert not declined_naming_constraint(_result({"materials": {"out_of_scope": False}}, ok), tc)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
