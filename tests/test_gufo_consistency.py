"""Tests for the reasoner-based gUFO consistency check (Q9).

Runnable without pytest:  python tests/test_gufo_consistency.py
"""

import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from rdflib import RDF  # noqa: E402

from evaluation.gufo_consistency import check_gufo_consistency, disjoint_pairs, load_ontology  # noqa: E402
from mcp.gufo_export import AII, GUFO, export_session_graph, iri  # noqa: E402
from mcp.logger import MCPLogger  # noqa: E402
from test_gufo_export import _build_session  # noqa: E402


def _graph():
    logger = MCPLogger(str(Path(tempfile.mkdtemp()) / "t.db"))
    session, _ = _build_session(logger)
    return export_session_graph(session, logger)


def test_ontology_and_disjointness_loaded():
    """gUFO parses and yields disjoint pairs including Endurant versus Event."""
    assert len(load_ontology()) > 500
    names = {(str(a).split("#")[-1], str(b).split("#")[-1]) for a, b in disjoint_pairs()}
    assert ("Endurant", "Event") in names or ("Event", "Endurant") in names


def test_well_formed_export_is_consistent():
    """The export of a well-formed session passes the reasoner check and infers UFO types."""
    res = check_gufo_consistency(_graph())
    assert res.passed, res.violations
    assert res.inferred_triples > 100


def test_mode_typed_as_event_is_caught():
    """A verdict additionally typed as an event lands in two disjoint categories."""
    g = _graph()
    verdict = next(g.subjects(RDF.type, AII.ComplianceVerdict))
    g.add((verdict, RDF.type, GUFO.Event))
    res = check_gufo_consistency(g)
    assert not res.passed
    assert any(v["individual"].startswith("verdict/") for v in res.violations)


def test_event_inhering_is_caught_through_domain():
    """An event used as the subject of inheresIn is inferred to be an Aspect, which is disjoint with Event."""
    g = _graph()
    entry = next(g.subjects(RDF.type, AII.LogEntry))
    g.add((entry, GUFO.inheresIn, iri("agent", "materials")))
    res = check_gufo_consistency(g)
    assert not res.passed
    assert any(v["individual"].startswith("entry/") for v in res.violations)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
