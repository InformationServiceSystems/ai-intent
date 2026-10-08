"""Specification-predicate consistency must hold: text, predicate and manifest agree for every boundary constraint.

C1 (numbers) and C3 (manifest wording) must produce no findings. C2 (term proxies) and C4 (constraints
without predicates) are known and listed here, so that any new divergence fails this test.

Runnable without pytest:  python tests/test_spec_consistency.py
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

from evaluation.spec_consistency import run_all  # noqa: E402

KNOWN_TERM_PROXIES = {"MANIFEST_STOCKS_LARGECAP", "MANIFEST_MATERIALS_APPROVED"}
KNOWN_WITHOUT_PREDICATE = {
    ("bonds", "Must flag any recommendation that would increase overall portfolio duration above 7 years"),
    ("materials", "Rebalancing trigger: flag to orchestrator if allocation drifts more than ±5% from target"),
}


def test_numbers_in_text_match_predicate_bounds():
    """Every max_threshold constraint states in its text the bound its predicate enforces."""
    assert [f for f in run_all() if f.check == "C1_BOUND"] == []


def test_registry_text_equals_manifest_text():
    """The text the gate cites is the text the agent received."""
    assert [f.detail for f in run_all() if f.check == "C3_MANIFEST"] == []


def test_term_proxies_are_the_known_ones():
    """Only the two documented constraints check a proxy term list instead of the stated rule."""
    found = {f.rule_id for f in run_all() if f.check == "C2_TERMS"}
    assert found == KNOWN_TERM_PROXIES, found


def test_constraints_without_predicate_are_the_known_ones():
    """Only the two documented manifest constraints lack a predicate."""
    found = {(f.agent_id, f.detail.split(": ", 1)[1].strip("'")) for f in run_all() if f.check == "C4_COVERAGE"}
    assert found == KNOWN_WITHOUT_PREDICATE, found


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
