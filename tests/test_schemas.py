"""Response schemas: valid JSON schemas with the typed fields the gate evaluates, and placeholder items are ignored.

Runnable without pytest:  python tests/test_schemas.py
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from agents.compliance import _structured_items  # noqa: E402
from agents.schemas import BONDS_FORMAT, MATERIALS_FORMAT, STOCKS_FORMAT, SYNTHESIS_FORMAT, StocksResponse  # noqa: E402


def test_formats_carry_required_typed_fields():
    """Each schema requires the fields the corresponding constraints read."""
    def required(fmt):
        return set(fmt["json_schema"]["schema"]["required"])
    assert {"positions", "analysis", "out_of_scope"} <= required(STOCKS_FORMAT)
    assert {"holdings", "portfolio_duration_years"} <= required(BONDS_FORMAT)
    assert {"commodities", "inflation_rationale"} <= required(MATERIALS_FORMAT)
    assert {"final_recommendation", "allocation_by_asset_class"} <= required(SYNTHESIS_FORMAT)
    assert "accountability_note" not in required(SYNTHESIS_FORMAT)   # ROADMAP 4: the note is a projection of the trace
    pos = STOCKS_FORMAT["json_schema"]["schema"]["$defs"]["Position"]["required"]
    assert {"name", "market_cap_usd", "instrument", "esg_assessment"} <= set(pos)


def test_schema_validates_a_response():
    """A response in the declared shape parses; a wrong enum value is rejected."""
    ok = StocksResponse(analysis="x", constraint_flags=[], recommendation="buy", confidence="high",
                        proposed_allocation=[0.05], out_of_scope=False,
                        positions=[{"name": "Apple", "market_cap_usd": 2.8e12, "allocation": 0.05, "instrument": "spot equity", "esg_assessment": "fine"}])
    assert ok.positions[0].market_cap_usd == 2.8e12
    try:
        StocksResponse(analysis="x", constraint_flags=[], recommendation="maybe", confidence="high",
                       proposed_allocation=[], out_of_scope=False, positions=[])
        raise AssertionError("invalid recommendation accepted")
    except ValueError:
        pass


def test_placeholder_items_are_ignored():
    """An item copied from the prompt's example is not evaluated as a real position."""
    items = _structured_items([{"name": "Example Corp (replace with the real company)", "market_cap_usd": 123456789000},
                               {"name": "Apple", "market_cap_usd": 2.8e12}])
    assert [i["name"] for i in items] == ["Apple"]
    assert _structured_items([{"name": "Example commodity (replace)", "allocation": 0.1}]) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
