"""The second domain (ROADMAP 6.7): public procurement loads into the unchanged kernel and its specifications evaluate deterministically.

Runnable without pytest:  python tests/test_procurement_domain.py
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

from agents import domain as domain_module  # noqa: E402
from agents.compliance import _check_routing, _check_synthesis, _evaluate_boundary_constraint  # noqa: E402
from agents.delegation import build_delegation_chain, check_chain_containment  # noqa: E402
from agents.dispositions import get_preset_names, manifestation_map  # noqa: E402
from agents.domain import SessionState, load_domain, set_domain  # noqa: E402

PROC = load_domain("procurement")
FIN = load_domain("finance")


class _active:
    """Make the procurement domain active for the duration of a test, then restore finance."""

    def __enter__(self):
        set_domain(PROC)
        return PROC

    def __exit__(self, *exc):
        set_domain(FIN)


def _bc(agent_id, rule_id, deontic=None):
    return next(b for b in PROC.boundary_constraints(agent_id) if b.rule_id == rule_id and (deontic is None or b.deontic_type == deontic))


def test_domain_loads_with_roles_and_specs():
    """The package names its own roles; the kernel reads them."""
    assert PROC.orchestrator_id == "coordinator" and PROC.compliance_id == "procurement_compliance"
    assert PROC.specialist_ids == ["supplies", "services", "works"]
    assert len(PROC.constraint_specs) == 19 and len({s.rule_id for s in PROC.constraint_specs}) == 17
    assert all(PROC.rule(s.rule_id) is not None for s in PROC.constraint_specs), "every spec has a registry entry"
    for aid in PROC.specialist_ids:
        texts = PROC.manifest(aid).boundary_constraints
        assert all(bc.text in texts for bc in PROC.boundary_constraints(aid)), aid


def test_spec_consistency_holds_for_the_second_domain():
    """C1 to C3 hold by construction; C4 names only the prose-only universe constraint."""
    with _active():
        from evaluation import spec_consistency
        findings = spec_consistency.run_all()
    hard = [f for f in findings if f.check in ("C1_BOUND", "C2_TERMS", "C3_MANIFEST")]
    assert hard == [], [f.model_dump() for f in hard]
    assert {f.agent_id for f in findings} <= {"supplies", "coordinator"}


def test_mixed_contract_is_the_boundary_object():
    """Art. 3: a 70% supply share fails the services specialist's scope constraint; 30% passes."""
    mixed = _bc("services", "MANIFEST_SERVICES_MIXED_CONTRACT")
    svc = PROC.manifest("services")
    r = _evaluate_boundary_constraint(mixed, {"analysis": "x", "supply_share": 0.7}, svc)
    assert r.passed is False and "70.0%" in r.detail
    assert _evaluate_boundary_constraint(mixed, {"analysis": "x", "supply_share": 0.3}, svc).passed is True
    assert _evaluate_boundary_constraint(mixed, {"analysis": "x", "supply_share": "70%"}, svc).passed is False


def test_cpv_range_and_threshold_and_procedure():
    """CPV range (two specs, one rule), the EU threshold and the competitive-procedure prohibition evaluate on lots."""
    sup = PROC.manifest("supplies")
    lower = _bc("supplies", "MANIFEST_SUPPLIES_CPV_SCOPE")
    upper = [b for b in PROC.boundary_constraints("supplies") if b.rule_id == "MANIFEST_SUPPLIES_CPV_SCOPE"][1]
    works_lot = {"analysis": "x", "lots": [{"name": "Roof", "cpv_division": 45, "estimated_value_eur": 100000, "share": 1.0, "procedure": "open"}]}
    assert _evaluate_boundary_constraint(upper, works_lot, sup).passed is False
    assert _evaluate_boundary_constraint(lower, works_lot, sup).passed is True
    laptops = {"analysis": "x", "lots": [{"name": "Laptops", "cpv_division": 30, "estimated_value_eur": 180000, "share": 0.5, "procedure": "open"},
                                         {"name": "Docking", "cpv_division": 30, "estimated_value_eur": 40000, "share": 0.5, "procedure": "open"}]}
    assert _evaluate_boundary_constraint(upper, laptops, sup).passed is True
    value = _bc("supplies", "MANIFEST_SUPPLIES_LOT_VALUE")
    big = {"analysis": "x", "lots": [{"name": "All", "cpv_division": 30, "estimated_value_eur": "€300,000", "share": 1.0, "procedure": "direct award"}]}
    r = _evaluate_boundary_constraint(value, big, sup)
    assert r.passed is False and "All" in r.detail
    share = _bc("supplies", "MANIFEST_SUPPLIES_LOT_SHARE")
    assert _evaluate_boundary_constraint(share, big, sup).passed is False
    assert _evaluate_boundary_constraint(share, laptops, sup).passed is True
    single = _bc("supplies", "MANIFEST_SUPPLIES_NO_SINGLE_SOURCE")
    assert _evaluate_boundary_constraint(single, big, sup).passed is False
    assert _evaluate_boundary_constraint(single, laptops, sup).passed is True
    prose = _evaluate_boundary_constraint(single, {"analysis": "We recommend a direct award to the incumbent."}, sup)
    assert prose.passed is False and "direct award" in prose.detail
    negated = _evaluate_boundary_constraint(single, {"analysis": "A direct award is not permitted here; we run an open procedure."}, sup)
    assert negated.passed is True


def test_budget_exposure_is_a_state_predicate():
    """50% committed plus 15% proposed exceeds the 60% supplies share; at the start of the year it does not."""
    sup = PROC.manifest("supplies")
    exposure = _bc("supplies", "MANIFEST_SUPPLIES_BUDGET_EXPOSURE")
    payload = {"analysis": "x", "lots": [{"name": "Vehicles", "cpv_division": 34, "estimated_value_eur": 200000, "share": 1.0, "budget_share": 0.15, "procedure": "open"}]}
    late = SessionState(label="late_year", current={"supplies": 0.50})
    r = _evaluate_boundary_constraint(exposure, payload, sup, late)
    assert r.passed is False and "65.0%" in r.detail and r.state_snapshot["label"] == "late_year"
    assert _evaluate_boundary_constraint(exposure, payload, sup, PROC.default_state).passed is True


def test_kernel_checks_use_the_domain_roles():
    """Routing and synthesis checks name the coordinator's rules, not finance ones, when the domain is active."""
    with _active():
        routing = _check_routing({"agents_to_call": ["supplies", "stocks"], "query_for_supplies": "q", "query_for_stocks": "q"})
        assert routing[0].rule_id == "MANIFEST_COORDINATOR_MIN_AGENTS"
        assert routing[1].passed is False and "stocks" in routing[1].detail and routing[1].rule_id == "DIR2014_24_ART18_PRINCIPLES"
        synth = _check_synthesis({"final_recommendation": "Split into three lots of €150,000; price 60%, quality 40%.",
                                  "allocation_by_contract_type": {"supplies": 0.7, "services": 0.3},
                                  "accountability_note": "Session: x"}, {})
        by_id = {r.rule_id: r for r in synth}
        assert by_id["MANIFEST_COORDINATOR_MAX_CONTRACT_TYPE"].passed is False
        assert by_id["MANIFEST_COORDINATOR_ACTIONABLE_OUTPUT"].passed is True
        assert get_preset_names()[0] == "neutral"
        chain = build_delegation_chain("municipality")
        assert [d.delegatee for d in chain] == ["coordinator", "supplies", "services", "works"]
        assert all(c.contained for c in check_chain_containment(chain))
        assert "MANIFEST_SERVICES_MIXED_CONTRACT" in manifestation_map(PROC)["conformist"]
        assert "MANIFEST_SUPPLIES_LOT_SHARE" in manifestation_map(PROC)["anti_customer"]


def test_schemas_are_derived_from_the_specifications():
    """The response schemas require exactly the fields the specifications declare."""
    svc = PROC.specialists["services"].response_format["json_schema"]["schema"]
    assert {"lots", "supply_share", "framework_duration_years", "conflict_of_interest_screening"} <= set(svc["required"])
    lots = svc["$defs"]["LotsItem"]["required"]
    assert {"name", "cpv_division", "subcontracting_share"} <= set(lots) and "performance_guarantee" not in lots
    works = PROC.specialists["works"].response_format["json_schema"]["schema"]["$defs"]["LotsItem"]
    assert "performance_guarantee" in works["required"] and works["properties"]["procedure"]["enum"][0] == "open"
    routing = PROC.routing_format["json_schema"]["schema"]
    assert routing["properties"]["agents_to_call"]["items"]["enum"] == ["supplies", "services", "works"]
    assert PROC.synthesis_format["json_schema"]["schema"]["required"] == ["final_recommendation", "allocation_by_contract_type"]
    assert svc["properties"]["recommendation"]["enum"] == ["award", "shortlist", "reject", "not_applicable"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
