"""Design-time consistency checks over the OWL rendering of a domain's Mandates (ROADMAP 2.2).

The runtime gate checks one message against one Mandate. It cannot see defects of the
specification itself: a risk parameter that no predicate reads (changing it changes nothing),
a predicate that reads another agent's parameter, bounds that contradict each other, a sub-mandate
cap above its parent's cap, or a model whose cardinalities the content violates. These checks
run on `mcp/mandate_export.py`'s rendering merged with the OntoUML model, under the closed-world
reading that design-time validation needs (OWL's open world would rarely report a violation).

Usage:  python evaluation/design_checks.py [--domain NAME] [--all]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import BaseModel
from rdflib import OWL, RDF, Graph, URIRef

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.domain import Domain, available_domains, load_domain  # noqa: E402
from mcp.mandate_export import AII, OM, export_domain_mandates  # noqa: E402

ONTOUML = Path(__file__).resolve().parent.parent / "ontology" / "ontouml" / "ai-intent.gufo.ttl"

PREFIXES = """
PREFIX om:  <https://github.com/InformationServiceSystems/ai-intent/ontology/ontouml##>
PREFIX aii: <https://github.com/InformationServiceSystems/ai-intent/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# Parameters the kernel reads directly rather than through a predicate.
KERNEL_PARAMETERS = {"min_sub_agents_consulted", "max_revisions", "timeout_seconds", "deterministic_checks_first"}


class DesignFinding(BaseModel):
    """One defect of a specification."""

    check: str
    subject: str
    detail: str


class DesignCheck(BaseModel):
    """A named design-time check: a SPARQL query whose rows are findings, or a Python function over the graph."""

    check_id: str
    claim: str
    query: str | None = None


CHECKS: list[DesignCheck] = [
    DesignCheck(
        check_id="D1_UNUSED_PARAMETER",
        claim="Every risk parameter is read by a predicate, a containment rule or the kernel; otherwise changing it changes nothing",
        query="""
        SELECT ?mandate ?key WHERE {
          ?p a aii:RiskParameter ; aii:key ?key ; aii:ofMandate ?m . ?m rdfs:label ?mandate .
          FILTER NOT EXISTS { ?bc aii:readsParameter ?p }
          FILTER NOT EXISTS { ?bc aii:readsSetParameter ?p }
          FILTER NOT EXISTS { ?bc aii:conditionParameter ?p }
          FILTER NOT EXISTS { ?c aii:childParameter ?p }
          FILTER NOT EXISTS { ?c aii:parentParameter ?p }
        }""",
    ),
    DesignCheck(
        check_id="D2_FOREIGN_OR_MISSING_KEY",
        claim="A predicate reads a parameter of its own Mandate, and the parameter exists",
        query="""
        SELECT ?rule ?key WHERE {
          { ?bc aii:readsParameterKey ?key ; aii:readsParameter ?p } UNION { ?bc aii:readsSetParameterKey ?key ; aii:readsSetParameter ?p }
          UNION { ?bc aii:conditionParameterKey ?key ; aii:conditionParameter ?p }
          ?bc aii:ruleId ?rule .
          FILTER NOT EXISTS { ?p a aii:RiskParameter }
        }""",
    ),
    DesignCheck(
        check_id="D3_CONTRADICTORY_BOUNDS",
        claim="A min and a max constraint on the same field of the same Mandate admit at least one value",
        query="""
        SELECT ?rule1 ?rule2 ?lo ?hi WHERE {
          ?a aii:kind "min" ; aii:constraintMandate ?m ; aii:fieldPath ?f ; aii:readsParameter ?pa ; aii:ruleId ?rule1 .
          ?b aii:kind "max" ; aii:constraintMandate ?m ; aii:fieldPath ?f ; aii:readsParameter ?pb ; aii:ruleId ?rule2 .
          ?pa aii:value ?lo . ?pb aii:value ?hi .
          FILTER (?lo > ?hi)
        }""",
    ),
    DesignCheck(
        check_id="D4_SET_CONFLICT",
        claim="No value the Mandate approves (in_set) is also forbidden (not_in_set) on the same field",
        query="""
        SELECT ?rule1 ?rule2 ?value WHERE {
          ?a aii:kind "in_set" ; aii:constraintMandate ?m ; aii:fieldPath ?f ; aii:readsSetParameter ?p ; aii:ruleId ?rule1 .
          ?p aii:member ?value .
          ?b aii:kind "not_in_set" ; aii:constraintMandate ?m ; aii:fieldPath ?f ; aii:forbiddenValue ?fv ; aii:ruleId ?rule2 .
          FILTER (CONTAINS(LCASE(STR(?value)), LCASE(STR(?fv))))
        }""",
    ),
    DesignCheck(
        check_id="D5_CAP_ABOVE_PARENT",
        claim="A sub-mandate's allocation cap does not exceed its parent's allocation cap",
        query="""
        SELECT ?child ?rule ?childCap ?parentCap WHERE {
          ?bc aii:tag "allocation_cap" ; aii:unit "percent" ; aii:constraintMandate ?cm ; aii:readsParameter ?cp ; aii:ruleId ?rule .
          ?cm om:subMandateOf ?pm ; rdfs:label ?child .
          ?pbc aii:tag "allocation_cap" ; aii:unit "percent" ; aii:constraintMandate ?pm ; aii:readsParameter ?pp .
          ?cp aii:value ?childCap . ?pp aii:value ?parentCap .
          FILTER (?childCap > ?parentCap)
        }""",
    ),
    DesignCheck(
        check_id="D6_RULE_REGISTRY",
        claim="Every constraint is operationalised by a registered rule that applies to its Mandate",
        query="""
        SELECT ?rule ?mandate WHERE {
          ?bc om:operationalisedBy ?r ; aii:ruleId ?rule ; aii:constraintMandate ?m . ?m rdfs:label ?mandate .
          FILTER NOT EXISTS { ?r a om:RegulatoryRule ; aii:appliesTo ?m }
        }""",
    ),
    DesignCheck(
        check_id="D8_EXCEPTION_TARGET",
        claim="Every norm exception is registered and defeats a constraint that exists",
        query="""
        SELECT ?exc ?problem WHERE {
          ?e a aii:NormException ; aii:ruleId ?exc .
          { FILTER NOT EXISTS { ?e aii:defeats ?bc } BIND("defeats no existing constraint" AS ?problem) }
          UNION
          { ?e om:operationalisedBy ?r . FILTER NOT EXISTS { ?r a om:RegulatoryRule } BIND("not in the rule registry" AS ?problem) }
        }""",
    ),
    DesignCheck(
        check_id="D9_EXCEPTION_EXPRESSIBLE",
        claim="Every exception's condition can be stated in the response schema of the agent it concerns (Python check)",
    ),
    DesignCheck(
        check_id="D7_MODEL_CARDINALITY",
        claim="The Mandate content satisfies the cardinality restrictions of the OntoUML model (closed world)",
    ),
]


def _augment(g: Graph) -> None:
    """Add the helper triples the queries use: the constraint's Mandate as a direct property and the field path."""
    for bc, _, m in list(g.triples((None, OM.constraintInheresInMandate, None))):
        g.add((bc, AII.constraintMandate, m))
        field = g.value(bc, AII.structuredField)
        item = g.value(bc, AII.itemKey)
        if field is not None:
            g.add((bc, AII.fieldPath, type(field)(f"{field}.{item}" if item is not None else str(field))))


def _cardinality_findings(data: Graph, model: Graph) -> list[DesignFinding]:
    """Count, per restricted class, the values of each (possibly inverse) property against exact and max cardinalities."""
    findings: list[DesignFinding] = []
    for cls, _, restriction in model.triples((None, URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"), None)):
        if (restriction, RDF.type, OWL.Restriction) not in model:
            continue
        prop = model.value(restriction, OWL.onProperty)
        inverse = model.value(prop, OWL.inverseOf) if prop is not None else None
        for kind in (OWL.qualifiedCardinality, OWL.maxQualifiedCardinality, OWL.cardinality, OWL.maxCardinality):
            bound = model.value(restriction, kind)
            if bound is None:
                continue
            on_class = model.value(restriction, OWL.onClass)
            for individual in data.subjects(RDF.type, cls):
                if inverse is not None:
                    values = set(data.subjects(inverse, individual))
                else:
                    values = set(data.objects(individual, prop))
                if on_class is not None:
                    values = {v for v in values if (v, RDF.type, on_class) in data}
                if len(values) > int(bound):
                    name = str(cls).split("#")[-1]
                    path = f"inverse of {str(inverse).split('#')[-1]}" if inverse is not None else str(prop).split("#")[-1]
                    findings.append(DesignFinding(
                        check="D7_MODEL_CARDINALITY", subject=str(individual).split("/")[-1],
                        detail=f"{name} allows at most {int(bound)} via {path}, the content has {len(values)}"))
    return findings


def run_design_checks(domain: Domain, model_path: Path | None = ONTOUML) -> list[DesignFinding]:
    """Render the domain, merge the OntoUML model, and run D1 to D7."""
    data = export_domain_mandates(domain)
    _augment(data)
    findings: list[DesignFinding] = []
    for check in CHECKS:
        if check.query is None:
            continue
        for row in data.query(PREFIXES + check.query):
            values = [str(v) for v in row]
            if check.check_id == "D1_UNUSED_PARAMETER" and values[1] in KERNEL_PARAMETERS:
                continue
            findings.append(DesignFinding(check=check.check_id, subject=values[0], detail=", ".join(values[1:])))
    if model_path is not None and model_path.exists():
        findings += _cardinality_findings(data, Graph().parse(str(model_path)))
    findings += _exception_expressibility(domain)
    return findings


def _exception_expressibility(domain: Domain) -> list[DesignFinding]:
    """D9: every exception's condition fields can be stated in the response schema of the agent whose constraint it defeats.

    Under constrained decoding a field the schema lacks cannot be emitted, so an exception that reads it can never apply.
    """
    findings: list[DesignFinding] = []
    for exc in domain.exceptions:
        spec = next((s for s in domain.constraint_specs if s.rule_id == exc.defeats), None)
        if spec is None or spec.agent_id not in domain.specialists:
            continue
        schema = domain.specialists[spec.agent_id].response_format["json_schema"]["schema"]
        props = schema.get("properties", {})
        missing: list[str] = []
        if exc.when_field and exc.when_field not in props:
            missing.append(exc.when_field)
        if exc.requires_field and exc.requires_field not in props:
            missing.append(exc.requires_field)
        if exc.when_key and spec.structured_field:
            ref = (props.get(spec.structured_field, {}).get("items") or {}).get("$ref", "")
            item = schema.get("$defs", {}).get(ref.split("/")[-1], {}) if ref else {}
            if exc.when_key not in item.get("properties", {}):
                missing.append(f"{spec.structured_field}[].{exc.when_key}")
        if missing:
            findings.append(DesignFinding(check="D9_EXCEPTION_EXPRESSIBLE", subject=exc.exception_id,
                                          detail=f"the response schema of {spec.agent_id} cannot state {missing}"))
    return findings


def main() -> int:
    """Print the findings per domain; exit 1 if any check other than D1 and D7 reports a finding."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--domain", default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    names = available_domains() if args.all or not args.domain else [args.domain]
    hard = 0
    for name in names:
        findings = run_design_checks(load_domain(name))
        print(f"{name}: {len(findings)} findings")
        for f in findings:
            print(f"  [{f.check}] {f.subject}: {f.detail}")
        hard += sum(1 for f in findings if f.check not in ("D1_UNUSED_PARAMETER", "D7_MODEL_CARDINALITY"))
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
