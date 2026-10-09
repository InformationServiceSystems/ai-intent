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


BONDS = get_manifest("bonds")
IG = _bc("bonds", "MANIFEST_BONDS_IG_ONLY")
DUR = _bc("bonds", "MANIFEST_BONDS_MAX_DURATION")
LADDER_MAX = next(b for b in get_boundary_constraints_for_agent("bonds") if b.rule_id == "MANIFEST_BONDS_LADDER" and b.deontic_type == "F")
LADDER_REQ = next(b for b in get_boundary_constraints_for_agent("bonds") if b.rule_id == "MANIFEST_BONDS_LADDER" and b.deontic_type == "O")
NO_EM = _bc("bonds", "MANIFEST_BONDS_NO_EM")
STK_LEV = _bc("stocks", "MANIFEST_STOCKS_NO_LEVERAGE")
STK_ESG = _bc("stocks", "MANIFEST_STOCKS_ESG")
MAT_INFL = _bc("materials", "MANIFEST_MATERIALS_INFLATION")
CENTRAL_CAP = _bc("central", "MANIFEST_CENTRAL_MAX_ASSET_CLASS")
CENTRAL = get_manifest("central")

HOLDINGS_OK = [
    {"name": "UST 2y", "credit_rating": "AA+", "maturity_years": 2, "allocation": 0.25, "region": "developed"},
    {"name": "Corp 5y", "credit_rating": "A-", "maturity_years": 5, "allocation": 0.25, "region": "developed"},
    {"name": "Corp 7y", "credit_rating": "Baa1", "maturity_years": 7, "allocation": 0.20, "region": "developed"},
]


def test_rating_floor_from_structured_holdings():
    """A BB holding fails the rating floor; AA+, A- and Baa1 pass; Moody's notation is understood."""
    ok = _evaluate_boundary_constraint(IG, {"analysis": "x", "holdings": HOLDINGS_OK}, BONDS)
    assert ok.passed is True and "BBB+" in ok.detail
    bad = _evaluate_boundary_constraint(IG, {"analysis": "solid names", "holdings": HOLDINGS_OK + [{"name": "HY 3y", "credit_rating": "BB", "maturity_years": 3, "allocation": 0.1}]}, BONDS)
    assert bad.passed is False and "HY 3y" in bad.detail
    prose = _evaluate_boundary_constraint(IG, {"analysis": "Add some junk bonds for yield."}, BONDS)
    assert prose.passed is False and prose.detail == "Found sub-investment-grade reference: 'junk'"


def test_duration_from_structured_number():
    """The portfolio duration field is compared with the 10-year limit; prose regex remains the fallback."""
    assert _evaluate_boundary_constraint(DUR, {"analysis": "x", "portfolio_duration_years": 6.5}, BONDS).passed is True
    r = _evaluate_boundary_constraint(DUR, {"analysis": "x", "portfolio_duration_years": "12 years"}, BONDS)
    assert r.passed is False and "structured" in r.detail
    assert _evaluate_boundary_constraint(DUR, {"analysis": "A 15 year bond."}, BONDS).passed is False


def test_ladder_bucket_summed_per_maturity_year():
    """Allocations are summed per maturity year and each sum is compared with the 30% bucket cap."""
    assert _evaluate_boundary_constraint(LADDER_MAX, {"analysis": "x", "holdings": HOLDINGS_OK}, BONDS).passed is True
    heavy = HOLDINGS_OK + [{"name": "Corp 5y bis", "credit_rating": "A", "maturity_years": 5, "allocation": 0.10}]
    r = _evaluate_boundary_constraint(LADDER_MAX, {"analysis": "x", "holdings": heavy}, BONDS)
    assert r.passed is False and "5: 35.0%" in r.detail


def test_ladder_presence_needs_two_maturities():
    """The obligation to ladder is satisfied by at least two distinct maturity years in the holdings."""
    assert _evaluate_boundary_constraint(LADDER_REQ, {"analysis": "x", "holdings": HOLDINGS_OK}, BONDS).passed is True
    single = [{"name": "UST 5y", "credit_rating": "AA+", "maturity_years": 5, "allocation": 0.5}]
    assert _evaluate_boundary_constraint(LADDER_REQ, {"analysis": "x", "holdings": single}, BONDS).passed is False
    assert _evaluate_boundary_constraint(LADDER_REQ, {"analysis": "A laddered structure across years."}, BONDS).passed is True


def test_emerging_market_region_field():
    """A holding whose region is emerging fails; the prose fallback still catches 'emerging market'."""
    em = HOLDINGS_OK + [{"name": "Brazil 10y", "credit_rating": "BBB", "maturity_years": 10, "allocation": 0.1, "region": "emerging"}]
    r = _evaluate_boundary_constraint(NO_EM, {"analysis": "x", "holdings": em}, BONDS)
    assert r.passed is False and "Brazil 10y" in r.detail
    assert _evaluate_boundary_constraint(NO_EM, {"analysis": "x", "holdings": HOLDINGS_OK}, BONDS).passed is True
    assert _evaluate_boundary_constraint(NO_EM, {"analysis": "Some emerging market debt."}, BONDS).passed is False


def test_instrument_and_esg_fields_on_positions():
    """Leveraged instruments fail the instrument check; a position without ESG assessment fails the obligation."""
    good = [{"name": "Apple", "market_cap_usd": 2.8e12, "instrument": "spot equity", "esg_assessment": "No material concerns."}]
    assert _evaluate_boundary_constraint(STK_LEV, {"analysis": "x", "positions": good}, STK).passed is True
    assert _evaluate_boundary_constraint(STK_ESG, {"analysis": "x", "positions": good}, STK).passed is True
    lev = [{"name": "TQQQ", "market_cap_usd": 2e10, "instrument": "3x leveraged ETF", "esg_assessment": "n/a"}]
    r = _evaluate_boundary_constraint(STK_LEV, {"analysis": "x", "positions": lev}, STK)
    assert r.passed is False and "TQQQ" in r.detail
    negated = [{"name": "Gold ETF", "market_cap_usd": 2e10, "instrument": "physical or unleveraged ETF", "esg_assessment": "n/a"},
               {"name": "B", "market_cap_usd": 2e10, "instrument": "non-leveraged fund, no margin", "esg_assessment": "n/a"}]
    assert _evaluate_boundary_constraint(STK_LEV, {"analysis": "x", "positions": negated}, STK).passed is True
    mixed = [{"name": "C", "market_cap_usd": 2e10, "instrument": "unleveraged, but bought on margin", "esg_assessment": "n/a"}]
    assert _evaluate_boundary_constraint(STK_LEV, {"analysis": "x", "positions": mixed}, STK).passed is False
    no_esg = [{"name": "Apple", "market_cap_usd": 2.8e12, "instrument": "spot equity"}]
    assert _evaluate_boundary_constraint(STK_ESG, {"analysis": "x", "positions": no_esg}, STK).passed is False
    assert _evaluate_boundary_constraint(STK_ESG, {"analysis": "Strong governance and sustainability record."}, STK).passed is True


def test_inflation_rationale_field_and_asset_class_cap():
    """A non-empty inflation_rationale satisfies the obligation; the asset-class dict is checked against 40%."""
    assert _evaluate_boundary_constraint(MAT_INFL, {"analysis": "x", "inflation_rationale": "Gold tracks CPI over long horizons."}, MAT).passed is True
    assert _evaluate_boundary_constraint(MAT_INFL, {"analysis": "x", "inflation_rationale": ""}, MAT).passed is False
    ok = {"final_recommendation": "x", "allocation_by_asset_class": {"equities": 0.35, "bonds": 0.40, "materials": 0.10}}
    assert _evaluate_boundary_constraint(CENTRAL_CAP, ok, CENTRAL).passed is True
    bad = {"final_recommendation": "x", "allocation_by_asset_class": {"equities": 0.55, "bonds": 0.30}}
    r = _evaluate_boundary_constraint(CENTRAL_CAP, bad, CENTRAL)
    assert r.passed is False and "equities: 55.0%" in r.detail
    assert _evaluate_boundary_constraint(CENTRAL_CAP, {"final_recommendation": "Put 60% in equities."}, CENTRAL).passed is False


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
