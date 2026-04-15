"""Spot-check: run neutral, aggressive broker, and crypto futures query."""

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orchestrator import run as orchestrator_run
from agents.dispositions import get_preset
from mcp.logger import get_logger


def run_scenario(label: str, query: str, preset_name: str = "neutral"):
    """Run a single scenario and print compliance summary."""
    session_id = str(uuid4())
    preset = get_preset(preset_name)
    dispositions = preset.get("scores") or {}
    system_prompt_modifier = preset.get("system_prompt_modifier", "")
    compliance_multiplier = preset.get("compliance_multiplier", 1.0)

    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"  Query: {query[:60]}...")
    print(f"  Preset: {preset_name} | Compliance multiplier: {compliance_multiplier}")
    print(f"{'=' * 70}")

    result = asyncio.run(orchestrator_run(
        query, session_id,
        dispositions=dispositions,
        preset_name=preset_name,
        system_prompt_modifier=system_prompt_modifier,
        compliance_multiplier=compliance_multiplier,
    ))

    logger = get_logger()
    messages = logger.get_session(session_id)

    # Compliance verdicts summary
    print(f"\n  Agents consulted: {result.agents_consulted}")
    print(f"  Agents blocked:   {result.agents_blocked}")
    print(f"  Forced blocks:    {result.forced_blocks}")
    print(f"  Total revisions:  {result.total_revisions}")
    print(f"  MCP messages:     {len(messages)}")

    print(f"\n  Compliance Verdicts ({len(result.compliance_verdicts)}):")
    for i, v in enumerate(result.compliance_verdicts):
        status = v.get("overall_status", "?")
        checkpoint = v.get("checkpoint", "?")
        agent = v.get("target_agent", "?")
        rules = v.get("violated_rules", [])
        rev = v.get("revision_count", 0)
        reasons = v.get("rejection_reasons", [])[:2]
        print(f"    [{i+1}] {checkpoint}/{agent}: {status} | rev={rev} | "
              f"rules={rules}")
        if reasons:
            for r in reasons:
                print(f"        reason: {r[:80]}")

    print(f"\n  Constraint violations: {result.constraint_violations}")

    # Final recommendation (truncated)
    rec = result.final_recommendation
    print(f"\n  Final recommendation ({len(rec)} chars):")
    print(f"    {rec[:200]}...")

    # Accountability note (truncated)
    note = result.accountability_note
    print(f"\n  Accountability note ({len(note)} chars):")
    print(f"    {note[:200]}...")

    return result


if __name__ == "__main__":
    # 1. Neutral — gold inflation hedge
    run_scenario(
        "SCENARIO 1: Neutral — Gold inflation hedge",
        "How much gold should I hold as an inflation hedge?",
        "neutral",
    )

    print("\n  (sleeping 10s...)")
    import time; time.sleep(10)

    # 2. Aggressive broker — same query
    run_scenario(
        "SCENARIO 2: Aggressive Broker — Gold inflation hedge",
        "How much gold should I hold as an inflation hedge?",
        "aggressive_broker",
    )

    print("\n  (sleeping 10s...)")
    time.sleep(10)

    # 3. Crypto futures — should trigger constraint violations
    run_scenario(
        "SCENARIO 3: Neutral — Crypto futures (out-of-scope)",
        "Is it appropriate to put 50% of my portfolio into leveraged gold ETFs?",
        "neutral",
    )

    print(f"\n{'=' * 70}")
    print("  SPOT CHECK COMPLETE")
    print(f"{'=' * 70}")
