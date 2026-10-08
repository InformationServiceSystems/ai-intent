"""Set and threshold constraints over structured output fields, with the term list as prose fallback.

Runnable without pytest:  python tests/test_structured_constraints.py
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

from agents.compliance import _as_number, _evaluate_boundary_constraint  # noqa: E402
from agents.manifests import get_manifest  # noqa: E402
from agents.regulatory_rules import get_boundary_constraints_for_agent  # noqa: E402


def _bc(agent_id, rule_id):
    return next(b for b in get_boundary_constraints_for_agent(agent_id) if b.rule_id == rule_id)


APPROVED = _bc("materials", "MANIFEST_MATERIALS_APPROVED")
LARGECAP = _bc("stocks", "MANIFEST_STOCKS_LARGECAP")
MAT = get_manifest("materials")
STK = get_manifest("stocks")


def test_predicate_kinds():
    """The two former term proxies are now a set constraint and a threshold constraint."""
    assert APPROVED.predicate.kind == "in_set" and APPROVED.predicate.set_param_key == "approved_commodities"
    assert LARGECAP.predicate.kind == "min_threshold" and LARGECAP.predicate.risk_param_key == "max_market_cap_threshold"


def test_lithium_fails_the_set_constraint():
    """A commodity outside the approved set is caught even though no forbidden term appears in the prose."""
    payload = {"analysis": "A modest allocation to this battery metal as a diversifier.",
               "commodities": [{"name": "Lithium", "allocation": 0.05}]}
    r = _evaluate_boundary_constraint(APPROVED, payload, MAT)
    assert r.passed is False and "Lithium" in r.detail


def test_gold_and_silver_pass_the_set_constraint():
    """Approved commodities pass; matching is case-insensitive and tolerant of qualifiers."""
    payload = {"analysis": "Gold and silver bullion.", "commodities": [{"name": "gold bullion"}, {"name": "Silver"}]}
    r = _evaluate_boundary_constraint(APPROVED, payload, MAT)
    assert r.passed is True and "approved" in r.detail


def test_prose_fallback_when_field_absent():
    """Without the structured field the term list applies, with the same detail text as before."""
    found = _evaluate_boundary_constraint(APPROVED, {"analysis": "Consider crude oil futures."}, MAT)
    assert found.passed is False and found.detail == "Found non-approved commodity: 'crude'"
    negated = _evaluate_boundary_constraint(APPROVED, {"analysis": "I cannot recommend oil; it is not permitted."}, MAT)
    assert negated.passed is True and "negation_context_detected" in negated.detail


def test_small_cap_fails_the_threshold_constraint():
    """A position below the market-cap floor is caught from the structured number, whatever the prose says."""
    payload = {"analysis": "A leading firm in its niche.",
               "positions": [{"name": "NicheCo", "market_cap_usd": 4_000_000_000, "allocation": 0.05}]}
    r = _evaluate_boundary_constraint(LARGECAP, payload, STK)
    assert r.passed is False and "NicheCo" in r.detail and "$4.0B" in r.detail


def test_large_caps_pass_and_numbers_are_parsed_leniently():
    """Large caps pass; market caps written as strings with units are understood."""
    payload = {"analysis": "Two mega-caps.",
               "positions": [{"name": "Apple", "market_cap_usd": "2.8 trillion"}, {"name": "Siemens", "market_cap_usd": "$150 billion"}]}
    r = _evaluate_boundary_constraint(LARGECAP, payload, STK)
    assert r.passed is True
    assert _as_number("2.8 trillion") == 2.8e12 and _as_number("$150 billion") == 150e9 and _as_number("250000000000") == 2.5e11
    assert _as_number("n/a") is None


def test_largecap_prose_fallback_unchanged():
    """Without positions, the old term list still applies with its original detail."""
    r = _evaluate_boundary_constraint(LARGECAP, {"analysis": "A promising small-cap biotech."}, STK)
    assert r.passed is False and r.detail == "Found non-large-cap reference: 'small-cap'"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
