"""Q9: check a session graph against the gUFO axioms with an OWL-RL reasoner (domain, range, subclass, disjointness)."""

from __future__ import annotations

import argparse
import glob
import sys
import time
from functools import lru_cache
from pathlib import Path

import owlrl
from pydantic import BaseModel
from rdflib import OWL, RDF, Graph, URIRef
from rdflib.collection import Collection

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.sparql_checks import CheckResult  # noqa: E402

ONTOLOGY_PATH = Path(__file__).parent / "ontology" / "gufo.ttl"
CHECK_ID = "Q9_GUFO_CONSISTENT"
CLAIM = "The session graph is consistent with the gUFO axioms: no individual falls into two disjoint UFO categories after OWL-RL closure"


class GufoConsistency(BaseModel):
    """Outcome of the reasoner-based check on one graph."""

    passed: bool
    inferred_triples: int
    violations: list[dict[str, str]]
    seconds: float


@lru_cache(maxsize=1)
def load_ontology() -> Graph:
    """Parse the gUFO ontology once (CC BY 4.0, http://purl.org/nemo/gufo)."""
    return Graph().parse(str(ONTOLOGY_PATH), format="turtle")


@lru_cache(maxsize=1)
def disjoint_pairs() -> tuple[tuple[URIRef, URIRef], ...]:
    """All pairwise disjoint class pairs of gUFO, from owl:disjointWith and owl:AllDisjointClasses."""
    onto = load_ontology()
    pairs: set[tuple[URIRef, URIRef]] = set()
    for c1, _, c2 in onto.triples((None, OWL.disjointWith, None)):
        pairs.add((c1, c2))
    for axiom in onto.subjects(RDF.type, OWL.AllDisjointClasses):
        members = list(Collection(onto, onto.value(axiom, OWL.members)))
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pairs.add((members[i], members[j]))
    return tuple(sorted(pairs))


def _local(uri: URIRef) -> str:
    """Return the fragment of an IRI for readable reports."""
    return str(uri).split("#")[-1]


def check_gufo_consistency(graph: Graph, only_namespace: str = "ai-intent") -> GufoConsistency:
    """Close the graph under OWL-RL with the gUFO axioms and report individuals typed into disjoint classes."""
    start = time.perf_counter()
    closed = Graph()
    for triple in graph:
        closed.add(triple)
    for triple in load_ontology():
        closed.add(triple)
    before = len(closed)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(closed)
    violations: list[dict[str, str]] = []
    for x in closed.subjects(RDF.type, OWL.Nothing):
        if only_namespace in str(x):
            violations.append({"individual": _local(x), "class_a": "owl:Nothing", "class_b": ""})
    for c1, c2 in disjoint_pairs():
        shared = set(closed.subjects(RDF.type, c1)) & set(closed.subjects(RDF.type, c2))
        for x in shared:
            if only_namespace in str(x):
                violations.append({"individual": _local(x), "class_a": _local(c1), "class_b": _local(c2)})
    return GufoConsistency(
        passed=not violations,
        inferred_triples=len(closed) - before,
        violations=sorted(violations, key=lambda v: v["individual"]),
        seconds=round(time.perf_counter() - start, 2),
    )


def as_check_result(result: GufoConsistency) -> CheckResult:
    """Render the reasoner outcome in the same shape as the SPARQL checks."""
    return CheckResult(check_id=CHECK_ID, claim=CLAIM, passed=result.passed, violations=result.violations)


def main() -> int:
    """Run Q9 over persisted session graphs: python evaluation/gufo_consistency.py --prefix ufo_hpc3"""
    parser = argparse.ArgumentParser(description="gUFO consistency over persisted session graphs")
    parser.add_argument("--prefix", default="ufo_hpc", help="session file prefix under evaluation/sessions")
    parser.add_argument("--limit", type=int, default=0, help="check at most N graphs (0 = all)")
    args = parser.parse_args()
    files = sorted(glob.glob(str(Path(__file__).parent / "sessions" / f"{args.prefix}*_TC-*.ttl")))
    if args.limit:
        files = files[: args.limit]
    failed = 0
    inferred = []
    seconds = []
    for f in files:
        res = check_gufo_consistency(Graph().parse(f, format="turtle"))
        inferred.append(res.inferred_triples)
        seconds.append(res.seconds)
        if not res.passed:
            failed += 1
            print(f"FAIL {Path(f).name}: {res.violations[:3]}")
    n = len(files)
    if n:
        print(f"{n} graphs, {failed} inconsistent; inferred triples mean {sum(inferred)//n}; "
              f"seconds per graph mean {sum(seconds)/n:.1f}, max {max(seconds):.1f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
