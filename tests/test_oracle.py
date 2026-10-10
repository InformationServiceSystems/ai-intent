"""Independent oracle (ROADMAP 3.2): the fast SPARQL path equals the SHACL engine, and the gate fixes the oracle found hold.

Runnable without pytest:  python tests/test_oracle.py
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

from rdflib import Graph  # noqa: E402

from agents.compliance import _evaluate_boundary_constraint, _rating_rank, _structured_items  # noqa: E402
from agents.domain import load_domain  # noqa: E402
from evaluation.oracle_agreement import EX, oracle_number, oracle_rating, oracle_violations, render_response  # noqa: E402


def _graph():
    g = Graph()
    render_response(g, EX["r/a"], "materials", {"commodities": [{"name": "Gold", "allocation": 0.10}, {"name": "Silver", "allocation": 0.05}],
                                                 "inflation_rationale": "tracks CPI"}, {"target": {"materials": 0.10}})
    render_response(g, EX["r/b"], "materials", {"commodities": [{"name": "Copper", "allocation": 0.2, "instrument": "futures"}],
                                                 "inflation_rationale": ""}, {"target": {"materials": 0.10}})
    render_response(g, EX["r/c"], "bonds", {"holdings": [{"name": "X", "credit_rating": "BBB+/Baa1", "maturity_years": 2, "allocation": 0.3},
                                                         {"name": "Y", "credit_rating": "N/A", "maturity_years": 5, "allocation": 0.2}],
                                             "portfolio_duration_years": 10}, None)
    render_response(g, EX["r/d"], "materials", {"commodities": [{"name": "Gold", "allocation": 0.1, "instrument": "physical or unleveraged ETF, potentially with leverage"}],
                                                 "inflation_rationale": "tracks CPI"}, None)
    render_response(g, EX["r/e"], "materials", {"commodities": [{"name": "Gold", "allocation": 0.1, "instrument": "physical or unleveraged ETF"}],
                                                 "inflation_rationale": "tracks CPI"}, None)
    render_response(g, EX["r/f"], "stocks", {"positions": [{"name": "Company A", "market_cap_usd": 10_000_000_000, "allocation": 0.05, "instrument": "spot equity"}]}, None)
    return g


def test_fast_path_equals_shacl_engine():
    """Running each shape's SELECT once gives the same violations as pyshacl's per-focus-node validation."""
    g = _graph()
    fast = oracle_violations(g)
    engine = oracle_violations(g, use_pyshacl=True)
    assert fast == engine and fast
    assert (str(EX["r/a"]), "MANIFEST_MATERIALS_MAX_ALLOC") not in fast        # 0.10 + 0.05 is exactly 15 %
    assert {(str(EX["r/b"]), r) for r in ("MANIFEST_MATERIALS_MAX_ALLOC", "MANIFEST_MATERIALS_APPROVED",
                                          "MANIFEST_MATERIALS_NO_LEVERAGE", "MANIFEST_MATERIALS_REBALANCE",
                                          "MANIFEST_MATERIALS_INFLATION")} <= fast
    assert (str(EX["r/c"]), "MANIFEST_BONDS_IG_ONLY") in fast                   # N/A is not investment grade
    assert (str(EX["r/c"]), "MANIFEST_BONDS_MAX_DURATION") in fast              # "remain below 10 years"
    assert (str(EX["r/d"]), "MANIFEST_MATERIALS_NO_LEVERAGE") in fast           # "with leverage" after an "unleveraged" alternative
    assert (str(EX["r/e"]), "MANIFEST_MATERIALS_NO_LEVERAGE") not in fast       # "unleveraged" alone is not leverage
    assert (str(EX["r/f"]), "MANIFEST_STOCKS_LARGECAP") in fast                 # "must exceed $10 billion": exactly 10 billion violates


def test_bounds_are_strict_where_the_text_excludes_them():
    """The gate reads "must exceed" and "remain below" as excluding the bound, like the oracle; "maximum" admits it."""
    d = load_domain("finance")
    cap = next(b for b in d.boundary_constraints("stocks") if b.rule_id == "MANIFEST_STOCKS_LARGECAP")
    at = _evaluate_boundary_constraint(cap, {"analysis": "x", "positions": [{"name": "A", "market_cap_usd": 10_000_000_000}]}, d.manifest("stocks"))
    above = _evaluate_boundary_constraint(cap, {"analysis": "x", "positions": [{"name": "A", "market_cap_usd": 10_000_000_001}]}, d.manifest("stocks"))
    assert at.passed is False and above.passed is True
    dur = next(b for b in d.boundary_constraints("bonds") if b.rule_id == "MANIFEST_BONDS_MAX_DURATION")
    at = _evaluate_boundary_constraint(dur, {"analysis": "x", "portfolio_duration_years": 10}, d.manifest("bonds"))
    below = _evaluate_boundary_constraint(dur, {"analysis": "x", "portfolio_duration_years": 9.9}, d.manifest("bonds"))
    assert at.passed is False and below.passed is True
    pos = next(b for b in d.boundary_constraints("stocks") if b.rule_id == "MANIFEST_STOCKS_MAX_POSITION")
    at = _evaluate_boundary_constraint(pos, {"analysis": "x", "positions": [{"name": "A", "allocation": 0.10}]}, d.manifest("stocks"))
    assert at.passed is True


def test_oracle_readings():
    """The oracle's own number and rating readings."""
    assert oracle_number("12%") == 0.12 and oracle_number("€221,000") == 221000 and oracle_number(25, fraction=True) == 0.25
    assert oracle_rating("N/A") is None and oracle_rating("BBB+/Baa1") == oracle_rating("BBB+") and oracle_rating("A (S&P)") == oracle_rating("A")


def test_gate_fixes_found_by_the_oracle():
    """Unrated holdings fail the floor, combined notations parse, copied examples are evaluated, empty set values fail."""
    d = load_domain("finance")
    ig = next(b for b in d.boundary_constraints("bonds") if b.rule_id == "MANIFEST_BONDS_IG_ONLY")
    r = _evaluate_boundary_constraint(ig, {"analysis": "x", "holdings": [{"name": "Gold ETF", "credit_rating": "N/A"}]}, d.manifest("bonds"))
    assert r.passed is False
    assert _rating_rank("BBB+/Baa1") == _rating_rank("BBB+") and _rating_rank("Aaa (Moody's)") == _rating_rank("AAA")
    items = _structured_items([{"name": "Example bond (replace)", "credit_rating": "AA+", "maturity_years": 5, "allocation": 0.25, "region": "developed"}])
    assert items and items[0]["allocation"] == 0.25
    p = load_domain("procurement")
    cpv = next(b for b in p.boundary_constraints("works") if b.rule_id == "MANIFEST_WORKS_CPV_SCOPE")
    r = _evaluate_boundary_constraint(cpv, {"analysis": "x", "lots": [{"name": "Bicycle supply contract", "cpv_division": ""}]}, p.manifest("works"))
    assert r.passed is False


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
