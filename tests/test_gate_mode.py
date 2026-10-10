"""The gate's observe mode for the prompt-only ablation: the same verdicts are logged, nothing is revised or blocked.

Runnable without pytest:  python tests/test_gate_mode.py
"""

import asyncio
import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("AI_INTENT_DB", str(Path(tempfile.mkdtemp()) / "t.db"))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from agents import compliance as compliance_module  # noqa: E402
from agents.compliance import ComplianceAgent, gate_mode  # noqa: E402
from evaluation.ablation import delivered  # noqa: E402
from mcp.logger import get_logger  # noqa: E402

# A stocks response that breaches the 10% single-position limit on every attempt.
_OVERSIZED = {
    "analysis": "Buy Apple.", "constraint_flags": [], "recommendation": "buy", "confidence": "high",
    "proposed_allocation": [0.25], "out_of_scope": False,
    "positions": [{"name": "Apple", "market_cap_usd": 3.0e12, "allocation": 0.25, "instrument": "spot equity",
                   "esg_assessment": "No material ESG concerns."}],
}


async def _no_semantic(*args, **kwargs):
    """Stand-in for the semantic checker: these tests concern the deterministic predicates only."""
    return []


def _run(mode: str, session_id: str):
    """Route the oversized response through the gate in the given mode and return (result, verdict, calls, methods)."""
    calls = []

    async def agent(query, sid, disposition=None):
        calls.append(query)
        get_logger().log(compliance_module.build_message(sid, "inbound", "stocks", "central", "stocks.result", dict(_OVERSIZED)))
        return dict(_OVERSIZED)

    previous, original = os.environ.get("AI_INTENT_GATE_MODE"), compliance_module._run_semantic_checks
    os.environ["AI_INTENT_GATE_MODE"] = mode
    compliance_module._run_semantic_checks = _no_semantic
    try:
        result, verdict = asyncio.run(ComplianceAgent().route("stocks", agent, "q", session_id))
    finally:
        compliance_module._run_semantic_checks = original
        if previous is None:
            os.environ.pop("AI_INTENT_GATE_MODE", None)
        else:
            os.environ["AI_INTENT_GATE_MODE"] = previous
    return result, verdict, calls, [m.method for m in get_logger().get_session(session_id)]


def test_enforce_blocks_after_revisions():
    """Enforce (the default): the oversized response is revised twice and then blocked."""
    result, verdict, calls, methods = _run("enforce", "s-enforce")
    assert result is None and verdict.overall_status == "forced_block"
    assert "MANIFEST_STOCKS_MAX_POSITION" in verdict.violated_rules
    assert len(calls) == 3 and "compliance.block.stocks" in methods


def test_observe_delivers_the_first_response_with_the_same_verdict():
    """Observe: one call, the same rejection logged, the response delivered and the delivery recorded."""
    result, verdict, calls, methods = _run("observe", "s-observe")
    assert result == _OVERSIZED and not verdict.approved
    assert "MANIFEST_STOCKS_MAX_POSITION" in verdict.violated_rules
    assert len(calls) == 1
    assert "compliance.reject.stocks" in methods and "compliance.observe.stocks" in methods
    assert not any(m.startswith("compliance.revision.") or m.startswith("compliance.block.") for m in methods)


def test_unknown_mode_is_an_error():
    """A misspelt mode fails loudly instead of silently enforcing or observing."""
    os.environ["AI_INTENT_GATE_MODE"] = "obsrve"
    try:
        gate_mode()
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    finally:
        os.environ.pop("AI_INTENT_GATE_MODE", None)
    assert gate_mode() == "enforce"


def test_delivered_messages_from_a_log():
    """The ablation counts the last verdict per unblocked specialist and the last synthesis."""
    def m(i, method, payload, frm="central"):
        return {"id": i, "method": method, "payload": payload, "from_agent": frm}
    log = [
        m("a1", "stocks.result", {}, "stocks"),
        m("v1", "compliance.reject.stocks", {"checkpoint": "analysis", "target_agent": "stocks", "message_id": "a1", "approved": False}),
        m("a2", "stocks.result", {}, "stocks"),
        m("v2", "compliance.approve.stocks", {"checkpoint": "analysis", "target_agent": "stocks", "message_id": "a2", "approved": True}),
        m("b1", "bonds.result", {}, "bonds"),
        m("v3", "compliance.reject.bonds", {"checkpoint": "analysis", "target_agent": "bonds", "message_id": "b1", "approved": False}),
        m("x", "compliance.block.bonds", {}),
        m("s1", "intent.synthesize", {}),
        m("v4", "compliance.reject.central", {"checkpoint": "synthesis", "target_agent": "central", "message_id": "s1", "approved": False}),
        m("y", "compliance.approve.stocks.final", {}),
    ]
    out = {(v["target_agent"], a["id"]) for v, a in delivered(log)}
    assert out == {("stocks", "a2"), ("central", "s1")}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
