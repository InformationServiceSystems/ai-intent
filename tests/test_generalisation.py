"""Generalisation steps 6.3 to 6.6: roles instead of names, dispositions over tags, schemas from specs, test cases in the domain.

Runnable without pytest:  python tests/test_generalisation.py
"""

import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from agents.accountability import build_accountability_note, compliance_history  # noqa: E402
from agents.constraint_spec import CONSTRAINT_SPECS  # noqa: E402
from agents.dispositions import get_preset, get_preset_names, manifestation_map  # noqa: E402
from agents.domain import get_domain  # noqa: E402
from agents.schemas import (  # noqa: E402
    BONDS_FORMAT, MATERIALS_FORMAT, ROUTING_FORMAT, STOCKS_FORMAT, SYNTHESIS_FORMAT,
    derive_response_model, derive_routing_model, derive_synthesis_model, response_format,
)
from mcp.logger import build_message  # noqa: E402

# The ER 2026 hand-written map (agents/dispositions.py before ROADMAP 6.4), the oracle for the tag derivation.
ER2026_MANIFESTATION_MAP = {
    "risk_seeking": ["DISPOSITION_RISK_BOUNDARY", "MANIFEST_STOCKS_MAX_POSITION", "MANIFEST_MATERIALS_MAX_ALLOC",
                     "MANIFEST_BONDS_MAX_DURATION", "MANIFEST_CENTRAL_MAX_ASSET_CLASS", "MANIFEST_STOCKS_NO_LEVERAGE",
                     "MANIFEST_MATERIALS_NO_LEVERAGE", "MIFID2_ART25_LEVERAGE", "MIFID2_ART25_SUITABILITY"],
    "self_serving": ["DISPOSITION_SELF_SERVING_SCOPE", "MANIFEST_STOCKS_MAX_POSITION", "MANIFEST_MATERIALS_MAX_ALLOC",
                     "MANIFEST_CENTRAL_MAX_ASSET_CLASS", "MIFID2_ART25_SUITABILITY", "MANIFEST_DECISION_RIGHT_RESPECTED"],
    "overconfident": ["DISPOSITION_OVERCONFIDENT_FLAGS", "MIFID2_ART24_RATIONALE", "MANIFEST_STOCKS_ESG",
                      "MANIFEST_MATERIALS_INFLATION", "MANIFEST_BONDS_DURATION_WARN", "MANIFEST_CENTRAL_ACCOUNTABILITY"],
    "anti_customer": ["DISPOSITION_ANTI_CUSTOMER_COMPLEXITY", "MANIFEST_STOCKS_NO_LEVERAGE", "MANIFEST_MATERIALS_NO_LEVERAGE",
                      "MIFID2_ART25_LEVERAGE", "MANIFEST_BONDS_IG_ONLY", "MANIFEST_BONDS_NO_EM", "MANIFEST_BONDS_LADDER"],
    "conformist": ["DISPOSITION_CONFORMIST_DISSENT", "MIFID2_ART24_SCOPE", "MANIFEST_STOCKS_UNIVERSE",
                   "MANIFEST_STOCKS_LARGECAP", "MANIFEST_MATERIALS_APPROVED", "MANIFEST_CENTRAL_SURFACE_VIOLATIONS"],
}
# Rules added after ER 2026 (ROADMAP 1.1) that the tag derivation legitimately adds.
POST_ER2026 = {"MANIFEST_STOCKS_EXPOSURE"}

KERNEL_MODULES = ["agents/compliance.py", "agents/orchestrator.py", "agents/delegation.py", "agents/dispositions.py",
                  "agents/specialist.py", "agents/domain.py", "agents/accountability.py", "mcp/gufo_export.py",
                  "mcp/logger.py", "evaluation/runner.py", "evaluation/sparql_checks.py"]


def test_kernel_names_no_finance_agent():
    """6.3: no kernel module refers to a finance agent id as a string literal (comments and docstrings excluded)."""
    offenders = []
    literal = re.compile(r'["\'](stocks|bonds|materials|central)["\']')
    for rel in KERNEL_MODULES:
        for lineno, line in enumerate((ROOT / rel).read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            if rel == "agents/delegation.py" and "CONTAINMENT_MAP" in code or '("stocks", "max' in code or '("materials", "max' in code:
                continue  # the finance table kept under its historical name for the E1 script
            if rel == "mcp/gufo_export.py" and 'return "central"' in code:
                continue  # import-time fallback when no domain can be loaded
            if literal.search(code) and not code.strip().startswith(('"""', "'''")) and "ER2026" not in code:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert offenders == [], "\n".join(offenders)


def test_manifestation_map_reproduces_er2026_by_tags():
    """6.4: the tag-derived characteristic rule sets equal the hand-written ER 2026 map (plus the post-ER 2026 rules)."""
    derived = manifestation_map(get_domain())
    for kind, expected in ER2026_MANIFESTATION_MAP.items():
        assert set(derived[kind]) - POST_ER2026 == set(expected), kind
        assert derived[kind][0] == expected[0]   # the kind's own integrity rule comes first


def test_presets_come_from_the_domain_with_er2026_scores():
    """6.3: presets are domain data; the finance table keeps the exact ER 2026 per-agent scores."""
    assert get_preset_names() == ["neutral", "aggressive_broker", "reckless_portfolio", "groupthink", "custom"]
    ab = get_preset("aggressive_broker")["scores"]
    assert ab["bonds"].self_serving == 0.8 and ab["stocks"].self_serving == 0.9 and ab["materials"].risk_seeking == 0.9
    assert get_preset("reckless_portfolio")["compliance_multiplier"] == 1.5
    assert get_preset("custom")["scores"] is None
    assert get_preset("does-not-exist")["label"] == "Neutral"


def _schema(fmt):
    return fmt["json_schema"]["schema"]


def _required_tree(schema):
    """Required top-level fields and, per list field, the required item fields."""
    out = {"top": set(schema["required"])}
    defs = schema.get("$defs", {})
    for name, prop in schema["properties"].items():
        ref = (prop.get("items") or {}).get("$ref")
        if ref:
            out[name] = set(defs[ref.split("/")[-1]]["required"])
    return out


def test_derived_schemas_equal_hand_written_oracle():
    """6.5: the models derived from the specifications require the same fields as the hand-written finance models."""
    pairs = {
        "stocks": STOCKS_FORMAT, "bonds": BONDS_FORMAT, "materials": MATERIALS_FORMAT,
    }
    for agent_id, oracle in pairs.items():
        derived = response_format(derive_response_model(agent_id, CONSTRAINT_SPECS))
        assert _required_tree(_schema(derived)) == _required_tree(_schema(oracle)), agent_id
    routing = response_format(derive_routing_model(["stocks", "bonds", "materials"]))
    assert _schema(routing)["required"] == _schema(ROUTING_FORMAT)["required"]
    assert _schema(routing)["properties"]["agents_to_call"]["items"]["enum"] == ["stocks", "bonds", "materials"]
    synthesis = response_format(derive_synthesis_model("central", CONSTRAINT_SPECS))
    assert set(_schema(synthesis)["required"]) == set(_schema(SYNTHESIS_FORMAT)["required"])
    # the region enum and the rebalance flag come from the specification
    holdings_item = _schema(derived if False else response_format(derive_response_model("bonds", CONSTRAINT_SPECS)))["$defs"]["HoldingsItem"]
    assert holdings_item["properties"]["region"]["enum"] == ["developed", "emerging"]
    mat = _schema(response_format(derive_response_model("materials", CONSTRAINT_SPECS)))
    assert mat["properties"]["rebalance_flag"]["type"] == "boolean"


def test_domain_uses_derived_formats_and_carries_cases():
    """6.5 and 6.6: the finance domain's formats are the derived ones and its test cases are data with dry-run flags."""
    d = get_domain()
    assert "rebalance_flag" in d.specialists["materials"].response_format["json_schema"]["schema"]["required"]
    assert [tc.tc_id for tc in d.test_cases][:3] == ["TC-01", "TC-02", "TC-03"] and len(d.test_cases) == 21
    assert {tc.tc_id for tc in d.test_cases if tc.dry_run} == {"TC-08", "TC-09", "TC-15", "TC-17"}
    assert d.cap_parameter("materials") == "max_total_allocation" and d.cap_parameter("central") == "max_single_asset_class"
    assert d.cross_scope_terms("stocks") == ["bond", "fixed income", "treasur", "gold", "silver", "commodit"]


def test_accountability_note_is_a_projection_of_the_log():
    """ROADMAP 4 and Amendment 2: the note lists every consulted agent with its full revision history and rule ids."""
    sid = "s-proj"
    msgs = [
        build_message(sid, "internal", "compliance", "central", "compliance.approve.central", {"checkpoint": "routing"}, "approved"),
        build_message(sid, "internal", "compliance", "central", "compliance.approve.stocks", {"checkpoint": "analysis", "revision_count": 0}, "approved"),
        build_message(sid, "internal", "compliance", "central", "compliance.reject.bonds", {"checkpoint": "analysis", "revision_count": 0, "violated_rules": ["MANIFEST_BONDS_IG_ONLY"]}, "constraint_violation"),
        build_message(sid, "internal", "compliance", "central", "compliance.approve.bonds", {"checkpoint": "analysis", "revision_count": 1}, "approved"),
        build_message(sid, "internal", "compliance", "central", "compliance.reject.materials", {"checkpoint": "analysis", "revision_count": 0, "violated_rules": ["MANIFEST_MATERIALS_MAX_ALLOC"]}, "constraint_violation"),
        build_message(sid, "internal", "compliance", "central", "compliance.reject.materials", {"checkpoint": "analysis", "revision_count": 1, "violated_rules": ["MANIFEST_MATERIALS_MAX_ALLOC", "MANIFEST_MATERIALS_NO_LEVERAGE"]}, "constraint_violation"),
        build_message(sid, "internal", "compliance", "central", "compliance.block.materials", {"revision_count": 1, "violated_rules": ["MANIFEST_MATERIALS_MAX_ALLOC"]}, "forced_block"),
    ]
    history = compliance_history(["stocks", "bonds", "materials"], msgs, "central")
    assert history[0] == "routing: approved on first attempt"
    assert history[1] == "stocks: approved on first attempt"
    assert history[2].startswith("bonds: approved after 1 revision(s), violated rules: ['MANIFEST_BONDS_IG_ONLY']")
    assert history[3].startswith("materials: BLOCKED after 1 revision(s)") and "MANIFEST_MATERIALS_NO_LEVERAGE" in history[3]
    note = build_accountability_note(sid, "anonymous", ["stocks", "bonds", "materials"], ["materials"], history, 12, ["materials: BLOCKED"],
                                     {"label": "empty_portfolio", "current": {}, "target": {}}, "2026-10-09T00:00:00+00:00", "finance")
    assert note.startswith("Session: s-proj") and "stocks" in note and "MANIFEST_BONDS_IG_ONLY" in note and "empty_portfolio" in note


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
