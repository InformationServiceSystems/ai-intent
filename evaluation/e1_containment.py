"""E1: mutate every bounded sub-mandate parameter above its parent bound and confirm containment reports it."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.delegation import check_mandate_containment, containment_map  # noqa: E402
from agents.domain import get_domain  # noqa: E402
from agents.manifests import get_manifest  # noqa: E402

MUTATIONS = [0.0, 0.5, 1.0, 1.5]   # fractions above the parent bound: 0.0 is the boundary itself


def run() -> list[dict]:
    """Return one row per (sub-mandate, parameter, mutation) with the containment outcome."""
    parent = get_manifest(get_domain().orchestrator_id)
    rows = []
    for (agent_id, parameter), parent_parameter in containment_map().items():
        bound = float(parent.risk_parameters[parent_parameter])
        original = float(get_manifest(agent_id).risk_parameters[parameter])
        for frac in [None] + MUTATIONS:
            child = get_manifest(agent_id).model_copy(deep=True)
            value = original if frac is None else round(bound * (1 + frac), 4)
            child.risk_parameters[parameter] = value
            checks = [c for c in check_mandate_containment(parent, child) if c.parameter == parameter]
            contained = checks[0].contained if checks else None
            expected = value <= bound
            rows.append({
                "agent": agent_id, "parameter": parameter, "value": value, "parent_bound": bound,
                "contained": contained, "expected": expected, "correct": contained == expected,
            })
    return rows


def main() -> int:
    """Print the E1 table and exit non-zero if any mutation was misjudged."""
    rows = run()
    print("| Sub-mandate | Parameter | Value | Parent bound | Contained | Correct |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['agent']} | {r['parameter']} | {r['value']:.2f} | {r['parent_bound']:.2f} | {r['contained']} | {'yes' if r['correct'] else 'NO'} |")
    wrong = [r for r in rows if not r["correct"]]
    print(f"\n{len(rows)} cases, {len(wrong)} misjudged")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
