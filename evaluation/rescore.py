"""Re-score persisted campaign sessions with the current scoring functions, without re-running any model.

The persisted session (orchestration result plus MCP log) is the source of truth for the scorers;
the results files are a projection of it. When a scorer changes, this script recomputes every case's
scores from its session file and rewrites the results and report files in place, keeping the run's
timestamp and recording the rescoring in the file. The model-dependent content is untouched.

Usage:  python evaluation/rescore.py PREFIX [PREFIX ...] [--domain NAME]
PREFIX names a single run (evaluation/PREFIX_results.json, as written by runner.py --output-prefix) or a
campaign whose workers wrote evaluation/PREFIX_p{i}_results.json (run_parallel.py). The domain is read
from the results file; --domain is the fallback for files that do not record it.
"""

from __future__ import annotations

import collections
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent


def rescore_file(results_path: Path) -> dict[str, int]:
    """Recompute the scores of every case in one results file from its session files; return the count of changed cells per dimension."""
    data = json.loads(results_path.read_text())
    domain_id = data.get("domain") or os.environ.get("AI_INTENT_DOMAIN") or "finance"
    if os.environ.get("AI_INTENT_DOMAIN") != domain_id:
        os.environ["AI_INTENT_DOMAIN"] = domain_id
    from agents.domain import load_domain, set_domain
    set_domain(load_domain(domain_id))
    from agents.orchestrator import OrchestrationResult
    from mcp.logger import MCPMessage
    from evaluation import runner
    runner.DETERMINISTIC_ROUTING = data.get("routing_mode") == "override"

    cases = {tc["tc_id"]: tc for tc in runner.test_cases()}
    worker_prefix = results_path.name[: -len("results.json")] if results_path.name.endswith("_results.json") else None
    changed: collections.Counter = collections.Counter()
    for entry in data["results"]:
        tc = cases.get(entry["tc_id"])
        stem = f"{worker_prefix}{entry['tc_id']}_{entry['session_id'][:8]}"
        session_file = runner.SESSIONS_DIR / f"{stem}.json"
        if tc is None or not session_file.exists():
            changed["skipped"] += 1
            continue
        session = json.loads(session_file.read_text())
        result = OrchestrationResult.model_validate(session["orchestration_result"])
        messages = [MCPMessage.model_validate(m) for m in session["mcp_log"]]
        scores, cda_notes, sp_notes, ex_notes, am_notes = runner.score_result(tc, result, messages)
        for dim, value in scores.items():
            if entry["scores"].get(dim) != value:
                changed[dim] += 1
        applicable = {k: v for k, v in scores.items() if v is not None}
        entry.update({
            "scores": scores,
            "total": sum(applicable.values()),
            "max_possible": len(applicable) * 2,
            "pass": all(v >= 1 for v in applicable.values()),
            "cda_notes": {k: str(v) if not isinstance(v, (str, list, dict, bool)) else v for k, v in cda_notes.items()} if cda_notes else {},
            "sp_notes": sp_notes, "ex_notes": ex_notes, "am_notes": am_notes,
        })

    dim_summary, pass_thresholds, overall_pass = runner._compute_summary(data["results"])
    data.update({
        "dimension_summary": dim_summary,
        "cda_exposure": runner.cda_exposure(data["results"]),
        "cda_conditional": runner.cda_conditional(data["results"]),
        "pass_thresholds": pass_thresholds,
        "overall_pass": overall_pass,
        "rescored": True,
        "rescored_at": datetime.now(timezone.utc).isoformat(),
    })
    results_path.write_text(json.dumps(data, indent=2, default=str))
    report = runner.generate_report(data["results"], data["run_timestamp"])
    (results_path.parent / results_path.name.replace("results", "report").replace(".json", ".md")).write_text(report)
    return dict(changed)


def rescore_prefix(prefix: str) -> None:
    """Rescore a single run or every worker of a campaign: the current results file and its timestamped copies."""
    total: collections.Counter = collections.Counter()
    single = ROOT / f"{prefix}_results.json"
    targets = [single] if single.exists() else sorted(ROOT.glob(f"{prefix}_p*_results.json"))
    if not targets:
        print(f"{prefix}: no results file")
        return
    for current in targets:
        changed = rescore_file(current)
        total.update(changed)
        worker = current.name[: -len("_results.json")]
        for stamped in ROOT.glob(f"{worker}_results_*_run*.json"):
            # Same sessions, same scores: rewrite the archived copy and its report from the rescored current file.
            archived = json.loads(stamped.read_text())
            fresh = json.loads(current.read_text())
            archived.update({k: fresh[k] for k in ("results", "dimension_summary", "cda_exposure", "cda_conditional", "pass_thresholds", "overall_pass", "rescored", "rescored_at")})
            stamped.write_text(json.dumps(archived, indent=2, default=str))
            (stamped.parent / stamped.name.replace("results", "report").replace(".json", ".md")).write_text(
                runner_report(archived))
    print(f"{prefix}: changed cells {dict(total) or 'none'}")


def runner_report(data: dict) -> str:
    """The runner's report for a results dict."""
    from evaluation import runner
    return runner.generate_report(data["results"], data["run_timestamp"])


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--domain" in args:
        i = args.index("--domain")
        os.environ["AI_INTENT_DOMAIN"] = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(2)
    for prefix in args:
        rescore_prefix(prefix)
