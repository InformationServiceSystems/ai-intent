"""Re-score persisted sessions with the current scoring functions, without calling the model.

Usage:  python evaluation/rescore.py PREFIX [--domain NAME]
Reads evaluation/PREFIX_results.json, reloads every session from evaluation/sessions/PREFIX_*.json,
recomputes the scores and rewrites PREFIX_results.json and PREFIX_report.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.domain import get_domain, load_domain, set_domain  # noqa: E402
from agents.orchestrator import OrchestrationResult  # noqa: E402
from mcp.logger import MCPMessage  # noqa: E402
from evaluation import runner  # noqa: E402

OUT = Path(__file__).parent


def rescore(prefix: str) -> dict:
    """Recompute every case's scores from its persisted session and rewrite the results and the report."""
    results_path = OUT / f"{prefix}_results.json"
    data = json.loads(results_path.read_text())
    cases = {tc["tc_id"]: tc for tc in runner.test_cases(get_domain())}
    for r in data["results"]:
        files = list((OUT / "sessions").glob(f"{prefix}_{r['tc_id']}_{r['session_id'][:8]}.json"))
        if not files:
            print(f"  {r['tc_id']}: no session file, kept as is")
            continue
        session = json.loads(files[0].read_text())
        result = OrchestrationResult(**session["orchestration_result"])
        messages = [MCPMessage(**m) for m in session["mcp_log"]]
        tc = cases[r["tc_id"]]
        scores: dict[str, int | None] = {}
        cda_notes: dict = {}
        sp_notes: dict = {}
        for dim in runner.DIMENSIONS:
            if dim not in tc["dimensions"]:
                scores[dim] = None
            elif dim == "ME":
                scores[dim] = runner.score_me(result, tc)
            elif dim == "CDA":
                if tc.get("expected_rule_ids") and runner.declined_naming_constraint(result, tc):
                    scores[dim], cda_notes = None, {"detail": "not exercised: the agent declined, naming the constraint (scored under ME)"}
                    scores["ME"] = 2
                else:
                    scores[dim], cda_notes = runner.score_cda(result, tc.get("expected_rule_ids", []), messages)
            elif dim == "ATC":
                scores[dim] = runner.score_atc(result, messages)
            elif dim == "DC":
                scores[dim] = runner.score_dc(result, tc, messages)
            elif dim == "BVC":
                scores[dim] = runner.score_bvc(result, messages)
            elif dim == "CGP":
                scores[dim] = runner.score_cgp(result, messages)
            elif dim == "SP":
                if tc.get("expected_state_rule_ids") and runner.declined_naming_constraint(result, tc):
                    scores[dim], sp_notes = None, {"detail": "not exercised: the agent declined, naming the constraint (scored under ME)"}
                    scores["ME"] = 2
                else:
                    scores[dim], sp_notes = runner.score_sp(result, tc)
        applicable = {k: v for k, v in scores.items() if v is not None}
        r.update({
            "scores": scores, "total": sum(applicable.values()), "max_possible": len(applicable) * 2,
            "pass": all(v >= 1 for v in applicable.values()),
            "cda_notes": {k: str(v) if not isinstance(v, (str, list, dict, bool)) else v for k, v in cda_notes.items()} if cda_notes else {},
            "sp_notes": sp_notes, "rescored": True,
        })
        notes = [n for n in str(r.get("notes", "")).split("; ") if n and not n.startswith("MCP messages")]
        if len(messages) > tc.get("max_mcp_messages", 999):
            notes.append(f"MCP messages ({len(messages)}) exceeded max ({tc['max_mcp_messages']})")
        r["notes"] = "; ".join(notes)
        print(f"  {r['tc_id']}: {r['total']}/{r['max_possible']} {'PASS' if r['pass'] else 'FAIL'} {applicable}")
    dim_summary, pass_thresholds, overall = runner._compute_summary(data["results"])
    data.update({"dimension_summary": dim_summary, "pass_thresholds": pass_thresholds, "overall_pass": overall, "rescored": True})
    results_path.write_text(json.dumps(data, indent=2, default=str))
    (OUT / f"{prefix}_report.md").write_text(runner.generate_report(data["results"], data["run_timestamp"]))
    print(f"{prefix}: overall {'PASS' if overall else 'FAIL'}; " + ", ".join(f"{d} {v['pct']}%" for d, v in dim_summary.items() if v["max"]))
    return data


def main() -> int:
    """Parse the prefix and optional domain, then re-score."""
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if "--domain" in args:
        name = args[args.index("--domain") + 1]
        set_domain(load_domain(name))
    rescore(args[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
