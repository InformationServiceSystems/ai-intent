"""Find sessions whose log contains a model or connection error, so that they are excluded or re-run before scoring.

A forced block replaces an error result in the orchestration result, so the check reads the log itself:
every `{agent}.result` with status `error`, and every routing or synthesis entry that records a model error.

Usage:  python evaluation/session_health.py PREFIX [PREFIX ...]
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def session_errors(log: list[dict]) -> list[str]:
    """Error descriptions in one session log."""
    out = []
    for m in log:
        method, status, payload = m["method"], m.get("response_status"), m.get("payload") or {}
        if method.endswith(".result") and (status == "error" or str(payload.get("analysis", "")).startswith("Error:")):
            out.append(f"{method}: {str(payload.get('analysis', ''))[:80]}")
        elif method == "intent.route" and str(payload.get("routing_rationale", "")).startswith("Routing error"):
            out.append(f"intent.route: {payload.get('routing_rationale', '')[:80]}")
        elif method == "intent.synthesize" and payload.get("synthesis_error"):
            out.append(f"intent.synthesize: {str(payload.get('synthesis_error'))[:80]}")
    return out


def infrastructure_errors(errors: list[str]) -> list[str]:
    """Errors caused by the serving infrastructure (connection, timeout), as opposed to malformed model output."""
    return [e for e in errors if any(k in e.lower() for k in ("connection", "timed out", "timeout", "refused"))]


def scan(prefix: str) -> dict:
    """Sessions of a prefix with errors, by test case."""
    bad: dict[str, list[str]] = {}
    files = sorted((ROOT / "sessions").glob(f"{prefix}*.json"))
    for f in files:
        errs = session_errors(json.loads(f.read_text())["mcp_log"])
        if errs:
            bad[f.stem] = errs
    infra = {k: v for k, v in bad.items() if infrastructure_errors(v)}
    return {"prefix": prefix, "sessions": len(files), "with_errors": len(bad), "with_infrastructure_errors": len(infra), "files": bad}


def main() -> int:
    """Print the count of affected sessions per prefix and a breakdown by error kind."""
    total_bad = 0
    for prefix in sys.argv[1:]:
        r = scan(prefix)
        kinds = collections.Counter(e.split(":")[0] + ": " + e.split(": ", 1)[1][:30] for errs in r["files"].values() for e in errs)
        print(f"{prefix}: {r['with_errors']} of {r['sessions']} sessions with errors, {r['with_infrastructure_errors']} from the infrastructure {dict(kinds.most_common(3))}")
        total_bad += r["with_infrastructure_errors"]
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())
