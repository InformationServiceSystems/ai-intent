"""Render a domain's Mandates as RDF in the vocabulary of the OntoUML model, for design-time reasoning (ROADMAP 2.2).

The session export (mcp/gufo_export.py) renders what happened; this module renders what was
specified: Principal, Mandates, their decomposition, boundary constraints with the keys their
predicates read, risk parameters with their values, registry rules, containment rules. The
classes and object properties are those of `ontology/ontouml/ai-intent.gufo.ttl`; the data
properties for predicate keys and parameter values are in the `aii:` namespace of the export.
"""

from __future__ import annotations

from typing import Any

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection

from agents.domain import Domain

# The OntoUML transformation writes class IRIs with a double hash; kept as generated.
OM = Namespace("https://github.com/InformationServiceSystems/ai-intent/ontology/ontouml##")
AII = Namespace("https://github.com/InformationServiceSystems/ai-intent/ontology#")


def _iri(kind: str, domain_id: str, ident: str) -> URIRef:
    """IRI of a mandate-level individual, scoped by domain."""
    return AII[f"{kind}/{domain_id}/{ident}"]


def _literal(value: Any) -> Literal:
    """Typed literal for a risk-parameter value."""
    if isinstance(value, bool):
        return Literal(value, datatype=XSD.boolean)
    if isinstance(value, (int, float)):
        return Literal(float(value), datatype=XSD.decimal)
    return Literal(str(value))


def export_domain_mandates(domain: Domain, distinct_constraints: bool = True) -> Graph:
    """Build the graph of a domain's specification: one Mandate per agent with its constraints, parameters and rules."""
    g = Graph()
    g.bind("om", OM)
    g.bind("aii", AII)
    d = domain.domain_id

    principal = _iri("principal", d, domain.principal.principal_id)
    g.add((principal, RDF.type, OM.Principal))

    for agent_id, manifest in domain.manifests.items():
        mandate = _iri("mandate", d, agent_id)
        agent = _iri("agent", d, agent_id)
        g.add((mandate, RDF.type, OM.Mandate))
        g.add((mandate, RDFS.label, Literal(agent_id)))
        g.add((agent, RDF.type, OM.Agent))
        g.add((agent, OM.governedBy, mandate))
        g.add((principal, OM.owns, mandate))
        if manifest.parent_mandate_id:
            g.add((mandate, OM.subMandateOf, _iri("mandate", d, manifest.parent_mandate_id)))
        if manifest.decision_right:
            g.add((mandate, AII.decisionRight, Literal(manifest.decision_right)))
        for key, value in manifest.risk_parameters.items():
            param = _iri("param", d, f"{agent_id}/{key}")
            g.add((param, RDF.type, AII.RiskParameter))
            g.add((param, AII.key, Literal(key)))
            g.add((param, AII.ofMandate, mandate))
            if isinstance(value, list):
                for v in value:
                    g.add((param, AII.member, Literal(str(v))))
            else:
                g.add((param, AII.value, _literal(value)))

    constraints_by_mandate: dict[str, list[URIRef]] = {}
    for i, spec in enumerate(domain.constraint_specs):
        bc = _iri("constraint", d, f"{spec.agent_id}/{i}")
        mandate = _iri("mandate", d, spec.agent_id)
        constraints_by_mandate.setdefault(spec.agent_id, []).append(bc)
        g.add((bc, RDF.type, OM.BoundaryConstraint))
        g.add((bc, OM.constraintInheresInMandate, mandate))
        g.add((bc, OM.operationalisedBy, _iri("rule", d, spec.rule_id)))
        g.add((bc, AII.ruleId, Literal(spec.rule_id)))
        g.add((bc, AII.kind, Literal(spec.kind)))
        g.add((bc, AII.deonticType, Literal(spec.deontic_type)))
        g.add((bc, AII.variable, Literal(spec.variable)))
        for tag in spec.tags:
            g.add((bc, AII.tag, Literal(tag)))
        if spec.structured_field:
            g.add((bc, AII.structuredField, Literal(spec.structured_field)))
        if spec.item_key:
            g.add((bc, AII.itemKey, Literal(spec.item_key)))
        if spec.aggregate:
            g.add((bc, AII.aggregate, Literal(spec.aggregate)))
        if spec.unit:
            g.add((bc, AII.unit, Literal(spec.unit)))
        for prop, key in (("readsParameter", spec.risk_param_key), ("readsSetParameter", spec.set_param_key)):
            if key:
                g.add((bc, AII[prop + "Key"], Literal(key)))
                g.add((bc, AII[prop], _iri("param", d, f"{spec.agent_id}/{key}")))
        if spec.condition_param:
            g.add((bc, AII.conditionParameterKey, Literal(spec.condition_param)))
            g.add((bc, AII.conditionParameter, _iri("param", d, f"{spec.agent_id}/{spec.condition_param}")))
        for value in spec.forbidden_values or []:
            g.add((bc, AII.forbiddenValue, Literal(value)))

    if distinct_constraints:
        # Constraints are distinct individuals; without this, OWL's open world would let a
        # cardinality restriction merge them instead of reporting the clash.
        for members in constraints_by_mandate.values():
            if len(members) > 1:
                node = BNode()
                g.add((node, RDF.type, OWL.AllDifferent))
                lst = BNode()
                Collection(g, lst, members)
                g.add((node, OWL.distinctMembers, lst))

    for rule in domain.rules:
        r = _iri("rule", d, rule.rule_id)
        g.add((r, RDF.type, OM.RegulatoryRule))
        g.add((r, AII.ruleId, Literal(rule.rule_id)))
        g.add((r, AII.severity, Literal(rule.severity)))
        for agent_id in rule.applies_to:
            g.add((r, AII.appliesTo, _iri("mandate", d, agent_id)))

    for c in domain.containment_rules:
        node = _iri("containment", d, f"{c.child_id}/{c.parameter}")
        g.add((node, RDF.type, AII.ContainmentRule))
        g.add((node, AII.childParameter, _iri("param", d, f"{c.child_id}/{c.parameter}")))
        g.add((node, AII.parentParameter, _iri("param", d, f"{domain.manifest(c.child_id).parent_mandate_id}/{c.parent_parameter}")))
    return g
