"""Launch N independent single-run evaluation workers against one Ollama endpoint, each with its own database."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    """Start the workers, wait for all of them, and report exit codes."""
    parser = argparse.ArgumentParser(description="parallel evaluation workers")
    parser.add_argument("--workers", type=int, default=10, help="number of independent runs")
    parser.add_argument("--prefix", default="ufo_hpc", help="output prefix; worker i writes {prefix}_p{i}_*")
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11435/v1"))
    parser.add_argument("--dry-run", action="store_true", help="pass --dry-run to every worker")
    parser.add_argument("--stagger", type=float, default=3.0, help="seconds between worker starts")
    args = parser.parse_args()

    logs = ROOT / "evaluation" / "logs"
    logs.mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)

    procs: list[tuple[int, subprocess.Popen]] = []
    for i in range(1, args.workers + 1):
        env = dict(os.environ)
        env["OLLAMA_BASE_URL"] = args.base_url
        env["AI_INTENT_DB"] = str(ROOT / "data" / f"sessions_{args.prefix}_p{i}.db")
        env["PYTHONUNBUFFERED"] = "1"
        cmd = [sys.executable, "evaluation/runner.py", "--runs", "1", "--output-prefix", f"{args.prefix}_p{i}"]
        if args.dry_run:
            cmd.append("--dry-run")
        log = open(logs / f"{args.prefix}_p{i}.log", "w")
        procs.append((i, subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)))
        print(f"worker {i}: pid {procs[-1][1].pid} -> {log.name}")
        time.sleep(args.stagger)

    codes = {}
    for i, p in procs:
        codes[i] = p.wait()
        print(f"worker {i} finished with exit code {codes[i]}")
    failed = [i for i, c in codes.items() if c != 0]
    print(f"{len(procs)} workers done, {len(failed)} failed{': ' + str(failed) if failed else ''}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
