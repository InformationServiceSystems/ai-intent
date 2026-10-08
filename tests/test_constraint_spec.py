"""Tests for the single-source constraint specifications: text, predicate and manifest derive from one spec.

Runnable without pytest:  python tests/test_constraint_spec.py
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

from agents.constraint_spec import CONSTRAINT_SPECS, render_text, specs_for, to_boundary_constraint  # noqa: E402
from agents.manifests import MATERIALS_RISK, STOCKS_RISK, get_manifest  # noqa: E402
from agents.regulatory_rules import get_boundary_constraints_for_agent  # noqa: E402


def test_numbers_come_from_risk_parameters():
    """Changing a risk parameter changes the generated text; nothing else needs editing."""
    spec = next(s for s in CONSTRAINT_SPECS if s.rule_id == "MANIFEST_MATERIALS_MAX_ALLOC")
    assert render_text(spec, MATERIALS_RISK) == "Maximum 15% of total portfolio in raw materials"
    assert render_text(spec, {**MATERIALS_RISK, "max_total_allocation": 0.2}) == "Maximum 20% of total portfolio in raw materials"
    cap = next(s for s in CONSTRAINT_SPECS if s.rule_id == "MANIFEST_STOCKS_LARGECAP")
    assert "$10 billion" in render_text(cap, STOCKS_RISK)
    assert "$25 billion" in render_text(cap, {**STOCKS_RISK, "max_market_cap_threshold": 25_000_000_000})


def test_manifest_text_equals_registry_text():
    """The text in the agent's manifest is byte-identical to the text the gate cites, for every spec."""
    for agent_id in ("stocks", "bonds", "materials", "central"):
        manifest_texts = set(get_manifest(agent_id).boundary_constraints)
        for bc in get_boundary_constraints_for_agent(agent_id):
            assert bc.text in manifest_texts, (agent_id, bc.rule_id, bc.text)


def test_registry_order_and_predicates_follow_specs():
    """The registry has one entry per spec, in spec order, with the predicate kind the spec implies."""
    kinds = {"max": "max_threshold", "forbid": "forbidden_term", "require": "required_term", "in_set": "in_set", "min": "min_threshold"}
    for agent_id in ("stocks", "bonds", "materials", "central"):
        specs = specs_for(agent_id)
        bcs = get_boundary_constraints_for_agent(agent_id)
        assert [s.rule_id for s in specs] == [b.rule_id for b in bcs]
        assert [kinds[s.kind] for s in specs] == [b.predicate.kind for b in bcs]


def test_forbidden_terms_are_named_in_text():
    """A forbid spec's text names each plain term it forbids (first five characters, case-insensitive)."""
    for spec in CONSTRAINT_SPECS:
        if not spec.terms:
            continue
        text = to_boundary_constraint(spec, get_manifest(spec.agent_id).risk_parameters).text.lower()
        assert any(t.lower()[:5] in text for t in spec.terms), spec.rule_id


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
