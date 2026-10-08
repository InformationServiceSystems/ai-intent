"""Stock broker sub-agent for equity analysis."""

from typing import Any

from agents.manifests import DispositionProfile, STOCKS_MANIFEST, manifest_to_system_prompt
from mcp.logger import build_message, get_logger
from agents.schemas import STOCKS_FORMAT
from utils.llm import chat, safe_parse_json

_AGENT_ID = STOCKS_MANIFEST.agent_id

_JSON_INSTRUCTION = """

IMPORTANT: Your analysis MUST include ESG screening commentary for every position recommended, and "positions" MUST list every company you recommend (never leave it empty when you recommend equities). These are hard constraints — omitting them will cause your response to be rejected.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive response text — must include ESG screening for each position",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "buy | hold | sell | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.08, 0.06],
  "positions": [{"name": "Example Corp (replace with the real company)", "market_cap_usd": 123456789000, "allocation": 0.08, "instrument": "spot equity", "esg_assessment": "one sentence on ESG concerns for this company"}],
  "out_of_scope": false
}
"proposed_allocation" is the list of per-position allocation fractions you are proposing, as decimals (0.08 = 8%). Use an empty list [] if you propose no specific allocations. These numbers are checked directly against your position limit.
"positions" lists each equity you recommend with its actual market capitalisation in US dollars as a number (for example 2800000000000 for a $2.8 trillion company; never copy the example value), its allocation fraction, the instrument type (spot equity, ETF; never margin, short, leveraged or derivative products) and a one-sentence ESG assessment. These fields are checked directly against your constraints.
If the query is out of scope, set out_of_scope to true and name the specific constraint violated in analysis."""


async def analyze(query: str, session_id: str, disposition: DispositionProfile | None = None) -> dict[str, Any]:
    """Call the LLM with the stocks manifest and log the interaction via MCP."""
    logger = get_logger()
    system_prompt = manifest_to_system_prompt(STOCKS_MANIFEST, disposition) + _JSON_INSTRUCTION

    # Log outbound
    outbound = build_message(session_id, "outbound", "central", _AGENT_ID, f"{_AGENT_ID}.analyze", {"query": query}, "pending")
    logger.log(outbound)

    try:
        raw = chat(system_prompt, query, response_format=STOCKS_FORMAT)
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
