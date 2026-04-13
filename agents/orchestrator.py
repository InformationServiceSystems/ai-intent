"""Central investment orchestrator — routes all messages through ComplianceAgent."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from agents.compliance import (
    ComplianceVerdict,
    get_compliance_agent,
)
from agents.manifests import DispositionProfile, CENTRAL_MANIFEST, manifest_to_system_prompt
from agents.stocks import analyze as stocks_analyze
from agents.bonds import analyze as bonds_analyze
from agents.materials import analyze as materials_analyze
from mcp.logger import build_message, get_logger
from utils.llm import chat, safe_parse_json

_AGENT_FUNCS = {
    "stocks": stocks_analyze,
    "bonds": bonds_analyze,
    "materials": materials_analyze,
}

ROUTING_INSTRUCTION = """

You will receive a user investment query. Determine which specialist sub-agents to consult and what specific sub-question to send each one.

Available agents:
- "stocks": Handles large-cap equity analysis (stocks like AAPL, MSFT, JNJ). Use for equity/stock questions.
- "bonds": Handles fixed-income/bond analysis (treasuries, corporate bonds, TIPS). Use for bond/fixed-income questions.
- "materials": Handles commodities (Gold, Silver) and inflation hedging. Use for gold, silver, precious metals, commodities, or inflation hedge questions.

Route to ALL agents that are relevant. For example, a gold inflation hedge query should include "materials". A diversified portfolio query should include all three.

Respond ONLY in this JSON format (no other text):
{"routing_rationale": "...", "agents_to_call": ["stocks", "bonds", "materials"], "query_for_stocks": "...", "query_for_bonds": "...", "query_for_materials": "..."}

Set query_for_X to null for agents NOT in agents_to_call."""

_SYNTHESIS_INSTRUCTION = """

You are synthesizing results from specialist sub-agents into a final investment recommendation.

IMPORTANT: Your recommendation MUST include specific allocation percentages (e.g., "allocate 10% to gold"). Vague qualitative language like "limited allocation" or "balanced approach" is NOT acceptable and will be rejected by compliance.

You MUST produce a JSON response with exactly these two fields (no other text):
{{"final_recommendation": "A plain-language investment recommendation with SPECIFIC allocation percentages based on the sub-agent results", "accountability_note": "Session: {session_id} | Agents consulted: [list] | Compliance history: [include full compliance history from context — which agents were revised or blocked] | Violations: [list or none] | Blocked: [list or none] | Generated: {timestamp}"}}

Replace the placeholders with actual values from the context provided. The accountability note MUST include the compliance history showing any revision cycles that occurred."""


class OrchestrationResult(BaseModel):
    """Return type for a full orchestration run."""

    session_id: str
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


async def run(
    query: str,
    session_id: str,
    dispositions: dict[str, DispositionProfile] | None = None,
    preset_name: str = "neutral",
    system_prompt_modifier: str = "",
    compliance_multiplier: float = 1.0,
) -> OrchestrationResult:
    """Execute the full orchestration pipeline for a user query."""
    query_clean = (query or "").strip()
    if not query_clean:
        raise ValueError("Query must be a non-empty string")

    dispositions = dispositions or {}
    logger = get_logger()
    compliance = get_compliance_agent()

    # Apply compliance multiplier from disposition preset
    base_max_revisions = compliance._max_revisions
    compliance._max_revisions = round(base_max_revisions * compliance_multiplier)

    central_disp = dispositions.get("central")
    system_prompt = manifest_to_system_prompt(CENTRAL_MANIFEST, central_disp)

    # Inject disposition system prompt modifier
    if system_prompt_modifier:
        system_prompt = f"DISPOSITION CONTEXT: {system_prompt_modifier}\n\n{system_prompt}"

    all_verdicts: list[ComplianceVerdict] = []
    total_revisions = 0
    forced_blocks: list[str] = []

    # Log dispositions with preset name
    active_disps = {k: v.model_dump() for k, v in dispositions.items() if any(val > 0 for val in v.model_dump().values())}
    disp_payload = {
        "preset": preset_name,
        "compliance_multiplier": compliance_multiplier,
    }
    if active_disps:
        disp_payload["scores"] = active_disps
    logger.log(build_message(
        session_id, "internal", "central", "central",
        "disposition.active", disp_payload,
    ))

    # Step A — Log user query
    logger.log(build_message(session_id, "internal", "user", "central", "user.query", {"query": query_clean}))

    # Step B — Routing call → routed through compliance (CP1)
    routing = await _route_with_compliance(system_prompt, query_clean, session_id, compliance, all_verdicts)

    agents_to_call = routing.get("agents_to_call", [])
    routing_rationale = routing.get("routing_rationale", "")

    # Step C — Sub-agent calls → each routed through compliance (CP2)
    tasks = []
    agent_ids = []
    for agent_id in agents_to_call:
        if agent_id in _AGENT_FUNCS:
            sub_query = routing.get(f"query_for_{agent_id}")
            if not isinstance(sub_query, str) or not sub_query.strip():
                sub_query = query_clean
            agent_disp = dispositions.get(agent_id)
            # Every call goes through compliance.route() — no direct calls
            tasks.append(compliance.route(
                agent_id, _AGENT_FUNCS[agent_id], sub_query, session_id,
                disposition=agent_disp,
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
                # FORCED BLOCK — compliance permanently rejected this agent's output
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
                all_violations.append(
                    f"{agent_id}: BLOCKED — {', '.join(verdict.rejection_reasons[:2])}"
                )
            else:
                sub_agent_results[agent_id] = result
                flags = result.get("constraint_flags", [])
                all_constraints.extend(flags)
                if result.get("out_of_scope"):
                    all_violations.append(f"{agent_id}: {result.get('analysis', 'out of scope')}")

    # Build compliance history for the accountability note
    # Include EVERY consulted agent, not just those with verdicts
    compliance_history = []

    # Routing checkpoint
    routing_verdicts = [v for v in all_verdicts if v.checkpoint == "routing"]
    if routing_verdicts:
        rv = routing_verdicts[-1]
        if rv.overall_status == "approved":
            compliance_history.append(f"routing: approved" + (f" after revision" if rv.revision_count > 0 else ""))
        else:
            compliance_history.append(f"routing: {rv.overall_status}, violated rules: {rv.violated_rules}")

    # Per-agent analysis checkpoints — ensure every consulted agent appears
    agent_verdicts: dict[str, ComplianceVerdict] = {}
    for v in all_verdicts:
        if v.checkpoint == "analysis":
            agent_verdicts[v.target_agent] = v  # last verdict per agent

    for agent_id in agent_ids:
        v = agent_verdicts.get(agent_id)
        if v is None:
            compliance_history.append(f"{agent_id}: no compliance verdict recorded")
        elif v.overall_status == "approved" and v.revision_count == 0:
            compliance_history.append(f"{agent_id}: approved on first attempt")
        elif v.overall_status == "approved" and v.revision_count > 0:
            compliance_history.append(f"{agent_id}: approved after {v.revision_count} revision(s), violated rules: {v.violated_rules}")
        elif v.overall_status == "forced_block":
            compliance_history.append(f"{agent_id}: BLOCKED after {v.revision_count} revision(s), violated rules: {v.violated_rules}")
        elif v.overall_status == "rejected":
            compliance_history.append(f"{agent_id}: rejected, violated rules: {v.violated_rules}")

    # Step D — Synthesis call → routed through compliance (CP3)
    synthesis = await _synthesize_with_compliance(
        system_prompt, query_clean, session_id, sub_agent_results,
        agent_ids, agents_blocked, all_constraints, all_violations,
        compliance_history, compliance, all_verdicts,
    )

    final_recommendation = str(synthesis.get("final_recommendation", ""))
    accountability_note = str(synthesis.get("accountability_note", ""))

    # Step E — Log final output
    logger.log(build_message(
        session_id, "inbound", "central", "user", "investment.response",
        {"final_recommendation": final_recommendation, "accountability_note": accountability_note},
    ))

    orch_result = OrchestrationResult(
        session_id=session_id,
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
    )

    # Restore compliance max_revisions to base value
    compliance._max_revisions = base_max_revisions

    return orch_result


async def _route_with_compliance(
    system_prompt: str, query: str, session_id: str,
    compliance: Any, all_verdicts: list[ComplianceVerdict],
) -> dict[str, Any]:
    """Run routing call with CP1 compliance gate and retry loop."""
    logger = get_logger()
    max_retries = 2

    for attempt in range(max_retries + 1):
        routing_prompt = system_prompt + ROUTING_INSTRUCTION
        try:
            raw_routing = chat(routing_prompt, query)
            routing = safe_parse_json(raw_routing)
        except Exception as e:
            routing = {"routing_rationale": f"Routing error: {e}", "agents_to_call": ["stocks", "bonds", "materials"]}

        logger.log(build_message(session_id, "internal", "central", "central", "intent.route", routing))

        # CP1: Route through compliance
        verdict = await compliance.evaluate_routing(routing, session_id)
        all_verdicts.append(verdict)

        if verdict.approved:
            return routing

        if attempt == max_retries:
            verdict.overall_status = "forced_block"
            logger.log(build_message(
                session_id, "internal", "compliance", "central",
                "compliance.block.routing",
                {"reason": "Max routing retries exceeded"},
                "forced_block",
            ))
            # Still return routing — orchestrator needs agent list even if non-compliant
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
    compliance_history: list[str],
    compliance: Any, all_verdicts: list[ComplianceVerdict],
) -> dict[str, Any]:
    """Run synthesis call with CP3 compliance gate and retry loop."""
    logger = get_logger()
    max_retries = 2
    now = datetime.now(timezone.utc).isoformat()

    blocked_note = ""
    if agents_blocked:
        blocked_note = f"\nBLOCKED AGENTS (compliance rejected their output): {agents_blocked}\n"

    history_note = ""
    if compliance_history:
        history_note = "\nCOMPLIANCE HISTORY (include this in the accountability note):\n" + "\n".join(f"  - {h}" for h in compliance_history) + "\n"

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
        synthesis_prompt = system_prompt + _SYNTHESIS_INSTRUCTION.format(session_id=session_id, timestamp=now)

        try:
            raw_synthesis = chat(synthesis_prompt, context)
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
                "accountability_note": f"Session: {session_id} | Synthesis error (attempt {attempt+1}) | Agents: {agent_ids} | Blocked: {agents_blocked} | {now}",
            }

        logger.log(build_message(session_id, "internal", "central", "central", "intent.synthesize", synthesis))

        # CP3: Route through compliance
        verdict = await compliance.evaluate_synthesis(synthesis, sub_agent_results, session_id)
        all_verdicts.append(verdict)

        if verdict.approved:
            return synthesis

        if attempt == max_retries:
            verdict.overall_status = "forced_block"
            logger.log(build_message(
                session_id, "internal", "compliance", "central",
                "compliance.block.synthesis",
                {"reason": "Max synthesis retries exceeded"},
                "forced_block",
            ))
            return synthesis

        context = (
            f"{context}\n\n"
            f"[COMPLIANCE FEEDBACK — Synthesis revision {attempt + 1}]\n"
            f"{verdict.revision_instruction}"
        )

    return synthesis
