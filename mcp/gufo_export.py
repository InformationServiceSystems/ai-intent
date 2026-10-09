"""Export a session's MCP log as a gUFO-typed RDF graph so that accountability traces can be queried with SPARQL."""

from __future__ import annotations

from typing import Any

from urllib.parse import quote

from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

from mcp.logger import MCPLogger, MCPMessage, get_logger

GUFO = Namespace("http://purl.org/nemo/gufo#")
AII = Namespace("https://github.com/InformationServiceSystems/ai-intent/ontology#")

_PROPOSED_ACTION_METHODS = {"intent.route": "routing", "intent.synthesize": "synthesis"}
_VERDICT_PREFIXES = ("compliance.approve.", "compliance.reject.", "compliance.block.")


def iri(kind: str, ident: str) -> URIRef:
    """Return the IRI of an individual of the given kind, percent-encoding the identifier."""
    return AII[kind + "/" + quote(str(ident), safe="")]


def _agent_node(agent_id: str) -> URIRef:
    """Return the IRI for an agent, the user or a principal."""
    return iri("agent", agent_id)


def _bind(graph: Graph) -> None:
    """Bind the namespaces used by the export."""
    graph.bind("gufo", GUFO)
    graph.bind("aii", AII)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)


def _add_schema(graph: Graph) -> None:
    """Add the subclass axioms that ground AI-Intent constructs in gUFO categories."""
    axioms = [
        (AII.Principal, GUFO.FunctionalComplex),
        (AII.Agent, GUFO.FunctionalComplex),
        (AII.Mandate, GUFO.Object),
        (AII.Session, GUFO.Event),
        (AII.LogEntry, GUFO.Event),
        (AII.ProposedAction, GUFO.Event),
        (AII.ComplianceVerdict, GUFO.IntrinsicMode),
        (AII.AccountabilityTrace, GUFO.Situation),
        (AII.Delegation, GUFO.Relator),
        (AII.Commitment, GUFO.ExtrinsicMode),
        (AII.Claim, GUFO.ExtrinsicMode),
        (AII.Disposition, GUFO.IntrinsicMode),
        (AII.CommitmentBreach, GUFO.Situation),
    ]
    for sub, sup in axioms:
        graph.add((sub, RDFS.subClassOf, sup))


def _add_entry(graph: Graph, session: URIRef, trace: URIRef, m: MCPMessage, sequence: int) -> URIRef:
    """Add one MCP message as a gufo:Event that is a proper part of the session event."""
    entry = iri("entry", m.id)
    graph.add((entry, AII.sequence, Literal(sequence, datatype=XSD.integer)))
    graph.add((entry, RDF.type, AII.LogEntry))
    graph.add((entry, RDF.type, GUFO.Event))
    graph.add((entry, RDFS.label, Literal(m.method)))
    graph.add((entry, AII.method, Literal(m.method)))
    graph.add((entry, AII.direction, Literal(m.direction)))
    graph.add((entry, AII.status, Literal(m.response_status)))
    stamp = Literal(m.timestamp.isoformat(), datatype=XSD.dateTimeStamp)
    graph.add((entry, GUFO.hasBeginPointInXSDDateTimeStamp, stamp))
    graph.add((entry, GUFO.hasEndPointInXSDDateTimeStamp, stamp))
    graph.add((entry, GUFO.isEventProperPartOf, session))
    graph.add((trace, AII.comprises, entry))
    for role, agent_id in (("fromAgent", m.from_agent), ("toAgent", m.to_agent)):
        node = _agent_node(agent_id)
        graph.add((entry, AII[role], node))
        graph.add((node, GUFO.participatedIn, entry))
    return entry


def _classify_proposed_action(graph: Graph, entry: URIRef, m: MCPMessage) -> str | None:
    """Type the entry as a Proposed Action if it carries pre-delivery content, returning its checkpoint."""
    checkpoint: str | None = None
    if m.method in _PROPOSED_ACTION_METHODS:
        checkpoint = _PROPOSED_ACTION_METHODS[m.method]
    elif m.method.endswith(".result") and m.method.count(".") == 1:
        checkpoint = "analysis"
    if checkpoint is None:
        return None
    graph.add((entry, RDF.type, AII.ProposedAction))
    graph.add((entry, AII.checkpoint, Literal(checkpoint)))
    graph.add((entry, AII.proposedBy, _agent_node(m.from_agent)))
    return checkpoint


def _target_agent(method: str) -> str | None:
    """Extract the target agent from a compliance method name such as compliance.reject.stocks."""
    parts = method.split(".")
    if len(parts) < 3 or parts[0] != "compliance":
        return None
    # Routing and synthesis checkpoints are the orchestrator's own actions.
    if parts[2] in ("routing", "synthesis"):
        try:
            from agents.domain import get_domain
            return get_domain().orchestrator_id
        except Exception:
            return "central"
    return parts[2]


def _add_verdict(
    graph: Graph,
    entry: URIRef,
    m: MCPMessage,
    entries_by_id: dict[str, URIRef],
    last_action_by_agent: dict[str, URIRef],
    rule_labels: dict[str, str],
) -> None:
    """Add the verdict a compliance event issues as a mode of the target agent, historically dependent on the evaluated action."""
    target = _target_agent(m.method)
    if target is None:
        return
    graph.add((entry, AII.targetAgent, _agent_node(target)))
    if m.method.endswith(".final") or not m.method.startswith(_VERDICT_PREFIXES):
        return
    verdict = iri("verdict", m.id)
    graph.add((verdict, RDF.type, AII.ComplianceVerdict))
    graph.add((verdict, RDF.type, GUFO.IntrinsicMode))
    graph.add((verdict, GUFO.inheresIn, _agent_node(target)))
    graph.add((verdict, AII.issuedBy, entry))
    graph.add((entry, AII.issues, verdict))
    approved = m.method.startswith("compliance.approve.")
    graph.add((verdict, AII.approved, Literal(approved, datatype=XSD.boolean)))
    status = m.payload.get("overall_status") or ("approved" if approved else m.response_status)
    graph.add((verdict, AII.overallStatus, Literal(str(status))))
    graph.add((verdict, AII.revisionCount, Literal(int(m.payload.get("revision_count") or 0), datatype=XSD.integer)))
    checkpoint = m.payload.get("checkpoint")
    if checkpoint:
        graph.add((verdict, AII.checkpoint, Literal(str(checkpoint))))
    for rule_id in m.payload.get("violated_rules") or []:
        rule = iri("rule", rule_id)
        graph.add((rule, RDF.type, AII.RegulatoryRule))
        graph.add((rule, RDFS.label, Literal(rule_labels.get(rule_id, rule_id))))
        graph.add((verdict, AII.violatesRule, rule))
    # The evaluated Proposed Action: the message id recorded in the verdict when it refers to a
    # logged entry, otherwise the most recent Proposed Action of the target agent at this point.
    referenced = str(m.payload.get("message_id") or "")
    action = entries_by_id.get(referenced) or last_action_by_agent.get(target)
    if action is not None:
        graph.add((verdict, GUFO.historicallyDependsOn, action))


def _add_delegations(graph: Graph, payload: dict[str, Any]) -> None:
    """Add delegation relators, commitments, claims and containment checks from a delegation.establish payload."""
    for d in payload.get("chain") or []:
        delegation = iri("delegation", d['delegation_id'])
        delegator = _agent_node(d["delegator"])
        delegatee = _agent_node(d["delegatee"])
        graph.add((delegation, RDF.type, AII.Delegation))
        graph.add((delegation, RDF.type, GUFO.Relator))
        graph.add((delegation, GUFO.mediates, delegator))
        graph.add((delegation, GUFO.mediates, delegatee))
        graph.add((delegation, AII.delegator, delegator))
        graph.add((delegation, AII.delegatee, delegatee))
        graph.add((delegation, AII.mandate, iri("mandate", d['mandate_id'])))
        graph.add((iri("mandate", d['mandate_id']), RDF.type, AII.Mandate))
        if d.get("parent_delegation_id"):
            graph.add((delegation, AII.parentDelegation, iri("delegation", d['parent_delegation_id'])))
        c = d["commitment"]
        commitment = iri("commitment", c['commitment_id'])
        graph.add((commitment, RDF.type, AII.Commitment))
        graph.add((commitment, RDF.type, GUFO.ExtrinsicMode))
        graph.add((commitment, GUFO.inheresIn, _agent_node(c["committed_party"])))
        graph.add((commitment, GUFO.externallyDependsOn, _agent_node(c["beneficiary"])))
        graph.add((commitment, AII.content, Literal(c["content"])))
        graph.add((commitment, AII.constitutes, delegation))
        for rule_id in c.get("rule_ids") or []:
            graph.add((commitment, AII.coversRule, iri("rule", rule_id)))
        k = d["claim"]
        claim = iri("claim", k['claim_id'])
        graph.add((claim, RDF.type, AII.Claim))
        graph.add((claim, RDF.type, GUFO.ExtrinsicMode))
        graph.add((claim, GUFO.inheresIn, _agent_node(k["holder"])))
        graph.add((claim, GUFO.externallyDependsOn, _agent_node(k["against"])))
        graph.add((claim, AII.counterpartOf, commitment))
        graph.add((claim, AII.constitutes, delegation))
    for i, check in enumerate(payload.get("containment_checks") or []):
        node = iri("containment", f"{check['parent_id']}/{check['child_id']}/{check['parameter']}")
        graph.add((node, RDF.type, AII.ContainmentCheck))
        graph.add((node, AII.parentMandate, iri("mandate", check['parent_id'])))
        graph.add((node, AII.childMandate, iri("mandate", check['child_id'])))
        graph.add((node, AII.parameter, Literal(check["parameter"])))
        graph.add((node, AII.contained, Literal(bool(check["contained"]), datatype=XSD.boolean)))


def _add_dispositions(graph: Graph, payload: dict[str, Any]) -> None:
    """Add disposition modes per agent and kind from a disposition.active payload."""
    for agent_id, scores in (payload.get("scores") or {}).items():
        for kind, degree in scores.items():
            if float(degree) <= 0.0:
                continue
            node = iri("disposition", f"{agent_id}/{kind}")
            graph.add((node, RDF.type, AII.Disposition))
            graph.add((node, RDF.type, GUFO.IntrinsicMode))
            graph.add((node, GUFO.inheresIn, _agent_node(agent_id)))
            graph.add((node, AII.kind, Literal(kind)))
            graph.add((node, AII.degree, Literal(float(degree), datatype=XSD.decimal)))
            graph.add((node, AII.preset, Literal(str(payload.get("preset", "")))))


def _add_manifestations(graph: Graph, payload: dict[str, Any]) -> None:
    """Link dispositions to the rejection events in which they were manifested."""
    for mf in payload.get("manifestations") or []:
        node = iri("disposition", f"{mf['agent_id']}/{mf['kind']}")
        graph.add((node, GUFO.manifestedIn, iri("entry", mf['event_id'])))


def _add_breach(graph: Graph, entry: URIRef, payload: dict[str, Any]) -> None:
    """Add the commitment breach situation a forced block brings about."""
    if not payload.get("breached_commitment"):
        return
    breach = iri("breach", f"{payload['agent']}/{entry.split('/')[-1]}")
    graph.add((breach, RDF.type, AII.CommitmentBreach))
    graph.add((breach, RDF.type, GUFO.Situation))
    graph.add((entry, GUFO.broughtAbout, breach))
    graph.add((breach, AII.breachedCommitment, iri("commitment", payload['breached_commitment'])))
    graph.add((breach, AII.breachingAgent, _agent_node(payload["agent"])))
    for party in payload.get("answerable_to") or []:
        graph.add((breach, AII.answerableTo, _agent_node(party)))
    for rule_id in payload.get("violated_rules") or []:
        graph.add((breach, AII.violatesRule, iri("rule", rule_id)))


def _rule_labels() -> dict[str, str]:
    """Return rule descriptions from the registry, or an empty mapping if the registry is unavailable."""
    try:
        from agents.regulatory_rules import ALL_RULES
        return {r.rule_id: r.description for r in ALL_RULES}
    except Exception:
        return {}


def export_session_graph(session_id: str, logger: MCPLogger | None = None) -> Graph:
    """Build the gUFO-typed graph of one session from the MCP log alone."""
    logger = logger or get_logger()
    messages = logger.get_session(session_id)
    graph = Graph()
    _bind(graph)
    _add_schema(graph)

    session = iri("session", session_id)
    trace = iri("trace", session_id)
    graph.add((session, RDF.type, AII.Session))
    graph.add((session, RDF.type, GUFO.Event))
    graph.add((session, RDFS.label, Literal(f"Session {session_id}")))
    graph.add((trace, RDF.type, AII.AccountabilityTrace))
    graph.add((trace, RDF.type, GUFO.Situation))
    graph.add((session, GUFO.broughtAbout, trace))

    principal_id = logger.get_principal(session_id)
    if principal_id:
        principal = _agent_node(principal_id)
        graph.add((principal, RDF.type, AII.Principal))
        graph.add((principal, RDF.type, GUFO.FunctionalComplex))
        graph.add((session, AII.principal, principal))

    rule_labels = _rule_labels()
    entries_by_id: dict[str, URIRef] = {}
    last_action_by_agent: dict[str, URIRef] = {}
    seen_agents: set[str] = set()

    for sequence, m in enumerate(messages):
        if m.timestamp:
            graph.add((session, GUFO.hasEndPointInXSDDateTimeStamp,
                       Literal(m.timestamp.isoformat(), datatype=XSD.dateTimeStamp)))
        entry = _add_entry(graph, session, trace, m, sequence)
        entries_by_id[m.id] = entry
        for agent_id in (m.from_agent, m.to_agent):
            if agent_id not in seen_agents and agent_id != principal_id:
                node = _agent_node(agent_id)
                graph.add((node, RDF.type, AII.Agent))
                graph.add((node, RDF.type, GUFO.FunctionalComplex))
                graph.add((node, RDFS.label, Literal(agent_id)))
                seen_agents.add(agent_id)
        if _classify_proposed_action(graph, entry, m) is not None:
            last_action_by_agent[m.from_agent] = entry
        if m.method.startswith("compliance."):
            _add_verdict(graph, entry, m, entries_by_id, last_action_by_agent, rule_labels)
        elif m.method == "delegation.establish":
            _add_delegations(graph, m.payload)
        elif m.method == "disposition.active":
            _add_dispositions(graph, m.payload)
        elif m.method.startswith("disposition.manifest."):
            _add_manifestations(graph, m.payload)
        elif m.method.startswith("delegation.breach."):
            _add_breach(graph, entry, m.payload)

    begin = messages[0].timestamp.isoformat() if messages else None
    if begin:
        graph.add((session, GUFO.hasBeginPointInXSDDateTimeStamp, Literal(begin, datatype=XSD.dateTimeStamp)))
    return graph


def session_to_turtle(session_id: str, logger: MCPLogger | None = None) -> str:
    """Serialise one session's gUFO graph as Turtle."""
    return export_session_graph(session_id, logger).serialize(format="turtle")
