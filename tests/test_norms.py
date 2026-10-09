"""Defeasible norms and session-mutable Mandates (ROADMAP 1.3), including an offline end-to-end session.

Runnable without pytest:  python tests/test_norms.py
"""

import asyncio
import json
import sys
import tempfile
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

from agents import domain as domain_module  # noqa: E402
from agents.compliance import _evaluate_boundary_constraint  # noqa: E402
from agents.domain import ContainmentRule, load_domain, set_domain  # noqa: E402
from agents.norms import MandateAmendment, NormException, admit  # noqa: E402
from agents.regulatory_rules import RegulatoryRule  # noqa: E402


def _finance_with_index_exception():
    """Finance plus a stronger norm: broad index funds may take up to 25 % (illustrative)."""
    d = load_domain("finance").model_copy(deep=True)
    d.manifests["stocks"].risk_parameters["max_index_fund_position"] = 0.25
    d.containment_rules.append(ContainmentRule(child_id="stocks", parameter="max_index_fund_position", parent_parameter="max_single_asset_class"))
    d.exceptions = [NormException(
        exception_id="EXC_STOCKS_INDEX_FUND", defeats="MANIFEST_STOCKS_MAX_POSITION",
        description="A broad, diversified index fund may exceed the single-position cap up to its own bound",
        regulatory_basis="Illustrative (UCITS diversification)", when_key="instrument", when_values=["index fund", "index etf"],
        effect="bound", bound_param_key="max_index_fund_position", priority=2)]
    d.rules = d.rules + [RegulatoryRule(rule_id="EXC_STOCKS_INDEX_FUND", description="Index funds up to 25 %", applies_to=["stocks"],
                                        check_type="deterministic", severity="block", regulatory_basis="Illustrative", tags=["allocation_cap"])]
    return d


def test_exception_defeats_the_cap_for_covered_items_only():
    """A 20 % index fund passes under the exception's 25 % bound; a 20 % single stock still fails; 30 % in the fund fails."""
    d = _finance_with_index_exception()
    set_domain(d)
    try:
        bc = next(b for b in d.boundary_constraints("stocks") if b.rule_id == "MANIFEST_STOCKS_MAX_POSITION")
        m = d.manifest("stocks")
        ok = {"analysis": "x", "positions": [{"name": "World index", "instrument": "index ETF", "allocation": 0.20},
                                             {"name": "Apple", "instrument": "spot equity", "allocation": 0.08}]}
        r = _evaluate_boundary_constraint(bc, ok, m)
        assert r.passed and r.exceptions_applied[0]["exception_id"] == "EXC_STOCKS_INDEX_FUND" and r.exceptions_applied[0]["bound"] == 0.25
        single = {"analysis": "x", "positions": [{"name": "World index", "instrument": "index ETF", "allocation": 0.20},
                                                 {"name": "Apple", "instrument": "spot equity", "allocation": 0.20}]}
        assert _evaluate_boundary_constraint(bc, single, m).passed is False
        over = {"analysis": "x", "positions": [{"name": "World index", "instrument": "index ETF", "allocation": 0.30}]}
        r = _evaluate_boundary_constraint(bc, over, m)
        assert r.passed is False and "EXC_STOCKS_INDEX_FUND" in r.detail
    finally:
        set_domain(load_domain("finance"))


def test_payload_level_exemption_and_priority():
    """A payload-level exception with a required justification exempts the constraint; without the justification it does not."""
    d = load_domain("procurement").model_copy(deep=True)
    d.exceptions = [NormException(
        exception_id="EXC_ART32_URGENCY", defeats="MANIFEST_SUPPLIES_NO_SINGLE_SOURCE",
        description="Extreme urgency (Art. 32(2)(c)) permits the negotiated procedure without prior publication",
        regulatory_basis="Directive 2014/24/EU Art. 32(2)(c)", when_field="extreme_urgency", requires_field="urgency_justification")]
    set_domain(d)
    try:
        bc = next(b for b in d.boundary_constraints("supplies") if b.rule_id == "MANIFEST_SUPPLIES_NO_SINGLE_SOURCE")
        m = d.manifest("supplies")
        lots = [{"name": "Generators", "procedure": "negotiated without prior publication"}]
        assert _evaluate_boundary_constraint(bc, {"analysis": "x", "lots": lots, "extreme_urgency": True}, m).passed is False
        r = _evaluate_boundary_constraint(bc, {"analysis": "x", "lots": lots, "extreme_urgency": True,
                                               "urgency_justification": "Flood; unforeseeable; no time for an open procedure"}, m)
        assert r.passed and "Defeated by EXC_ART32_URGENCY" in r.detail
    finally:
        set_domain(load_domain("finance"))


def test_exception_is_checked_at_design_time():
    """D8 reports an exception that defeats no constraint; the index-fund parameter counts as read (no D1 finding)."""
    from evaluation.design_checks import run_design_checks
    d = _finance_with_index_exception()
    assert [f for f in run_design_checks(d)] == []
    d.exceptions[0] = d.exceptions[0].model_copy(update={"defeats": "MANIFEST_STOCKS_NOT_A_RULE"})
    assert any(f.check == "D8_EXCEPTION_TARGET" for f in run_design_checks(d))


def test_amendment_admission():
    """Owner, existing parameter, containment and design checks decide admission; the registry is never mutated."""
    d = load_domain("finance")
    ok, amended = admit(d, MandateAmendment(amendment_id="a1", principal_id="anonymous", agent_id="materials",
                                            parameter="max_total_allocation", new_value=0.20, reason="client risk profile updated"))
    assert ok.admitted and ok.old_value == 0.15 and amended.manifest("materials").risk_parameters["max_total_allocation"] == 0.20
    assert "Maximum 20% of total portfolio in raw materials" in amended.manifest("materials").boundary_constraints
    assert d.manifest("materials").risk_parameters["max_total_allocation"] == 0.15
    stranger, _ = admit(d, MandateAmendment(amendment_id="a2", principal_id="someone-else", agent_id="materials",
                                            parameter="max_total_allocation", new_value=0.20, reason="x"))
    assert not stranger.admitted and "does not own" in stranger.reasons[0]
    beyond, _ = admit(d, MandateAmendment(amendment_id="a3", principal_id="anonymous", agent_id="materials",
                                          parameter="max_total_allocation", new_value=0.50, reason="x"))
    assert not beyond.admitted and any("containment" in r for r in beyond.reasons)
    unknown, _ = admit(d, MandateAmendment(amendment_id="a4", principal_id="anonymous", agent_id="materials",
                                           parameter="max_leverage", new_value=2, reason="x"))
    assert not unknown.admitted


def _stub_llm(materials_allocation: float):
    """Canned model answers for an offline session: routing is overridden, so only the specialist and the synthesis speak."""
    def specialist_chat(system, user, model=None, response_format=None, timeout=None):
        return json.dumps({"analysis": "Gold as an inflation hedge.", "constraint_flags": [], "recommendation": "buy",
                           "confidence": "medium", "proposed_allocation": [materials_allocation], "out_of_scope": False,
                           "commodities": [{"name": "Gold", "allocation": materials_allocation, "instrument": "physical"}],
                           "inflation_rationale": "Gold tracks CPI over long horizons.", "rebalance_flag": True})

    def synthesis_chat(system, user, model=None, response_format=None, timeout=None):
        return json.dumps({"final_recommendation": f"Allocate {materials_allocation * 100:.0f}% to physical gold.",
                           "allocation_by_asset_class": {"materials": materials_allocation}})

    def semantic_chat(system, user, model=None, response_format=None, timeout=None):
        return json.dumps({"results": []})
    return specialist_chat, synthesis_chat, semantic_chat


def _offline_session(amendments, allocation: float):
    import agents.compliance as compliance_mod
    import agents.orchestrator as orch
    import agents.specialist as spec
    import mcp.logger as logger_mod
    from agents.orchestrator import run
    from evaluation.sparql_checks import run_checks
    from mcp.gufo_export import export_session_graph

    specialist_chat, synthesis_chat, semantic_chat = _stub_llm(allocation)
    saved = (spec.chat, orch.chat, compliance_mod.chat, logger_mod._logger_instance)
    tmp = tempfile.mkdtemp()
    spec.chat, orch.chat, compliance_mod.chat = specialist_chat, synthesis_chat, semantic_chat
    logger_mod._logger_instance = logger_mod.MCPLogger(f"{tmp}/s.db")
    set_domain(load_domain("finance"))
    try:
        result = asyncio.run(run("Put 18% into gold.", "offline-1", routing_override={"agents_to_call": ["materials"]},
                                 amendments=amendments))
        graph = export_session_graph("offline-1")
        checks = {c.check_id: c.passed for c in run_checks(graph)}
        methods = [m.method for m in logger_mod._logger_instance.get_session("offline-1")]
        return result, checks, methods
    finally:
        spec.chat, orch.chat, compliance_mod.chat, logger_mod._logger_instance = saved


def test_offline_session_with_admitted_amendment():
    """With the Principal's amendment to 20 %, an 18 % gold proposal is delivered; the registry is unchanged afterwards."""
    amendment = MandateAmendment(amendment_id="a1", principal_id="anonymous", agent_id="materials",
                                 parameter="max_total_allocation", new_value=0.20, reason="client risk profile updated")
    result, checks, methods = _offline_session([amendment], 0.18)
    assert methods.index("governance.amend") < methods.index("delegation.establish")
    assert result.amendments[0]["admitted"] and result.forced_blocks == [] and "materials" in result.sub_agent_results
    assert all(checks.values()), checks
    assert domain_module.get_domain().manifest("materials").risk_parameters["max_total_allocation"] == 0.15


def test_offline_session_without_amendment_blocks():
    """Without the amendment the same 18 % proposal breaches the 15 % cap on every attempt and is blocked."""
    result, checks, methods = _offline_session([], 0.18)
    assert result.forced_blocks == ["materials"] and "governance.amend" not in methods
    assert all(checks.values()), checks


def test_rejected_amendment_is_logged_and_has_no_effect():
    """An amendment by a non-owner is logged as rejected and the 15 % cap still applies."""
    stranger = MandateAmendment(amendment_id="a2", principal_id="someone-else", agent_id="materials",
                                parameter="max_total_allocation", new_value=0.20, reason="x")
    result, checks, methods = _offline_session([stranger], 0.18)
    assert "governance.amend.rejected" in methods and not result.amendments[0]["admitted"]
    assert result.forced_blocks == ["materials"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
