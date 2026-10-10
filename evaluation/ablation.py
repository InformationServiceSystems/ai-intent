"""Prompt-only ablation: how many rule-violating messages reach the principal with and without the gate.

The enforce arm is a campaign run as usual; the observe arm is the same campaign with
AI_INTENT_GATE_MODE=observe, in which the gate evaluates and logs every message but revises and blocks
nothing, so the Mandates act only through the prompts and the derived response schemas. For every session
the delivered messages are taken from the log: per specialist the last evaluated response unless the
specialist was blocked, and the last synthesis. A delivered message violates a Mandate if the gate's
logged verdict rejects it, and, independently, if the SHACL oracle (evaluation/oracle_agreement.py)
finds a violated shape on it. Only block-severity rules count (a warn rule records an obligation to flag,
it does not stop delivery), and a declined response (out_of_scope) recommends nothing, as on the gate's
decline path. A synthesis that exhausted its retries is counted as delivered, since the orchestrator
returns it.

Usage:  python evaluation/ablation.py --enforce fin_ --observe abl_ [--markdown OUT.md] [--json OUT.json]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

from rdflib import Graph

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from agents.domain import load_domain  # noqa: E402
from evaluation.oracle_agreement import EX, RULE_FIELDS, _field_present, oracle_violations, render_response  # noqa: E402

_VERDICT = re.compile(r"^compliance\.(approve|reject)\.[^.]+$")


def delivered(log: list[dict]) -> list[tuple[dict, dict]]:
    """The (verdict, message) pairs for the messages the session delivered: last analysis per unblocked agent, last synthesis."""
    by_id = {m["id"]: m for m in log}
    blocked = {m["method"].split(".", 2)[2] for m in log if m["method"].startswith("compliance.block.")}
    last: dict[tuple[str, str], tuple[dict, dict]] = {}
    for m in log:
        if not _VERDICT.match(m["method"]):
            continue
        verdict = m["payload"]
        checkpoint = verdict.get("checkpoint")
        action = by_id.get(verdict.get("message_id"))
        if checkpoint not in ("analysis", "synthesis") or action is None:
            continue
        last[(checkpoint, verdict.get("target_agent", ""))] = (verdict, action)
    return [v for (cp, agent), v in last.items() if cp == "synthesis" or agent not in blocked]


_DOMAINS: dict[str, object] = {}


def blocking(rule_id: str, domain_id: str) -> bool:
    """Whether the rule has block severity in the domain's registry."""
    if domain_id not in _DOMAINS:
        _DOMAINS[domain_id] = load_domain(domain_id)
    rule = _DOMAINS[domain_id].rule(rule_id)  # type: ignore[attr-defined]
    return rule is None or rule.severity == "block"


def collect(prefix: str) -> tuple[list[dict], Graph]:
    """One row per delivered message of the arm, with the gate's verdict, and the oracle's data graph."""
    g = Graph()
    rows: list[dict] = []
    for f in sorted((ROOT / "sessions").glob(f"{prefix}*.json")):
        session = json.loads(f.read_text())
        log = session["mcp_log"]
        state = next((m["payload"] for m in log if m["method"] == "state.snapshot"), None)
        campaign = re.sub(r"_p\d+$", "", f.stem.split("_TC-")[0].split("_PC-")[0].split("_CL-")[0])
        for verdict, action in delivered(log):
            node = EX[f"r/{f.stem}/{action['id']}"]
            payload = action["payload"]
            declined = payload.get("out_of_scope") is True
            typed = not declined and any(_field_present(payload, field) for field in set(RULE_FIELDS.values()))
            if typed:
                render_response(g, node, action["from_agent"], payload, state)
            rows.append({"campaign": campaign, "key": campaign[len(prefix):], "session": f.stem, "tc_id": session.get("tc_id"),
                         "domain": session.get("domain") or "finance",
                         "gate_mode": session.get("gate_mode", "enforce"), "checkpoint": verdict.get("checkpoint"),
                         "agent": action["from_agent"], "response": str(node), "gate_violation": not declined and not verdict.get("approved", True),
                         "gate_rules": verdict.get("violated_rules") or []})
    return rows, g


def arm(prefix: str) -> dict[str, dict]:
    """Counts per campaign key (model and domain) for one arm."""
    rows, g = collect(prefix)
    violated = collections.defaultdict(set)
    for node, rule in oracle_violations(g):
        violated[node].add(rule)
    out: dict[str, dict] = {}
    for key in sorted({r["key"] for r in rows}):
        mine = [r for r in rows if r["key"] == key]
        sessions = {r["session"] for r in mine}
        for r in mine:
            r["oracle_rules"] = sorted(x for x in violated.get(r["response"], ()) if blocking(x, r["domain"]))
        gate_bad = [r for r in mine if r["gate_violation"]]
        oracle_bad = [r for r in mine if r["oracle_rules"]]
        out[key] = {
            "gate_modes": sorted({r["gate_mode"] for r in mine}),
            "sessions": len(sessions), "delivered": len(mine),
            "delivered_gate_violation": len(gate_bad), "delivered_oracle_violation": len(oracle_bad),
            "sessions_gate_violation": len({r["session"] for r in gate_bad}),
            "sessions_oracle_violation": len({r["session"] for r in oracle_bad}),
            "rules_gate": dict(collections.Counter(x for r in gate_bad for x in r["gate_rules"]).most_common()),
            "rules_oracle": dict(collections.Counter(x for r in oracle_bad for x in r["oracle_rules"]).most_common()),
        }
    return out


def _pct(n: int, d: int) -> str:
    """A count with its percentage of a total."""
    return f"{n} ({n / d * 100:.1f} %)" if d else "–"


def main() -> int:
    """Print the comparison of both arms per model and domain."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--enforce", default="fin_", help="session prefix of the enforce arm")
    parser.add_argument("--observe", default="abl_", help="session prefix of the observe (prompt-only) arm")
    parser.add_argument("--markdown", default=None)
    parser.add_argument("--json", default=str(ROOT / "ablation.json"))
    args = parser.parse_args()
    arms = {"gate": arm(args.enforce), "prompt-only": arm(args.observe)}
    for name, expected in (("gate", "enforce"), ("prompt-only", "observe")):
        wrong = {k: v["gate_modes"] for k, v in arms[name].items() if v["gate_modes"] != [expected]}
        if wrong:
            print(f"warning: {name} arm has sessions not run in {expected} mode: {wrong}")
    lines = ["| Model, domain | Arm | Sessions | Delivered messages | Violating (gate) | Violating (oracle) | Sessions with a violation reaching the principal (gate / oracle) |",
             "|---|---|---|---|---|---|---|"]
    for key in sorted(set(arms["gate"]) | set(arms["prompt-only"])):
        for name in ("gate", "prompt-only"):
            c = arms[name].get(key)
            if c is None:
                continue
            lines.append(f"| {key} | {name} | {c['sessions']} | {c['delivered']} | {_pct(c['delivered_gate_violation'], c['delivered'])} | "
                         f"{_pct(c['delivered_oracle_violation'], c['delivered'])} | "
                         f"{_pct(c['sessions_gate_violation'], c['sessions'])} / {_pct(c['sessions_oracle_violation'], c['sessions'])} |")
    text = "\n".join(lines)
    print(text)
    Path(args.json).write_text(json.dumps(arms, indent=1))
    if args.markdown:
        Path(args.markdown).write_text("# Prompt-only ablation\n\n" + (__doc__ or "").split("\n\n")[1] + "\n\n" + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
