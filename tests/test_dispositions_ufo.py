"""Tests for UFO disposition constructs: bearer, degree and manifestation attribution.

Runnable without pytest:  python tests/test_dispositions_ufo.py
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

from agents.dispositions import detect_manifestations, dispositions_for, get_preset  # noqa: E402
from agents.manifests import DispositionProfile  # noqa: E402
from mcp.logger import build_message  # noqa: E402


def _reject(agent: str, rules: list[str], revision: int = 0, method: str = "reject"):
    return build_message(
        "s1", "internal", "compliance", "central", f"compliance.{method}.{agent}",
        {"violated_rules": rules, "revision_count": revision}, "constraint_violation",
    )


def test_dispositions_for_omits_zero_degree():
    """Only kinds with a positive score become disposition constructs."""
    profile = get_preset("reckless_portfolio")["scores"]["materials"]
    kinds = {d.kind for d in dispositions_for("materials", profile)}
    assert kinds == {"self_serving", "risk_seeking", "overconfident", "anti_customer"}
    assert all(d.bearer == "materials" for d in dispositions_for("materials", profile))
    assert dispositions_for("materials", None) == []


def test_manifestation_attributed_to_matching_kinds():
    """A cap violation under a risk-seeking profile is a manifestation of risk_seeking and self_serving."""
    profile = get_preset("reckless_portfolio")["scores"]["materials"]
    messages = [
        _reject("materials", ["MANIFEST_MATERIALS_MAX_ALLOC"]),
        _reject("stocks", ["MANIFEST_STOCKS_MAX_POSITION"]),   # other agent, must be ignored
    ]
    found = detect_manifestations("materials", profile, messages)
    assert {m.kind for m in found} == {"risk_seeking", "self_serving"}
    assert all(m.rule_ids == ["MANIFEST_MATERIALS_MAX_ALLOC"] for m in found)
    assert all(m.event_id == messages[0].id for m in found)


def test_no_manifestation_at_or_below_threshold():
    """Neutral scores (0.1, and conformist exactly 0.5) never produce a manifestation."""
    profile = get_preset("neutral")["scores"]["materials"]
    messages = [_reject("materials", ["MANIFEST_MATERIALS_MAX_ALLOC"]), _reject("materials", ["MIFID2_ART24_SCOPE"])]
    assert detect_manifestations("materials", profile, messages) == []
    assert DispositionProfile(conformist=0.5).conformist == 0.5
    assert detect_manifestations("materials", DispositionProfile(conformist=0.5), messages) == []
    assert len(detect_manifestations("materials", DispositionProfile(conformist=0.51), messages)) == 1


def test_no_manifestation_for_unrelated_rule():
    """A groupthink profile (conformist=1.0) is not manifested by a cap violation."""
    profile = get_preset("groupthink")["scores"]["bonds"]
    messages = [_reject("bonds", ["MANIFEST_BONDS_MAX_DURATION"])]
    assert detect_manifestations("bonds", profile, messages) == []
    scope = [_reject("bonds", ["MIFID2_ART24_SCOPE"], method="block", revision=2)]
    found = detect_manifestations("bonds", profile, scope)
    assert len(found) == 1 and found[0].kind == "conformist" and found[0].revision_count == 2


def test_custom_profile():
    """A custom profile with a single high score manifests only that kind."""
    profile = DispositionProfile(overconfident=0.9)
    messages = [_reject("stocks", ["MANIFEST_STOCKS_ESG", "MANIFEST_STOCKS_MAX_POSITION"])]
    found = detect_manifestations("stocks", profile, messages)
    assert len(found) == 1 and found[0].kind == "overconfident" and found[0].rule_ids == ["MANIFEST_STOCKS_ESG"]


def test_integrity_checks_share_the_manifestation_threshold():
    """The neutral conformist score of exactly 0.5 neither triggers the integrity check nor counts as a manifestation."""
    from agents.compliance import _check_disposition_integrity
    payload = {"analysis": "Gold 10%.", "constraint_flags": [], "recommendation": "buy", "confidence": "high", "out_of_scope": False}
    assert _check_disposition_integrity("materials", payload, DispositionProfile(conformist=0.5)) == []
    fired = _check_disposition_integrity("materials", payload, DispositionProfile(conformist=0.51))
    assert [r.rule_id for r in fired] == ["DISPOSITION_CONFORMIST_DISSENT"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
