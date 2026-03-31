"""Sequence diagram component for visualizing MCP message flow."""

import streamlit as st

from mcp.logger import MCPMessage, get_logger


_DIRECTION_COLORS = {
    "outbound": "#2196F3",     # blue
    "inbound": "#4CAF50",      # green
    "internal": "#FF9800",     # amber
}

_STATUS_OVERRIDE = {
    "error": "#F44336",             # red
    "constraint_violation": "#FF5722",  # orange
}

_ACTOR_ORDER = ["user", "central", "stocks", "bonds", "materials"]
_ACTOR_LABELS = {
    "user": "User",
    "central": "Central\\nOrchestrator",
    "stocks": "Stocks\\nAgent",
    "bonds": "Bonds\\nAgent",
    "materials": "Materials\\nAgent",
}


def _build_sequence_dot(messages: list[MCPMessage]) -> str:
    """Build a Graphviz DOT string representing a sequence diagram."""
    # Determine which actors appear in this session
    actors_seen = set()
    for msg in messages:
        actors_seen.add(msg.from_agent)
        actors_seen.add(msg.to_agent)

    actors = [a for a in _ACTOR_ORDER if a in actors_seen]

    lines = [
        'digraph sequence {',
        '  rankdir=TB;',
        '  node [shape=box, style="filled,rounded", fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=9];',
        '',
    ]

    # Actor header nodes
    for i, actor in enumerate(actors):
        label = _ACTOR_LABELS.get(actor, actor)
        lines.append(f'  actor_{actor} [label="{label}", fillcolor="#E3F2FD", pos="{i * 2},0!"];')

    # Invisible edges to enforce actor ordering
    if len(actors) > 1:
        chain = " -> ".join(f"actor_{a}" for a in actors)
        lines.append(f'  {{ rank=same; {chain} [style=invis]; }}')

    lines.append('')

    # Message nodes and edges
    for idx, msg in enumerate(messages):
        color = _STATUS_OVERRIDE.get(msg.response_status, _DIRECTION_COLORS.get(msg.direction, "#999"))
        label = msg.method
        ts = msg.timestamp.strftime("%H:%M:%S")

        status_marker = ""
        if msg.response_status == "constraint_violation":
            status_marker = " [VIOLATION]"
        elif msg.response_status == "error":
            status_marker = " [ERROR]"

        from_node = f"actor_{msg.from_agent}"
        to_node = f"actor_{msg.to_agent}"

        # For internal messages (from=to), use a self-loop
        if msg.from_agent == msg.to_agent:
            lines.append(f'  msg_{idx} [label="{label}{status_marker}\\n{ts}", shape=note, fillcolor="{color}20", fontcolor="{color}"];')
            lines.append(f'  {from_node} -> msg_{idx} [color="{color}", style=dashed];')
        else:
            lines.append(f'  {from_node} -> {to_node} [label="{label}{status_marker}\\n{ts}", color="{color}", fontcolor="{color}", penwidth=1.5];')

    lines.append('}')
    return '\n'.join(lines)


def render_intent_flow(session_id: str) -> None:
    """Render a sequence diagram of all MCP messages for a session."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    if not messages:
        st.caption("No messages to display.")
        return

    st.caption(f"Message flow: {len(messages)} messages")

    # Render as graphviz
    dot = _build_sequence_dot(messages)
    try:
        st.graphviz_chart(dot, use_container_width=True)
    except Exception:
        # Fallback: render as text-based sequence
        _render_text_sequence(messages)

    # Clickable message detail list below
    st.divider()
    st.markdown("**Message Details:**")
    for i, msg in enumerate(messages):
        icon = {"outbound": "->", "inbound": "<-", "internal": "**"}
        direction_icon = icon.get(msg.direction, "--")
        status_color = "red" if msg.response_status in ("error", "constraint_violation") else "green" if msg.response_status == "ok" else "gray"

        with st.expander(f"{i+1}. {msg.method} ({msg.from_agent} {direction_icon} {msg.to_agent}) — :{status_color}[{msg.response_status}]"):
            st.markdown(f"**Direction:** {msg.direction}")
            st.markdown(f"**Time:** {msg.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
            if msg.constraint_flags:
                st.markdown(f":red[**Constraint Flags:** {', '.join(msg.constraint_flags)}]")
            st.json(msg.payload)


def _render_text_sequence(messages: list[MCPMessage]) -> None:
    """Fallback text-based sequence rendering."""
    for msg in messages:
        ts = msg.timestamp.strftime("%H:%M:%S")
        arrow = {"outbound": "-->", "inbound": "<--", "internal": "---"}
        a = arrow.get(msg.direction, "---")
        status = f" [{msg.response_status}]" if msg.response_status != "ok" else ""
        st.code(f"[{ts}] {msg.from_agent} {a} {msg.to_agent} : {msg.method}{status}")
