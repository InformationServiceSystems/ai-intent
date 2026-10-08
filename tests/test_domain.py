"""The domain package carries everything domain-specific; the kernel reads it and behaves as before for finance.

Runnable without pytest:  python tests/test_domain.py
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

from agents.constraint_spec import CONSTRAINT_SPECS  # noqa: E402
from agents.domain import Domain, get_domain, load_domain  # noqa: E402
from agents.manifests import get_manifest  # noqa: E402
from agents.regulatory_rules import ALL_RULES  # noqa: E402
from agents.specialist import specialist_functions  # noqa: E402


def test_finance_domain_is_complete():
    """The finance domain exposes principal, five manifests, three specialists, all specs and rules, and instructions."""
    d = get_domain()
    assert isinstance(d, Domain) and d.domain_id == "finance"
    assert set(d.manifests) == {"central", "stocks", "bonds", "materials", "compliance"}
    assert d.orchestrator_id == "central" and d.compliance_id == "compliance"
    assert d.specialist_ids == ["stocks", "bonds", "materials"]
    assert [c.rule_id for c in d.constraint_specs] == [c.rule_id for c in CONSTRAINT_SPECS]
    assert [r.rule_id for r in d.rules] == [r.rule_id for r in ALL_RULES]
    assert "agents_to_call" in d.routing_instruction and "allocation_by_asset_class" in d.synthesis_instruction
    assert len(d.sample_queries) == 5 and d.principal.principal_id == "anonymous"


def test_manifests_in_domain_are_the_registry_manifests():
    """The domain's manifests are the same objects the registry serves, so nothing is duplicated."""
    d = get_domain()
    for agent_id, manifest in d.manifests.items():
        assert manifest is get_manifest(agent_id)


def test_specialist_configs_name_the_typed_fields():
    """Each specialist's instruction names the fields its constraints read, and its schema requires them."""
    d = get_domain()
    expected = {"stocks": "positions", "bonds": "holdings", "materials": "commodities"}
    for agent_id, field in expected.items():
        cfg = d.specialists[agent_id]
        assert f'"{field}"' in cfg.json_instruction
        assert field in cfg.response_format["json_schema"]["schema"]["required"]


def test_specialist_functions_follow_routing_order():
    """The kernel derives one analyze function per specialist, in the domain's order."""
    fns = specialist_functions()
    assert list(fns) == ["stocks", "bonds", "materials"]
    assert all(callable(fn) for fn in fns.values())
    from agents.stocks import analyze as stocks_analyze
    assert stocks_analyze.__name__ == "analyze_stocks"


def test_load_domain_by_name():
    """Domains are loaded by module name, which is how a second domain will be added."""
    d = load_domain("finance")
    assert d.domain_id == "finance"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
