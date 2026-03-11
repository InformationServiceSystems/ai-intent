"""Stock broker sub-agent for equity analysis."""

from typing import Any

from agents.manifests import STOCKS_MANIFEST, manifest_to_system_prompt
from mcp.logger import build_message, get_logger
from utils.llm import chat, safe_parse_json

_AGENT_ID = STOCKS_MANIFEST.agent_id

_JSON_INSTRUCTION = """

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive response text",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "buy | hold | sell | not_applicable",
  "confidence": "high | medium | low",
  "out_of_scope": false
}
If the query is out of scope, set out_of_scope to true and name the specific constraint violated in analysis."""


async def analyze(query: str, session_id: str) -> dict[str, Any]:
    """Call the LLM with the stocks manifest and log the interaction via MCP."""
    logger = get_logger()
    system_prompt = manifest_to_system_prompt(STOCKS_MANIFEST) + _JSON_INSTRUCTION

    # Log outbound
    outbound = build_message(session_id, "outbound", "central", _AGENT_ID, f"{_AGENT_ID}.analyze", {"query": query}, "pending")
    logger.log(outbound)

    try:
        raw = chat(system_prompt, query)
        result = safe_parse_json(raw)
    except Exception as e:
        result = {"analysis": f"Error: {e}", "constraint_flags": [], "recommendation": "not_applicable", "confidence": "low", "out_of_scope": False, "error": True}
        inbound = build_message(session_id, "inbound", _AGENT_ID, "central", f"{_AGENT_ID}.result", result, "error")
        logger.log(inbound)
        return result

    flags = result.get("constraint_flags", [])
    out_of_scope = result.get("out_of_scope", False)
    status = "constraint_violation" if out_of_scope else "ok"

    inbound = build_message(session_id, "inbound", _AGENT_ID, "central", f"{_AGENT_ID}.result", result, status, flags)
    logger.log(inbound)
    return result
