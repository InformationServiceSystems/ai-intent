"""Tests for the gUFO export and the SPARQL integrity checks over a synthetic session.

Runnable without pytest:  python tests/test_gufo_export.py
"""

import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from rdflib import RDF  # noqa: E402

from agents.delegation import accountability_record, build_delegation_chain, check_chain_containment  # noqa: E402
from agents.dispositions import detect_manifestations, get_preset  # noqa: E402
from evaluation.sparql_checks import run_checks  # noqa: E402
from mcp.gufo_export import AII, GUFO, export_session_graph, iri  # noqa: E402
from mcp.logger import MCPLogger, build_message  # noqa: E402


class _Clock:
    """Hands out strictly increasing timestamps so log order is unambiguous."""

    def __init__(self):
        self.t = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

    def next(self):
        self.t += timedelta(seconds=1)
        return self.t


def _log(logger, clock, session, direction, frm, to, method, payload, status="ok"):
    m = build_message(session, direction, frm, to, method, payload, status)
    m.timestamp = clock.next()
    logger.log(m)
    return m


def _build_session(logger, session="sess-ok"):
    """Write a plausible session with one revision, one manifestation and a synthesis."""
    clock = _Clock()
    logger.register_principal(session, "anonymous")
    preset = get_preset("reckless_portfolio")
    scores = {k: v.model_dump() for k, v in preset["scores"].items()}
    _log(logger, clock, session, "internal", "central", "central", "disposition.active",
         {"preset": "reckless_portfolio", "compliance_multiplier": 1.5, "scores": scores})
    _log(logger, clock, session, "internal", "user", "central", "user.query", {"query": "gold?"})
    chain = build_delegation_chain("anonymous")
    _log(logger, clock, session, "internal", "central", "central", "delegation.establish", {
        "chain": [d.model_dump() for d in chain],
        "containment_checks": [c.model_dump() for c in check_chain_containment(chain)],
    })
    _log(logger, clock, session, "internal", "central", "central", "intent.route",
         {"agents_to_call": ["materials"]})
    _log(logger, clock, session, "internal", "compliance", "central", "compliance.approve.central",
         {"approved": True, "checkpoint": "routing", "violated_rules": []}, "approved")
    _log(logger, clock, session, "outbound", "central", "materials", "materials.analyze", {"query": "gold?"}, "pending")
    r1 = _log(logger, clock, session, "inbound", "materials", "central", "materials.result",
              {"analysis": "25% gold", "proposed_allocation": [0.25]})
    rej = _log(logger, clock, session, "internal", "compliance", "central", "compliance.reject.materials",
               {"approved": False, "checkpoint": "analysis", "message_id": r1.id,
                "violated_rules": ["MANIFEST_MATERIALS_MAX_ALLOC"], "revision_count": 0}, "constraint_violation")
    _log(logger, clock, session, "outbound", "compliance", "central", "compliance.revision.materials",
         {"violated_rule_ids": ["MANIFEST_MATERIALS_MAX_ALLOC"], "revision_number": 1}, "constraint_violation")
    r2 = _log(logger, clock, session, "inbound", "materials", "central", "materials.result",
              {"analysis": "12% gold", "proposed_allocation": [0.12]})
    _log(logger, clock, session, "internal", "compliance", "central", "compliance.approve.materials",
         {"approved": True, "checkpoint": "analysis", "message_id": r2.id, "violated_rules": [],
          "revision_count": 1}, "approved")
    _log(logger, clock, session, "internal", "compliance", "central", "compliance.approve.materials.final",
         {"revision_count": 1, "approved": True}, "approved")
    manifestations = detect_manifestations("materials", preset["scores"]["materials"], logger.get_session(session))
    _log(logger, clock, session, "internal", "central", "central", "disposition.manifest.materials",
         {"manifestations": [m.model_dump() for m in manifestations]})
    _log(logger, clock, session, "internal", "central", "central", "intent.synthesize",
         {"final_recommendation": "12% gold"})
    _log(logger, clock, session, "internal", "compliance", "central", "compliance.approve.central",
         {"approved": True, "checkpoint": "synthesis", "violated_rules": []}, "approved")
    _log(logger, clock, session, "inbound", "central", "user", "investment.response", {"final_recommendation": "12% gold"})
    return session, rej


def _build_broken_session(logger, session="sess-bad"):
    """Write a session that violates two invariants: delivery after block, and a block without any commitment."""
    clock = _Clock()
    logger.register_principal(session, "anonymous")
    _log(logger, clock, session, "internal", "user", "central", "user.query", {"query": "x"})
    _log(logger, clock, session, "inbound", "stocks", "central", "stocks.result", {"analysis": "leveraged ETF"})
    _log(logger, clock, session, "internal", "compliance", "central", "compliance.block.stocks",
         {"violated_rules": ["MANIFEST_STOCKS_NO_LEVERAGE"], "revision_count": 2}, "forced_block")
    _log(logger, clock, session, "internal", "compliance", "central", "compliance.approve.stocks.final",
         {"revision_count": 2, "approved": True}, "approved")
    return session


def _logger():
    tmp = tempfile.mkdtemp()
    return MCPLogger(str(Path(tmp) / "t.db"))


def test_export_types_and_links():
    """The export types entries, actions, verdicts, modes and relators as announced."""
    logger = _logger()
    session, rej = _build_session(logger)
    g = export_session_graph(session, logger)
    verdicts = list(g.subjects(RDF.type, AII.ComplianceVerdict))
    assert len(verdicts) == 4
    actions = set(g.subjects(RDF.type, AII.ProposedAction))
    assert len(actions) == 4  # route, result x2, synthesize
    # the rejection verdict historically depends on the first result and inheres in materials
    v = iri("verdict", rej.id)
    assert (v, GUFO.inheresIn, iri("agent", "materials")) in g
    deps = list(g.objects(v, GUFO.historicallyDependsOn))
    assert len(deps) == 1 and deps[0] in actions
    assert (v, AII.violatesRule, iri("rule", "MANIFEST_MATERIALS_MAX_ALLOC")) in g
    # delegation relators and commitments
    assert len(list(g.subjects(RDF.type, AII.Delegation))) == 4
    assert (iri("commitment", "commitment:materials->central"), GUFO.inheresIn, iri("agent", "materials")) in g
    assert (iri("commitment", "commitment:materials->central"), GUFO.externallyDependsOn, iri("agent", "central")) in g
    # disposition manifested in the rejection event
    assert (iri("disposition", "materials/risk_seeking"), GUFO.manifestedIn, iri("entry", rej.id)) in g
    # trace situation brought about by the session
    assert (iri("session", session), GUFO.broughtAbout, iri("trace", session)) in g
    assert (iri("session", session), AII.principal, iri("agent", "anonymous")) in g


def test_integrity_checks_pass_on_well_formed_session():
    """All integrity checks pass for the well-formed session."""
    logger = _logger()
    session, _ = _build_session(logger)
    results = run_checks(export_session_graph(session, logger))
    failing = {r.check_id: r.violations for r in results if not r.passed}
    assert not failing, failing


def test_integrity_checks_catch_violations():
    """Delivery after a block and a block without commitment are both reported."""
    logger = _logger()
    session = _build_broken_session(logger)
    results = {r.check_id: r for r in run_checks(export_session_graph(session, logger))}
    assert not results["Q2_NO_DELIVERY_AFTER_BLOCK"].passed
    assert not results["Q3_BLOCKED_AGENT_ACCOUNTABLE"].passed
    assert results["Q7_TRACE_COMPLETE"].passed


def test_breach_reaches_principal():
    """A logged breach record becomes a situation answerable to the Principal."""
    logger = _logger()
    session, _ = _build_session(logger)
    chain = build_delegation_chain("anonymous")
    clock = _Clock()
    clock.t += timedelta(minutes=1)
    _log(logger, clock, session, "internal", "central", "central", "delegation.breach.materials",
         accountability_record("materials", chain, ["MANIFEST_MATERIALS_MAX_ALLOC"]), "forced_block")
    g = export_session_graph(session, logger)
    breaches = list(g.subjects(RDF.type, AII.CommitmentBreach))
    assert len(breaches) == 1
    assert (breaches[0], AII.answerableTo, iri("agent", "anonymous")) in g
    results = {r.check_id: r for r in run_checks(g)}
    assert results["Q4_BREACH_REACHES_PRINCIPAL"].passed


def test_turtle_serialises():
    """The graph serialises to Turtle with both namespaces bound."""
    logger = _logger()
    session, _ = _build_session(logger)
    ttl = export_session_graph(session, logger).serialize(format="turtle")
    assert "@prefix gufo:" in ttl and "@prefix aii:" in ttl
    assert "gufo:manifestedIn" in ttl and "gufo:historicallyDependsOn" in ttl


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
