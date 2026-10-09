"""Independent oracle for specification-to-predicate consistency (ROADMAP 3.2).

The gate's predicates and the evaluation's expected rule ids share one source (ConstraintSpec).
This oracle is a second encoding of the same Mandates in another formalism: SHACL-SPARQL shapes
written from the natural-language Mandate texts (evaluation/oracle/shapes_*.ttl), applied to the
oracle's own RDF rendering of every logged agent response. For every (response, rule) pair where the
gate evaluated the rule and the response carries the typed field the rule reads, the gate's verdict
on that rule is compared with the oracle's. A disagreement is a miscoding in one of the two encodings
or a reading of the text on which they differ; each is listed for inspection.

Independence is in source and formalism, not in authorship: both encodings were written by the same
author, the oracle from the texts and the response schema only.

Usage:  python evaluation/oracle_agreement.py [--prefix c4_ --prefix full_ ...] [--markdown OUT.md]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
EX = Namespace("https://github.com/InformationServiceSystems/ai-intent/oracle#")
SH = Namespace("http://www.w3.org/ns/shacl#")

# Fields the oracle treats as fractions of a whole (the response schema documents them as "0.08 means 8%").
FRACTION_FIELDS = {"allocation", "share", "budget_share", "subcontracting_share", "supply_share"}

# Which typed field each rule reads, from the Mandate texts: the comparison is made only when it is present.
RULE_FIELDS: dict[str, str] = {
    "MANIFEST_STOCKS_LARGECAP": "positions", "MANIFEST_STOCKS_MAX_POSITION": "positions",
    "MANIFEST_STOCKS_NO_LEVERAGE": "positions", "MANIFEST_STOCKS_ESG": "positions", "MANIFEST_STOCKS_EXPOSURE": "positions",
    "MANIFEST_BONDS_IG_ONLY": "holdings", "MANIFEST_BONDS_MAX_DURATION": "portfolio_duration_years",
    "MANIFEST_BONDS_NO_EM": "holdings", "MANIFEST_BONDS_LADDER": "holdings", "MANIFEST_BONDS_DURATION_WARN": "portfolio_duration_years",
    "MANIFEST_MATERIALS_MAX_ALLOC": "commodities", "MANIFEST_MATERIALS_APPROVED": "commodities",
    "MANIFEST_MATERIALS_NO_LEVERAGE": "commodities", "MANIFEST_MATERIALS_REBALANCE": "commodities",
    "MANIFEST_MATERIALS_INFLATION": "inflation_rationale", "MANIFEST_CENTRAL_MAX_ASSET_CLASS": "allocation_by_asset_class",
    "MANIFEST_SUPPLIES_CPV_SCOPE": "lots", "MANIFEST_SUPPLIES_LOT_VALUE": "lots", "MANIFEST_SUPPLIES_LOT_SHARE": "lots",
    "MANIFEST_SUPPLIES_NO_SINGLE_SOURCE": "lots", "MANIFEST_SUPPLIES_SUSTAINABILITY": "lots", "MANIFEST_SUPPLIES_BUDGET_EXPOSURE": "lots",
    "MANIFEST_SERVICES_CPV_SCOPE": "lots", "MANIFEST_SERVICES_MIXED_CONTRACT": "supply_share", "MANIFEST_SERVICES_LOT_VALUE": "lots",
    "MANIFEST_SERVICES_SUBCONTRACTING": "lots", "MANIFEST_SERVICES_FRAMEWORK_DURATION": "framework_duration_years",
    "MANIFEST_SERVICES_CONFLICT_SCREENING": "conflict_of_interest_screening",
    "MANIFEST_WORKS_CPV_SCOPE": "lots", "MANIFEST_WORKS_LOT_VALUE": "lots", "MANIFEST_WORKS_SUBCONTRACTING": "lots",
    "MANIFEST_WORKS_NO_SINGLE_SOURCE": "lots", "MANIFEST_WORKS_PERFORMANCE_GUARANTEE": "lots",
    "MANIFEST_COORDINATOR_MAX_CONTRACT_TYPE": "allocation_by_contract_type",
}

# The oracle's own ordinal rating scale (S&P/Fitch with Moody's equivalents), BBB+ = Baa1 = 15.
_SP = ["D", "C", "CC", "CCC-", "CCC", "CCC+", "B-", "B", "B+", "BB-", "BB", "BB+", "BBB-", "BBB", "BBB+", "A-", "A", "A+", "AA-", "AA", "AA+", "AAA"]
_MOODYS = ["D", "C", "Ca", "Caa3", "Caa2", "Caa1", "B3", "B2", "B1", "Ba3", "Ba2", "Ba1", "Baa3", "Baa2", "Baa1", "A3", "A2", "A1", "Aa3", "Aa2", "Aa1", "Aaa"]
RATING_RANK = {r: i + 1 for i, r in enumerate(_SP)} | {r: i + 1 for i, r in enumerate(_MOODYS)}


def oracle_number(raw, fraction: bool = False) -> float | None:
    """The oracle's reading of a number: plain numbers, '12%', '$2.8 trillion', '€221,000', '150k'."""
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
    else:
        text = str(raw).strip().lower().replace(",", "").replace("$", "").replace("€", "").replace("eur", "").strip()
        m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(%|trillion|billion|million|bn|k|t|b|m)?", text)
        if not m:
            return None
        value = float(m.group(1))
        unit = m.group(2)
        if unit == "%":
            return value / 100.0
        value *= {"trillion": 1e12, "t": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "m": 1e6, "k": 1e3}.get(unit or "", 1.0)
    if fraction and value > 1.0:
        value /= 100.0
    return value


def oracle_rating(raw) -> int | None:
    """Rank of the first token that is a rating on either scale, or None."""
    text = str(raw or "").strip()
    if text.lower() in ("n/a", "na", "nr", "not rated", "unrated", "none", ""):
        return None
    for token in re.findall(r"(?<![A-Za-z])[A-Za-z]+[+-]?\d?(?![A-Za-z+\-\d])", text):
        if token in RATING_RANK:
            return RATING_RANK[token]
    return None


def _literal(key: str, value) -> Literal | None:
    """Typed literal for one field value."""
    if isinstance(value, bool):
        return Literal(value, datatype=XSD.boolean)
    if key in ("name", "instrument", "region", "procedure", "credit_rating", "esg_assessment", "sustainability_criterion",
               "performance_guarantee", "inflation_rationale", "conflict_of_interest_screening"):
        return Literal(str(value))
    num = oracle_number(value, fraction=key in FRACTION_FIELDS)
    if num is not None:
        return _decimal(num)
    return Literal(str(value))


def _decimal(value: float) -> Literal:
    """xsd:decimal from the shortest decimal form of a float; Literal(0.4, xsd:decimal) would be 0.40000000000000002."""
    from decimal import Decimal
    return Literal(Decimal(repr(round(value, 9))), datatype=XSD.decimal)


def render_response(g: Graph, node: URIRef, agent: str, payload: dict, state: dict | None) -> None:
    """The oracle's RDF rendering of one response: scalars as literals, lists as item nodes, maps as share nodes."""
    g.add((node, RDF.type, EX.Response))
    g.add((node, EX.agent, Literal(agent)))
    for flag in payload.get("constraint_flags") or []:
        g.add((node, EX.flag, Literal(str(flag))))
    for key, value in payload.items():
        if key in ("analysis", "constraint_flags", "recommendation", "confidence", "out_of_scope", "proposed_allocation", "accountability_note", "model_accountability_note", "final_recommendation"):
            continue
        prop = EX[key]
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                n = BNode()
                g.add((node, prop, n))
                for k, v in item.items():
                    lit = _literal(k, v)
                    if lit is not None:
                        g.add((n, EX[k], lit))
                if "credit_rating" in item:
                    rank = oracle_rating(item["credit_rating"])
                    if rank is not None:
                        g.add((n, EX.rating_rank, Literal(rank, datatype=XSD.integer)))
        elif isinstance(value, dict):
            for k, v in value.items():
                n = BNode()
                g.add((node, prop, n))
                g.add((n, EX.category, Literal(str(k))))
                num = oracle_number(v, fraction=True)
                if num is not None:
                    g.add((n, EX.share, _decimal(num)))
        else:
            lit = _literal(key, value)
            if lit is not None:
                g.add((node, prop, lit))
    for kind in ("current", "target"):
        for k, v in ((state or {}).get(kind) or {}).items():
            g.add((node, EX[f"state_{kind}_{k}"], _decimal(float(v))))


def _field_present(payload: dict, field: str) -> bool:
    """The typed field the rule reads is present with content."""
    value = payload.get(field)
    if value in (None, "", [], {}):
        return False
    if isinstance(value, list):
        return any(isinstance(i, dict) for i in value)
    return True


def _current_gate(agent: str, payload: dict, state: dict | None, domain_id: str) -> dict[str, bool]:
    """The current gate's verdict per rule on a logged payload (deterministic boundary constraints only)."""
    from agents.compliance import _check_boundary_constraints
    from agents.domain import SessionState, load_domain, set_domain
    from agents import domain as domain_module
    if domain_module._active is None or domain_module._active.domain_id != domain_id:
        set_domain(load_domain(domain_id))
    st = SessionState(label=state.get("label", "logged"), current=state.get("current") or {}, target=state.get("target") or {}) if state else None
    out: dict[str, bool] = {}
    for r in _check_boundary_constraints(agent, payload, st):
        if r.rule_id in RULE_FIELDS:
            out[r.rule_id] = out.get(r.rule_id, True) and r.passed
    return out


def collect(prefixes: list[str], regate: bool = False) -> tuple[list[dict], Graph]:
    """Every (response, rule) pair the gate evaluated on a typed field, with the gate's verdict, and the data graph."""
    g = Graph()
    pairs: list[dict] = []
    files = sorted(f for p in prefixes for f in (ROOT / "sessions").glob(f"{p}*.json"))
    for f in files:
        session = json.loads(f.read_text())
        log = session["mcp_log"]
        by_id = {m["id"]: m for m in log}
        state = next((m["payload"] for m in log if m["method"] == "state.snapshot"), None)
        for m in log:
            if not (m["method"].startswith("compliance.approve.") or m["method"].startswith("compliance.reject.")):
                continue
            verdict = m["payload"]
            if verdict.get("checkpoint") not in ("analysis", "synthesis"):
                continue
            action = by_id.get(verdict.get("message_id"))
            if action is None:
                continue
            payload = action["payload"]
            agent = action["from_agent"]
            gate: dict[str, bool] = {}
            for r in verdict.get("deterministic_results") or []:
                rid = r.get("rule_id")
                if rid in RULE_FIELDS:
                    gate[rid] = gate.get(rid, True) and bool(r.get("passed"))
            if regate and gate:
                current = _current_gate(agent, payload, state, session.get("domain") or "finance")
                gate = {rid: current[rid] for rid in gate if rid in current}
            node = EX[f"r/{f.stem}/{action['id']}"]
            rendered = False
            for rid, passed in gate.items():
                if not _field_present(payload, RULE_FIELDS[rid]):
                    continue
                if not rendered:
                    render_response(g, node, agent, payload, state)
                    rendered = True
                pairs.append({"session": f.stem, "response": str(node), "agent": agent, "rule": rid, "gate_passed": passed,
                              "campaign": f.stem.split("_TC-")[0].split("_PC-")[0]})
    return pairs, g


def load_shapes() -> Graph:
    """All shapes of the second encoding."""
    shapes = Graph()
    for ttl in sorted((ROOT / "oracle").glob("shapes_*.ttl")):
        shapes.parse(str(ttl))
    return shapes


def oracle_violations(data: Graph, use_pyshacl: bool = False) -> set[tuple[str, str]]:
    """(response IRI, rule id) pairs the oracle finds violated.

    By the SHACL-SPARQL semantics a focus node violates a shape iff the shape's SELECT returns a row with
    $this bound to it. The fast path runs each SELECT once with $this free; `use_pyshacl` runs the SHACL
    engine instead (per focus node, slow) and is used by the test that checks the two agree.
    """
    shapes = load_shapes()
    rule_of = {str(s): str(o) for s, o in shapes.subject_objects(EX.ruleId)}
    out = set()
    if use_pyshacl:
        _, report, _ = validate(data, shacl_graph=shapes, advanced=True, allow_warnings=True, inference="none")
        for result in report.subjects(RDF.type, SH.ValidationResult):
            focus = report.value(result, SH.focusNode)
            shape = report.value(result, SH.sourceShape)
            if focus is not None and shape is not None and str(shape) in rule_of:
                out.add((str(focus), rule_of[str(shape)]))
        return out
    prefix = "PREFIX ex: <https://github.com/InformationServiceSystems/ai-intent/oracle#>\n"
    for shape, rule in rule_of.items():
        for constraint in shapes.objects(URIRef(shape), SH.sparql):
            select = str(shapes.value(constraint, SH.select)).replace("$this", "?this")
            for row in data.query(prefix + select):
                out.add((str(row[0]), rule))
    return out


def agreement(prefixes: list[str], regate: bool = False) -> dict:
    """Compare gate and oracle on every pair; return counts per rule and the disagreements."""
    pairs, data = collect(prefixes, regate)
    violated = oracle_violations(data)
    per_rule: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    disagreements = []
    for p in pairs:
        oracle_passed = (p["response"], p["rule"]) not in violated
        key = ("agree" if oracle_passed == p["gate_passed"] else
               "gate_pass_oracle_fail" if p["gate_passed"] else "gate_fail_oracle_pass")
        per_rule[p["rule"]][key] += 1
        if key != "agree":
            disagreements.append(dict(p, oracle_passed=oracle_passed))
    total = sum(sum(c.values()) for c in per_rule.values())
    agree = sum(c["agree"] for c in per_rule.values())
    return {"pairs": total, "agree": agree, "agreement_pct": round(agree / total * 100, 2) if total else 0.0,
            "responses": len({p["response"] for p in pairs}), "sessions": len({p["session"] for p in pairs}),
            "per_rule": {r: dict(c) for r, c in sorted(per_rule.items())}, "disagreements": disagreements}


def main() -> int:
    """Print the agreement table and write the disagreements as JSON."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--prefix", action="append", default=None)
    parser.add_argument("--markdown", default=None)
    parser.add_argument("--regate", action="store_true", help="re-evaluate the logged payloads with the current gate instead of reading the logged verdicts")
    parser.add_argument("--json", default=str(ROOT / "oracle_agreement.json"))
    args = parser.parse_args()
    result = agreement(args.prefix or ["c4_", "full_", "gen2_"], args.regate)
    lines = [("Current gate re-evaluated on the logged payloads. " if args.regate else "Gate verdicts as logged. ") + f"{result['pairs']} (response, rule) pairs from {result['responses']} responses in {result['sessions']} sessions; "
             f"agreement {result['agree']} of {result['pairs']} ({result['agreement_pct']} %)", "",
             "| Rule | Agree | Gate passes, oracle fails | Gate fails, oracle passes |", "|---|---|---|---|"]
    for rule, c in result["per_rule"].items():
        lines.append(f"| {rule} | {c.get('agree', 0)} | {c.get('gate_pass_oracle_fail', 0)} | {c.get('gate_fail_oracle_pass', 0)} |")
    text = "\n".join(lines)
    print(text)
    Path(args.json).write_text(json.dumps(result, indent=1, default=str))
    if args.markdown:
        Path(args.markdown).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
