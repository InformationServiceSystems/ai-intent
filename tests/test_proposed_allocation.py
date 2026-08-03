"""Tests for the structured `proposed_allocation` path in the boundary interpreter.

φ reads the structured field directly when present (with percent/fraction
normalization), and falls back to prose extraction when it is absent or empty —
so behavior is unchanged for the existing evaluation when no allocations are
supplied.

Runnable without pytest:  python tests/test_proposed_allocation.py
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

from agents.manifests import get_manifest  # noqa: E402
from agents.compliance import _evaluate_boundary_constraint, _coerce_allocations  # noqa: E402
from agents.regulatory_rules import get_boundary_constraints_for_agent  # noqa: E402


def _bc(agent, rule_id):
    return next(c for c in get_boundary_constraints_for_agent(agent) if c.rule_id == rule_id)


failures = 0


def check(label, cond):
    global failures
    if not cond:
        failures += 1
        print(f"FAIL: {label}")
    else:
        print(f"ok:   {label}")


def evalc(agent, rule_id, payload):
    return _evaluate_boundary_constraint(_bc(agent, rule_id), payload, get_manifest(agent))


# --- normalization helper --------------------------------------------------
check("coerce: absent -> None", _coerce_allocations(None) is None)
check("coerce: empty -> None", _coerce_allocations([]) is None)
check("coerce: fractions kept", _coerce_allocations([0.1, 0.05]) == [0.1, 0.05])
check("coerce: percents normalized", _coerce_allocations([10, 5]) == [0.10, 0.05])
check("coerce: string percents", _coerce_allocations(["18%"]) == [0.18])
check("coerce: junk skipped", _coerce_allocations(["x", 0.1]) == [0.1])

# --- materials MAX_ALLOC (bound 0.15) -------------------------------------
r = evalc("materials", "MANIFEST_MATERIALS_MAX_ALLOC", {"analysis": "gold", "proposed_allocation": [0.10, 0.05]})
check("materials within (fractions)", r.passed and r.detail == "All within limit")

r = evalc("materials", "MANIFEST_MATERIALS_MAX_ALLOC", {"analysis": "gold", "proposed_allocation": [0.20]})
check("materials over (fractions)", (not r.passed) and r.detail == "Allocations exceeding limit: ['20.0%']")

r = evalc("materials", "MANIFEST_MATERIALS_MAX_ALLOC", {"analysis": "gold", "proposed_allocation": [20]})
check("materials over (percent-form normalized)", not r.passed and r.detail == "Allocations exceeding limit: ['20.0%']")

# structured overrides prose: prose says 50% but structured says 10% -> passes
r = evalc("materials", "MANIFEST_MATERIALS_MAX_ALLOC", {"analysis": "allocate 50% to gold", "proposed_allocation": [0.10]})
check("materials structured overrides prose (pass)", r.passed)

# fallback: empty structured -> prose regex catches 20%
r = evalc("materials", "MANIFEST_MATERIALS_MAX_ALLOC", {"analysis": "allocate 20% to gold", "proposed_allocation": []})
check("materials empty -> prose fallback (over)", not r.passed)

# fallback: absent structured -> prose regex
r = evalc("materials", "MANIFEST_MATERIALS_MAX_ALLOC", {"analysis": "allocate 20% to gold"})
check("materials absent -> prose fallback (over)", not r.passed)

# --- stocks MAX_POSITION (bound 0.10) -------------------------------------
r = evalc("stocks", "MANIFEST_STOCKS_MAX_POSITION", {"analysis": "buy", "proposed_allocation": [0.08]})
check("stocks within", r.passed)

r = evalc("stocks", "MANIFEST_STOCKS_MAX_POSITION", {"analysis": "buy", "proposed_allocation": [0.12]})
check("stocks over", (not r.passed) and r.detail == "Positions exceeding limit: ['12.0%']")

# --- duration is a scalar, NOT an allocation: proposed_allocation ignored ---
r = evalc("bonds", "MANIFEST_BONDS_MAX_DURATION", {"analysis": "duration 12 years", "proposed_allocation": [0.5]})
check("duration uses prose, ignores proposed_allocation", (not r.passed) and r.detail == "Durations exceeding limit: [12.0]")


if failures:
    print(f"\n{failures} failure(s).")
    sys.exit(1)
print("\nAll proposed_allocation tests passed.")
