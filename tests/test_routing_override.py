"""Tests for the deterministic routing override used by the evaluation harness.

Runnable without pytest:  python tests/test_routing_override.py
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

from agents.compliance import ComplianceVerdict  # noqa: E402
from agents.orchestrator import _route_with_compliance  # noqa: E402
from mcp.logger import get_logger  # noqa: E402


class _Gate:
    """Stand-in Compliance Agent that records what it was asked to evaluate."""

    def __init__(self, approve: bool = True):
        self.approve = approve
        self.seen = []

    async def evaluate_routing(self, payload, session_id):
        self.seen.append(payload)
        return ComplianceVerdict(
            approved=self.approve, message_id="m", target_agent="central", checkpoint="routing",
            violated_rules=[] if self.approve else ["MIFID2_ART24_SCOPE"],
            overall_status="approved" if self.approve else "rejected",
        )


def test_override_routes_without_model_and_passes_gate():
    """The override is used verbatim, logged as intent.route, and evaluated by the gate."""
    gate = _Gate()
    verdicts = []
    routing = asyncio.run(_route_with_compliance(
        "sys", "Which tech stocks for my bond portfolio?", "s-override", gate, verdicts,
        routing_override={"agents_to_call": ["bonds"]},
    ))
    assert routing["agents_to_call"] == ["bonds"]
    assert routing["query_for_bonds"] == "Which tech stocks for my bond portfolio?"
    assert routing["routing_mode"] == "override"
    assert gate.seen == [routing] and len(verdicts) == 1 and verdicts[0].approved
    methods = [m.method for m in get_logger().get_session("s-override")]
    assert methods == ["intent.route"]


def test_rejected_override_is_blocked_not_retried():
    """A rejected override is logged as a routing block; there is no model retry."""
    gate = _Gate(approve=False)
    verdicts = []
    routing = asyncio.run(_route_with_compliance(
        "sys", "q", "s-override-bad", gate, verdicts, routing_override={"agents_to_call": ["stocks"]},
    ))
    assert routing["agents_to_call"] == ["stocks"]
    assert verdicts[0].overall_status == "forced_block"
    methods = [m.method for m in get_logger().get_session("s-override-bad")]
    assert methods == ["intent.route", "compliance.block.routing"]
    assert len(gate.seen) == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
