"""Generic orchestrator — routes every message of the active domain through the ComplianceAgent.

The orchestrator names no agent: it reads its own id, the gate and the specialists from the
Domain (ROADMAP 6.3), holds the session state the gate's state predicates compare proposed
actions with (ROADMAP 1.1), and generates the accountability note as a projection of the
trace rather than asking the model for it (ROADMAP 4).
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from agents.accountability import build_accountability_note, compliance_history
from agents.compliance import ComplianceVerdict, get_compliance_agent
from agents.delegation import accountability_record, build_delegation_chain, check_chain_containment
from agents.dispositions import detect_manifestations
from agents.domain import SessionState, get_domain
from agents.manifests import DispositionProfile, confidence_at_or_below, manifest_to_system_prompt
from agents.specialist import specialist_functions
from mcp.logger import build_message, get_logger
from utils.llm import chat, safe_parse_json


class OrchestrationResult(BaseModel):
    """Return type for a full orchestration run."""

    session_id: str
    principal_id: str
    query: str
    agents_consulted: list[str]
    agents_blocked: list[str]          # agents whose results were dropped by compliance
    sub_agent_results: dict[str, Any]
    final_recommendation: str
    accountability_note: str
    constraint_violations: list[str]
    routing_rationale: str
    compliance_verdicts: list[dict[str, Any]]
    total_revisions: int
    forced_blocks: list[str]           # replaces forced_passes
    dispositions_used: dict[str, dict[str, float]]
    escalations: list[dict[str, Any]] = []
    delegation_chain: list[dict[str, Any]] = []
    containment_checks: list[dict[str, Any]] = []
    commitment_breaches: list[dict[str, Any]] = []
    disposition_manifestations: list[dict[str, Any]] = []
    domain_id: str = "finance"
    state_snapshot: dict[str, Any] | None = None   # the session state the state predicates used
    model_accountability_note: str = ""            # what the model wrote, kept for comparison with the projection


async def run(
    query: str,
    session_id: str,
    dispositions: dict[str, DispositionProfile] | None = None,
    preset_name: str = "neutral",
    system_prompt_modifier: str = "",
    compliance_multiplier: float = 1.0,
    principal_id: str | None = None,
    routing_override: dict[str, Any] | None = None,
    state: SessionState | None = None,
) -> OrchestrationResult:
    """Execute the full orchestration pipeline for a user query.

    routing_override, when given, replaces the model's routing decision with a fixed one
    (used by the evaluation). state, when given, replaces the domain's default session state
    that the state predicates compare proposed actions with. principal_id defaults to the
    domain's Principal.
    """
    query_clean = (query or "").strip()
    if not query_clean:
        raise ValueError("Query must be a non-empty string")

    dispositions = dispositions or {}
    domain = get_domain()
    oid = domain.orchestrator_id
    agent_funcs = specialist_functions()
    logger = get_logger()
    compliance = get_compliance_agent()
    session_state = state or domain.default_state
    principal_id = principal_id or domain.principal.principal_id

    logger.register_principal(session_id, principal_id)

    base_max_revisions = compliance._max_revisions
    compliance._max_revisions = round(base_max_revisions * compliance_multiplier)

    central_disp = dispositions.get(oid)
    system_prompt = manifest_to_system_prompt(domain.manifest(oid), central_disp)
    if system_prompt_modifier:
        system_prompt = f"DISPOSITION CONTEXT: {system_prompt_modifier}\n\n{system_prompt}"

    all_verdicts: list[ComplianceVerdict] = []
    total_revisions = 0
    forced_blocks: list[str] = []
    escalations: list[dict[str, Any]] = []

    active_disps = {k: v.model_dump() for k, v in dispositions.items() if any(val > 0 for val in v.model_dump().values())}
    disp_payload: dict[str, Any] = {"preset": preset_name, "compliance_multiplier": compliance_multiplier}
    if active_disps:
        disp_payload["scores"] = active_disps
    logger.log(build_message(session_id, "internal", oid, oid, "disposition.active", disp_payload))

    # Session state (ROADMAP 1.1): logged before any sub-agent is called so every state
    # verdict can be reproduced from the trace.
    logger.log(build_message(session_id, "internal", oid, oid, "state.snapshot", session_state.snapshot()))

    # Delegation chain (UFO-C): Principal -> orchestrator -> sub-agents.
    delegation_chain = build_delegation_chain(principal_id)
    containment_checks = check_chain_containment(delegation_chain)
    all_contained = all(c.contained for c in containment_checks)
    logger.log(build_message(
        session_id, "internal", oid, oid, "delegation.establish",
        {
            "principal_id": principal_id,
            "chain": [d.model_dump() for d in delegation_chain],
            "containment_checks": [c.model_dump() for c in containment_checks],
            "all_contained": all_contained,
        },
        "ok" if all_contained else "constraint_violation",
    ))

    # Step A — Log user query
    logger.log(build_message(session_id, "internal", "user", oid, "user.query", {"query": query_clean}))

    # Step B — Routing call → routed through compliance (CP1)
    routing = await _route_with_compliance(
        system_prompt, query_clean, session_id, compliance, all_verdicts, routing_override=routing_override,
    )

    agents_to_call = routing.get("agents_to_call", [])
    routing_rationale = routing.get("routing_rationale", "")

    # Step C — Sub-agent calls → each routed through compliance (CP2)
    tasks = []
    agent_ids = []
    for agent_id in agents_to_call:
        if agent_id in agent_funcs:
            sub_query = routing.get(f"query_for_{agent_id}")
            if not isinstance(sub_query, str) or not sub_query.strip():
                sub_query = query_clean
            sub_query += _state_context(agent_id, session_state)
            tasks.append(compliance.route(
                agent_id, agent_funcs[agent_id], sub_query, session_id,
                disposition=dispositions.get(agent_id), state=session_state,
            ))
            agent_ids.append(agent_id)

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    sub_agent_results: dict[str, Any] = {}
    agents_blocked: list[str] = []
    all_violations: list[str] = []
    all_constraints: list[str] = []

    for agent_id, result_tuple in zip(agent_ids, results_list):
        if isinstance(result_tuple, Exception):
            sub_agent_results[agent_id] = {"analysis": f"Error: {result_tuple}", "error": True}
            agents_blocked.append(agent_id)
        else:
            result, verdict = result_tuple
            all_verdicts.append(verdict)
            total_revisions += verdict.revision_count

            if result is None:
                forced_blocks.append(agent_id)
                agents_blocked.append(agent_id)
                sub_agent_results[agent_id] = {
                    "analysis": f"Blocked by compliance after {verdict.revision_count} revision(s). "
                                f"Violated rules: {verdict.violated_rules}. "
                                f"Regulatory basis: {verdict.regulatory_basis}.",
                    "blocked": True,
                    "out_of_scope": False,
                    "recommendation": "not_applicable",
                    "confidence": "low",
                }
                all_violations.append(f"{agent_id}: BLOCKED — {', '.join(verdict.rejection_reasons[:2])}")
            else:
                sub_agent_results[agent_id] = result
                flags = result.get("constraint_flags", [])
                all_constraints.extend(flags)
                if result.get("out_of_scope"):
                    all_violations.append(f"{agent_id}: {result.get('analysis', 'out of scope')}")

    # Commitment breaches (UFO-C)
    commitment_breaches: list[dict[str, Any]] = []
    for agent_id in forced_blocks:
        last = [v for v in all_verdicts if v.target_agent == agent_id and v.checkpoint == "analysis"]
        violated = last[-1].violated_rules if last else []
        record = accountability_record(agent_id, delegation_chain, violated)
        commitment_breaches.append(record)
        logger.log(build_message(session_id, "internal", oid, oid, f"delegation.breach.{agent_id}", record, "forced_block"))

    # Disposition manifestations (UFO-B), read from the log
    disposition_manifestations: list[dict[str, Any]] = []
    session_messages = logger.get_session(session_id)
    for agent_id in agent_ids:
        found = detect_manifestations(agent_id, dispositions.get(agent_id), session_messages)
        if not found:
            continue
        payload = {"preset": preset_name, "manifestations": [m.model_dump() for m in found]}
        disposition_manifestations.extend(payload["manifestations"])
        logger.log(build_message(session_id, "internal", oid, oid, f"disposition.manifest.{agent_id}", payload))

    # Uncertainty policies
    for agent_id, result in sub_agent_results.items():
        if not isinstance(result, dict) or result.get("blocked") or result.get("error"):
            continue
        try:
            manifest = domain.manifest(agent_id)
        except KeyError:
            continue
        policy = manifest.uncertainty_policy
        observed = result.get("confidence")
        block_triggered = policy.block_below is not None and confidence_at_or_below(observed, policy.block_below)
        escalate_triggered = confidence_at_or_below(observed, policy.escalate_below)
        if not (escalate_triggered or block_triggered):
            continue
        action = "blocked" if block_triggered else "escalated"
        escalation = {
            "agent": agent_id,
            "observed_confidence": observed or "unknown",
            "escalate_below": policy.escalate_below,
            "block_below": policy.block_below,
            "action": action,
            "recommendation": result.get("recommendation"),
        }
        escalations.append(escalation)
        logger.log(build_message(
            session_id, "internal", agent_id, "user", f"uncertainty.escalate.{agent_id}", escalation,
            status="escalated" if action == "escalated" else "blocked",
        ))
        if block_triggered:
            agents_blocked.append(agent_id)
            sub_agent_results[agent_id] = {
                "analysis": (
                    f"Dropped by uncertainty policy: confidence={observed} <= block_below={policy.block_below}. "
                    f"Original recommendation withheld for principal review."
                ),
                "blocked": True,
                "out_of_scope": False,
                "recommendation": "not_applicable",
                "confidence": observed or "low",
            }
            all_violations.append(f"{agent_id}: BLOCKED — uncertainty policy (confidence={observed})")

    # Compliance history for the synthesis context and the note: full revision history from the log
    history = compliance_history(agent_ids, logger.get_session(session_id), oid)

    # Step D — Synthesis call → routed through compliance (CP3). The accountability note is
    # a projection of the trace, attached before the synthesis is logged and evaluated.
    now = datetime.now(timezone.utc).isoformat()

    def _note(model_payload: dict[str, Any]) -> str:
        messages = logger.get_session(session_id)
        checked = sum(len(v.deterministic_results) + len(v.semantic_results) for v in all_verdicts)
        return build_accountability_note(
            session_id, principal_id, agent_ids, agents_blocked,
            compliance_history(agent_ids, messages, oid), checked, all_violations,
            session_state.snapshot(), now, domain.domain_id,
        )

    synthesis = await _synthesize_with_compliance(
        system_prompt, query_clean, session_id, sub_agent_results,
        agent_ids, agents_blocked, all_constraints, all_violations,
        history, compliance, all_verdicts, now, _note,
    )

    final_recommendation = str(synthesis.get("final_recommendation", ""))
    accountability_note = str(synthesis.get("accountability_note", ""))

    # Step E — Log final output
    logger.log(build_message(
        session_id, "inbound", oid, "user", domain.response_method,
        {"final_recommendation": final_recommendation, "accountability_note": accountability_note},
    ))

    orch_result = OrchestrationResult(
        session_id=session_id,
        principal_id=principal_id,
        query=query_clean,
        agents_consulted=agent_ids,
        agents_blocked=agents_blocked,
        sub_agent_results=sub_agent_results,
        final_recommendation=final_recommendation,
        accountability_note=accountability_note,
        constraint_violations=all_violations,
        routing_rationale=routing_rationale,
        compliance_verdicts=[v.model_dump() for v in all_verdicts],
        total_revisions=total_revisions,
        forced_blocks=forced_blocks,
        dispositions_used=active_disps,
        escalations=escalations,
        delegation_chain=[d.model_dump() for d in delegation_chain],
        containment_checks=[c.model_dump() for c in containment_checks],
        commitment_breaches=commitment_breaches,
        disposition_manifestations=disposition_manifestations,
        domain_id=domain.domain_id,
        state_snapshot=session_state.snapshot(),
        model_accountability_note=str(synthesis.get("model_accountability_note", "")),
    )

    compliance._max_revisions = base_max_revisions
    return orch_result


def _state_context(agent_id: str, state: SessionState) -> str:
    """The session state the agent's state predicates will compare with, appended to its sub-question (ROADMAP 1.1)."""
    domain = get_domain()
    keys = {s.state_key for s in domain.specs_for(agent_id) if s.kind in ("drift", "state_max") and s.state_key}
    if not keys:
        return ""
    lines = []
    for k in sorted(keys):
        cur, tgt = state.current.get(k), state.target.get(k)
        part = f"{k}: currently {cur * 100:.0f}% of the portfolio or budget" if cur is not None else f"{k}: current share unknown"
        if tgt is not None:
            part += f", target {tgt * 100:.0f}%"
        lines.append(part)
    return "\n\n[SESSION STATE — your proposal is checked against it]\n" + "\n".join(lines)


async def _route_with_compliance(
    system_prompt: str, query: str, session_id: str,
    compliance: Any, all_verdicts: list[ComplianceVerdict],
    routing_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run routing call with CP1 compliance gate and retry loop."""
    logger = get_logger()
    domain = get_domain()
    oid, cid = domain.orchestrator_id, domain.compliance_id
    max_retries = 2

    if routing_override is not None:
        routing = {
            "routing_rationale": routing_override.get(
                "routing_rationale", "Deterministic routing supplied by the evaluation harness"),
            "agents_to_call": list(routing_override.get("agents_to_call", [])),
            "routing_mode": "override",
        }
        for agent_id in routing["agents_to_call"]:
            routing[f"query_for_{agent_id}"] = routing_override.get(f"query_for_{agent_id}", query)
        logger.log(build_message(session_id, "internal", oid, oid, "intent.route", routing))
        verdict = await compliance.evaluate_routing(routing, session_id)
        all_verdicts.append(verdict)
        if not verdict.approved:
            verdict.overall_status = "forced_block"
            logger.log(build_message(
                session_id, "internal", cid, oid, "compliance.block.routing",
                {"reason": "Routing override rejected by compliance", "violated_rules": verdict.violated_rules},
                "forced_block",
            ))
        return routing

    for attempt in range(max_retries + 1):
        routing_prompt = system_prompt + domain.routing_instruction
        try:
            raw_routing = chat(routing_prompt, query, response_format=domain.routing_format)
            routing = safe_parse_json(raw_routing)
            if not isinstance(routing, dict):
                raise ValueError("routing output is not a JSON object")
        except Exception as e:
            routing = {"routing_rationale": f"Routing error: {e}", "agents_to_call": list(domain.specialist_ids)}

        logger.log(build_message(session_id, "internal", oid, oid, "intent.route", routing))

        verdict = await compliance.evaluate_routing(routing, session_id)
        all_verdicts.append(verdict)

        if verdict.approved:
            return routing

        if attempt == max_retries:
            verdict.overall_status = "forced_block"
            logger.log(build_message(
                session_id, "internal", cid, oid, "compliance.block.routing",
                {"reason": "Max routing retries exceeded"}, "forced_block",
            ))
            return routing

        query = (
            f"{query}\n\n"
            f"[COMPLIANCE FEEDBACK — Routing revision {attempt + 1}]\n"
            f"{verdict.revision_instruction}"
        )

    return routing


async def _synthesize_with_compliance(
    system_prompt: str, query: str, session_id: str,
    sub_agent_results: dict[str, Any], agent_ids: list[str],
    agents_blocked: list[str],
    all_constraints: list[str], all_violations: list[str],
    compliance_history_lines: list[str],
    compliance: Any, all_verdicts: list[ComplianceVerdict],
    now: str, note_fn: Any,
) -> dict[str, Any]:
    """Run synthesis call with CP3 compliance gate and retry loop; the accountability note is projected from the trace."""
    logger = get_logger()
    domain = get_domain()
    oid, cid = domain.orchestrator_id, domain.compliance_id
    max_retries = 2

    blocked_note = ""
    if agents_blocked:
        blocked_note = f"\nBLOCKED AGENTS (compliance rejected their output): {agents_blocked}\n"

    history_note = ""
    if compliance_history_lines:
        history_note = "\nCOMPLIANCE HISTORY:\n" + "\n".join(f"  - {h}" for h in compliance_history_lines) + "\n"

    context = (
        f"User query: {query}\n\n"
        f"Sub-agent results:\n{sub_agent_results}\n\n"
        f"{blocked_note}{history_note}"
        f"Session ID: {session_id}\n"
        f"Agents consulted: {agent_ids}\n"
        f"Constraints checked: {all_constraints}\n"
        f"Violations found: {all_violations}\n"
        f"Timestamp: {now}"
    )

    for attempt in range(max_retries + 1):
        synthesis_prompt = system_prompt + domain.synthesis_instruction.replace("{session_id}", session_id).replace("{timestamp}", now)

        try:
            raw_synthesis = chat(synthesis_prompt, context, response_format=domain.synthesis_format)
            if not raw_synthesis or not raw_synthesis.strip():
                raise ValueError("LLM returned empty response")
            synthesis = safe_parse_json(raw_synthesis)
            if "final_recommendation" not in synthesis:
                raise ValueError("Missing 'final_recommendation' in synthesis response")
        except Exception as e:
            if attempt < max_retries:
                continue
            synthesis = {
                "final_recommendation": (
                    f"The analysis is complete but the system encountered a formatting error. "
                    f"Based on the sub-agent results: "
                    + "; ".join(
                        f"{aid}: {r.get('recommendation', 'N/A')} ({r.get('confidence', 'N/A')})"
                        for aid, r in sub_agent_results.items()
                        if isinstance(r, dict) and not r.get("error") and not r.get("blocked")
                    )
                ),
                "synthesis_error": str(e),
            }

        # ROADMAP 4: the note is a projection of the trace. The model's own note, if any, is kept for comparison.
        if synthesis.get("accountability_note"):
            synthesis["model_accountability_note"] = str(synthesis["accountability_note"])
        synthesis["accountability_note"] = note_fn(synthesis)

        logger.log(build_message(session_id, "internal", oid, oid, "intent.synthesize", synthesis))

        verdict = await compliance.evaluate_synthesis(synthesis, sub_agent_results, session_id)
        all_verdicts.append(verdict)

        if verdict.approved:
            return synthesis

        if attempt == max_retries:
            verdict.overall_status = "forced_block"
            logger.log(build_message(
                session_id, "internal", cid, oid, "compliance.block.synthesis",
                {"reason": "Max synthesis retries exceeded"}, "forced_block",
            ))
            return synthesis

        context = (
            f"{context}\n\n"
            f"[COMPLIANCE FEEDBACK — Synthesis revision {attempt + 1}]\n"
            f"{verdict.revision_instruction}"
        )

    return synthesis
