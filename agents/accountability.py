"""Accountability note as a projection of the Accountability Trace (ROADMAP 4): generated from the log and the verdicts, not written by the model."""

from __future__ import annotations

from typing import Any

from mcp.logger import MCPMessage


def compliance_history(agent_ids: list[str], messages: list[MCPMessage], orchestrator_id: str) -> list[str]:
    """One line per checkpoint and consulted agent, with the complete revision history read from the log (Amendment 2, Issues 1 and 6)."""
    lines: list[str] = []

    def _events(target: str) -> list[MCPMessage]:
        wanted = {f"compliance.reject.{target}", f"compliance.approve.{target}", f"compliance.block.{target}"}
        return [m for m in messages if m.method in wanted]

    # Routing checkpoint: verdicts target the orchestrator with checkpoint "routing".
    routing = [m for m in _events(orchestrator_id) if m.payload.get("checkpoint") == "routing"]
    if routing:
        rejected = [m for m in routing if m.method.startswith("compliance.reject.")]
        final = routing[-1]
        if final.method.startswith("compliance.approve."):
            lines.append("routing: approved" + (f" after {len(rejected)} revision(s)" if rejected else " on first attempt"))
        else:
            lines.append(f"routing: forced_block, violated rules: {final.payload.get('violated_rules', [])}")

    for agent_id in agent_ids:
        events = [m for m in _events(agent_id) if m.payload.get("checkpoint", "analysis") == "analysis"]
        if not events:
            lines.append(f"{agent_id}: no compliance verdict recorded")
            continue
        rejections = [m for m in events if m.method.startswith("compliance.reject.")]
        blocked = any(m.method.startswith("compliance.block.") for m in events)
        approved = any(m.method.startswith("compliance.approve.") for m in events)
        attempts = "; ".join(
            f"attempt {i} rejected on {m.payload.get('violated_rules', [])}"
            for i, m in enumerate(rejections, start=1)
        )
        all_rules = sorted({r for m in rejections for r in (m.payload.get("violated_rules") or [])})
        if blocked:
            lines.append(f"{agent_id}: BLOCKED after {len(rejections) - 1 if rejections else 0} revision(s), violated rules: {all_rules} ({attempts})")
        elif approved and not rejections:
            lines.append(f"{agent_id}: approved on first attempt")
        elif approved:
            lines.append(f"{agent_id}: approved after {len(rejections)} revision(s), violated rules: {all_rules} ({attempts})")
        else:
            lines.append(f"{agent_id}: rejected, violated rules: {all_rules}")
    return lines


def build_accountability_note(
    session_id: str,
    principal_id: str,
    agents_consulted: list[str],
    agents_blocked: list[str],
    history: list[str],
    constraints_checked: int,
    violations: list[str],
    state_snapshot: dict[str, Any] | None,
    timestamp: str,
    domain_id: str,
) -> str:
    """Render the note from trace facts only; every field the ER 2026 evaluation looks for is present by construction."""
    parts = [
        f"Session: {session_id}",
        f"Principal: {principal_id}",
        f"Domain: {domain_id}",
        f"Agents consulted: {agents_consulted}",
        "Compliance history: " + ("; ".join(history) if history else "none"),
        f"Constraints checked: {constraints_checked} rule evaluations across all checkpoints",
        "Violations: " + ("; ".join(violations) if violations else "none"),
        f"Blocked: {agents_blocked if agents_blocked else 'none'}",
    ]
    if state_snapshot:
        parts.append(f"Session state: {state_snapshot.get('label')} (current {state_snapshot.get('current')}, target {state_snapshot.get('target')})")
    parts.append(f"Generated: {timestamp}")
    return " | ".join(parts)
