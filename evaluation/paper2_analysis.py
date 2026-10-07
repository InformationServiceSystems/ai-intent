"""Aggregate runner results for the follow-up paper: E2 manifestation attribution and E3 integrity pass rates."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.dispositions import DEFAULT_MANIFESTATION_THRESHOLD, get_preset  # noqa: E402
from evaluation.sparql_checks import CHECKS  # noqa: E402

PRESET_BY_TC = {"TC-16": "neutral", "TC-17": "aggressive_broker", "TC-18": "reckless_portfolio", "TC-19": "groupthink"}


def load_runs(prefix: str) -> list[dict]:
    """Load every per-run results file written under the given output prefix."""
    files = sorted(glob.glob(str(Path(__file__).parent / f"{prefix}_results_*_run*.json")))
    return [json.load(open(f)) for f in files]


def e3_table(runs: list[dict]) -> str:
    """Pass rate per integrity check over all test-case sessions of all runs."""
    n = 0
    fails: Counter = Counter()
    triples = []
    for run in runs:
        for r in run["results"]:
            integ = r.get("integrity") or {}
            if "all_passed" not in integ:
                continue
            n += 1
            triples.append(integ.get("triples", 0))
            for c in integ.get("failed", []):
                fails[c] += 1
    lines = [f"Sessions: {n}. Triples per session: min {min(triples) if triples else 0}, "
             f"mean {sum(triples)//n if n else 0}, max {max(triples) if triples else 0}.", "",
             "| Check | Invariant | Failing sessions | Pass rate |", "|---|---|---|---|"]
    for c in CHECKS:
        f = fails[c.check_id]
        lines.append(f"| {c.check_id} | {c.claim} | {f} | {100*(n-f)/n:.1f}% |" if n else f"| {c.check_id} | {c.claim} | - | - |")
    return "\n".join(lines)


def e2_table(runs: list[dict]) -> str:
    """Attribution agreement: do attributed disposition kinds match the preset in force?"""
    rows = []
    per_preset: dict[str, dict] = defaultdict(lambda: {"sessions": 0, "rejections": 0, "attributed": 0,
                                                       "kinds": Counter(), "agree": 0, "total_kinds": 0})
    for run in runs:
        for r in run["results"]:
            preset = PRESET_BY_TC.get(r["tc_id"])
            if preset is None:
                continue
            p = per_preset[preset]
            p["sessions"] += 1
            scores = get_preset(preset)["scores"] or {}
            events = {(m["agent"], tuple(m["rules"])) for m in r.get("manifestations", [])}
            p["attributed"] += len(events)
            p["rejections"] += int(r.get("revisions", 0)) + len(r.get("commitment_breaches", []))
            for m in r.get("manifestations", []):
                p["kinds"][m["kind"]] += 1
                p["total_kinds"] += 1
                degree = getattr(scores.get(m["agent"]), m["kind"], 0.0) if scores.get(m["agent"]) else 0.0
                if degree >= DEFAULT_MANIFESTATION_THRESHOLD:
                    p["agree"] += 1
    lines = ["| Preset | Sessions | Revisions + blocks | Attributed rejection events | Attributions | Agreement with preset | Kinds |",
             "|---|---|---|---|---|---|---|"]
    for preset in ["neutral", "aggressive_broker", "reckless_portfolio", "groupthink"]:
        p = per_preset.get(preset)
        if not p:
            continue
        agree = f"{100*p['agree']/p['total_kinds']:.0f}%" if p["total_kinds"] else "n/a"
        kinds = ", ".join(f"{k} {v}" for k, v in p["kinds"].most_common()) or "none"
        lines.append(f"| {preset} | {p['sessions']} | {p['rejections']} | {p['attributed']} | {p['total_kinds']} | {agree} | {kinds} |")
    lines.append("")
    lines.append("Agreement counts an attribution as correct when the preset in force gives the agent a degree at or "
                 "above the manifestation threshold for the attributed kind. By construction this is 100% unless the "
                 "runner's preset and the attribution disagree; the informative numbers are the zero attributions "
                 "expected under the neutral preset and the kinds distribution under the others.")
    return "\n".join(lines)


def breach_table(runs: list[dict]) -> str:
    """Commitment breaches per test case: how often a block was resolved to an answerable chain."""
    rows: Counter = Counter()
    unresolved = 0
    for run in runs:
        for r in run["results"]:
            for b in r.get("commitment_breaches", []):
                rows[(r["tc_id"], b.get("agent"))] += 1
                if not b.get("answerable_to"):
                    unresolved += 1
    lines = ["| Test case | Agent | Breaches |", "|---|---|---|"]
    for (tc, agent), n in sorted(rows.items()):
        lines.append(f"| {tc} | {agent} | {n} |")
    lines.append("")
    lines.append(f"Breaches without an answerable party: {unresolved}.")
    return "\n".join(lines)


def main() -> None:
    """Write paper2/e2-e3-results.md from the runner's result files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="ufo", help="output prefix used with runner.py --output-prefix")
    parser.add_argument("--out", default=str(Path(__file__).parent.parent / "paper2" / "e2-e3-results.md"))
    args = parser.parse_args()
    runs = load_runs(args.prefix)
    if not runs:
        print(f"no result files for prefix {args.prefix!r}")
        return
    text = "\n\n".join([
        f"# E2 and E3 results (prefix `{args.prefix}`, {len(runs)} run(s))",
        "## E3: integrity checks over fresh sessions", e3_table(runs),
        "## E2: disposition manifestation attribution (TC-16 to TC-19)", e2_table(runs),
        "## Commitment breaches", breach_table(runs),
    ]) + "\n"
    Path(args.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
