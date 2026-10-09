"""Specification-predicate consistency must hold: text, predicate and manifest agree for every boundary constraint.

C1 (numbers), C2 (terms named) and C3 (manifest wording) must produce no findings now that texts are generated
from the specifications. C4 (constraints without predicates) lists the known cases, so that any new one fails this test.

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

KNOWN_TERM_PROXIES: set[str] = set()   # since constraint texts are generated, every forbidden term is named in the text
# Since ROADMAP 1.1 the rebalancing trigger is a state predicate; only the duration warning remains prose-only.
KNOWN_WITHOUT_PREDICATE = {
    ("bonds", "Must flag any recommendation that would increase overall portfolio duration above 7 years"),
}


def test_numbers_in_text_match_predicate_bounds():
    """Every max_threshold constraint states in its text the bound its predicate enforces."""
    assert [f for f in run_all() if f.check == "C1_BOUND"] == []


def test_registry_text_equals_manifest_text():
    """The text the gate cites is the text the agent received."""
    assert [f.detail for f in run_all() if f.check == "C3_MANIFEST"] == []


def test_term_proxies_are_the_known_ones():
    """Every term predicate is named in its generated text."""
    found = {f.rule_id for f in run_all() if f.check == "C2_TERMS"}
    assert found == KNOWN_TERM_PROXIES, found


def test_constraints_without_predicate_are_the_known_ones():
    """Only the documented manifest constraint lacks a predicate."""
    found = {(f.agent_id, f.detail.split(": ", 1)[1].strip("'")) for f in run_all() if f.check == "C4_COVERAGE"}
    assert found == KNOWN_WITHOUT_PREDICATE, found


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
