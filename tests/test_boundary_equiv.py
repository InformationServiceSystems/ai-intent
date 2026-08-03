"""Regression oracle for the ⟨text, φ, τ⟩ boundary-constraint interpreter.

The production deterministic checks were refactored from hard-coded per-agent
functions into a single generic interpreter driven by BoundaryConstraint data
(agents/regulatory_rules.py). This test keeps an independent copy of the
original imperative logic as an oracle and asserts the interpreter reproduces
it byte-for-byte across a battery of payloads. Any future drift in the
interpreter or the constraint data fails here.

Runnable without pytest:  python tests/test_boundary_equiv.py
Exits 0 if every RuleResult matches; 1 on the first divergence.
"""

import re
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The deterministic checkers need no LLM. Shim `openai` so importing
# compliance (via utils.llm) does not require the package to be installed.
if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from agents.manifests import CENTRAL_MANIFEST, get_manifest  # noqa: E402
from agents.compliance import (  # noqa: E402
    RuleResult,
    _check_boundary_constraints,
    _evaluate_boundary_constraint,
    _extract_percentages,
    _is_refusal_context,
)
from agents.regulatory_rules import get_boundary_constraints_for_agent  # noqa: E402


# --- independent oracle: the original imperative logic ---------------------

_LEV = re.compile(
    r"\b(margin|leverag|short\s*sell|short\s*position|derivative|futures?\b)", re.IGNORECASE
)
_SUBIG = re.compile(r"\b(BB[+-]?|B[+-]?|CCC|CC|C\b|junk|high[- ]yield)\b", re.IGNORECASE)
_COMM = re.compile(
    r"\b(oil|crude|natural\s*gas|copper|platinum|palladium|wheat|corn|soybean|crypto|bitcoin|ethereum)\b",
    re.IGNORECASE,
)
_ESG = (
    "esg", "environmental", "social responsibility", "governance",
    "sustainable", "sustainability", "responsible investing",
    "carbon", "emission", "climate", "ethical", "socially responsible",
    "green bond", "impact invest", "corporate responsibility",
)
_LADDER = (
    "ladder", "laddered", "stagger", "spread maturit",
    "maturity structure", "maturity schedule", "maturity bucket",
    "rolling maturit", "bond maturit", "diversif", "spread across",
    "year treasur", "year bond", "short-term", "medium-term", "long-term",
)
_INFLATION = (
    "inflation", "cpi", "purchasing power", "price stability", "real return",
    "hedge against", "store of value", "safe haven", "monetary policy",
    "currency debasement", "cost of living", "price increase",
    "correlat", "inverse", "protect",
)
_NEG = "Found term '{t}' but negation_context_detected — agent is declining/warning, not recommending"


def _forbidden(text, rx, rule, rule_id, found, clean, basis, neg_aware):
    m = rx.search(text)
    negated = neg_aware and m is not None and _is_refusal_context(text, m)
    violation = m is not None and not negated
    if negated:
        detail = _NEG.format(t=m.group())
    elif violation:
        detail = found.format(t=m.group())
    else:
        detail = clean
    return RuleResult(rule=rule, rule_id=rule_id, source="deterministic",
                      passed=not violation, detail=detail, regulatory_basis=basis)


def oracle_stocks(payload):
    a = payload.get("analysis", "")
    low = a.lower()
    m = get_manifest("stocks")
    out = [_forbidden(
        a, _LEV, "No margin trading, short selling, or leveraged equity products",
        "MANIFEST_STOCKS_NO_LEVERAGE", "Found forbidden term: '{t}'",
        "No leverage terms found", "AgentManifest.stocks", True)]
    over = [p for p in _extract_percentages(a) if p > m.risk_parameters["max_single_position"]]
    out.append(RuleResult(
        rule="Maximum 10% allocation to any single equity position",
        rule_id="MANIFEST_STOCKS_MAX_POSITION", source="deterministic",
        passed=len(over) == 0,
        detail=f"Positions exceeding limit: {[f'{p*100:.1f}%' for p in over]}" if over else "All within limit",
        regulatory_basis="AgentManifest.stocks"))
    esg = any(t in low for t in _ESG)
    out.append(RuleResult(
        rule="ESG screening required: must flag ESG concerns for any new position",
        rule_id="MANIFEST_STOCKS_ESG", source="deterministic", passed=esg,
        detail="ESG screening present" if esg else "No ESG screening language found in analysis",
        regulatory_basis="AgentManifest.stocks"))
    lc = re.search(r"\b(mid[- ]?cap|small[- ]?cap|micro[- ]?cap|penny stock|otc)\b", low)
    out.append(RuleResult(
        rule="Large-cap equities only: market capitalization must exceed $10 billion",
        rule_id="MANIFEST_STOCKS_LARGECAP", source="deterministic", passed=lc is None,
        detail=f"Found non-large-cap reference: '{lc.group()}'" if lc else "No non-large-cap references",
        regulatory_basis="AgentManifest.stocks"))
    return out


def oracle_bonds(payload):
    a = payload.get("analysis", "")
    low = a.lower()
    m = get_manifest("bonds")
    out = [_forbidden(
        a, _SUBIG, "Investment grade only: minimum credit rating BBB+",
        "MANIFEST_BONDS_IG_ONLY", "Found sub-investment-grade reference: '{t}'",
        "No sub-investment-grade references", "AgentManifest.bonds", False)]
    dm = re.findall(r"(\d+(?:\.\d+)?)\s*(?:year|yr)", a, re.IGNORECASE)
    over_d = [float(d) for d in dm if float(d) > m.risk_parameters["max_duration_years"]]
    out.append(RuleResult(
        rule="Portfolio duration must remain below 10 years",
        rule_id="MANIFEST_BONDS_MAX_DURATION", source="deterministic", passed=len(over_d) == 0,
        detail=f"Durations exceeding limit: {over_d}" if over_d else "All within limit",
        regulatory_basis="AgentManifest.bonds"))
    over_b = [p for p in _extract_percentages(a) if p > m.risk_parameters["max_single_maturity_bucket"]]
    out.append(RuleResult(
        rule="No more than 30% maturing in any single year",
        rule_id="MANIFEST_BONDS_LADDER", source="deterministic", passed=len(over_b) == 0,
        detail=f"Buckets exceeding limit: {[f'{p*100:.1f}%' for p in over_b]}" if over_b else "All within limit",
        regulatory_basis="AgentManifest.bonds"))
    em = re.search(r"\b(emerging market|em debt|frontier market|developing countr)", low)
    out.append(RuleResult(
        rule="No emerging market sovereign or corporate debt",
        rule_id="MANIFEST_BONDS_NO_EM", source="deterministic", passed=em is None,
        detail=f"Found emerging market reference: '{em.group()}'" if em else "No emerging market references",
        regulatory_basis="AgentManifest.bonds"))
    lad = any(t in low for t in _LADDER)
    out.append(RuleResult(
        rule="Laddered maturity structure required",
        rule_id="MANIFEST_BONDS_LADDER", source="deterministic", passed=lad,
        detail="Maturity ladder structure discussed" if lad else "No laddered maturity language found in analysis",
        regulatory_basis="AgentManifest.bonds"))
    return out


def oracle_materials(payload):
    a = payload.get("analysis", "")
    low = a.lower()
    m = get_manifest("materials")
    out = [_forbidden(
        a, _COMM, "Direct exposure permitted for Gold and Silver only",
        "MANIFEST_MATERIALS_APPROVED", "Found non-approved commodity: '{t}'",
        "Only approved commodities referenced", "AgentManifest.materials", True)]
    over = [p for p in _extract_percentages(a) if p > m.risk_parameters["max_total_allocation"]]
    out.append(RuleResult(
        rule="Maximum 15% of total portfolio in raw materials",
        rule_id="MANIFEST_MATERIALS_MAX_ALLOC", source="deterministic", passed=len(over) == 0,
        detail=f"Allocations exceeding limit: {[f'{p*100:.1f}%' for p in over]}" if over else "All within limit",
        regulatory_basis="AgentManifest.materials"))
    out.append(_forbidden(
        a, _LEV, "No leveraged commodity ETFs or futures contracts",
        "MANIFEST_MATERIALS_NO_LEVERAGE", "Found forbidden term: '{t}'",
        "No leverage terms found", "AgentManifest.materials", True))
    inf = any(t in low for t in _INFLATION)
    out.append(RuleResult(
        rule="Must provide inflation correlation rationale for every recommendation",
        rule_id="MANIFEST_MATERIALS_INFLATION", source="deterministic", passed=inf,
        detail="Inflation rationale present" if inf else "No inflation rationale found in analysis",
        regulatory_basis="AgentManifest.materials"))
    return out


def oracle_central(payload):
    rec = str(payload.get("final_recommendation", ""))
    over = [p for p in _extract_percentages(rec) if p > CENTRAL_MANIFEST.risk_parameters["max_single_asset_class"]]
    return [RuleResult(
        rule="Maximum 40% allocation to any single asset class",
        rule_id="MANIFEST_CENTRAL_MAX_ASSET_CLASS", source="deterministic", passed=len(over) == 0,
        detail=f"Asset class allocations exceeding limit: {[f'{p*100:.1f}%' for p in over]}" if over else "All within limit",
        regulatory_basis="AgentManifest.central")]


# --- payload batteries -----------------------------------------------------

STOCKS_PAYLOADS = [
    {"analysis": "We favour large-cap names with strong ESG profiles, allocating 8% to each."},
    {"analysis": "Allocate 15% to a single equity position."},
    {"analysis": "Use margin to buy 5% positions after ESG screening."},
    {"analysis": "We cannot use margin or futures here. ESG screening applied, 5% positions."},
    {"analysis": "Consider small-cap value at 5% each, ESG reviewed."},
    {"analysis": "Reduced from 33% to 9% per name, ESG considered."},
    {"analysis": ""},
    {"analysis": "Buy 12% of one name; also short selling ideas; no sustainability mention."},
]
BONDS_PAYLOADS = [
    {"analysis": "Investment grade only, laddered maturity across 3, 5 and 7 year bonds, max 20% per year."},
    {"analysis": "Add some high-yield BB rated corporate debt."},
    {"analysis": "Target a portfolio duration of 12 years with a laddered structure."},
    {"analysis": "Put 40% maturing in a single year."},
    {"analysis": "Emerging market sovereign debt looks attractive, laddered."},
    {"analysis": ""},
    {"analysis": "BBB+ names, duration 6 years, spread across maturities, 25% per bucket."},
]
MATERIALS_PAYLOADS = [
    {"analysis": "Gold at 10% as a hedge against inflation."},
    {"analysis": "Add oil exposure at 5% for inflation protection."},
    {"analysis": "We do not recommend oil or futures; gold only at 10%, hedge against inflation."},
    {"analysis": "Allocate 20% to gold and silver as an inflation hedge."},
    {"analysis": "Use futures on gold at 5%, inflation hedge."},
    {"analysis": "Gold at 5%."},
    {"analysis": ""},
]
SYNTHESIS_PAYLOADS = [
    {"final_recommendation": "Allocate 50% to equities."},
    {"final_recommendation": "A balanced 30/30/40 split across the classes."},
    {"final_recommendation": ""},
    {"final_recommendation": "Reduced from 45% to 35% in equities."},
]


failures = 0


def _compare(label, oracle_list, new_list):
    global failures
    a = [r.model_dump() for r in oracle_list]
    b = [r.model_dump() for r in new_list]
    if a != b:
        failures += 1
        print(f"MISMATCH [{label}]")
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                print(f"  idx {i}:\n    oracle: {x}\n    new:    {y}")
        if len(a) != len(b):
            print(f"  length differs: oracle={len(a)} new={len(b)}")


central_bc = get_boundary_constraints_for_agent("central")[0]
for i, pl in enumerate(STOCKS_PAYLOADS):
    _compare(f"stocks[{i}]", oracle_stocks(pl), _check_boundary_constraints("stocks", pl))
for i, pl in enumerate(BONDS_PAYLOADS):
    _compare(f"bonds[{i}]", oracle_bonds(pl), _check_boundary_constraints("bonds", pl))
for i, pl in enumerate(MATERIALS_PAYLOADS):
    _compare(f"materials[{i}]", oracle_materials(pl), _check_boundary_constraints("materials", pl))
for i, pl in enumerate(SYNTHESIS_PAYLOADS):
    _compare(f"central[{i}]", oracle_central(pl), [_evaluate_boundary_constraint(central_bc, pl, CENTRAL_MANIFEST)])


if failures:
    print(f"\n{failures} mismatch group(s) — interpreter is NOT equivalent to the oracle.")
    sys.exit(1)
print("All boundary-constraint evaluations match the independent oracle.")
