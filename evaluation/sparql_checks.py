"""Integrity checks over gUFO session graphs: SPARQL queries that must return no rows for a well-formed trace."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import BaseModel
from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.gufo_export import export_session_graph  # noqa: E402
from mcp.logger import MCPLogger, get_logger  # noqa: E402

PREFIXES = """
PREFIX gufo: <http://purl.org/nemo/gufo#>
PREFIX aii:  <https://github.com/InformationServiceSystems/ai-intent/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


class IntegrityCheck(BaseModel):
    """A named SPARQL query whose result rows are violations of one trace invariant."""

    check_id: str
    claim: str
    description: str
    query: str


class CheckResult(BaseModel):
    """Outcome of one integrity check on one session graph."""

    check_id: str
    claim: str
    passed: bool
    violations: list[dict[str, str]]


CHECKS: list[IntegrityCheck] = [
    IntegrityCheck(
        check_id="Q1_VERDICT_SINGLE_ACTION",
        claim="A Compliance Verdict is a mode that historically depends on exactly one Proposed Action",
        description="Verdicts with zero or several evaluated actions",
        query="""
        SELECT ?verdict (COUNT(?action) AS ?actions) WHERE {
          ?verdict a aii:ComplianceVerdict .
          OPTIONAL { ?verdict gufo:historicallyDependsOn ?action . ?action a aii:ProposedAction }
        } GROUP BY ?verdict HAVING (COUNT(?action) != 1)
        """,
    ),
    IntegrityCheck(
        check_id="Q2_NO_DELIVERY_AFTER_BLOCK",
        claim="A blocked agent's output is never delivered afterwards in the same session",
        description="Final approvals for an agent that follow a block of that agent",
        query="""
        SELECT ?agent ?block ?final WHERE {
          ?block a aii:LogEntry ; aii:method ?bm ; aii:targetAgent ?agent ; aii:sequence ?sb .
          FILTER(STRSTARTS(STR(?bm), "compliance.block."))
          ?final a aii:LogEntry ; aii:method ?fm ; aii:targetAgent ?agent ; aii:sequence ?sf .
          FILTER(STRSTARTS(STR(?fm), "compliance.approve.") && STRENDS(STR(?fm), ".final"))
          FILTER(?sf > ?sb)
        }
        """,
    ),
    IntegrityCheck(
        check_id="Q3_BLOCKED_AGENT_ACCOUNTABLE",
        claim="Every blocked agent bears a Commitment, so the breach has an answerable party",
        description="Blocked agents without a commitment inhering in them",
        query="""
        SELECT ?agent WHERE {
          ?block a aii:LogEntry ; aii:method ?m ; aii:targetAgent ?agent .
          FILTER(STRSTARTS(STR(?m), "compliance.block."))
          FILTER NOT EXISTS { ?c a aii:Commitment ; gufo:inheresIn ?agent }
        }
        """,
    ),
    IntegrityCheck(
        check_id="Q4_BREACH_REACHES_PRINCIPAL",
        claim="Every commitment breach is answerable to the session's Principal",
        description="Breach situations whose answerable parties do not include the Principal",
        query="""
        SELECT ?breach WHERE {
          ?breach a aii:CommitmentBreach .
          ?session a aii:Session ; aii:principal ?principal .
          FILTER NOT EXISTS { ?breach aii:answerableTo ?principal }
        }
        """,
    ),
    IntegrityCheck(
        check_id="Q5_MANIFESTATION_HAS_BEARER",
        claim="A disposition is manifested only in events of the agent that bears it, and only if its degree is positive",
        description="Manifestations whose event targets another agent or whose disposition has no degree",
        query="""
        SELECT ?disposition ?event WHERE {
          ?disposition a aii:Disposition ; gufo:inheresIn ?bearer ; gufo:manifestedIn ?event .
          OPTIONAL { ?disposition aii:degree ?degree }
          OPTIONAL { ?event aii:targetAgent ?target }
          FILTER(!BOUND(?degree) || ?degree <= 0 || (BOUND(?target) && ?target != ?bearer))
        }
        """,
    ),
    IntegrityCheck(
        check_id="Q6_EVERY_ANALYSIS_EVALUATED",
        claim="Every Proposed Action at the analysis checkpoint receives a verdict before anything is delivered",
        description="Analysis-checkpoint actions without a verdict depending on them",
        query="""
        SELECT ?action WHERE {
          ?action a aii:ProposedAction ; aii:checkpoint "analysis" ; aii:status ?status .
          FILTER(?status != "error")
          FILTER NOT EXISTS { ?v a aii:ComplianceVerdict ; gufo:historicallyDependsOn ?action }
        }
        """,
    ),
    IntegrityCheck(
        check_id="Q7_TRACE_COMPLETE",
        claim="The Accountability Trace is the situation brought about by the whole session: it comprises every log entry",
        description="Log entries missing from the trace situation",
        query="""
        SELECT ?entry WHERE {
          ?entry a aii:LogEntry .
          FILTER NOT EXISTS { ?trace a aii:AccountabilityTrace ; aii:comprises ?entry }
        }
        """,
    ),
    IntegrityCheck(
        check_id="Q8_VIOLATED_RULE_IN_COMMITMENT",
        claim="A rule a verdict names against an agent belongs to that agent's commitment",
        description="Violated rules that the breaching agent never committed to",
        query="""
        SELECT ?agent ?rule WHERE {
          ?verdict a aii:ComplianceVerdict ; gufo:inheresIn ?agent ; aii:violatesRule ?rule .
          ?commitment a aii:Commitment ; gufo:inheresIn ?agent .
          FILTER NOT EXISTS { ?commitment aii:coversRule ?rule }
        }
        """,
    ),
]


def run_checks(graph: Graph, checks: list[IntegrityCheck] | None = None) -> list[CheckResult]:
    """Run every integrity check against a graph and report the violating rows."""
    results: list[CheckResult] = []
    for check in checks or CHECKS:
        rows = graph.query(PREFIXES + check.query)
        violations = [
            {str(var): str(row[i]) for i, var in enumerate(rows.vars) if row[i] is not None}
            for row in rows
        ]
        results.append(CheckResult(
            check_id=check.check_id, claim=check.claim, passed=not violations, violations=violations,
        ))
    return results


def check_session(session_id: str, logger: MCPLogger | None = None) -> list[CheckResult]:
    """Export one session to gUFO and run all integrity checks on it."""
    return run_checks(export_session_graph(session_id, logger or get_logger()))


def _print_results(session_id: str, results: list[CheckResult]) -> None:
    """Print a one-line-per-check summary for a session."""
    print(f"session {session_id}")
    for r in results:
        mark = "pass" if r.passed else f"FAIL ({len(r.violations)})"
        print(f"  {r.check_id:<32} {mark}")
        for v in r.violations[:3]:
            print(f"      {v}")


def main() -> int:
    """Command-line entry: check one session, or the most recent N sessions."""
    parser = argparse.ArgumentParser(description="SPARQL integrity checks over gUFO session graphs")
    parser.add_argument("session_id", nargs="?", help="session to check; omit with --all")
    parser.add_argument("--all", action="store_true", help="check the most recent sessions")
    parser.add_argument("--limit", type=int, default=20, help="number of sessions with --all")
    parser.add_argument("--turtle", metavar="PATH", help="also write the session graph as Turtle")
    args = parser.parse_args()

    logger = get_logger()
    if args.all:
        sessions = logger.get_all_sessions()[: args.limit]
    elif args.session_id:
        sessions = [args.session_id]
    else:
        parser.error("give a session_id or --all")
        return 2

    failed = 0
    for sid in sessions:
        graph = export_session_graph(sid, logger)
        results = run_checks(graph)
        _print_results(sid, results)
        failed += sum(1 for r in results if not r.passed)
        if args.turtle and len(sessions) == 1:
            Path(args.turtle).write_text(graph.serialize(format="turtle"))
            print(f"  wrote {args.turtle}")
    print(f"{len(sessions)} session(s), {failed} failing check(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
