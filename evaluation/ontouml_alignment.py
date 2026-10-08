"""Check that the OntoUML model's gUFO typing agrees with the typing the session export declares for each construct."""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import RDFS, Graph, Namespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.gufo_export import AII, GUFO, _add_schema  # noqa: E402

MODEL_TTL = Path(__file__).resolve().parent.parent / "ontology" / "ontouml" / "ai-intent.gufo.ttl"
MODEL_NS = Namespace("https://github.com/InformationServiceSystems/ai-intent/ontology/ontouml#")

# Export construct -> class name in the OntoUML model (names as the transformation writes them).
CONSTRUCT_TO_MODEL = {
    "Principal": "Principal",
    "Agent": "Agent",
    "Mandate": "Mandate",
    "Session": "Session",
    "LogEntry": "LogEntry",
    "ProposedAction": "ProposedAction",
    "ComplianceVerdict": "ComplianceVerdict",
    "AccountabilityTrace": "AccountabilityTrace",
    "Delegation": "Delegation",
    "Commitment": "Commitment",
    "Claim": "Claim",
    "Disposition": "Disposition",
    "CommitmentBreach": "CommitmentBreach",
}

# gUFO classes that the transformation uses for a given export typing are accepted as equal
# when they stand in a subclass relation in gUFO itself (e.g. the model says Kind-of-FunctionalComplex).
GUFO_EQUIVALENT = {
    GUFO.FunctionalComplex: {GUFO.FunctionalComplex, GUFO.Object},
    GUFO.Object: {GUFO.Object, GUFO.FunctionalComplex},
}


def export_typing() -> dict[str, set]:
    """Return the gUFO superclass the export declares for each aii construct."""
    g = Graph()
    _add_schema(g)
    typing: dict[str, set] = {}
    for sub, _, sup in g.triples((None, RDFS.subClassOf, None)):
        typing.setdefault(str(sub).split("#")[-1], set()).add(sup)
    return typing


def model_typing() -> dict[str, set]:
    """Return the gUFO superclasses of each model class, following the model's own generalizations."""
    g = Graph().parse(str(MODEL_TTL), format="turtle")
    parents: dict = {}
    for sub, _, sup in g.triples((None, RDFS.subClassOf, None)):
        if str(sub).startswith(str(MODEL_NS)) and (str(sup).startswith(str(GUFO)) or str(sup).startswith(str(MODEL_NS))):
            parents.setdefault(sub, set()).add(sup)
    typing: dict[str, set] = {}
    for cls in list(parents):
        seen, stack, gufo_types = set(), [cls], set()
        while stack:
            node = stack.pop()
            for sup in parents.get(node, ()):
                if str(sup).startswith(str(GUFO)):
                    gufo_types.add(sup)
                elif sup not in seen:
                    seen.add(sup)
                    stack.append(sup)
        typing[str(cls).split("#")[-1]] = gufo_types
    return typing


def compare() -> list[dict[str, str]]:
    """Return one row per construct with the export typing, the model typing and the verdict."""
    exp, mod = export_typing(), model_typing()
    rows = []
    for construct, model_name in CONSTRUCT_TO_MODEL.items():
        e = exp.get(construct, set())
        m = mod.get(model_name, set())
        agree = False
        for ec in e:
            accepted = GUFO_EQUIVALENT.get(ec, {ec})
            if m & accepted:
                agree = True
        rows.append({
            "construct": construct,
            "export": ", ".join(sorted(str(x).split("#")[-1] for x in e)) or "-",
            "model": ", ".join(sorted(str(x).split("#")[-1] for x in m)) or "-",
            "agree": "yes" if agree else "NO",
        })
    return rows


def main() -> int:
    """Print the alignment table and exit non-zero on any disagreement."""
    rows = compare()
    print("| Construct | Export typing (gufo:) | OntoUML model typing (gufo:) | Agree |")
    print("|---|---|---|---|")
    for r in rows:
        print(f"| {r['construct']} | {r['export']} | {r['model']} | {r['agree']} |")
    bad = [r for r in rows if r["agree"] != "yes"]
    print(f"\n{len(rows)} constructs, {len(bad)} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
