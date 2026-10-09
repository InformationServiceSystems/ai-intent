"""Aggregate parallel campaigns (run_parallel.py workers) into one table per campaign: dimension means and spread, exposure, integrity.

Usage:  python evaluation/campaign_summary.py PREFIX [PREFIX ...] [--markdown OUT.md]
Each PREFIX names a campaign whose workers wrote evaluation/PREFIX_p{i}_results.json.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent
DIMS = ["ME", "CDA", "ATC", "BVC", "CGP", "DC", "SP"]


def load(prefix: str) -> list[dict]:
    """Every worker's results file of a campaign."""
    return [json.loads(p.read_text()) for p in sorted(ROOT.glob(f"{prefix}_p*_results.json"))]


def summarise(prefix: str) -> dict:
    """Per-dimension mean, standard deviation and range of the run percentages, plus case-level and integrity counts."""
    runs = load(prefix)
    out: dict = {"prefix": prefix, "runs": len(runs), "domain": runs[0].get("domain") if runs else None,
                 "model": runs[0].get("model") if runs else None, "dims": {}}
    for d in DIMS:
        pcts = [r["dimension_summary"][d]["pct"] for r in runs if r["dimension_summary"].get(d, {}).get("max")]
        if pcts:
            out["dims"][d] = {"mean": round(statistics.mean(pcts), 1),
                              "std": round(statistics.stdev(pcts), 1) if len(pcts) > 1 else 0.0,
                              "min": min(pcts), "max": max(pcts)}
    cases = [c for r in runs for c in r["results"]]
    out["sessions"] = len(cases)
    out["cases_passed"] = sum(1 for c in cases if c["pass"])
    out["integrity_ok"] = sum(1 for c in cases if (c.get("integrity") or {}).get("all_passed"))
    out["forced_blocks"] = sum(c.get("forced_blocks_actual", 0) for c in cases)
    out["exceptions"] = sum(1 for c in cases if str(c.get("notes", "")).startswith("Exception"))
    ex = [r.get("cda_exposure") or {} for r in runs]
    exp = sum(e.get("expected", 0) for e in ex)
    prop = sum(e.get("proposed", 0) for e in ex)
    out["exposure"] = {"expected": exp, "proposed": prop, "caught_first": sum(e.get("caught_first", 0) for e in ex),
                       "pct": round(prop / exp * 100, 1) if exp else 0.0}
    cc = []
    for r in runs:
        c = r.get("cda_conditional")
        if c is None:
            from evaluation.runner import cda_conditional
            c = cda_conditional(r["results"])
        if c["cases"]:
            cc.append(c["pct"])
    out["cda_conditional"] = {"mean": round(statistics.mean(cc), 1) if cc else None,
                              "std": round(statistics.stdev(cc), 1) if len(cc) > 1 else 0.0,
                              "cases": sum((r.get("cda_conditional") or {}).get("cases", 0) for r in runs)}
    out["mean_duration_s"] = round(statistics.mean(c.get("duration_s", 0) for c in cases), 1) if cases else 0
    return out


def markdown(summaries: list[dict]) -> str:
    """One table of dimension means (± std) and one of counts."""
    lines = ["| Campaign | Model | Domain | Runs | " + " | ".join(DIMS) + " | CDA given exposure |",
             "|---|---|---|---|" + "---|" * len(DIMS) + "---|"]
    for s in summaries:
        cells = [f"{s['dims'][d]['mean']} ± {s['dims'][d]['std']}" if d in s["dims"] else "—" for d in DIMS]
        cc = s["cda_conditional"]
        cells.append(f"{cc['mean']} ± {cc['std']}" if cc["mean"] is not None else "—")
        lines.append(f"| {s['prefix']} | {s['model']} | {s['domain']} | {s['runs']} | " + " | ".join(cells) + " |")
    lines += ["", "| Campaign | Sessions | Cases passed | Integrity ok | Forced blocks | Exceptions | CDA exposure | Mean s/case |",
              "|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        e = s["exposure"]
        lines.append(f"| {s['prefix']} | {s['sessions']} | {s['cases_passed']} | {s['integrity_ok']} | {s['forced_blocks']} | "
                     f"{s['exceptions']} | {e['proposed']} of {e['expected']} ({e['pct']} %), {e['caught_first']} on attempt 1 | {s['mean_duration_s']} |")
    return "\n".join(lines)


def main() -> int:
    """Print (and optionally write) the campaign tables."""
    args = sys.argv[1:]
    out_path = None
    if "--markdown" in args:
        out_path = args[args.index("--markdown") + 1]
        args = [a for a in args if a not in ("--markdown", out_path)]
    summaries = [summarise(p) for p in args]
    md = markdown(summaries)
    print(md)
    if out_path:
        Path(out_path).write_text(md + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
