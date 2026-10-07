"""Tests for the UFO-C delegation chain: commitments, claims, containment and accountability resolution.

Runnable without pytest:  python tests/test_delegation.py
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

from agents.delegation import (  # noqa: E402
    accountability_record,
    build_delegation_chain,
    check_chain_containment,
    check_mandate_containment,
    resolve_accountability,
)
from agents.manifests import get_manifest  # noqa: E402


def test_chain_structure():
    """Principal delegates to central, central to the three sub-agents."""
    chain = build_delegation_chain()
    assert [d.delegatee for d in chain] == ["central", "stocks", "bonds", "materials"]
    root = chain[0]
    assert root.delegator == "anonymous" and root.parent_delegation_id is None
    for sub in chain[1:]:
        assert sub.delegator == "central"
        assert sub.parent_delegation_id == root.delegation_id
        assert sub.commitment.committed_party == sub.delegatee
        assert sub.commitment.beneficiary == "central"
        assert sub.claim.holder == "central" and sub.claim.against == sub.delegatee
        assert sub.claim.commitment_id == sub.commitment.commitment_id
        assert sub.commitment.rule_ids, f"{sub.delegatee} commitment must cover rules"


def test_containment_holds_for_registry():
    """Every sub-mandate in the registry is contained in the central mandate."""
    results = check_chain_containment(build_delegation_chain())
    assert results, "expected containment checks"
    failing = [r for r in results if not r.contained]
    assert not failing, failing
    numeric = [r for r in results if r.parameter in ("max_single_position", "max_total_allocation")]
    assert {r.child_id for r in numeric} == {"stocks", "materials"}


def test_containment_detects_oversized_sub_mandate():
    """A sub-mandate that grants more than the parent is reported as not contained."""
    parent = get_manifest("central")
    child = get_manifest("materials").model_copy(deep=True)
    child.risk_parameters["max_total_allocation"] = 0.55
    results = check_mandate_containment(parent, child)
    numeric = [r for r in results if r.parameter == "max_total_allocation"]
    assert len(numeric) == 1 and numeric[0].contained is False
    assert numeric[0].parent_value == 0.40 and numeric[0].child_value == 0.55


def test_accountability_path_reaches_principal():
    """The accountability path of a sub-agent runs through central to the Principal."""
    chain = build_delegation_chain()
    path = resolve_accountability("materials", chain)
    assert [d.delegatee for d in path] == ["materials", "central"]
    assert path[-1].delegator == "anonymous"
    record = accountability_record("materials", chain, ["MANIFEST_MATERIALS_MAX_ALLOC", "NOT_A_RULE"])
    assert record["principal"] == "anonymous"
    assert record["answerable_to"] == ["central", "anonymous"]
    assert record["breached_commitment"] == "commitment:materials->central"
    assert record["rules_in_commitment"] == ["MANIFEST_MATERIALS_MAX_ALLOC"]


def test_unknown_agent_has_empty_record():
    """An agent outside the chain yields an empty accountability record rather than an error."""
    record = accountability_record("compliance", build_delegation_chain(), [])
    assert record["chain"] == [] and record["answerable_to"] == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
