"""Design-time checks (ROADMAP 2.2): both domains are clean, and every check reports the defect it targets when one is injected.

Runnable without pytest:  python tests/test_design_checks.py
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
from agents.domain import load_domain  # noqa: E402
from evaluation.design_checks import ONTOUML, run_design_checks  # noqa: E402


def _mutated(name: str):
    """A deep copy of a domain that the mutation may change freely."""
    return load_domain(name).model_copy(deep=True)


def _checks(domain) -> set[str]:
    return {f.check for f in run_design_checks(domain)}


def test_both_domains_are_clean():
    """No finding on the shipped specifications, including the OntoUML cardinalities."""
    for name in ("finance", "procurement"):
        assert run_design_checks(load_domain(name)) == [], name


def test_d1_unused_parameter():
    """A parameter no predicate reads is reported."""
    d = _mutated("finance")
    d.manifests["stocks"].risk_parameters["max_sector_share"] = 0.25
    assert "D1_UNUSED_PARAMETER" in _checks(d)


def test_d2_foreign_key():
    """A predicate reading a parameter its own Mandate does not define is reported."""
    d = _mutated("finance")
    spec = next(s for s in d.constraint_specs if s.rule_id == "MANIFEST_STOCKS_MAX_POSITION")
    spec.risk_param_key = "max_total_allocation"     # a materials parameter
    assert "D2_FOREIGN_OR_MISSING_KEY" in _checks(d)


def test_d3_contradictory_bounds():
    """A floor above the ceiling on the same field is reported."""
    d = _mutated("procurement")
    d.manifests["services"].risk_parameters["min_cpv_division"] = 99
    assert "D3_CONTRADICTORY_BOUNDS" in _checks(d)


def test_d4_set_conflict():
    """An approved value that a prohibition on the same field forbids is reported."""
    d = _mutated("finance")
    d.constraint_specs.append(next(s for s in d.constraint_specs if s.rule_id == "MANIFEST_MATERIALS_NO_LEVERAGE")
                              .model_copy(update={"item_key": "name", "forbidden_values": ["silver"], "condition_param": None}))
    assert "D4_SET_CONFLICT" in _checks(d)


def test_d5_cap_above_parent():
    """A sub-mandate cap above the parent's cap is reported."""
    d = _mutated("finance")
    d.manifests["materials"].risk_parameters["max_total_allocation"] = 0.55
    assert "D5_CAP_ABOVE_PARENT" in _checks(d)


def test_d6_unregistered_rule():
    """A constraint whose rule is not in the registry is reported."""
    d = _mutated("procurement")
    d.rules = [r for r in d.rules if r.rule_id != "MANIFEST_SERVICES_LOT_VALUE"]
    assert "D6_RULE_REGISTRY" in _checks(d)


def test_d7_model_cardinality(tmp_path=None):
    """The original model's exactly-one constraint per Mandate is reported against the content."""
    import tempfile
    text = ONTOUML.read_text().replace(
        "owl:onProperty [ owl:inverseOf :constraintInheresInMandate ];\n  owl:someValuesFrom :BoundaryConstraint",
        "owl:onProperty [ owl:inverseOf :constraintInheresInMandate ];\n  owl:qualifiedCardinality \"1\"^^xsd:nonNegativeInteger;\n  owl:onClass :BoundaryConstraint")
    assert "qualifiedCardinality \"1\"^^xsd:nonNegativeInteger;\n  owl:onClass :BoundaryConstraint" in text
    with tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False) as f:
        f.write(text)
    found = run_design_checks(load_domain("finance"), Path(f.name))
    assert any(x.check == "D7_MODEL_CARDINALITY" and x.subject == "stocks" for x in found)


def test_condition_parameters_take_effect():
    """leverage_permitted and performance_guarantee_required now change what the gate enforces."""
    d = _mutated("finance")
    bc = next(b for b in d.boundary_constraints("stocks") if b.rule_id == "MANIFEST_STOCKS_NO_LEVERAGE")
    payload = {"analysis": "x", "positions": [{"name": "T", "instrument": "3x leveraged ETF"}]}
    assert _evaluate_boundary_constraint(bc, payload, d.manifest("stocks")).passed is False
    d.manifests["stocks"].risk_parameters["leverage_permitted"] = True
    r = _evaluate_boundary_constraint(bc, payload, d.manifest("stocks"))
    assert r.passed is True and "Not applicable" in r.detail


def test_duration_warning_is_a_non_blocking_flag_obligation():
    """Above 7 years without a duration flag the obligation fails; flagged it passes; the rule has warn severity."""
    d = load_domain("finance")
    bc = next(b for b in d.boundary_constraints("bonds") if b.rule_id == "MANIFEST_BONDS_DURATION_WARN")
    m = d.manifest("bonds")
    assert _evaluate_boundary_constraint(bc, {"analysis": "x", "portfolio_duration_years": 8.5}, m).passed is False
    assert _evaluate_boundary_constraint(bc, {"analysis": "x", "portfolio_duration_years": 8.5, "constraint_flags": ["Duration above 7 years"]}, m).passed is True
    assert _evaluate_boundary_constraint(bc, {"analysis": "x", "portfolio_duration_years": 6}, m).passed is True
    assert d.rule("MANIFEST_BONDS_DURATION_WARN").severity == "warn"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
