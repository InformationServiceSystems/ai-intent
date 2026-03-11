"""Central investment orchestrator that delegates to specialist sub-agents."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from agents.manifests import CENTRAL_MANIFEST, manifest_to_system_prompt
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

_ROUTING_INSTRUCTION = """

You will receive a user investment query. Determine which specialist sub-agents to consult (stocks, bonds, materials — use only those relevant to the query) and what specific sub-question to send each one. Respond ONLY in this JSON format (no other text):
{"routing_rationale": "...", "agents_to_call": ["stocks", "bonds"], "query_for_stocks": "...", "query_for_bonds": "...", "query_for_materials": null}"""

_SYNTHESIS_INSTRUCTION = """

You are synthesizing results from specialist sub-agents into a final investment recommendation. You MUST produce a JSON response with exactly these two fields (no other text):
{{"final_recommendation": "A plain-language investment recommendation based on the sub-agent results", "accountability_note": "Session: {session_id} | Agents consulted: [list] | Constraints checked: [list] | Violations: [list or none] | Generated: {timestamp}"}}

Replace the placeholders with actual values from the context provided."""


class OrchestrationResult(BaseModel):
    """Return type for a full orchestration run."""

    session_id: str
    query: str
    agents_consulted: list[str]
    sub_agent_results: dict[str, Any]
    final_recommendation: str
    accountability_note: str
    constraint_violations: list[str]
    routing_rationale: str


async def run(query: str, session_id: str) -> OrchestrationResult:
    """Execute the full orchestration pipeline for a user query."""
    logger = get_logger()
    system_prompt = manifest_to_system_prompt(CENTRAL_MANIFEST)

    # Step A — Log user query
    logger.log(build_message(session_id, "internal", "user", "central", "user.query", {"query": query}))

    # Step B — Routing call
    routing_prompt = system_prompt + _ROUTING_INSTRUCTION
    try:
        raw_routing = chat(routing_prompt, query)
        routing = safe_parse_json(raw_routing)
    except Exception as e:
        routing = {"routing_rationale": f"Routing error: {e}", "agents_to_call": ["stocks", "bonds", "materials"]}

    logger.log(build_message(session_id, "internal", "central", "central", "intent.route", routing))

    agents_to_call = routing.get("agents_to_call", [])
    routing_rationale = routing.get("routing_rationale", "")

    # Step C — Parallel sub-agent calls
    tasks = []
    agent_ids = []
    for agent_id in agents_to_call:
        if agent_id in _AGENT_FUNCS:
            sub_query = routing.get(f"query_for_{agent_id}")
            if not isinstance(sub_query, str) or not sub_query.strip():
                sub_query = query
            tasks.append(_AGENT_FUNCS[agent_id](sub_query, session_id))
            agent_ids.append(agent_id)

    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    sub_agent_results: dict[str, Any] = {}
    all_violations: list[str] = []
    all_constraints: list[str] = []

    for agent_id, result in zip(agent_ids, results_list):
        if isinstance(result, Exception):
            sub_agent_results[agent_id] = {"analysis": f"Error: {result}", "error": True}
        else:
            sub_agent_results[agent_id] = result
            flags = result.get("constraint_flags", [])
            all_constraints.extend(flags)
            if result.get("out_of_scope"):
                all_violations.append(f"{agent_id}: {result.get('analysis', 'out of scope')}")

    # Step D — Synthesis call
    now = datetime.now(timezone.utc).isoformat()
    context = (
        f"User query: {query}\n\n"
        f"Sub-agent results:\n{sub_agent_results}\n\n"
        f"Session ID: {session_id}\n"
        f"Agents consulted: {agent_ids}\n"
        f"Constraints checked: {all_constraints}\n"
        f"Violations found: {all_violations}\n"
        f"Timestamp: {now}"
    )
    synthesis_prompt = system_prompt + _SYNTHESIS_INSTRUCTION.format(session_id=session_id, timestamp=now)

    try:
        raw_synthesis = chat(synthesis_prompt, context)
        synthesis = safe_parse_json(raw_synthesis)
    except Exception as e:
        synthesis = {
            "final_recommendation": f"Synthesis error: {e}. Raw sub-agent results: {sub_agent_results}",
            "accountability_note": f"Session: {session_id} | Error during synthesis | Agents: {agent_ids} | {now}",
        }

    logger.log(build_message(session_id, "internal", "central", "central", "intent.synthesize", synthesis))

    final_recommendation = synthesis.get("final_recommendation", "")
    accountability_note = synthesis.get("accountability_note", "")

    # Step E — Log final output
    logger.log(build_message(
        session_id, "inbound", "central", "user", "investment.response",
        {"final_recommendation": final_recommendation, "accountability_note": accountability_note},
    ))

    return OrchestrationResult(
        session_id=session_id,
        query=query,
        agents_consulted=agent_ids,
        sub_agent_results=sub_agent_results,
        final_recommendation=final_recommendation,
        accountability_note=accountability_note,
        constraint_violations=all_violations,
        routing_rationale=routing_rationale,
    )
