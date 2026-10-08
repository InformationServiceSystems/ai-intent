"""Generic specialist agent: prompt, response schema and audit logging derive from the domain's manifest and configuration."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from agents.domain import get_domain
from agents.manifests import DispositionProfile, manifest_to_system_prompt
from mcp.logger import build_message, get_logger
from utils.llm import chat, safe_parse_json

AnalyzeFn = Callable[..., Awaitable[dict[str, Any]]]


async def analyze(agent_id: str, query: str, session_id: str, disposition: DispositionProfile | None = None) -> dict[str, Any]:
    """Call the LLM with the agent's manifest and response schema, logging the outbound call and the inbound result."""
    domain = get_domain()
    manifest = domain.manifest(agent_id)
    config = domain.specialists[agent_id]
    logger = get_logger()
    orchestrator = domain.orchestrator_id
    system_prompt = manifest_to_system_prompt(manifest, disposition) + config.json_instruction

    logger.log(build_message(session_id, "outbound", orchestrator, agent_id, f"{agent_id}.analyze", {"query": query}, "pending"))

    try:
        raw = chat(system_prompt, query, response_format=config.response_format)
        result = safe_parse_json(raw)
    except Exception as e:
        result = {"analysis": f"Error: {e}", "constraint_flags": [], "recommendation": "not_applicable",
                  "confidence": "low", "out_of_scope": False, "error": True}
        logger.log(build_message(session_id, "inbound", agent_id, orchestrator, f"{agent_id}.result", result, "error"))
        return result

    flags = result.get("constraint_flags", [])
    status = "constraint_violation" if result.get("out_of_scope", False) else "ok"
    logger.log(build_message(session_id, "inbound", agent_id, orchestrator, f"{agent_id}.result", result, status, flags))
    return result


def make_analyze(agent_id: str) -> AnalyzeFn:
    """Return an analyze(query, session_id, disposition=None) coroutine bound to one specialist."""
    async def _analyze(query: str, session_id: str, disposition: DispositionProfile | None = None) -> dict[str, Any]:
        return await analyze(agent_id, query, session_id, disposition)
    _analyze.__name__ = f"analyze_{agent_id}"
    _analyze.__doc__ = f"Analyze a query as the {agent_id} specialist of the active domain."
    return _analyze


def specialist_functions() -> dict[str, AnalyzeFn]:
    """Return analyze functions for every specialist of the active domain, in routing order."""
    return {agent_id: make_analyze(agent_id) for agent_id in get_domain().specialist_ids}
